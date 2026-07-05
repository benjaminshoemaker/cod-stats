#!/usr/bin/env python3
"""Generate an Advanced Warfare title-wide rate-over-replacement pilot report."""
import html
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path


GAME = "Advanced Warfare"
REPLACEMENT_PERCENTILE = 0.25
ROLES = ("AR", "Flex", "SMG")
DISPLAY_ROLES = ("AR", "Flex", "SMG", "Unknown")
SPLITS = {
    "overall": {"label": "Overall", "min_maps": 20},
    "respawn": {"label": "Respawn", "min_maps": 14},
    "snd": {"label": "S&D", "min_maps": 5},
}
ROLE_COLORS = {"AR": "#2563eb", "Flex": "#7c3aed", "SMG": "#dc2626", "Unknown": "#6b7280"}


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


def aggregate(resolve_role):
    players = defaultdict(lambda: {
        "overall": empty_bucket(),
        "respawn": empty_bucket(),
        "snd": empty_bucket(),
    })
    for row in json.loads(Path("player_stats_participants.json").read_text()):
        if row.get("Game") != GAME:
            continue
        player = row.get("Player") or row.get("PlayerLink") or row.get("PlayerName")
        if not player:
            continue
        split = "snd" if is_snd(row.get("Mode")) else "respawn"
        add_stat(players[player]["overall"], row)
        add_stat(players[player][split], row)

    out = []
    for player, splits in players.items():
        rec = {"player": player, "role": resolve_role(player, GAME), "splits": {}}
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
        out.append(rec)
    return out


def score_split(players, split):
    min_maps = SPLITS[split]["min_maps"]
    qualified = [p for p in players if p["splits"][split]["maps"] >= min_maps]
    baselines = {
        "All": {
            "players": len(qualified),
            "kills_per_map": percentile([p["splits"][split]["kpm"] for p in qualified], REPLACEMENT_PERCENTILE),
            "interactions_per_map": percentile([p["splits"][split]["ipm"] for p in qualified], REPLACEMENT_PERCENTILE),
        }
    }

    scored = []
    for player in qualified:
        stats = player["splits"][split]
        baseline = baselines["All"]
        if baseline["kills_per_map"] is None or baseline["interactions_per_map"] is None:
            continue
        row = {
            **{k: v for k, v in stats.items() if k != "events"},
            "player": player["player"],
            "role": player["role"],
            "events": stats["events"],
            "kills_over_repl_per_map": stats["kpm"] - baseline["kills_per_map"],
            "interactions_over_repl_per_map": stats["ipm"] - baseline["interactions_per_map"],
        }
        row["kills_over_repl_total"] = row["kills_over_repl_per_map"] * stats["maps"]
        row["interactions_over_repl_total"] = row["interactions_over_repl_per_map"] * stats["maps"]
        scored.append(row)
    return qualified, scored, baselines


def esc(value):
    return html.escape(str(value))


def scale(values, lo_px, hi_px, pad=0):
    lo = min(values)
    hi = max(values)
    if lo == hi:
        return lambda _: (lo_px + hi_px) / 2
    lo -= pad
    hi += pad
    return lambda v: lo_px + (v - lo) / (hi - lo) * (hi_px - lo_px)


def legend_items():
    out = []
    for i, role in enumerate(DISPLAY_ROLES):
        y = i * 20
        out.append(f'<rect x="0" y="{y}" width="12" height="12" fill="{ROLE_COLORS[role]}" rx="2"></rect>')
        out.append(f'<text x="18" y="{y + 10}" class="axis">{role}</text>')
    return "".join(out)


