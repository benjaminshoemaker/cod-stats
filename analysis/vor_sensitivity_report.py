#!/usr/bin/env python3
"""Multi-title VOR sensitivity report for kills and respawn pressure rates."""
import html
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path


GAMES = ["Black Ops 2", "Advanced Warfare", "Infinite Warfare", "Black Ops 6"]
REPLACEMENT_PERCENTILE = 0.25
THRESHOLDS = {
    "low": {"overall": 12, "respawn": 8, "snd": 4},
    "base": {"overall": 20, "respawn": 14, "snd": 5},
    "high": {"overall": 40, "respawn": 28, "snd": 10},
}
SPLITS = {
    "overall": "Overall K/map",
    "respawn_kills": "Respawn K/map",
    "respawn_interactions": "Respawn interactions/map",
    "snd": "S&D K/map",
}
ROLE_COLORS = {"AR": "#2563eb", "Flex": "#7c3aed", "SMG": "#dc2626", "Unknown": "#6b7280"}
ROLES = ("AR", "Flex", "SMG")
DISPLAY_ROLES = ("AR", "Flex", "SMG", "Unknown")


def mkey(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def is_snd(mode):
    text = str(mode or "").lower().replace("&", "and")
    return "search" in text and "destroy" in text


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
    return {"kills": 0, "deaths": 0, "maps": 0, "events": set()}


def add_stat(bucket, row):
    bucket["kills"] += int(row["Kills"])
    bucket["deaths"] += int(row["Deaths"])
    bucket["maps"] += 1
    if row.get("Event"):
        bucket["events"].add(row["Event"])


def game_order():
    seen, out = set(), []
    rows = sorted(json.loads(Path("major_events.json").read_text()), key=lambda r: r.get("Date") or "")
    for row in rows:
        game = row.get("Game")
        if game and game not in seen:
            seen.add(game)
            out.append(game)
    return {game: i for i, game in enumerate(out)}


def role_resolver(order):
    by_player = defaultdict(list)
    for row in json.loads(Path("player_roles.json").read_text()).get("roles", []):
        player = row.get("player")
        role = row.get("role")
        if not player or role not in ROLES:
            continue
        start = order.get(row.get("start_game"), 0) if row.get("start_game") else 0
        end = order.get(row.get("end_game"), len(order) - 1) if row.get("end_game") else len(order) - 1
        by_player[mkey(player)].append((start, end, role))

    def resolve(player, game):
        gi = order[game]
        matches = [role for start, end, role in by_player.get(mkey(player), []) if start <= gi <= end]
        return matches[0] if len(matches) == 1 else "Unknown"

    return resolve


def aggregate(rows, resolve_role):
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
            add_stat(by_player[player]["overall"], row)
            add_stat(by_player[player][split], row)
        players = []
        for player, splits in by_player.items():
            rec = {"player": player, "role": resolve_role(player, game), "splits": {}}
            for split, bucket in splits.items():
                kills = bucket["kills"]
                deaths = bucket["deaths"]
                maps = bucket["maps"]
                interactions = kills + deaths
                rec["splits"][split] = {
                    "kills": kills,
                    "deaths": deaths,
                    "maps": maps,
                    "events": len(bucket["events"]),
                    "interactions": interactions,
                    "kd": kills / deaths if deaths else None,
                    "kpm": kills / maps if maps else None,
                    "ipm": interactions / maps if maps else None,
                }
            players.append(rec)
        by_game[game] = players
    return by_game


def score_metric(players, metric, threshold):
    split = "respawn" if metric.startswith("respawn") else ("snd" if metric == "snd" else "overall")
    stat = "ipm" if metric == "respawn_interactions" else "kpm"
    qualified = [p for p in players if p["splits"][split]["maps"] >= threshold]
    repl = percentile([p["splits"][split][stat] for p in qualified], REPLACEMENT_PERCENTILE)
    rows = []
    if repl is None:
        return {"replacement": None, "qualified": 0, "rows": []}
    for player in qualified:
        s = player["splits"][split]
        val = s[stat] - repl
        rows.append({
            "player": player["player"],
            "role": player["role"],
            "maps": s["maps"],
            "events": s["events"],
            "kd": s["kd"],
            "kpm": s["kpm"],
            "ipm": s["ipm"],
            "rate_over_repl": val,
            "total_over_repl": val * s["maps"],
        })
    rows.sort(key=lambda r: r["rate_over_repl"], reverse=True)
    return {"replacement": repl, "qualified": len(qualified), "rows": rows}


def score_all(by_game):
    out = {}
    for game, players in by_game.items():
        out[game] = {}
        for tier, thresholds in THRESHOLDS.items():
            out[game][tier] = {
                "overall": score_metric(players, "overall", thresholds["overall"]),
                "respawn_kills": score_metric(players, "respawn_kills", thresholds["respawn"]),
                "respawn_interactions": score_metric(players, "respawn_interactions", thresholds["respawn"]),
                "snd": score_metric(players, "snd", thresholds["snd"]),
            }
    return out


def esc(value):
    return html.escape(str(value))


def role_counts(players):
    return Counter(p["role"] for p in players)


def top_names(score, n=10):
    return [r["player"] for r in score["rows"][:n]]


def stability_rows(scores, game, metric):
    low = top_names(scores[game]["low"][metric])
    base = top_names(scores[game]["base"][metric])
    high = top_names(scores[game]["high"][metric])
    union = []
    for name in low + base + high:
        if name not in union:
            union.append(name)
    rows = []
    for name in union:
        rows.append(
            "<tr>"
            f"<td>{esc(name)}</td>"
            f"<td>{low.index(name)+1 if name in low else ''}</td>"
            f"<td>{base.index(name)+1 if name in base else ''}</td>"
            f"<td>{high.index(name)+1 if name in high else ''}</td>"
            "</tr>"
        )
    return "<table><tr><th>Player</th><th>Low</th><th>Base</th><th>High</th></tr>" + "".join(rows) + "</table>"


def score_table(score, metric, n=12):
    label = "/map"
    head = "<tr><th>Player</th><th>Role</th><th>Maps</th><th>K/D</th><th>Rate +/-</th><th>Total +/-</th></tr>"
    rows = []
    for row in score["rows"][:n]:
        rows.append(
            "<tr>"
            f"<td>{esc(row['player'])}</td><td>{esc(row['role'])}</td><td>{row['maps']}</td>"
            f"<td>{row['kd']:.3f}</td><td>{row['rate_over_repl']:+.2f}{label}</td><td>{row['total_over_repl']:+.1f}</td>"
            "</tr>"
        )
    return "<table>" + head + "".join(rows) + "</table>"


def scatter(scores, game, tier="base", width=920, height=430):
    kills = {r["player"]: r for r in scores[game][tier]["respawn_kills"]["rows"]}
    ints = {r["player"]: r for r in scores[game][tier]["respawn_interactions"]["rows"]}
    names = [n for n in kills if n in ints]
    if not names:
        return ""
    xs = [kills[n]["rate_over_repl"] for n in names]
    ys = [ints[n]["rate_over_repl"] for n in names]
    lo_x, hi_x = min(xs) - 0.25, max(xs) + 0.25
    lo_y, hi_y = min(ys) - 0.35, max(ys) + 0.35
    def sx(v): return 70 + (v - lo_x) / (hi_x - lo_x) * (width - 114)
    def sy(v): return height - 58 - (v - lo_y) / (hi_y - lo_y) * (height - 88)
    zero_x = sx(0)
    zero_y = sy(0)
    top = set(top_names(scores[game][tier]["respawn_interactions"], 8) + top_names(scores[game][tier]["respawn_kills"], 8))
    parts = [f'<svg viewBox="0 0 {width} {height}" class="chart" role="img">']
    parts.append(f'<line x1="70" y1="{zero_y:.1f}" x2="{width-44}" y2="{zero_y:.1f}" class="zero"></line>')
    parts.append(f'<line x1="{zero_x:.1f}" y1="30" x2="{zero_x:.1f}" y2="{height-58}" class="zero"></line>')
    parts.append(f'<text x="{width/2-90:.0f}" y="{height-16}" class="axis">Respawn K/map +/-</text>')
    parts.append('<text x="12" y="26" class="axis">Respawn interactions/map +/-</text>')
    for name in names:
        row = kills[name]
        color = ROLE_COLORS.get(row["role"], ROLE_COLORS["Unknown"])
        radius = max(3, min(9, row["maps"] / 18))
        parts.append(f'<circle cx="{sx(kills[name]["rate_over_repl"]):.1f}" cy="{sy(ints[name]["rate_over_repl"]):.1f}" r="{radius:.1f}" fill="{color}" opacity="0.72"><title>{esc(name)} · K {kills[name]["rate_over_repl"]:+.2f}/map · Int {ints[name]["rate_over_repl"]:+.2f}/map</title></circle>')
        if name in top:
            parts.append(f'<text x="{sx(kills[name]["rate_over_repl"])+7:.1f}" y="{sy(ints[name]["rate_over_repl"])-5:.1f}" class="point-label">{esc(name)}</text>')
    parts.append("</svg>")
    return "".join(parts)


def game_section(game, players, scores):
    counts = dict(role_counts(players))
    cards = []
    for metric in SPLITS:
        s = scores[game]["base"][metric]
        cards.append(f'<div class="card"><div class="k">{esc(SPLITS[metric])}</div><div class="v">{s["qualified"]}</div><div class="sub">base qualified</div></div>')
    blocks = []
    for metric, label in SPLITS.items():
        base = scores[game]["base"][metric]
        blocks.append(
            f"<h3>{esc(label)} sensitivity</h3>"
            f"<p>Replacement at base threshold: {base['replacement']:.2f}/map. Top-10 rank stability across low/base/high minimum-map filters.</p>"
            f"{stability_rows(scores, game, metric)}"
            f"<h4>Base threshold top {esc(label)}</h4>"
            f"{score_table(base, metric)}"
        )
    return f"""
<section>
<h2>{esc(game)}</h2>
<p>Role context: {esc(counts)}. Baselines are title-wide. Low/base/high thresholds: overall {THRESHOLDS['low']['overall']}/{THRESHOLDS['base']['overall']}/{THRESHOLDS['high']['overall']}, respawn {THRESHOLDS['low']['respawn']}/{THRESHOLDS['base']['respawn']}/{THRESHOLDS['high']['respawn']}, S&D {THRESHOLDS['low']['snd']}/{THRESHOLDS['base']['snd']}/{THRESHOLDS['high']['snd']} maps.</p>
<div class="cards">{''.join(cards)}</div>
<h3>Base respawn pressure map</h3>
{scatter(scores, game)}
{''.join(blocks)}
</section>
"""


def page(by_game, scores):
    sections = "\n".join(game_section(game, by_game[game], scores) for game in GAMES)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>VOR sensitivity pilot</title>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;margin:0;background:#f7f8fb;color:#111827}}
main{{max-width:1120px;margin:0 auto;padding:28px 18px 56px}}
h1{{font-size:32px;margin:0 0 8px}} h2{{font-size:24px;margin:38px 0 10px}} h3{{font-size:17px;margin:24px 0 8px}} h4{{font-size:14px;margin:14px 0 6px}} p{{color:#4b5563;line-height:1.5}}
.cards{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:14px 0}}
.card{{background:white;border:1px solid #d8dee8;border-radius:8px;padding:12px}} .k{{font-size:12px;color:#6b7280;font-weight:700;text-transform:uppercase}} .v{{font-size:24px;font-weight:800;margin-top:4px}} .sub{{font-size:12px;color:#6b7280}}
.chart{{background:white;border:1px solid #d8dee8;border-radius:8px;padding:10px;box-sizing:border-box}} .axis{{font-size:12px;fill:#4b5563}} .point-label{{font-size:11px;fill:#111827;font-weight:700}} .zero{{stroke:#111827;stroke-width:1;opacity:.32;stroke-dasharray:4 4}}
table{{width:100%;border-collapse:collapse;background:white;border:1px solid #d8dee8;border-radius:8px;overflow:hidden;margin:8px 0 12px}} th,td{{padding:8px 9px;border-bottom:1px solid #e5eaf2;text-align:left;font-size:13px}} th{{background:#eef2f7;color:#4b5563;text-transform:uppercase;font-size:11px}}
section{{border-top:1px solid #d8dee8;margin-top:34px;padding-top:4px}}
@media(max-width:860px){{.cards{{grid-template-columns:1fr 1fr}} table{{display:block;overflow-x:auto}}}}
</style>
</head>
<body><main>
<h1>VOR sensitivity pilot</h1>
<p>Title-wide rate-over-replacement checks for {', '.join(esc(g) for g in GAMES)}. Kills are evaluated for Overall, Respawn, and S&D. Interactions are evaluated only for Respawn as a pressure/pace metric. Each table compares low/base/high minimum-map filters to expose fragile names.</p>
{sections}
</main></body></html>"""


def main():
    rows = json.loads(Path("player_stats_participants.json").read_text())
    by_game = aggregate(rows, role_resolver(game_order()))
    scores = score_all(by_game)
    Path("analysis/vor_sensitivity.html").write_text(page(by_game, scores))
    print("wrote analysis/vor_sensitivity.html")
    for game in GAMES:
        print(f"\n{game}")
        for metric, label in SPLITS.items():
            base = scores[game]["base"][metric]
            names = ", ".join(top_names(base, 5))
            print(f"  {label}: q={base['qualified']} repl={base['replacement']:.2f}/map top={names}")


if __name__ == "__main__":
    main()
