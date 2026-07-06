#!/usr/bin/env python3
"""Decompose kill/death/interaction signals against map wins.

Uses cached PlayerStats rows with Win from vor_mapwin_validation.py.
No role adjustment is used.
"""
import html
import json
import math
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CACHE_PATH = ROOT / "analysis/vor_mapwin_target_stats.json"
OUT_PATH = ROOT / "analysis/vor_decomposition_validation.html"
GAMES = ["Black Ops 2", "Advanced Warfare", "Infinite Warfare", "Black Ops 6"]
SPLITS = ["overall", "respawn", "snd"]
MIN_MAPS = {"overall": 40, "respawn": 28, "snd": 10}
PRIOR_MIN_MAPS = {"overall": 20, "respawn": 14, "snd": 5}
METRICS = {
    "kpm": "Kills/map",
    "dpm": "Deaths/map",
    "ipm": "Interactions/map",
    "kd": "K/D",
    "kill_share": "Kill share",
    "death_share": "Death share",
    "interaction_share": "Interaction share",
}


def esc(value):
    return html.escape(str(value))


def mkey(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def is_snd(mode):
    text = str(mode or "").lower().replace("&", "and")
    return "search" in text and "destroy" in text


def stat_bool(value):
    text = str(value if value is not None else "").strip().lower()
    if text in {"1", "true", "t", "yes", "y", "win", "won"}:
        return 1
    if text in {"0", "false", "f", "no", "n", "loss", "lost"}:
        return 0
    return None


def corr(xs, ys):
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pairs) < 3:
        return None
    xs = [float(p[0]) for p in pairs]
    ys = [float(p[1]) for p in pairs]
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if not sx or not sy:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def fmt(value, digits=2):
    if value is None:
        return "n/a"
    return f"{value:+.{digits}f}" if isinstance(value, float) else str(value)


def pct(value):
    return "n/a" if value is None else f"{100 * value:.1f}%"


def split_for(row):
    return "snd" if is_snd(row.get("Mode")) else "respawn"


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


def team_map_key(row):
    return map_key(row) + (row.get("Team") or "",)


def load_rows():
    raw = json.loads(CACHE_PATH.read_text())
    rows = []
    for row in raw:
        game = row.get("Game")
        if game not in GAMES:
            continue
        win = stat_bool(row.get("Win"))
        try:
            kills = int(row.get("Kills"))
            deaths = int(row.get("Deaths"))
        except (TypeError, ValueError):
            continue
        if win is None:
            continue
        out = dict(row)
        out["kills"] = kills
        out["deaths"] = deaths
        out["interactions"] = kills + deaths
        out["kpm"] = kills
        out["dpm"] = deaths
        out["ipm"] = kills + deaths
        out["kd"] = kills / deaths if deaths else None
        out["win"] = win
        out["split"] = split_for(row)
        out["player_key"] = mkey(row.get("Player") or row.get("PlayerLink") or row.get("PlayerName"))
        out["player"] = row.get("Player") or row.get("PlayerLink") or row.get("PlayerName")
        rows.append(out)
    add_team_shares(rows)
    return rows


def add_team_shares(rows):
    by_team_map = defaultdict(list)
    for row in rows:
        by_team_map[team_map_key(row)].append(row)
    for group in by_team_map.values():
        team_kills = sum(r["kills"] for r in group)
        team_deaths = sum(r["deaths"] for r in group)
        team_interactions = sum(r["interactions"] for r in group)
        complete = len(group) >= 4 and team_kills > 0 and team_deaths > 0 and team_interactions > 0
        for row in group:
            row["team_rows"] = len(group)
            if complete:
                row["kill_share"] = row["kills"] / team_kills
                row["death_share"] = row["deaths"] / team_deaths
                row["interaction_share"] = row["interactions"] / team_interactions
            else:
                row["kill_share"] = None
                row["death_share"] = None
                row["interaction_share"] = None