def bar_chart(rows, metric, title, width=920, row_h=28):
    rows = rows[:12]
    label_w, right_pad = 150, 150
    chart_w = width - label_w - right_pad
    height = 44 + row_h * len(rows)
    lo = min(0, min(r[metric] for r in rows))
    hi = max(r[metric] for r in rows)
    span = hi - lo if hi != lo else 1
    zero_x = label_w + (0 - lo) / span * chart_w
    parts = [f'<h3>{esc(title)}</h3><svg viewBox="0 0 {width} {height}" class="chart" role="img">']
    parts.append(f'<line x1="{zero_x:.1f}" y1="34" x2="{zero_x:.1f}" y2="{height - 8}" class="zero"></line>')
    for i, row in enumerate(rows):
        y = 38 + i * row_h
        x1 = label_w + (min(0, row[metric]) - lo) / span * chart_w
        x2 = label_w + (max(0, row[metric]) - lo) / span * chart_w
        color = ROLE_COLORS[row["role"]]
        parts.append(f'<text x="0" y="{y + 16}" class="label">{esc(row["player"])}</text>')
        parts.append(f'<rect x="{x1:.1f}" y="{y}" width="{max(1, x2 - x1):.1f}" height="18" fill="{color}" rx="3"></rect>')
        parts.append(f'<text x="{max(x1, x2) + 8:.1f}" y="{y + 14}" class="value">{row[metric]:+.2f}/map · {row["role"]} · {row["maps"]} maps</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def histogram(rows, metric, title, width=920, height=230):
    vals = [r[metric] for r in rows]
    lo, hi = min(vals), max(vals)
    bins = 18
    step = (hi - lo) / bins if hi != lo else 1
    counts = {role: [0] * bins for role in DISPLAY_ROLES}
    for row in rows:
        idx = min(bins - 1, max(0, int((row[metric] - lo) / step)))
        counts[row["role"]][idx] += 1
    max_count = max(max(v) for v in counts.values()) or 1
    plot_x, plot_y, plot_w, plot_h = 52, 24, width - 86, height - 70
    bw = plot_w / bins
    parts = [f'<h3>{esc(title)}</h3><svg viewBox="0 0 {width} {height}" class="chart" role="img">']
    parts.append(f'<line x1="{plot_x}" y1="{plot_y + plot_h}" x2="{plot_x + plot_w}" y2="{plot_y + plot_h}" class="grid"></line>')
    for b in range(bins):
        x = plot_x + b * bw
        slot = bw / len(DISPLAY_ROLES)
        for ri, role in enumerate(DISPLAY_ROLES):
            h = counts[role][b] / max_count * plot_h
            parts.append(f'<rect x="{x + ri * slot:.1f}" y="{plot_y + plot_h - h:.1f}" width="{max(1, slot - 2):.1f}" height="{h:.1f}" fill="{ROLE_COLORS[role]}" opacity="0.78"></rect>')
    zero = plot_x + (0 - lo) / (hi - lo if hi != lo else 1) * plot_w
    parts.append(f'<line x1="{zero:.1f}" y1="{plot_y}" x2="{zero:.1f}" y2="{plot_y + plot_h}" class="zero"></line>')
    parts.append(f'<text x="{plot_x}" y="{height - 20}" class="axis">{lo:+.2f}/map</text>')
    parts.append(f'<text x="{plot_x + plot_w - 70}" y="{height - 20}" class="axis">{hi:+.2f}/map</text>')
    parts.append('<g transform="translate(690 8)">' + legend_items() + '</g>')
    parts.append("</svg>")
    return "\n".join(parts)


def scatter(rows, split, width=920, height=470):
    x = scale([r["kills_over_repl_per_map"] for r in rows], 70, width - 44, pad=0.2)
    y = scale([r["interactions_over_repl_per_map"] for r in rows], height - 58, 30, pad=0.4)
    top_names = {r["player"] for r in sorted(rows, key=lambda r: r["kills_over_repl_per_map"] + r["interactions_over_repl_per_map"], reverse=True)[:12]}
    parts = [f'<h3>{esc(SPLITS[split]["label"])} K/map vs interactions/map over replacement</h3><svg viewBox="0 0 {width} {height}" class="chart" role="img">']
    zero_x = x(0)
    zero_y = y(0)
    parts.append(f'<line x1="70" y1="{zero_y:.1f}" x2="{width - 44}" y2="{zero_y:.1f}" class="zero"></line>')
    parts.append(f'<line x1="{zero_x:.1f}" y1="30" x2="{zero_x:.1f}" y2="{height - 58}" class="zero"></line>')
    parts.append(f'<text x="{width / 2 - 90:.0f}" y="{height - 16}" class="axis">Kills over replacement per map</text>')
    parts.append(f'<text x="12" y="26" class="axis">Interactions over replacement per map</text>')
    for row in sorted(rows, key=lambda r: r["maps"]):
        radius = max(3, min(10, row["maps"] / 16))
        parts.append(f'<circle cx="{x(row["kills_over_repl_per_map"]):.1f}" cy="{y(row["interactions_over_repl_per_map"]):.1f}" r="{radius:.1f}" fill="{ROLE_COLORS[row["role"]]}" opacity="0.72"><title>{esc(row["player"])} · {row["role"]} · K/map over repl {row["kills_over_repl_per_map"]:+.2f} · Int/map over repl {row["interactions_over_repl_per_map"]:+.2f}</title></circle>')
        if row["player"] in top_names:
            parts.append(f'<text x="{x(row["kills_over_repl_per_map"]) + 7:.1f}" y="{y(row["interactions_over_repl_per_map"]) - 5:.1f}" class="point-label">{esc(row["player"])}</text>')
    parts.append('<g transform="translate(690 12)">' + legend_items() + '</g>')
    parts.append("</svg>")
    return "\n".join(parts)


def baseline_table(baselines):
    rows = []
    for name, b in baselines.items():
        if not b["players"]:
            continue
        rows.append(f"<tr><td>{name}</td><td>{b['players']}</td><td>{b['kills_per_map']:.2f}</td><td>{b['interactions_per_map']:.2f}</td></tr>")
    return "<table><tr><th>Baseline</th><th>Qualified players</th><th>Replacement K/map</th><th>Replacement Int/map</th></tr>" + "".join(rows) + "</table>"


def player_table(rows, include_interactions):
    if include_interactions:
        head = "<tr><th>Player</th><th>Role</th><th>Maps</th><th>K/D</th><th>K/map +/-</th><th>Int/map +/-</th><th>Total K +/-</th><th>Total Int +/-</th></tr>"
    else:
        head = "<tr><th>Player</th><th>Role</th><th>Maps</th><th>K/D</th><th>K/map +/-</th><th>Total K +/-</th></tr>"
    body = []
    for row in rows[:24]:
        cells = (
            f"<td>{esc(row['player'])}</td><td>{row['role']}</td><td>{row['maps']}</td><td>{row['kd']:.3f}</td>"
            f"<td>{row['kills_over_repl_per_map']:+.2f}</td>"
        )
        if include_interactions:
            cells += f"<td>{row['interactions_over_repl_per_map']:+.2f}</td>"
        cells += f"<td>{row['kills_over_repl_total']:+.1f}</td>"
        if include_interactions:
            cells += f"<td>{row['interactions_over_repl_total']:+.1f}</td>"
        body.append("<tr>" + cells + "</tr>")
    return "<table>" + head + "".join(body) + "</table>"


def split_section(split, scored, baselines):
    label = SPLITS[split]["label"]
    top_k = sorted(scored, key=lambda r: r["kills_over_repl_per_map"], reverse=True)
    top_combo = sorted(scored, key=lambda r: r["kills_over_repl_per_map"] + r["interactions_over_repl_per_map"], reverse=True)
    if split == "snd":
        return f"""
<section>
<h2>{esc(label)} kills</h2>
<p>Ranked by K/map above a title-wide replacement baseline. Interactions are intentionally omitted here because S&D interaction volume is not treated as a value metric in this prototype. Minimum maps for this split: {SPLITS[split]['min_maps']}.</p>
{baseline_table(baselines)}
{histogram(scored, "kills_over_repl_per_map", f"{label} K/map over replacement distribution")}
{bar_chart(top_k, "kills_over_repl_per_map", f"Top {label} K/map over replacement")}
<h3>Top S&D K/map table</h3>
{player_table(top_k, include_interactions=False)}
</section>
"""
    if split == "respawn":
        top_i = sorted(scored, key=lambda r: r["interactions_over_repl_per_map"], reverse=True)
        return f"""
<section>
<h2>{esc(label)} kills and pressure</h2>
<p>Respawn uses both K/map over replacement and interactions/map over replacement. Interactions are treated as a pressure/pace signal here because respawn modes reward sustained engagements, trades, breaks, and map pressure. Minimum maps for this split: {SPLITS[split]['min_maps']}.</p>
{baseline_table(baselines)}
{histogram(scored, "kills_over_repl_per_map", f"{label} K/map over replacement distribution")}
{histogram(scored, "interactions_over_repl_per_map", f"{label} interactions/map over replacement distribution")}
{scatter(scored, split)}
<div class="twocol">
  <div>{bar_chart(top_k, "kills_over_repl_per_map", f"Top {label} K/map over replacement")}</div>
  <div>{bar_chart(top_i, "interactions_over_repl_per_map", f"Top {label} interactions/map over replacement")}</div>
</div>
<h3>Top respawn combined rate table</h3>
{player_table(top_combo, include_interactions=True)}
</section>
"""
    return f"""
<section>
<h2>{esc(label)} kills</h2>
<p>Ranked by K/map above a title-wide replacement baseline. Overall interactions are not emphasized because their meaning is mixed across respawn and S&D. Minimum maps for this split: {SPLITS[split]['min_maps']}.</p>
{baseline_table(baselines)}
{histogram(scored, "kills_over_repl_per_map", f"{label} K/map over replacement distribution")}
{bar_chart(top_k, "kills_over_repl_per_map", f"Top {label} K/map over replacement")}
<h3>Top overall K/map table</h3>
{player_table(top_k, include_interactions=False)}
</section>
"""


def page(players, split_data):
    role_counts = Counter(p["role"] for p in players)
    cards = []
    for split, data in split_data.items():
        cards.append(f'<div class="card"><div class="k">{esc(SPLITS[split]["label"])} scored</div><div class="v">{len(data["scored"])}</div><div class="sub">min {SPLITS[split]["min_maps"]} maps</div></div>')
    sections = "\n".join(split_section(split, data["scored"], data["baselines"]) for split, data in split_data.items())
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Advanced Warfare title-wide rate VOR pilot</title>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;margin:0;background:#f7f8fb;color:#111827}}
main{{max-width:1120px;margin:0 auto;padding:28px 18px 56px}}
h1{{font-size:32px;margin:0 0 8px}} h2{{font-size:22px;margin:36px 0 10px}} h3{{font-size:16px;margin:22px 0 8px}} p{{color:#4b5563;line-height:1.5}}
.cards{{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;margin:18px 0}}
.card{{background:white;border:1px solid #d8dee8;border-radius:8px;padding:12px}} .k{{font-size:12px;color:#6b7280;font-weight:700;text-transform:uppercase}} .v{{font-size:24px;font-weight:800;margin-top:4px}} .sub{{font-size:12px;color:#6b7280}}
.twocol{{display:grid;grid-template-columns:1fr;gap:14px}}
.chart{{background:white;border:1px solid #d8dee8;border-radius:8px;padding:10px;box-sizing:border-box}}
.label{{font-size:13px;fill:#111827;font-weight:700}} .value,.axis{{font-size:12px;fill:#4b5563}} .point-label{{font-size:11px;fill:#111827;font-weight:700}} .grid{{stroke:#cfd6e3;stroke-width:1}} .zero{{stroke:#111827;stroke-width:1;opacity:.32;stroke-dasharray:4 4}}
table{{width:100%;border-collapse:collapse;background:white;border:1px solid #d8dee8;border-radius:8px;overflow:hidden;margin:10px 0 14px}} th,td{{padding:8px 9px;border-bottom:1px solid #e5eaf2;text-align:left;font-size:13px}} th{{background:#eef2f7;color:#4b5563;text-transform:uppercase;font-size:11px}}
section{{border-top:1px solid #d8dee8;margin-top:32px;padding-top:4px}}
@media(max-width:860px){{.cards{{grid-template-columns:1fr 1fr}} table{{display:block;overflow-x:auto}}}}
</style>
</head>
<body><main>
<h1>Advanced Warfare title-wide rate VOR pilot</h1>
<p>This version focuses on rate above replacement, not total volume. K/map over replacement is shown for Overall, Respawn, and S&D. Interactions/map over replacement is shown only for Respawn, where engagement volume is a pressure/pace signal. Baselines are title-wide because the replacement pool does not have complete role coverage; known roles from <code>player_roles.json</code> are shown only as visual context.</p>
<div class="cards">
  <div class="card"><div class="k">AW stat players</div><div class="v">{len(players)}</div></div>
  <div class="card"><div class="k">Known-role players</div><div class="v">{sum(role_counts[r] for r in ROLES)}</div></div>
  <div class="card"><div class="k">Unknown-role players</div><div class="v">{role_counts['Unknown']}</div></div>
  {''.join(cards)}
</div>
<p>Role counts: {dict(role_counts)}</p>
{sections}
</main></body></html>"""


def main():
    resolve = role_resolver(game_order())
    players = aggregate(resolve)
    split_data = {}
    for split in SPLITS:
        qualified, scored, baselines = score_split(players, split)
        split_data[split] = {"qualified": qualified, "scored": scored, "baselines": baselines}
    Path("analysis/advanced_warfare_vor.html").write_text(page(players, split_data))
    print("wrote analysis/advanced_warfare_vor.html")
    print("role counts", dict(Counter(p["role"] for p in players)))
    for split, data in split_data.items():
        print(f"\n{SPLITS[split]['label']}: scored={len(data['scored'])} min_maps={SPLITS[split]['min_maps']}")
        b = data["baselines"]["All"]
        print(f"  All: n={b['players']} repl_kpm={b['kills_per_map']:.2f} repl_ipm={b['interactions_per_map']:.2f}")
        print("  Top K/map over replacement")
        for row in sorted(data["scored"], key=lambda r: r["kills_over_repl_per_map"], reverse=True)[:8]:
            print(f"    {row['player']:14} {row['role']:4} {row['kills_over_repl_per_map']:+.2f}/map int={row['interactions_over_repl_per_map']:+.2f}/map maps={row['maps']:3d} K/D={row['kd']:.3f}")
        if split == "respawn":
            print("  Top Respawn Int/map over replacement")
            for row in sorted(data["scored"], key=lambda r: r["interactions_over_repl_per_map"], reverse=True)[:8]:
                print(f"    {row['player']:14} {row['role']:4} {row['interactions_over_repl_per_map']:+.2f}/map k={row['kills_over_repl_per_map']:+.2f}/map maps={row['maps']:3d} K/D={row['kd']:.3f}")


if __name__ == "__main__":
    main()
