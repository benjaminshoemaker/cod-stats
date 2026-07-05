#!/usr/bin/env python3
"""Mode-adjusted VOR pilot validated against PlayerStats map wins.

This is intentionally an analysis artifact. It does not write generated site
data and does not use role as a replacement-level bucket.
"""
import html
import json
import math
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import fetch_source


GAMES = ["Black Ops 2", "Advanced Warfare", "Infinite Warfare", "Black Ops 6"]
REPLACEMENT_PERCENTILE = 0.25
THRESHOLDS = {
    "overall_kills": 40,
    "respawn_kills": 28,
    "respawn_interactions": 28,
    "snd_kills": 10,
}
METRICS = {
    "overall_kills": ("Overall K/map", "overall", "kpm"),
    "respawn_kills": ("Respawn K/map", "respawn", "kpm"),
    "respawn_interactions": ("Respawn interactions/map", "respawn", "ipm"),
    "snd_kills": ("S&D K/map", "snd", "kpm"),
}
CACHE_PATH = ROOT / "analysis/vor_mapwin_target_stats.json"
PROGRESS_PATH = ROOT / "analysis/vor_mapwin_target_stats.progress.json"
OUT_PATH = ROOT / "analysis/vor_mapwin_validation.html"
TOP_N = 10


def esc(value):
    return html.escape(str(value))


def mkey(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def is_snd(mode):
    text = str(mode or "").lower().replace("&", "and")
    return "search" in text and "destroy" in text


def stat_bool(value):
    if isinstance(value, bool):
        return value
    text = str(value if value is not None else "").strip().lower()
    if text in {"1", "true", "t", "yes", "y", "win", "won"}:
        return True
    if text in {"0", "false", "f", "no", "n", "loss", "lost"}:
        return False
    return None


def percentile(vals, pct):
    vals = sorted(vals)
    if not vals:
        return None
    if len(vals) == 1:
        return vals[0]
    pos = (len(vals) - 1) * pct
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return vals[lo]
    return vals[lo] + (vals[hi] - vals[lo]) * (pos - lo)


def corr(xs, ys):
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pairs) < 3:
        return None
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if not sx or not sy:
        return None
    return sum((x - mx) * (y - my) for x, y in pairs) / (sx * sy)


def target_events():
    rows = json.loads((ROOT / "player_stats_participants.events.json").read_text())
    return [row for row in rows if row.get("game") in GAMES]


def query_params(event):
    return {
        "tables": "PlayerStats=PS,PlayerRedirects=PR,Tournaments=TO",
        "fields": (
            "PR.OverviewPage=Player,PS.PlayerName=PlayerName,PS.PlayerLink=PlayerLink,"
            "TO.Name=Event,PS.TournamentPage=EventId,PS.GameTitle=Game,PS.Gamemode=Mode,"
            "PS.Date=Date,PS.Team=Team,PS.TeamVs=TeamVs,PS.Kills=Kills,"
            "PS.Deaths=Deaths,PS.KDRatio=KDRatio,PS.Map=Map,PS.SeriesId=SeriesId,PS.Win=Win"
        ),
        "where": (
            f"PS.TournamentPage={fetch_source._quoted([event['page']])} "
            f"AND PS.GameTitle={fetch_source._quoted([event['game']])} "
            'AND PS.Date <= "2026-06-29" '
            "AND PS.Kills IS NOT NULL AND PS.Deaths IS NOT NULL"
        ),
        "join_on": "PS.PlayerLink=PR.AllName,PS.TournamentPage=TO.OverviewPage",
        "order_by": "PS.Date,PS.TournamentPage,PR.OverviewPage,PS.Gamemode",
    }


def load_or_fetch_rows():
    rows = json.loads(CACHE_PATH.read_text()) if CACHE_PATH.exists() else []
    progress = json.loads(PROGRESS_PATH.read_text()) if PROGRESS_PATH.exists() else {
        "completed": [],
        "failed": {},
    }
    completed = set(progress.get("completed", []))
    failed = dict(progress.get("failed", {}))

    events = target_events()
    for i, event in enumerate(events, 1):
        page = event["page"]
        if page in completed:
            print(f"[{i}/{len(events)}] skipping {event['event']}")
            continue
        print(f"[{i}/{len(events)}] fetching {event['event']} ({page})")
        try:
            new_rows = fetch_source.flat(fetch_source.cargo_all(query_params(event)))
        except SystemExit as exc:
            failed[page] = {
                "event": event["event"],
                "game": event["game"],
                "error": str(exc),
            }
            PROGRESS_PATH.write_text(json.dumps({"completed": sorted(completed), "failed": failed}))
            print(f"  failed: {exc}")
            time.sleep(fetch_source.PAUSE)
            continue
        rows = fetch_source._merge_stat_rows(rows, fetch_source.slim_player_stat_rows(new_rows))
        completed.add(page)
        failed.pop(page, None)
        CACHE_PATH.write_text(json.dumps(rows))
        PROGRESS_PATH.write_text(json.dumps({"completed": sorted(completed), "failed": failed}))
        time.sleep(fetch_source.PAUSE)
    return rows, progress


