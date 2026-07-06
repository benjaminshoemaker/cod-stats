#!/usr/bin/env python3
"""Prototype page for title/mode Kills Over Replacement."""
import html
import json
import math
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "analysis/kills_vor_prototype.html"
GAMES = ["Black Ops 2", "Advanced Warfare", "Infinite Warfare", "Black Ops 6"]
REPLACEMENT_PERCENTILE = 0.25
SPLITS = {
    "respawn": {"label": "Respawn", "min_maps": 28, "description": "Hardpoint, Control, Uplink, CTF, and other non-S&D modes."},
    "snd": {"label": "Search & Destroy", "min_maps": 10, "description": "S&D maps only."},
}


def esc(value):
    return html.escape(str(value))


def is_snd(mode):
    text = str(mode or "").lower().replace("&", "and")
    return "search" in text and "destroy" in text


def mkey(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def place_value(place):
    text = str(place or "").strip()
    if not text:
        return None
    if text.isdigit():
        return float(text)
    match = re.match(r"^(\d+)\s*-\s*(\d+)$", text)
    if match:
        return (float(match.group(1)) + float(match.group(2))) / 2
    match = re.match(r"^>(\d+)$", text)
    if match:
        return float(match.group(1)) + 1
    return None


def median(vals):
    vals = sorted(v for v in vals if v is not None)
    if not vals:
        return None
    mid = len(vals) // 2
    if len(vals) % 2:
        return vals[mid]
    return (vals[mid - 1] + vals[mid]) / 2


def opponent_lookup():
    aliases = defaultdict(set)
    for row in json.loads((ROOT / "player_stats_participants.events.json").read_text()):
        game = row.get("game")
        event = row.get("event")
        page = row.get("page")
        if not game:
            continue
        for value in (event, page):
            if value:
                aliases[(game, event)].add(value)
                aliases[(game, page)].add(value)
    lookup = {}
    for row in json.loads((ROOT / "team_participation.json").read_text()):
        game = row.get("Game")
        event = row.get("Event")
        team = row.get("Team")
        if game not in GAMES or not event or not team:
            continue
        place = place_value(row.get("Place"))
        if place is None:
            continue
        event_names = aliases.get((game, event), {event})
        for event_name in event_names | {event}:
            lookup[(game, event_name, mkey(team))] = place
    return lookup


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


def empty_bucket():
    return {"kills": 0, "deaths": 0, "maps": 0, "events": set(), "opponent_places": [], "top8_maps": 0, "opponent_maps": 0}


def add(bucket, row, opponents):
    bucket["kills"] += int(row["Kills"])
    bucket["deaths"] += int(row["Deaths"])
    bucket["maps"] += 1
    if row.get("Event"):
        bucket["events"].add(row["Event"])
    opponent_place = opponents.get((row.get("Game"), row.get("Event"), mkey(row.get("TeamVs"))))
    if opponent_place is not None:
        bucket["opponent_places"].append(opponent_place)
        bucket["opponent_maps"] += 1
        if opponent_place <= 8:
            bucket["top8_maps"] += 1


def aggregate():
    rows = json.loads((ROOT / "player_stats_participants.json").read_text())
    opponents = opponent_lookup()
    by_game = {}
    for game in GAMES:
        by_player = defaultdict(lambda: {
            "overall": empty_bucket(),
            "respawn": empty_bucket(),
            "snd": empty_bucket(),
        })
        for row in rows:
            if row.get("Game") != game:
                continue
            player = row.get("Player") or row.get("PlayerLink") or row.get("PlayerName")
            if not player:
                continue
            split = "snd" if is_snd(row.get("Mode")) else "respawn"
            add(by_player[player]["overall"], row, opponents)
            add(by_player[player][split], row, opponents)
        players = []
        for player, splits in by_player.items():
            rec = {"player": player, "splits": {}}
            for split, bucket in splits.items():
                maps = bucket["maps"]
                kills = bucket["kills"]
                deaths = bucket["deaths"]
                rec["splits"][split] = {
                    "maps": maps,
                    "kills": kills,
                    "deaths": deaths,
                    "events": len(bucket["events"]),
                    "kpm": kills / maps if maps else None,
                    "kd": kills / deaths if deaths else None,
                    "median_opp_place": median(bucket["opponent_places"]),
                    "top8_opp_pct": bucket["top8_maps"] / bucket["opponent_maps"] if bucket["opponent_maps"] else None,
                    "opponent_maps": bucket["opponent_maps"],
                }
            players.append(rec)
        by_game[game] = players
    return by_game


def score_split(players, split):
    min_maps = SPLITS[split]["min_maps"]
    qualified = [p for p in players if p["splits"][split]["maps"] >= min_maps]
    repl = percentile([p["splits"][split]["kpm"] for p in qualified], REPLACEMENT_PERCENTILE)
    if repl is None:
        return {"replacement": None, "qualified": 0, "rows": []}
    scored = []
    for player in qualified:
        s = player["splits"][split]
        rate = s["kpm"] - repl
        scored.append({
            "player": player["player"],
            "maps": s["maps"],
            "events": s["events"],
            "kpm": s["kpm"],
            "kd": s["kd"],
            "median_opp_place": s["median_opp_place"],
            "top8_opp_pct": s["top8_opp_pct"],
            "opponent_maps": s["opponent_maps"],
            "rate": rate,
            "total": rate * s["maps"],
        })
    scored.sort(key=lambda r: r["rate"], reverse=True)
    return {"replacement": repl, "qualified": len(qualified), "rows": scored}


def score_all(by_game):
    return {game: {split: score_split(players, split) for split in SPLITS} for game, players in by_game.items()}


def fmt(value, digits=2):
    return "n/a" if value is None else f"{value:.{digits}f}"


def signed(value, digits=2):
    return "n/a" if value is None else f"{value:+.{digits}f}"


def pct(value):
    return "n/a" if value is None else f"{100 * value:.0f}%"


def bar_chart(score, title, n=10):
    rows = score["rows"][:n]
    if not rows:
        return ""
    max_val = max(abs(r["rate"]) for r in rows) or 1
    items = []
    for i, row in enumerate(rows, 1):
        width = 14 + abs(row["rate"]) / max_val * 78
        items.append(
            "<div class='bar-row'>"
            f"<div class='rank'>{i}</div>"
            f"<div class='bar-name'>{esc(row['player'])}</div>"
            "<div class='bar-track'>"
            f"<div class='bar-fill' style='width:{width:.1f}%'></div>"
            "</div>"
            f"<div class='bar-value'>{signed(row['rate'])}</div>"
            "</div>"
        )
    return f"<section class='viz'><h4>{esc(title)}</h4>{''.join(items)}</section>"


def distribution(score):
    rows = score["rows"]
    if not rows:
        return ""
    vals = [r["rate"] for r in rows]
    lo, hi = min(vals), max(vals)
    if lo == hi:
        hi = lo + 1
    bins = 18
    counts = [0] * bins
    for v in vals:
        idx = min(bins - 1, max(0, int((v - lo) / (hi - lo) * bins)))
        counts[idx] += 1
    max_count = max(counts) or 1
    bars = []
    for i, count in enumerate(counts):
        x = 44 + i * 32
        h = count / max_count * 112
        y = 132 - h
        bars.append(f"<rect x='{x}' y='{y:.1f}' width='24' height='{h:.1f}' rx='3'></rect>")
    zero = 44 + (0 - lo) / (hi - lo) * (bins * 32)
    return (
        "<svg class='hist' viewBox='0 0 660 168' role='img'>"
        f"<line x1='{zero:.1f}' x2='{zero:.1f}' y1='14' y2='138' class='zero'></line>"
        + "".join(bars)
        + f"<text x='44' y='158'>{signed(lo)}</text><text x='300' y='158'>0.00</text><text x='590' y='158'>{signed(hi)}</text>"
        + "</svg>"
    )


def table(score, n=12):
    rows = [
        "<table>",
        "<tr><th>Rank</th><th>Player</th><th>KOR/map</th><th>K/map</th><th>Total KOR</th><th>Maps</th><th>Events</th><th>K/D</th><th>Median opp place</th><th>Top-8 opp maps</th></tr>",
    ]
    for i, row in enumerate(score["rows"][:n], 1):
        rows.append(
            "<tr>"
            f"<td>{i}</td><td>{esc(row['player'])}</td><td class='num strong'>{signed(row['rate'])}</td>"
            f"<td class='num'>{fmt(row['kpm'])}</td><td class='num'>{signed(row['total'], 1)}</td>"
            f"<td class='num'>{row['maps']}</td><td class='num'>{row['events']}</td><td class='num'>{fmt(row['kd'], 3)}</td>"
            f"<td class='num'>{fmt(row['median_opp_place'], 1)}</td><td class='num'>{pct(row['top8_opp_pct'])}</td>"
            "</tr>"
        )
    rows.append("</table>")
    return "\n".join(rows)


def game_nav():
    return "<nav>" + "".join(f"<a href='#{re.sub('[^a-z0-9]+', '-', game.lower()).strip('-')}'>{esc(game)}</a>" for game in GAMES) + "</nav>"


def game_section(game, scores):
    cards = []
    for split, meta in SPLITS.items():
        score = scores[game][split]
        leader = score["rows"][0] if score["rows"] else None
        cards.append(
            "<div class='metric-card'>"
            f"<div class='label'>{esc(meta['label'])}</div>"
            f"<div class='value'>{fmt(score['replacement'])}</div>"
            f"<div class='sub'>replacement K/map · {score['qualified']} qualified</div>"
            f"<div class='leader'>{esc(leader['player']) if leader else 'n/a'} <span>{signed(leader['rate']) if leader else ''}</span></div>"
            "</div>"
        )
    blocks = []
    for split, meta in SPLITS.items():
        score = scores[game][split]
        blocks.append(
            "<section class='split-block'>"
            f"<div><h3>{esc(meta['label'])}</h3><p>{esc(meta['description'])} Replacement level is the 25th percentile among players with at least {meta['min_maps']} maps. Opponent context is display-only and does not change KOR.</p></div>"
            "<div class='split-grid'>"
            + bar_chart(score, "Top Kills Over Replacement per map")
            + "<section class='viz'><h4>Qualified-player distribution</h4>"
            + distribution(score)
            + "</section>"
            + "</div>"
            + table(score)
            + "</section>"
        )
    slug = re.sub("[^a-z0-9]+", "-", game.lower()).strip("-")
    return f"<section class='game' id='{slug}'><h2>{esc(game)}</h2><div class='cards'>{''.join(cards)}</div>{''.join(blocks)}</section>"


def build_html(scores):
    css = """
    :root{--bg:#f6f7f9;--ink:#111827;--muted:#5f6877;--line:#e2e6ec;--panel:#fff;--accent:#0f766e;--accent-soft:#ccfbf1;--dark:#172033}
    *{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
    header{background:#172033;color:white;padding:28px 28px 24px;border-bottom:4px solid #0f766e}
    .wrap{max-width:1260px;margin:0 auto}h1{font-size:34px;line-height:1.05;margin:0 0 10px;letter-spacing:0}header p{max-width:860px;color:#d8dee9;margin:0;line-height:1.45}
    nav{display:flex;gap:8px;flex-wrap:wrap;margin-top:18px}nav a{color:white;text-decoration:none;border:1px solid rgba(255,255,255,.24);border-radius:6px;padding:7px 10px;font-size:13px;background:rgba(255,255,255,.07)}
    main{max-width:1260px;margin:0 auto;padding:24px 28px 40px}.method{display:grid;grid-template-columns:1.3fr .7fr;gap:14px;margin-bottom:22px}
    .note,.formula{background:white;border:1px solid var(--line);border-radius:8px;padding:14px 16px}.formula code{display:block;background:#f1f5f9;border-radius:6px;padding:12px;line-height:1.5;white-space:normal}
    h2{font-size:27px;margin:36px 0 12px}h3{font-size:19px;margin:0 0 5px}h4{font-size:14px;margin:0 0 10px;color:#374151}
    p{color:var(--muted);line-height:1.45;margin:0}.cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:12px 0 18px}
    .metric-card{background:white;border:1px solid var(--line);border-radius:8px;padding:13px}.label{font-size:12px;text-transform:uppercase;color:#697386;letter-spacing:.04em}.value{font-size:29px;font-weight:760;margin-top:3px}.sub{font-size:12px;color:#697386}.leader{font-size:14px;margin-top:11px}.leader span{color:var(--accent);font-weight:760}
    .split-block{border-top:1px solid var(--line);padding-top:18px;margin-top:20px}.split-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:13px 0}
    .viz{background:white;border:1px solid var(--line);border-radius:8px;padding:13px;min-width:0}.bar-row{display:grid;grid-template-columns:26px 118px 1fr 56px;gap:8px;align-items:center;margin:8px 0}.rank{color:#697386;font-variant-numeric:tabular-nums}.bar-name{font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.bar-track{height:11px;background:#edf2f7;border-radius:999px;overflow:hidden}.bar-fill{height:100%;background:var(--accent);border-radius:999px}.bar-value{font-size:13px;text-align:right;font-variant-numeric:tabular-nums;color:#065f46;font-weight:700}
    .hist{width:100%;height:auto}.hist rect{fill:#0f766e;opacity:.82}.hist .zero{stroke:#334155;stroke-width:1.5;stroke-dasharray:4 4}.hist text{fill:#697386;font-size:12px}
    table{width:100%;border-collapse:collapse;background:white;border:1px solid var(--line);border-radius:8px;overflow:hidden;margin-top:10px}th,td{padding:8px 9px;border-bottom:1px solid #edf0f4;font-size:13px;text-align:left}th{background:#172033;color:white;font-weight:650}tr:last-child td{border-bottom:0}.num{text-align:right;font-variant-numeric:tabular-nums}.strong{font-weight:760;color:#065f46}
    @media(max-width:900px){header{padding:22px 16px}main{padding:18px 16px}.method,.cards,.split-grid{grid-template-columns:1fr}.bar-row{grid-template-columns:24px 92px 1fr 52px}}
    """
    html_doc = (
        "<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>Kills Over Replacement prototype</title><style>{css}</style></head><body>"
        "<header><div class='wrap'><h1>Kills Over Replacement</h1>"
        "<p>A narrow VOR-style prototype: kills per map above a title-and-mode replacement baseline. Respawn and S&D stay separate; no Overall score, role adjustment, interactions, or all-era score.</p>"
        + game_nav()
        + "</div></header><main>"
        "<section class='method'>"
        "<div class='note'><h3>What this is</h3><p>For each title and mode split, replacement level is the 25th percentile kills/map among qualified players. A player at +3.00 produced three more kills per map than that replacement baseline in the same title/split. Overall is intentionally excluded because respawn and S&D have different kill environments. Median opponent placement and top-8 opponent map rate are shown only to reveal schedule/bracket context.</p></div>"
        "<div class='formula'><h3>Formula</h3><code>KOR/map = player K/map - replacement K/map<br>Total KOR = KOR/map × maps played</code></div>"
        "</section>"
        + "".join(game_section(game, scores) for game in GAMES)
        + "</main></body></html>"
    )
    OUT_PATH.write_text(html_doc)


def print_summary(scores):
    for game in GAMES:
        print(f"\n{game}")
        for split, meta in SPLITS.items():
            score = scores[game][split]
            top = ", ".join(r["player"] for r in score["rows"][:5])
            print(f"  {meta['label']}: repl={fmt(score['replacement'])} q={score['qualified']} top5={top}")


def main():
    scores = score_all(aggregate())
    build_html(scores)
    print_summary(scores)
    print(f"\nWrote {OUT_PATH}")


if __name__ == "__main__":
    main()
