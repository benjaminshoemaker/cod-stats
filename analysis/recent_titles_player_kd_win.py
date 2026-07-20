#!/usr/bin/env python3
"""Build the local BO7 major respawn player K/D versus map-win report.

The source pull is intentionally isolated under analysis/. It does not alter
the committed production PlayerStats snapshots or generated site data.
"""
import html
import json
import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from build_data import ASOF
from scripts import fetch_source


GAME = "Black Ops 7"
GAMES = (GAME,)
CACHE_PATH = ROOT / "analysis/recent_titles_player_kd_win_stats.json"
PROGRESS_PATH = ROOT / "analysis/recent_titles_player_kd_win_stats.progress.json"
OUT_PATH = ROOT / "analysis/recent_titles_player_kd_win.html"
EVENTS_PATH = ROOT / "player_stats_participants.events.json"
PARTICIPANT_STATS_PATH = ROOT / "player_stats_participants.json"
VOR_WIN_CACHE_PATH = ROOT / "analysis/vor_mapwin_target_stats.json"
RESULT_QUERY_PAUSE = 30


def esc(value):
    return html.escape(str(value), quote=True)


def stat_bool(value):
    text = str(value if value is not None else "").strip().lower()
    if text in {"1", "true", "t", "yes", "y", "win", "won"}:
        return 1
    if text in {"0", "false", "f", "no", "n", "loss", "lost"}:
        return 0
    return None


def stat_int(value):
    try:
        return int(str(value).strip().replace(",", ""))
    except (TypeError, ValueError):
        return None


def is_respawn(mode):
    text = str(mode or "").lower().replace("&", "and")
    return not ("search" in text and "destroy" in text)


def player_name(row):
    return row.get("Player") or row.get("PlayerLink") or row.get("PlayerName") or ""


def event_key(row):
    return row.get("EventId") or row.get("Event") or ""


def map_key(row):
    return (
        row.get("Game") or "",
        event_key(row),
        row.get("SeriesId") or "",
        row.get("Mode") or "",
        row.get("Map") or "",
        row.get("Date") or "",
    )


def normalize_rows(raw_rows):
    rows = []
    rejected = {"non_target_game": 0, "non_respawn": 0, "invalid_stats_or_result": 0}
    for raw in raw_rows:
        if raw.get("Game") not in GAMES:
            rejected["non_target_game"] += 1
            continue
        if not is_respawn(raw.get("Mode")):
            rejected["non_respawn"] += 1
            continue
        kills = stat_int(raw.get("Kills"))
        deaths = stat_int(raw.get("Deaths"))
        win = stat_bool(raw.get("Win"))
        player = player_name(raw)
        if kills is None or deaths is None or win is None or not player:
            rejected["invalid_stats_or_result"] += 1
            continue
        row = dict(raw)
        row.update({
            "player": player,
            "kills": kills,
            "deaths": deaths,
            "win": win,
            "kd": kills / deaths if deaths else None,
            "resultBucket": "positive" if kills > deaths else "negative" if kills < deaths else "even",
        })
        rows.append(row)
    return rows, rejected


