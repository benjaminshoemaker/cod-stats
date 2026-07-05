#!/usr/bin/env python3
"""Validate pilot VOR leaders against placement outcomes and award recognition."""
import html
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

import vor_sensitivity_report as vor


TOP_N = 10
TIER = "high"
OUT_PATH = Path("analysis/vor_validation.html")


def esc(value):
    return html.escape(str(value))


def mkey(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def place_value(row):
    raw = row.get("PlaceNumber") or row.get("Place")
    if raw is None:
        return None
    text = str(raw).strip()
    if text.isdigit():
        return int(text)
    match = re.match(r"^(\d+)\s*-\s*(\d+)$", text)
    if match:
        return (int(match.group(1)) + int(match.group(2))) / 2
    match = re.match(r"^>(\d+)$", text)
    if match:
        return int(match.group(1)) + 1
    return None


def load_outcomes():
    outcomes = defaultdict(lambda: defaultdict(lambda: {
        "events": 0,
        "wins": 0,
        "finals": 0,
        "top4": 0,
        "places": [],
        "teams": set(),
    }))
    for row in json.loads(Path("player_participation.json").read_text()):
        game = row.get("Game")
        if game not in vor.GAMES:
            continue
        player = row.get("Player")
        key = mkey(player)
        if not key:
            continue
        place = place_value(row)
        if place is None:
            continue
        rec = outcomes[game][key]
        rec["name"] = player
        rec["events"] += 1
        rec["wins"] += int(place == 1)
        rec["finals"] += int(place <= 2)
        rec["top4"] += int(place <= 4)
        rec["places"].append(place)
        if row.get("Team"):
            rec["teams"].add(row["Team"])
    for game_records in outcomes.values():
        for rec in game_records.values():
            rec["avg_place"] = sum(rec["places"]) / len(rec["places"]) if rec["places"] else None
            rec["teams"] = sorted(rec["teams"])
    return outcomes


def load_awards():
    awards = defaultdict(lambda: defaultdict(list))
    for row in json.loads(Path("player_accolades.json").read_text()):
        game = row.get("Game")
        player = row.get("PlayerLink") or row.get("Player")
        if game not in vor.GAMES or not player:
            continue
        awards[game][mkey(player)].append(row)
    return awards


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


def top_outcome_sets(game_outcomes):
    eligible = [rec for rec in game_outcomes.values() if rec["events"] >= 2]
    by_wins = sorted(eligible, key=lambda r: (-r["wins"], -r["finals"], r["avg_place"], r["name"]))
    by_avg = sorted(eligible, key=lambda r: (r["avg_place"], -r["wins"], r["name"]))
    return {
        "wins": {mkey(r["name"]) for r in by_wins[:TOP_N]},
        "avg_place": {mkey(r["name"]) for r in by_avg[:TOP_N]},
    }


def award_summary(rows):
    counts = Counter(row.get("Type") or "Award" for row in rows)
    return ", ".join(f"{name} x{count}" if count > 1 else name for name, count in sorted(counts.items()))


def validate_metric(game, metric, score, outcomes, awards):
    rows = score["rows"]
    game_outcomes = outcomes[game]
    game_awards = awards[game]
    outcome_sets = top_outcome_sets(game_outcomes)
    top_rows = rows[:TOP_N]
    top_keys = [mkey(r["player"]) for r in top_rows]
    award_keys = set(game_awards)
    all_keys = [mkey(r["player"]) for r in rows]

    xs, avg_places, wins, top4s, award_counts = [], [], [], [], []
    for row in rows:
        key = mkey(row["player"])
        outcome = game_outcomes.get(key, {})
        xs.append(row["rate_over_repl"])
        avg_places.append(outcome.get("avg_place"))
        wins.append(outcome.get("wins", 0))
        top4s.append(outcome.get("top4", 0))
        award_counts.append(len(game_awards.get(key, [])))

    # Lower average placement is better, so negate it for a positive "better outcome" coefficient.
    neg_avg_places = [-p if p is not None else None for p in avg_places]
    return {
        "top_rows": top_rows,
        "top_keys": top_keys,
        "top_wins_overlap": len(set(top_keys) & outcome_sets["wins"]),
        "top_avg_place_overlap": len(set(top_keys) & outcome_sets["avg_place"]),
        "top_award_overlap": len(set(top_keys) & award_keys),
        "award_coverage": len(award_keys),
        "corr_avg_place": corr(xs, neg_avg_places),
        "corr_wins": corr(xs, wins),
        "corr_top4": corr(xs, top4s),
        "corr_awards": corr(xs, award_counts),
        "award_rank_overlap": len(set(all_keys[:TOP_N]) & award_keys),
    }


def fmt_corr(value):
    return "n/a" if value is None else f"{value:+.2f}"


def fmt_place(value):
    return "" if value is None else f"{value:.1f}"


def metric_table(game, metric, result, outcomes, awards):
    rows = [
        "<table>",
        "<tr><th>Rank</th><th>Player</th><th>Role</th><th>Maps</th><th>Rate +/-</th><th>Wins</th><th>Top 4s</th><th>Avg place</th><th>Awards</th></tr>",
    ]
    for i, row in enumerate(result["top_rows"], 1):
        key = mkey(row["player"])
        outcome = outcomes[game].get(key, {})
        player_awards = awards[game].get(key, [])
        rows.append(
            "<tr>"
            f"<td>{i}</td>"
            f"<td>{esc(row['player'])}</td>"
            f"<td>{esc(row['role'])}</td>"
            f"<td>{row['maps']}</td>"
            f"<td>{row['rate_over_repl']:+.2f}/map</td>"
            f"<td>{outcome.get('wins', 0)}</td>"
            f"<td>{outcome.get('top4', 0)}</td>"
            f"<td>{fmt_place(outcome.get('avg_place'))}</td>"
            f"<td>{esc(award_summary(player_awards))}</td>"
            "</tr>"
        )
    rows.append("</table>")
    return "\n".join(rows)


def summary_cards(game, metric, label, result):
    return (
        '<div class="cards">'
        f'<div class="card"><div class="k">Top-{TOP_N} vs wins</div><div class="v">{result["top_wins_overlap"]}/{TOP_N}</div><div class="sub">overlap with title win leaders</div></div>'
        f'<div class="card"><div class="k">Top-{TOP_N} vs avg place</div><div class="v">{result["top_avg_place_overlap"]}/{TOP_N}</div><div class="sub">overlap with best average placements</div></div>'
        f'<div class="card"><div class="k">Top-{TOP_N} awards hit</div><div class="v">{result["top_award_overlap"]}/{TOP_N}</div><div class="sub">{result["award_coverage"]} awarded players in local data</div></div>'
        f'<div class="card"><div class="k">Outcome coefficients</div><div class="v small">W {fmt_corr(result["corr_wins"])} · T4 {fmt_corr(result["corr_top4"])} · Place {fmt_corr(result["corr_avg_place"])}</div><div class="sub">Pearson on qualified players; place is inverted</div></div>'
        "</div>"
    )


def build_report():
    stats_rows = json.loads(Path("player_stats_participants.json").read_text())
    resolve_role = vor.role_resolver(vor.game_order())
    by_game = vor.aggregate(stats_rows, resolve_role)
    scores = vor.score_all(by_game)
    outcomes = load_outcomes()
    awards = load_awards()

    all_results = defaultdict(dict)
    for game in vor.GAMES:
        for metric in vor.SPLITS:
            all_results[game][metric] = validate_metric(
                game,
                metric,
                scores[game][TIER][metric],
                outcomes,
                awards,
            )

    css = """
    body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;margin:0;background:#f7f8fa;color:#111827}
    main{max-width:1240px;margin:0 auto;padding:28px}
    h1{font-size:34px;margin:0 0 8px} h2{margin:34px 0 10px;font-size:25px} h3{margin:26px 0 10px;font-size:18px}
    p{color:#4b5563;line-height:1.45}.cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:12px 0}
    .card{background:white;border:1px solid #e5e7eb;border-radius:8px;padding:12px}.k{color:#6b7280;font-size:12px;text-transform:uppercase;letter-spacing:.04em}.v{font-weight:700;font-size:24px;margin-top:4px}.v.small{font-size:17px}.sub{color:#6b7280;font-size:12px;margin-top:3px}
    table{width:100%;border-collapse:collapse;background:white;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;margin:10px 0 18px}
    th,td{padding:8px 9px;border-bottom:1px solid #eef0f3;text-align:left;font-size:13px;vertical-align:top}th{background:#111827;color:white;font-weight:600}
    tr:last-child td{border-bottom:0}.note{background:#fff7ed;border:1px solid #fed7aa;color:#7c2d12;border-radius:8px;padding:10px 12px;margin:10px 0 18px}
    @media(max-width:900px){main{padding:16px}.cards{grid-template-columns:1fr 1fr}table{display:block;overflow-x:auto;white-space:nowrap}}
    """
    sections = []
    for game in vor.GAMES:
        award_players = len(awards[game])
        award_rows = sum(len(rows) for rows in awards[game].values())
        note = ""
        if award_players < 5:
            note = f'<div class="note">Award validation is thin for {esc(game)}: local accolades contain only {award_rows} rows across {award_players} players.</div>'
        blocks = []
        for metric, label in vor.SPLITS.items():
            result = all_results[game][metric]
            blocks.append(
                f"<h3>{esc(label)}</h3>"
                + summary_cards(game, metric, label, result)
                + metric_table(game, metric, result, outcomes, awards)
            )
        sections.append(f"<section><h2>{esc(game)}</h2>{note}{''.join(blocks)}</section>")

    html_doc = (
        "<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>VOR validation</title><style>{css}</style></head><body><main>"
        "<h1>VOR Validation: Outcomes and Awards</h1>"
        f"<p>Uses the <strong>{esc(TIER)}</strong> minimum-map thresholds from the sensitivity report. "
        "Validation checks are deliberately downstream of the metric: event placements, wins, top-four finishes, and local wiki award/accolade rows are not formula inputs.</p>"
        + "".join(sections)
        + "</main></body></html>"
    )
    OUT_PATH.write_text(html_doc)
    return all_results, scores, outcomes, awards


def print_summary(results, awards):
    for game in vor.GAMES:
        print(f"\n{game}")
        print(f"  Award coverage: {sum(len(v) for v in awards[game].values())} rows / {len(awards[game])} players")
        for metric, label in vor.SPLITS.items():
            r = results[game][metric]
            top = ", ".join(row["player"] for row in r["top_rows"][:5])
            print(
                f"  {label}: top5={top}; "
                f"wins overlap {r['top_wins_overlap']}/{TOP_N}; "
                f"avg-place overlap {r['top_avg_place_overlap']}/{TOP_N}; "
                f"award hit {r['top_award_overlap']}/{TOP_N}; "
                f"corr W {fmt_corr(r['corr_wins'])}, T4 {fmt_corr(r['corr_top4'])}, Place {fmt_corr(r['corr_avg_place'])}"
            )


if __name__ == "__main__":
    results, scores, outcomes, awards = build_report()
    print_summary(results, awards)
    print(f"\nWrote {OUT_PATH}")