def player_aggregates(rows):
    buckets = defaultdict(lambda: {
        "player": "",
        "kills": 0,
        "deaths": 0,
        "interactions": 0,
        "wins": 0,
        "maps": 0,
        "kill_share_sum": 0,
        "death_share_sum": 0,
        "interaction_share_sum": 0,
        "share_maps": 0,
    })
    for row in rows:
        for split in ("overall", row["split"]):
            key = (row["Game"], split, row["player_key"])
            b = buckets[key]
            b["player"] = row["player"]
            b["kills"] += row["kills"]
            b["deaths"] += row["deaths"]
            b["interactions"] += row["interactions"]
            b["wins"] += row["win"]
            b["maps"] += 1
            if row["kill_share"] is not None:
                b["kill_share_sum"] += row["kill_share"]
                b["death_share_sum"] += row["death_share"]
                b["interaction_share_sum"] += row["interaction_share"]
                b["share_maps"] += 1
    out = defaultdict(lambda: defaultdict(list))
    for (game, split, _player_key), b in buckets.items():
        if b["maps"] < MIN_MAPS[split]:
            continue
        maps = b["maps"]
        deaths = b["deaths"]
        share_maps = b["share_maps"]
        out[game][split].append({
            "player": b["player"],
            "maps": maps,
            "wins": b["wins"],
            "map_win_rate": b["wins"] / maps,
            "kpm": b["kills"] / maps,
            "dpm": b["deaths"] / maps,
            "ipm": b["interactions"] / maps,
            "kd": b["kills"] / deaths if deaths else None,
            "kill_share": b["kill_share_sum"] / share_maps if share_maps else None,
            "death_share": b["death_share_sum"] / share_maps if share_maps else None,
            "interaction_share": b["interaction_share_sum"] / share_maps if share_maps else None,
        })
    return out


def aggregate_correlations(aggs):
    out = defaultdict(dict)
    for game in GAMES:
        for split in SPLITS:
            players = aggs[game][split]
            out[game][split] = {
                metric: corr([p.get(metric) for p in players], [p["map_win_rate"] for p in players])
                for metric in METRICS
            }
            out[game][split]["n"] = len(players)
    return out


def residual_corr(rows, metric, group_fn):
    groups = defaultdict(list)
    for row in rows:
        value = row.get(metric)
        if value is None:
            continue
        groups[group_fn(row)].append((value, row["win"]))
    rx, ry = [], []
    for vals in groups.values():
        if len(vals) < 4:
            continue
        mx = sum(v for v, _ in vals) / len(vals)
        my = sum(y for _, y in vals) / len(vals)
        for v, y in vals:
            rx.append(v - mx)
            ry.append(y - my)
    return corr(rx, ry), len(rx)


def row_level_validations(rows):
    out = defaultdict(lambda: defaultdict(dict))
    for game in GAMES:
        game_rows = [r for r in rows if r["Game"] == game]
        for split in SPLITS:
            split_rows = game_rows if split == "overall" else [r for r in game_rows if r["split"] == split]
            for metric in METRICS:
                out[game][split][metric] = {
                    "simple": corr([r.get(metric) for r in split_rows], [r["win"] for r in split_rows]),
                    "same_map": residual_corr(split_rows, metric, map_key),
                    "event_mode": residual_corr(
                        split_rows,
                        metric,
                        lambda r: (r["Game"], event_key(r), r.get("Mode") or "", r.get("Map") or ""),
                    ),
                }
            out[game][split]["n"] = len(split_rows)
    return out


def prior_event_validation(rows):
    rows_sorted = sorted(rows, key=lambda r: (r.get("Game") or "", r.get("Date") or "", event_key(r), r.get("SeriesId") or ""))
    histories = defaultdict(lambda: defaultdict(lambda: {"kills": 0, "deaths": 0, "interactions": 0, "maps": 0}))
    out_rows = []
    current_event = None
    pending = []

    def flush_pending():
        for row in pending:
            player_hist = histories[(row["Game"], row["player_key"])]
            for split in ("overall", row["split"]):
                h = player_hist[split]
                h["kills"] += row["kills"]
                h["deaths"] += row["deaths"]
                h["interactions"] += row["interactions"]
                h["maps"] += 1

    for row in rows_sorted:
        ek = (row["Game"], event_key(row))
        if current_event is None:
            current_event = ek
        if ek != current_event:
            flush_pending()
            pending = []
            current_event = ek
        player_hist = histories[(row["Game"], row["player_key"])]
        prior = {}
        for split in ("overall", row["split"]):
            h = player_hist[split]
            if h["maps"] >= PRIOR_MIN_MAPS[split]:
                prior[f"{split}_kpm"] = h["kills"] / h["maps"]
                prior[f"{split}_dpm"] = h["deaths"] / h["maps"]
                prior[f"{split}_ipm"] = h["interactions"] / h["maps"]
                prior[f"{split}_kd"] = h["kills"] / h["deaths"] if h["deaths"] else None
                prior[f"{split}_maps"] = h["maps"]
        if prior:
            out_rows.append({**row, **prior})
        pending.append(row)
    flush_pending()

    out = defaultdict(lambda: defaultdict(dict))
    for game in GAMES:
        game_rows = [r for r in out_rows if r["Game"] == game]
        for split in SPLITS:
            split_rows = game_rows if split == "overall" else [r for r in game_rows if r["split"] == split]
            prefix = split
            out[game][split]["n"] = len(split_rows)
            for metric in ("kpm", "dpm", "ipm", "kd"):
                key = f"{prefix}_{metric}"
                out[game][split][metric] = {
                    "simple": corr([r.get(key) for r in split_rows], [r["win"] for r in split_rows]),
                    "same_map": residual_corr(
                        [{**r, "prior_metric": r.get(key)} for r in split_rows],
                        "prior_metric",
                        map_key,
                    ),
                }
    return out