def validate_maps(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[map_key(row)].append(row)
    valid_keys = []
    invalid = []
    for key, group in sorted(groups.items()):
        reasons = []
        if len(group) != 8:
            reasons.append(f"expected 8 player rows, found {len(group)}")
        if len({r["player"] for r in group}) != len(group):
            reasons.append("duplicate player rows")
        teams = {r.get("Team") or "" for r in group}
        if len(teams) != 2 or "" in teams:
            reasons.append(f"expected 2 named teams, found {len(teams - {''})}")
        wins = Counter(r["win"] for r in group)
        if wins != Counter({0: 4, 1: 4}):
            reasons.append(f"expected four win and four loss rows, found {dict(wins)}")
        for team in teams - {""}:
            team_results = {r["win"] for r in group if r.get("Team") == team}
            if len(team_results) != 1:
                reasons.append(f"inconsistent result within team {team}")
        if reasons:
            invalid.append({"key": list(key), "rows": len(group), "reasons": reasons})
        else:
            valid_keys.append(key)
    valid_set = set(valid_keys)
    valid_rows = [row for row in rows if map_key(row) in valid_set]
    return {
        "maps": len(groups),
        "validMaps": len(valid_keys),
        "validRows": len(valid_rows),
        "validMapKeys": valid_keys,
        "invalidMaps": invalid,
        "rows": valid_rows,
    }


def ratio(num, den):
    return num / den if den else None


def corr(xs, ys):
    pairs = [(float(x), float(y)) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pairs) < 3:
        return None
    mx = sum(x for x, _ in pairs) / len(pairs)
    my = sum(y for _, y in pairs) / len(pairs)
    sx = math.sqrt(sum((x - mx) ** 2 for x, _ in pairs))
    sy = math.sqrt(sum((y - my) ** 2 for _, y in pairs))
    if not sx or not sy:
        return None
    return sum((x - mx) * (y - my) for x, y in pairs) / (sx * sy)


def corr_ci(value, maps):
    """Approximate 95% Fisher-z interval for a descriptive correlation."""
    if value is None or maps < 4 or abs(value) >= 1:
        return None, None
    z = math.atanh(value)
    margin = 1.96 / math.sqrt(maps - 3)
    return math.tanh(z - margin), math.tanh(z + margin)


def stability_label(maps):
    if maps < 10:
        return "very small sample"
    if maps < 25:
        return "small sample"
    return "descriptive"


def association_status(group):
    maps = len(group)
    if len({row["win"] for row in group}) < 2:
        return "unavailable — no outcome variation"
    if len({row["kd"] for row in group if row["kd"] is not None}) < 2:
        return "unavailable — no K/D variation"
    if maps < 10:
        return "unstable — very small sample"
    if maps < 25:
        return "unstable — small sample"
    return "descriptive — larger sample"


def kd_band(row):
    if row["deaths"] == 0:
        return "No deaths"
    if row["kills"] == row["deaths"]:
        return "Exactly 1.00"
    value = row["kd"]
    if value < 0.8:
        return "Below 0.80"
    if value < 1:
        return "0.80–0.99"
    if value < 1.2:
        return "1.01–1.19"
    return "1.20+"


def aggregate_players(rows, mode=None):
    if mode:
        rows = [row for row in rows if row.get("Mode") == mode]
    buckets = defaultdict(list)
    for row in rows:
        buckets[row["player"]].append(row)
    out = []
    for player, group in buckets.items():
        maps = len(group)
        wins = sum(r["win"] for r in group)
        losses = maps - wins
        counts = Counter(r["resultBucket"] for r in group)
        positive_wins = sum(r["win"] for r in group if r["resultBucket"] == "positive")
        even_wins = sum(r["win"] for r in group if r["resultBucket"] == "even")
        negative_wins = sum(r["win"] for r in group if r["resultBucket"] == "negative")
        nonpositive_maps = counts["even"] + counts["negative"]
        nonpositive_wins = even_wins + negative_wins
        positive_win_rate = ratio(positive_wins, counts["positive"])
        nonpositive_win_rate = ratio(nonpositive_wins, nonpositive_maps)
        kd_win_corr = corr([r["kd"] for r in group], [r["win"] for r in group])
        kd_ci_low, kd_ci_high = corr_ci(kd_win_corr, sum(r["kd"] is not None for r in group))
        out.append({
            "player": player,
            "maps": maps,
            "wins": wins,
            "losses": losses,
            "winRate": ratio(wins, maps),
            "kills": sum(r["kills"] for r in group),
            "deaths": sum(r["deaths"] for r in group),
            "overallKd": ratio(sum(r["kills"] for r in group), sum(r["deaths"] for r in group)),
            "titles": len({r.get("Game") for r in group}),
            "positiveMaps": counts["positive"],
            "positiveWins": positive_wins,
            "positiveLosses": counts["positive"] - positive_wins,
            "evenMaps": counts["even"],
            "evenWins": even_wins,
            "negativeMaps": counts["negative"],
            "negativeWins": negative_wins,
            "winGivenPositive": positive_win_rate,
            "winGivenEven": ratio(even_wins, counts["even"]),
            "winGivenNegative": ratio(negative_wins, counts["negative"]),
            "winGivenNonpositive": nonpositive_win_rate,
            "positiveWinUplift": (
                positive_win_rate - nonpositive_win_rate
                if positive_win_rate is not None and nonpositive_win_rate is not None else None
            ),
            "positiveGivenWin": ratio(positive_wins, wins),
            "positiveGivenLoss": ratio(counts["positive"] - positive_wins, losses),
            "negativeGivenWin": ratio(negative_wins, wins),
            "positiveRateGap": (
                ratio(positive_wins, wins) - ratio(counts["positive"] - positive_wins, losses)
                if wins and losses else None
            ),
            "kdWinCorr": kd_win_corr,
            "kdWinCiLow": kd_ci_low,
            "kdWinCiHigh": kd_ci_high,
            "killsWinCorr": corr([r["kills"] for r in group], [r["win"] for r in group]),
            "deathsWinCorr": corr([r["deaths"] for r in group], [r["win"] for r in group]),
            "associationStatus": association_status(group),
            "stability": stability_label(maps),
        })
    return sorted(out, key=lambda row: (-row["maps"], row["player"].lower()))


def aggregate_overall(rows):
    counts = Counter(r["resultBucket"] for r in rows)
    wins = Counter(r["resultBucket"] for r in rows if r["win"])
    return {
        "rows": len(rows),
        "players": len({r["player"] for r in rows}),
        "maps": len({map_key(r) for r in rows}),
        "events": len({event_key(r) for r in rows}),
        "titles": len({r.get("Game") for r in rows}),
        "positiveMaps": counts["positive"],
        "evenMaps": counts["even"],
        "negativeMaps": counts["negative"],
        "winGivenPositive": ratio(wins["positive"], counts["positive"]),
        "winGivenEven": ratio(wins["even"], counts["even"]),
        "winGivenNegative": ratio(wins["negative"], counts["negative"]),
        "kdWinCorr": corr([r["kd"] for r in rows], [r["win"] for r in rows]),
        "killsWinCorr": corr([r["kills"] for r in rows], [r["win"] for r in rows]),
        "deathsWinCorr": corr([r["deaths"] for r in rows], [r["win"] for r in rows]),
    }


def build_summaries(rows):
    summaries = {"All respawn": aggregate_players(rows)}
    summaries.update({mode: aggregate_players(rows, mode) for mode in sorted({r.get("Mode") for r in rows})})
    return summaries


BAND_ORDER = ("Below 0.80", "0.80–0.99", "Exactly 1.00", "1.01–1.19", "1.20+", "No deaths")


def aggregate_kd_bands(rows, mode=None):
    if mode and mode != "All respawn":
        rows = [row for row in rows if row.get("Mode") == mode]
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["player"], kd_band(row))].append(row)
    result = []
    for (player, band), group in grouped.items():
        wins = sum(row["win"] for row in group)
        result.append({
            "player": player,
            "band": band,
            "bandOrder": BAND_ORDER.index(band),
            "maps": len(group),
            "wins": wins,
            "losses": len(group) - wins,
            "winRate": ratio(wins, len(group)),
        })
    return sorted(result, key=lambda row: (row["player"].lower(), row["bandOrder"]))