def empty_bucket():
    return {"kills": 0, "deaths": 0, "maps": 0, "wins": 0, "events": set()}


def add_row(bucket, row):
    win = stat_bool(row.get("Win"))
    if win is None:
        return
    bucket["kills"] += int(row["Kills"])
    bucket["deaths"] += int(row["Deaths"])
    bucket["maps"] += 1
    bucket["wins"] += 1 if win else 0
    if row.get("EventId") or row.get("Event"):
        bucket["events"].add(row.get("EventId") or row.get("Event"))


def finish_bucket(bucket):
    maps = bucket["maps"]
    kills = bucket["kills"]
    deaths = bucket["deaths"]
    return {
        "kills": kills,
        "deaths": deaths,
        "interactions": kills + deaths,
        "maps": maps,
        "wins": bucket["wins"],
        "events": len(bucket["events"]),
        "kpm": kills / maps if maps else None,
        "ipm": (kills + deaths) / maps if maps else None,
        "kd": kills / deaths if deaths else None,
        "map_win_rate": bucket["wins"] / maps if maps else None,
    }


def aggregate(rows):
    work = defaultdict(lambda: defaultdict(lambda: {
        "name": "",
        "overall": empty_bucket(),
        "respawn": empty_bucket(),
        "snd": empty_bucket(),
    }))
    for row in rows:
        game = row.get("Game")
        if game not in GAMES:
            continue
        player = row.get("Player") or row.get("PlayerLink") or row.get("PlayerName")
        if not player:
            continue
        key = mkey(player)
        rec = work[game][key]
        rec["name"] = player
        split = "snd" if is_snd(row.get("Mode")) else "respawn"
        add_row(rec["overall"], row)
        add_row(rec[split], row)

    out = {}
    for game, players in work.items():
        out[game] = []
        for rec in players.values():
            out[game].append({
                "player": rec["name"],
                "overall": finish_bucket(rec["overall"]),
                "respawn": finish_bucket(rec["respawn"]),
                "snd": finish_bucket(rec["snd"]),
            })
    return out


def score_metric(players, metric):
    _label, split, stat = METRICS[metric]
    threshold = THRESHOLDS[metric]
    qualified = [p for p in players if p[split]["maps"] >= threshold and p[split][stat] is not None]
    repl = percentile([p[split][stat] for p in qualified], REPLACEMENT_PERCENTILE)
    if repl is None:
        return {"replacement": None, "qualified": 0, "rows": []}
    rows = []
    for player in qualified:
        s = player[split]
        rate = s[stat] - repl
        rows.append({
            "player": player["player"],
            "maps": s["maps"],
            "wins": s["wins"],
            "map_win_rate": s["map_win_rate"],
            "events": s["events"],
            "kd": s["kd"],
            "kpm": s["kpm"],
            "ipm": s["ipm"],
            "rate_over_repl": rate,
            "total_over_repl": rate * s["maps"],
        })
    rows.sort(key=lambda r: r["rate_over_repl"], reverse=True)
    return {"replacement": repl, "qualified": len(qualified), "rows": rows}


def validate(score):
    rows = score["rows"]
    top = rows[:TOP_N]
    win_rate_top = sorted(rows, key=lambda r: (-r["map_win_rate"], -r["maps"], r["player"]))[:TOP_N]
    map_wins_top = sorted(rows, key=lambda r: (-r["wins"], -r["map_win_rate"], r["player"]))[:TOP_N]
    top_keys = {mkey(r["player"]) for r in top}
    return {
        "top_win_rate_overlap": len(top_keys & {mkey(r["player"]) for r in win_rate_top}),
        "top_map_wins_overlap": len(top_keys & {mkey(r["player"]) for r in map_wins_top}),
        "corr_win_rate": corr([r["rate_over_repl"] for r in rows], [r["map_win_rate"] for r in rows]),
        "corr_map_wins": corr([r["rate_over_repl"] for r in rows], [r["wins"] for r in rows]),
    }


def fmt(value, digits=2):
    return "n/a" if value is None else f"{value:.{digits}f}"