def top_deltas(aggs):
    out = defaultdict(dict)
    for game in GAMES:
        players = aggs[game]["respawn"]
        rows = []
        for p in players:
            rows.append({
                "player": p["player"],
                "maps": p["maps"],
                "win": p["map_win_rate"],
                "kpm": p["kpm"],
                "dpm": p["dpm"],
                "ipm": p["ipm"],
                "kd": p["kd"],
            })
        out[game]["high_interactions_low_win"] = sorted(
            rows,
            key=lambda r: (-r["ipm"], r["win"], r["player"]),
        )[:8]
        out[game]["high_kills_high_win"] = sorted(
            rows,
            key=lambda r: (-r["kpm"], -r["win"], r["player"]),
        )[:8]
    return out


def corr_table(title, data, metrics):
    rows = [f"<h3>{esc(title)}</h3>", "<table><tr><th>Game</th><th>Split</th><th>N</th>" + "".join(f"<th>{esc(METRICS.get(m, m))}</th>" for m in metrics) + "</tr>"]
    for game in GAMES:
        for split in SPLITS:
            d = data[game][split]
            rows.append(
                "<tr>"
                f"<td>{esc(game)}</td><td>{esc(split)}</td><td>{d.get('n', '')}</td>"
                + "".join(f"<td>{fmt(d.get(m), 2)}</td>" for m in metrics)
                + "</tr>"
            )
    rows.append("</table>")
    return "\n".join(rows)


def row_validation_table(title, data, metrics, subkey):
    rows = [f"<h3>{esc(title)}</h3>", "<table><tr><th>Game</th><th>Split</th><th>N</th>" + "".join(f"<th>{esc(METRICS.get(m, m))}</th>" for m in metrics) + "</tr>"]
    for game in GAMES:
        for split in SPLITS:
            d = data[game][split]
            cells = []
            for m in metrics:
                val = d[m][subkey]
                if isinstance(val, tuple):
                    cells.append(f"<td>{fmt(val[0], 2)} <span class='n'>n={val[1]}</span></td>")
                else:
                    cells.append(f"<td>{fmt(val, 2)}</td>")
            rows.append(f"<tr><td>{esc(game)}</td><td>{esc(split)}</td><td>{d.get('n', '')}</td>{''.join(cells)}</tr>")
    rows.append("</table>")
    return "\n".join(rows)


def prior_table(title, data, metrics):
    rows = [f"<h3>{esc(title)}</h3>", "<table><tr><th>Game</th><th>Split</th><th>N</th>" + "".join(f"<th>Prior {esc(METRICS.get(m, m))}</th>" for m in metrics) + "</tr>"]
    for game in GAMES:
        for split in SPLITS:
            d = data[game][split]
            cells = []
            for m in metrics:
                val = d[m]["simple"]
                cells.append(f"<td>{fmt(val, 2)}</td>")
            rows.append(f"<tr><td>{esc(game)}</td><td>{esc(split)}</td><td>{d.get('n', '')}</td>{''.join(cells)}</tr>")
    rows.append("</table>")
    return "\n".join(rows)


def list_table(title, rows):
    out = [f"<h3>{esc(title)}</h3>", "<table><tr><th>Player</th><th>Maps</th><th>Map win%</th><th>K/map</th><th>D/map</th><th>Interactions/map</th><th>K/D</th></tr>"]
    for r in rows:
        out.append(
            "<tr>"
            f"<td>{esc(r['player'])}</td><td>{r['maps']}</td><td>{pct(r['win'])}</td>"
            f"<td>{r['kpm']:.2f}</td><td>{r['dpm']:.2f}</td><td>{r['ipm']:.2f}</td><td>{r['kd']:.3f}</td>"
            "</tr>"
        )
    out.append("</table>")
    return "\n".join(out)