def target_events():
    events = json.loads(EVENTS_PATH.read_text())
    stats = json.loads(PARTICIPANT_STATS_PATH.read_text())
    recorded = {
        (row.get("Game"), row.get("EventId") or row.get("Event"))
        for row in stats
        if row.get("Game") == GAME and is_respawn(row.get("Mode"))
    }
    return [
        event for event in events
        if event.get("game") == GAME
        and (event.get("date") or "") <= ASOF
        and "challengers" not in f"{event.get('event') or ''} {event.get('page') or ''}".lower()
        and (event.get("game"), event.get("page")) in recorded
    ]


def result_key(row):
    return (
        row.get("Game") or "",
        row.get("EventId") or row.get("Event") or "",
        row.get("SeriesId") or "",
        row.get("Mode") or row.get("Gamemode") or "",
        row.get("Map") or "",
        row.get("Date") or "",
        row.get("Team") or "",
    )


def result_query_params(game, events, mode):
    pages = [event["page"] for event in events]
    return {
        "tables": "PlayerStats=PS",
        "fields": (
            "PS.TournamentPage=EventId,PS.GameTitle=Game,PS.Gamemode=Mode,PS.Date=Date,"
            "PS.Team=Team,PS.TeamVs=TeamVs,PS.Map=Map,PS.SeriesId=SeriesId,PS.Win=Win"
        ),
        "where": (
            f"PS.TournamentPage IN({fetch_source._quoted(pages)}) "
            f"AND PS.GameTitle={fetch_source._quoted([game])} "
            f"AND PS.Gamemode={fetch_source._quoted([mode])} "
            f'AND PS.Date <= "{ASOF}" '
            "AND PS.Win IS NOT NULL"
        ),
        "group_by": (
            "PS.TournamentPage,PS.GameTitle,PS.Gamemode,PS.Date,PS.Team,PS.TeamVs,"
            "PS.Map,PS.SeriesId,PS.Win"
        ),
        "order_by": "PS.Date,PS.TournamentPage,PS.SeriesId,PS.Gamemode,PS.Team",
    }