def metric_table(score):
    rows = [
        "<table>",
        "<tr><th>Rank</th><th>Player</th><th>Maps</th><th>Rate +/-</th><th>Total +/-</th><th>K/D</th><th>Map W-L</th><th>Map win%</th></tr>",
    ]
    for i, row in enumerate(score["rows"][:TOP_N], 1):
        losses = row["maps"] - row["wins"]
        rows.append(
            "<tr>"
            f"<td>{i}</td><td>{esc(row['player'])}</td><td>{row['maps']}</td>"
            f"<td>{row['rate_over_repl']:+.2f}/map</td><td>{row['total_over_repl']:+.1f}</td>"
            f"<td>{fmt(row['kd'], 3)}</td><td>{row['wins']}-{losses}</td>"
            f"<td>{fmt(100 * row['map_win_rate'], 1)}%</td>"
            "</tr>"
        )
    rows.append("</table>")
    return "\n".join(rows)


def build_report(scores):
    css = """
    body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;margin:0;background:#f7f8fa;color:#111827}
    main{max-width:1220px;margin:0 auto;padding:28px}h1{font-size:34px;margin:0 0 8px}h2{margin:34px 0 10px}h3{margin:22px 0 8px}
    p{color:#4b5563;line-height:1.45}.cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:10px 0}
    .card{background:white;border:1px solid #e5e7eb;border-radius:8px;padding:12px}.k{font-size:12px;color:#6b7280;text-transform:uppercase;letter-spacing:.04em}.v{font-size:21px;font-weight:750;margin-top:4px}.sub{font-size:12px;color:#6b7280;margin-top:3px}
    table{width:100%;border-collapse:collapse;background:white;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;margin:8px 0 18px}
    th,td{font-size:13px;text-align:left;padding:8px 9px;border-bottom:1px solid #eef0f3}th{background:#111827;color:white}tr:last-child td{border-bottom:0}
    @media(max-width:850px){main{padding:16px}.cards{grid-template-columns:1fr 1fr}table{display:block;overflow-x:auto;white-space:nowrap}}
    """
    sections = []
    for game in GAMES:
        blocks = []
        for metric, (label, _split, _stat) in METRICS.items():
            score = scores[game][metric]
            v = validate(score)
            blocks.append(
                f"<h3>{esc(label)}</h3>"
                '<div class="cards">'
                f'<div class="card"><div class="k">Qualified</div><div class="v">{score["qualified"]}</div><div class="sub">min maps {THRESHOLDS[metric]}</div></div>'
                f'<div class="card"><div class="k">Replacement</div><div class="v">{fmt(score["replacement"])}/map</div><div class="sub">25th percentile</div></div>'
                f'<div class="card"><div class="k">Top-10 vs win%</div><div class="v">{v["top_win_rate_overlap"]}/{TOP_N}</div><div class="sub">overlap with map-win-rate leaders</div></div>'
                f'<div class="card"><div class="k">Corr to win%</div><div class="v">{fmt(v["corr_win_rate"])}</div><div class="sub">qualified players</div></div>'
                "</div>"
                + metric_table(score)
            )
        sections.append(f"<section><h2>{esc(game)}</h2>{''.join(blocks)}</section>")
    html_doc = (
        "<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>VOR map-win validation</title><style>{css}</style></head><body><main>"
        "<h1>Mode-Adjusted VOR Map-Win Validation</h1>"
        "<p>Replacement is title/mode-specific only. Role is not used in the formula. Validation uses actual map wins from the wiki PlayerStats.Win field.</p>"
        + "".join(sections)
        + "</main></body></html>"
    )
    OUT_PATH.write_text(html_doc)


def main():
    rows, progress = load_or_fetch_rows()
    with_win = sum(1 for row in rows if "Win" in row)
    print(f"rows={len(rows)} with_win={with_win} cache={CACHE_PATH}")
    by_game = aggregate(rows)
    scores = {
        game: {metric: score_metric(by_game.get(game, []), metric) for metric in METRICS}
        for game in GAMES
    }
    build_report(scores)
    for game in GAMES:
        print(f"\n{game}")
        for metric, (label, _split, _stat) in METRICS.items():
            score = scores[game][metric]
            v = validate(score)
            top5 = ", ".join(r["player"] for r in score["rows"][:5])
            print(
                f"  {label}: q={score['qualified']} repl={fmt(score['replacement'])}/map "
                f"top5={top5}; corr_win%={fmt(v['corr_win_rate'])}; "
                f"top10_win%_overlap={v['top_win_rate_overlap']}/{TOP_N}"
            )
    print(f"\nWrote {OUT_PATH}")


if __name__ == "__main__":
    main()