def build_report(rows, aggs, agg_corrs, row_valid, prior_valid, deltas):
    css = """
    body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;margin:0;background:#f7f8fa;color:#111827}
    main{max-width:1240px;margin:0 auto;padding:28px}h1{font-size:34px;margin:0 0 8px}h2{margin:34px 0 10px}h3{margin:22px 0 8px}
    p{color:#4b5563;line-height:1.45}.note{background:#fff7ed;border:1px solid #fed7aa;color:#7c2d12;border-radius:8px;padding:10px 12px}
    table{width:100%;border-collapse:collapse;background:white;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;margin:8px 0 18px}
    th,td{font-size:13px;text-align:left;padding:8px 9px;border-bottom:1px solid #eef0f3;vertical-align:top}th{background:#111827;color:white}tr:last-child td{border-bottom:0}
    .n{color:#6b7280;font-size:11px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
    @media(max-width:900px){main{padding:16px}.grid{grid-template-columns:1fr}table{display:block;overflow-x:auto;white-space:nowrap}}
    """
    metrics = ["kpm", "dpm", "ipm", "kd"]
    share_metrics = ["kill_share", "death_share", "interaction_share"]
    sections = [
        corr_table("Player Aggregate Correlation To Map Win Rate", agg_corrs, metrics),
        corr_table("Player Aggregate Team-Share Correlation To Map Win Rate", agg_corrs, share_metrics),
        row_validation_table("Player-Map Simple Correlation To Map Win", row_valid, metrics, "simple"),
        row_validation_table("Same-Map Fixed-Effect Residual Correlation", row_valid, metrics, "same_map"),
        prior_table("Prior-Event Predictive Correlation To Future Map Win", prior_valid, metrics),
    ]
    game_sections = []
    for game in GAMES:
        game_sections.append(
            f"<h2>{esc(game)} Respawn Examples</h2><div class='grid'>"
            + list_table("High interactions, regardless of win rate", deltas[game]["high_interactions_low_win"])
            + list_table("High kills, then win rate", deltas[game]["high_kills_high_win"])
            + "</div>"
        )
    html_doc = (
        "<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>VOR decomposition validation</title><style>{css}</style></head><body><main>"
        "<h1>VOR Decomposition Validation</h1>"
        f"<p>Uses {len(rows):,} cached PlayerStats rows with actual map wins. Role is not used. "
        "Correlations are descriptive, not causal.</p>"
        "<div class='note'>Same-map residual correlation compares players within the same game/event/series/map/mode context. "
        "Prior-event validation uses only a player's earlier events in the same title/split, so it is the best leakage check here.</div>"
        + "".join(sections)
        + "".join(game_sections)
        + "</main></body></html>"
    )
    OUT_PATH.write_text(html_doc)


def print_summary(agg_corrs, row_valid, prior_valid):
    print("Aggregate player correlations to map win rate")
    for game in GAMES:
        print(f"\n{game}")
        for split in SPLITS:
            d = agg_corrs[game][split]
            print(
                f"  {split}: n={d['n']} "
                f"K {fmt(d['kpm'])} D {fmt(d['dpm'])} Int {fmt(d['ipm'])} KD {fmt(d['kd'])}"
            )
    print("\nSame-map residual correlations")
    for game in GAMES:
        print(f"\n{game}")
        for split in SPLITS:
            d = row_valid[game][split]
            vals = {m: d[m]["same_map"][0] for m in ("kpm", "dpm", "ipm", "kd")}
            print(
                f"  {split}: K {fmt(vals['kpm'])} D {fmt(vals['dpm'])} "
                f"Int {fmt(vals['ipm'])} KD {fmt(vals['kd'])}"
            )
    print("\nPrior-event predictive correlations")
    for game in GAMES:
        print(f"\n{game}")
        for split in SPLITS:
            d = prior_valid[game][split]
            print(
                f"  {split}: n={d['n']} "
                f"K {fmt(d['kpm']['simple'])} D {fmt(d['dpm']['simple'])} "
                f"Int {fmt(d['ipm']['simple'])} KD {fmt(d['kd']['simple'])}"
            )


def main():
    rows = load_rows()
    aggs = player_aggregates(rows)
    agg_corrs = aggregate_correlations(aggs)
    row_valid = row_level_validations(rows)
    prior_valid = prior_event_validation(rows)
    deltas = top_deltas(aggs)
    build_report(rows, aggs, agg_corrs, row_valid, prior_valid, deltas)
    print_summary(agg_corrs, row_valid, prior_valid)
    print(f"\nWrote {OUT_PATH}")


if __name__ == "__main__":
    main()