def seed_result_index(paths):
    result_index = {}
    conflicts = []
    for path in paths:
        if not path.exists():
            continue
        for row in json.loads(path.read_text()):
            if row.get("Game") not in GAMES or not is_respawn(row.get("Mode")):
                continue
            win = stat_bool(row.get("Win"))
            if win is None:
                continue
            key = result_key(row)
            if key in result_index and result_index[key] != win:
                conflicts.append(key)
            result_index[key] = win
    if conflicts:
        raise RuntimeError(f"Conflicting cached team-map results for {len(conflicts)} keys")
    return result_index


def materialize_rows(local_rows, pages, result_index):
    rows, missing = [], []
    for raw in local_rows:
        if raw.get("Game") not in GAMES or not is_respawn(raw.get("Mode")):
            continue
        event = raw.get("EventId") or raw.get("Event") or ""
        if event not in pages:
            continue
        row = dict(raw)
        row["EventId"] = event
        win = result_index.get(result_key(row))
        if win is None:
            missing.append(result_key(row))
            continue
        row["Win"] = win
        rows.append(row)
    return rows, missing


def load_or_fetch_rows():
    events = target_events()
    pages = {event["page"] for event in events}
    if CACHE_PATH.exists():
        rows = json.loads(CACHE_PATH.read_text())
        target_rows = [row for row in rows if row.get("Game") == GAME]
        cached_pages = {row.get("EventId") or row.get("Event") for row in target_rows}
        if (target_rows and cached_pages == pages
                and all(stat_bool(row.get("Win")) is not None for row in target_rows)):
            return target_rows, {"completed": ["team-map-results"], "failed": {}}

    local_rows = json.loads(PARTICIPANT_STATS_PATH.read_text())
    # Prefer result facts already present in the canonical major-map snapshot;
    # older events without Win still fall back to the isolated analysis caches.
    result_index = seed_result_index([PARTICIPANT_STATS_PATH, CACHE_PATH, VOR_WIN_CACHE_PATH])
    completed, failed, needed = [], {}, []
    for game in GAMES:
        game_events = [event for event in events if event.get("game") == game]
        game_pages = {event["page"] for event in game_events}
        modes = sorted({
            row.get("Mode") for row in local_rows
            if row.get("Game") == game and (row.get("EventId") or row.get("Event")) in game_pages
            and is_respawn(row.get("Mode"))
        })
        for mode in modes:
            expected = {
                result_key(row) for row in local_rows
                if row.get("Game") == game and row.get("Mode") == mode
                and (row.get("EventId") or row.get("Event")) in game_pages
            }
            key = f"{game}|{mode}"
            if expected <= result_index.keys():
                completed.append(key)
            else:
                needed.append((game, game_events, mode, key))

    for i, (game, game_events, mode, key) in enumerate(needed, 1):
        print(f"[{i}/{len(needed)}] fetching team-map results for {game} {mode}")
        try:
            result_rows = fetch_source.flat(fetch_source.cargo_all(result_query_params(game, game_events, mode)))
        except SystemExit as exc:
            failed[key] = {"error": str(exc)}
            PROGRESS_PATH.write_text(json.dumps({"completed": completed, "failed": failed}))
            continue
        for row in result_rows:
            win = stat_bool(row.get("Win"))
            if win is not None:
                result_index[result_key(row)] = win
        completed.append(key)
        rows, _missing = materialize_rows(local_rows, pages, result_index)
        CACHE_PATH.write_text(json.dumps(rows))
        PROGRESS_PATH.write_text(json.dumps({"completed": completed, "failed": failed}))
        if i < len(needed):
            time.sleep(RESULT_QUERY_PAUSE)

    rows, missing = materialize_rows(local_rows, pages, result_index)
    if missing:
        raise RuntimeError(f"Missing team-map result for {len(missing)} local player rows")
    CACHE_PATH.write_text(json.dumps(rows))
    progress = {"completed": completed, "failed": failed, "playerRows": len(rows)}
    PROGRESS_PATH.write_text(json.dumps(progress))
    return rows, progress


def pct(value):
    return "n/a" if value is None else f"{100 * value:.1f}%"


def signed(value):
    return "n/a" if value is None else f"{value:+.2f}"


def report_html(rows, audit, rejected, progress):
    summaries = build_summaries(rows)
    modes = list(summaries)
    mode_rows = {
        mode: rows if mode == "All respawn" else [row for row in rows if row.get("Mode") == mode]
        for mode in modes
    }
    overalls = {mode: aggregate_overall(selected) for mode, selected in mode_rows.items()}
    bands = {mode: aggregate_kd_bands(selected) for mode, selected in mode_rows.items()}
    coverage = {}
    drilldowns = {}
    for mode, selected in mode_rows.items():
        coverage[mode] = {
            "events": len({event_key(row) for row in selected}),
            "maps": len({map_key(row) for row in selected}),
            "players": len({row["player"] for row in selected}),
            "rows": len(selected),
            "modes": dict(sorted(Counter(row.get("Mode") for row in selected).items())),
        }
        drilldowns[mode] = [{
            "player": row["player"], "event": event_key(row), "date": row.get("Date"),
            "series": row.get("SeriesId"), "mode": row.get("Mode"), "map": row.get("Map"),
            "team": row.get("Team"), "opponent": row.get("TeamVs"), "kills": row["kills"],
            "deaths": row["deaths"], "kd": row["kd"], "bucket": row["resultBucket"],
            "result": "Win" if row["win"] else "Loss",
        } for row in selected]
    payload = json.dumps(summaries).replace("</", "<\\/")
    overall_payload = json.dumps(overalls).replace("</", "<\\/")
    band_payload = json.dumps(bands).replace("</", "<\\/")
    coverage_payload = json.dumps(coverage).replace("</", "<\\/")
    drilldown_payload = json.dumps(drilldowns).replace("</", "<\\/")
    initial = overalls["All respawn"]
    initial_coverage = coverage["All respawn"]
    failed = progress.get("failed") or {}
    cards = [
        ("Major events", initial_coverage["events"], "Non-Challengers Major/Premier events", "events-card"),
        ("Respawn maps", initial_coverage["maps"], " + ".join(f"{count // 8} {mode}" for mode, count in initial_coverage["modes"].items()), "maps-card"),
        ("Players", initial_coverage["players"], "Every recorded player included", "players-card"),
        ("Player-map rows", initial_coverage["rows"], "All eight rows present per valid map", "rows-card"),
    ]
    card_html = "".join(
        f'<div class="card"><div class="k">{esc(label)}</div><div class="v" id="{card_id}">{esc(value)}</div><div class="sub" id="{card_id}-note">{esc(note)}</div></div>'
        for label, value, note, card_id in cards
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Black Ops 7: player K/D and respawn map wins</title>
<link rel="stylesheet" href="../site/vendor/tabulator.min.css"><link rel="stylesheet" href="../site/assets/style.css">
<style>
body{{background:var(--bg,#0b0e13)}} main{{max-width:1500px;margin:0 auto;padding:28px 20px 60px}}
.cards{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:18px 0}}
.card{{border:1px solid var(--line);background:var(--panel);border-radius:10px;padding:14px}} .k{{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}} .v{{font-size:25px;font-weight:800;margin-top:4px}} .sub{{font-size:12px;color:var(--muted);margin-top:4px}}
.formula{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}} .formula .card .v{{font-size:20px}}
.controls{{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:18px 0}} select{{background:var(--panel);color:var(--text);border:1px solid var(--line);padding:8px;border-radius:6px}}
.callout{{border-left:3px solid var(--gold);padding:10px 14px;background:var(--panel);margin:16px 0}} code{{color:var(--gold)}}
.section-note{{max-width:920px}} .table-block{{margin-bottom:34px}}
@media(max-width:850px){{.cards,.formula{{grid-template-columns:1fr 1fr}}}} @media(max-width:520px){{.cards,.formula{{grid-template-columns:1fr}}}}
</style></head><body><main>
<p class="eyebrow">Local analysis · GitHub #27</p><h1>Black Ops 7: player K/D and respawn map wins</h1>
<p class="lede">Every recorded Black Ops 7 Major/Premier respawn player-map through {esc(ASOF)} with kills, deaths, and a validated team result. Challengers events are excluded. This is same-map association—not proof that a player's K/D independently caused the result or predicts future maps.</p>
<div class="cards">{card_html}</div>
<h2>What the three denominators mean</h2><div class="formula">
<div class="card"><div class="k">P(win | positive)</div><div class="v" id="positive-rate">{pct(initial['winGivenPositive'])}</div><div class="sub">Team win rate on positive player-maps</div></div>
<div class="card"><div class="k">P(win | even)</div><div class="v" id="even-rate">{pct(initial['winGivenEven'])}</div><div class="sub">Team win rate on exactly-even player-maps</div></div>
<div class="card"><div class="k">P(win | negative)</div><div class="v" id="negative-rate">{pct(initial['winGivenNegative'])}</div><div class="sub">Team win rate on negative player-maps</div></div></div>
<div class="callout" id="correlation-callout"><strong>All-player map-level correlations:</strong> K/D {signed(initial['kdWinCorr'])}; kills {signed(initial['killsWinCorr'])}; deaths {signed(initial['deathsWinCorr'])}. Player rows from the same map are not independent, so use these as descriptive orientation.</div>
<div class="controls"><label for="mode">Respawn mode</label><select id="mode">{"".join(f'<option>{esc(key)}</option>' for key in summaries)}</select></div>
<section class="table-block"><h2>All-player summary</h2><p class="section-note">Every recorded player remains in the report; map count and stability context sit beside each estimate. Click any header to sort.</p><div id="player-table"></div></section>
<section class="table-block"><h2>Positive, even, and negative maps</h2><p class="section-note">“Positive uplift” is P(win | positive) minus P(win | non-positive). Exactly 1.00 K/D is kept in the even bucket.</p><div id="bucket-table"></div></section>
<section class="table-block"><h2>Positive-in-loss and negative-in-win results</h2><p class="section-note">These are descriptive exceptions, not player-value rankings. Rates retain their own denominators: positive maps among losses and negative maps among wins.</p><div id="exception-table"></div></section>
<section class="table-block"><h2>Strongest and weakest continuous K/D–win relationships</h2><p class="section-note">Point-biserial Pearson correlation of map K/D with the binary team result, computed within each player. The approximate 95% interval is shown for context; unavailable and unstable estimates stay visible. Kills and deaths are shown separately to decompose the direction.</p><div id="association-table"></div></section>
<section class="table-block"><h2>Win rate by map K/D band</h2><p class="section-note">Each row is a player-band combination. Exact 1.00 K/D has its own band; no-death maps, if any, are not folded into a finite ratio band.</p><div id="band-table"></div></section>
<section class="table-block"><h2>Player map drilldown</h2><div class="controls"><label for="player">Player</label><select id="player"></select></div><div id="drilldown-table"></div></section>
<h2>Coverage audit</h2><div id="audit"></div>
<p class="small muted">Invalid maps: {len(audit['invalidMaps'])}. Rejected rows: {esc(json.dumps(rejected, sort_keys=True))}. Fetch failures: {esc(json.dumps(failed, sort_keys=True))}.</p>
<p class="small muted">Related team-level outslay analysis: <a href="https://github.com/benjaminshoemaker/cod-stats/issues/26">GitHub #26</a>.</p>
</main>
<script src="../site/vendor/tabulator.min.js"></script><script src="../site/assets/app.js"></script>
<script>
const summaries={payload};
const overalls={overall_payload};
const bands={band_payload};
const coverage={coverage_payload};
const drilldowns={drilldown_payload};
const pct=v=>v==null?'n/a':(100*v).toFixed(1)+'%'; const corr=v=>v==null?'n/a':(v>=0?'+':'')+v.toFixed(2);
const baseColumns=[
{{title:'Player',field:'player',frozen:true,headerTooltip:'Player'}},{{title:'Maps',field:'maps',hozAlign:'right',sorter:'number',headerTooltip:'Qualifying player-map rows'}},
{{title:'W–L',field:'wins',formatter:c=>c.getRow().getData().wins+'–'+c.getRow().getData().losses}},{{title:'Win%',field:'winRate',formatter:c=>pct(c.getValue()),sorter:'number'}},
{{title:'K/D',field:'overallKd',formatter:c=>c.getValue()==null?'n/a':c.getValue().toFixed(2),sorter:'number'}},
{{title:'Positive | win',field:'positiveGivenWin',formatter:c=>pct(c.getValue()),sorter:'number'}},{{title:'Positive | loss',field:'positiveGivenLoss',formatter:c=>pct(c.getValue()),sorter:'number'}},
{{title:'Positive gap',field:'positiveRateGap',formatter:c=>pct(c.getValue()),sorter:'number',headerTooltip:'P(positive | win) minus P(positive | loss)'}},
{{title:'Context',field:'stability'}}];
const bucketColumns=[{{title:'Player',field:'player',frozen:true}},{{title:'Maps',field:'maps',sorter:'number'}},
{{title:'Positive maps',field:'positiveMaps',sorter:'number'}},{{title:'Win | positive',field:'winGivenPositive',formatter:c=>pct(c.getValue()),sorter:'number'}},
{{title:'Even maps',field:'evenMaps',sorter:'number'}},{{title:'Win | even',field:'winGivenEven',formatter:c=>pct(c.getValue()),sorter:'number'}},
{{title:'Negative maps',field:'negativeMaps',sorter:'number'}},{{title:'Win | negative',field:'winGivenNegative',formatter:c=>pct(c.getValue()),sorter:'number'}},
{{title:'Win | non-pos.',field:'winGivenNonpositive',formatter:c=>pct(c.getValue()),sorter:'number'}},{{title:'Positive uplift',field:'positiveWinUplift',formatter:c=>pct(c.getValue()),sorter:'number'}}];
const exceptionColumns=[{{title:'Player',field:'player',frozen:true}},{{title:'Maps',field:'maps',sorter:'number'}},{{title:'Losses',field:'losses',sorter:'number'}},
{{title:'Positive losses',field:'positiveLosses',sorter:'number'}},{{title:'Positive | loss',field:'positiveGivenLoss',formatter:c=>pct(c.getValue()),sorter:'number'}},
{{title:'Wins',field:'wins',sorter:'number'}},{{title:'Negative wins',field:'negativeWins',sorter:'number'}},{{title:'Negative | win',field:'negativeGivenWin',formatter:c=>pct(c.getValue()),sorter:'number'}},{{title:'Context',field:'stability'}}];
const ci=c=>{{const d=c.getRow().getData();return d.kdWinCiLow==null?'n/a':corr(d.kdWinCiLow)+' to '+corr(d.kdWinCiHigh)}};
const associationColumns=[{{title:'Player',field:'player',frozen:true}},{{title:'Maps',field:'maps',sorter:'number'}},{{title:'K/D ↔ win',field:'kdWinCorr',formatter:c=>corr(c.getValue()),sorter:'number'}},
{{title:'Approx. 95% interval',field:'kdWinCiLow',formatter:ci,sorter:'number'}},{{title:'Kills ↔ win',field:'killsWinCorr',formatter:c=>corr(c.getValue()),sorter:'number'}},
{{title:'Deaths ↔ win',field:'deathsWinCorr',formatter:c=>corr(c.getValue()),sorter:'number',headerTooltip:'Negative means fewer deaths align with wins'}},{{title:'Estimate status',field:'associationStatus'}}];
const bandColumns=[{{title:'Player',field:'player',frozen:true}},{{title:'K/D band',field:'band'}},{{title:'Band order',field:'bandOrder',visible:false}},{{title:'Maps',field:'maps',sorter:'number'}},{{title:'W–L',field:'wins',formatter:c=>c.getRow().getData().wins+'–'+c.getRow().getData().losses}},{{title:'Win%',field:'winRate',formatter:c=>pct(c.getValue()),sorter:'number'}}];
const drilldownColumns=[{{title:'Date',field:'date'}},{{title:'Event',field:'event'}},{{title:'Mode',field:'mode'}},{{title:'Map',field:'map'}},{{title:'Team',field:'team'}},{{title:'Opponent',field:'opponent'}},{{title:'Kills',field:'kills',sorter:'number'}},{{title:'Deaths',field:'deaths',sorter:'number'}},{{title:'K/D',field:'kd',formatter:c=>c.getValue()==null?'n/a':c.getValue().toFixed(2),sorter:'number'}},{{title:'K/D bucket',field:'bucket'}},{{title:'Team result',field:'result'}}];
const tableOptions=(label,data,columns,sort)=>({{label,data,layout:'fitDataStretch',responsiveLayout:false,columns:columns.map(column=>({{headerTooltip:column.title,...column}})),initialSort:sort}});
const table=TableSurface.mountTabulator('#player-table',tableOptions('All-player BO7 respawn summary',summaries['All respawn'],baseColumns,[{{column:'maps',dir:'desc'}}]));
const bucketTable=TableSurface.mountTabulator('#bucket-table',tableOptions('Positive even and negative result buckets',summaries['All respawn'],bucketColumns,[{{column:'maps',dir:'desc'}}]));
const exceptionTable=TableSurface.mountTabulator('#exception-table',tableOptions('Positive losses and negative wins',summaries['All respawn'],exceptionColumns,[{{column:'positiveLosses',dir:'desc'}}]));
const associationTable=TableSurface.mountTabulator('#association-table',tableOptions('Within-player K/D and team-win associations',summaries['All respawn'],associationColumns,[{{column:'kdWinCorr',dir:'desc'}}]));
const bandTable=TableSurface.mountTabulator('#band-table',tableOptions('Player win rates by map K/D band',bands['All respawn'],bandColumns,[{{column:'player',dir:'asc'}},{{column:'bandOrder',dir:'asc'}}]));
const drilldownTable=TableSurface.mountTabulator('#drilldown-table',tableOptions('Underlying player-map values',[],drilldownColumns,[{{column:'date',dir:'desc'}}]));
function populatePlayers(mode){{
  const player=document.getElementById('player'); const prior=player.value;
  const names=[...new Set(drilldowns[mode].map(row=>row.player))].sort((a,b)=>a.localeCompare(b));
  player.innerHTML=names.map(name=>`<option>${{name}}</option>`).join('');
  if(names.includes(prior)) player.value=prior;
}}
function applyPlayer(){{const mode=document.getElementById('mode').value;const player=document.getElementById('player').value;drilldownTable.replaceData(drilldowns[mode].filter(row=>row.player===player));}}
function applyFilters(){{
  const mode=document.getElementById('mode').value;
  const overall=overalls[mode]; const scope=coverage[mode];
  document.getElementById('events-card').textContent=scope.events;
  document.getElementById('maps-card').textContent=scope.maps;
  document.getElementById('maps-card-note').textContent=Object.entries(scope.modes).map(([name,count])=>`${{count/8}} ${{name}}`).join(' + ');
  document.getElementById('players-card').textContent=scope.players;
  document.getElementById('rows-card').textContent=scope.rows;
  document.getElementById('positive-rate').textContent=pct(overall.winGivenPositive);
  document.getElementById('even-rate').textContent=pct(overall.winGivenEven);
  document.getElementById('negative-rate').textContent=pct(overall.winGivenNegative);
  document.getElementById('correlation-callout').innerHTML=`<strong>All-player map-level correlations:</strong> K/D ${{corr(overall.kdWinCorr)}}; kills ${{corr(overall.killsWinCorr)}}; deaths ${{corr(overall.deathsWinCorr)}}. Player rows from the same map are not independent, so use these as descriptive orientation.`;
  table.replaceData(summaries[mode]); bucketTable.replaceData(summaries[mode]); exceptionTable.replaceData(summaries[mode]); associationTable.replaceData(summaries[mode]); bandTable.replaceData(bands[mode]);
  populatePlayers(mode); applyPlayer();
}}
document.getElementById('mode').addEventListener('change',applyFilters);
document.getElementById('player').addEventListener('change',applyPlayer);
populatePlayers('All respawn'); applyPlayer();
document.getElementById('audit').innerHTML=TableSurface.dataTable({{label:'Coverage audit',head:'<thead><tr><th scope="col">Check</th><th scope="col">Result</th></tr></thead>',rows:`
<tr><td>Valid maps</td><td>{audit['validMaps']} / {audit['maps']}</td></tr><tr><td>Valid player rows</td><td>{audit['validRows']}</td></tr><tr><td>Invalid maps</td><td>{len(audit['invalidMaps'])}</td></tr><tr><td>Fetch failures</td><td>{len(failed)}</td></tr>`}});
</script></body></html>"""


def build_report(raw_rows, progress=None):
    rows, rejected = normalize_rows(raw_rows)
    audit = validate_maps(rows)
    valid_rows = audit.pop("rows")
    if audit["invalidMaps"]:
        raise RuntimeError(f"Recent-title map validation failed for {len(audit['invalidMaps'])} maps")
    if not valid_rows:
        raise RuntimeError("No valid recent-title respawn rows with map results")
    OUT_PATH.write_text(report_html(valid_rows, audit, rejected, progress or {"failed": {}}))
    return valid_rows, audit


def main():
    raw_rows, progress = load_or_fetch_rows()
    if progress.get("failed"):
        raise RuntimeError(f"PlayerStats fetch failures: {progress['failed']}")
    rows, audit = build_report(raw_rows, progress)
    print(f"wrote {OUT_PATH.relative_to(ROOT)}")
    print(f"validated {audit['validMaps']} maps, {len(rows)} player rows, {len({r['player'] for r in rows})} players")
    print(GAME, len({map_key(row) for row in rows}), "maps", dict(sorted(Counter(row.get("Mode") for row in rows).items())))


if __name__ == "__main__":
    main()
