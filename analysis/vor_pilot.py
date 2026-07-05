#!/usr/bin/env python3
"""Prototype title-level kills/interactions above replacement.

This is exploratory analysis, not site data. It intentionally uses title-level
baselines because the broad participant pool does not yet have curated roles.
"""
import json
import math
import sys
from collections import defaultdict
from pathlib import Path


DEFAULT_GAMES = ["Black Ops 2", "Advanced Warfare", "Infinite Warfare", "Black Ops 6"]
MIN_MAPS = 20
REPLACEMENT_PERCENTILE = 0.25


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


def aggregate(rows, game):
    by_player = defaultdict(lambda: {"kills": 0, "deaths": 0, "maps": 0, "events": set()})
    for row in rows:
        if row.get("Game") != game:
            continue
        player = row.get("Player") or row.get("PlayerLink") or row.get("PlayerName")
        if not player:
            continue
        bucket = by_player[player]
        bucket["kills"] += int(row["Kills"])
        bucket["deaths"] += int(row["Deaths"])
        bucket["maps"] += 1
        if row.get("Event"):
            bucket["events"].add(row["Event"])
    return by_player


def score_game(rows, game):
    by_player = aggregate(rows, game)
    qualified = {p: b for p, b in by_player.items() if b["maps"] >= MIN_MAPS}
    repl_kpm = percentile([b["kills"] / b["maps"] for b in qualified.values()], REPLACEMENT_PERCENTILE)
    repl_ipm = percentile([(b["kills"] + b["deaths"]) / b["maps"] for b in qualified.values()], REPLACEMENT_PERCENTILE)
    out = []
    for player, b in qualified.items():
        kills, deaths, maps = b["kills"], b["deaths"], b["maps"]
        interactions = kills + deaths
        kpm = kills / maps
        ipm = interactions / maps
        out.append({
            "player": player,
            "maps": maps,
            "events": len(b["events"]),
            "kills": kills,
            "deaths": deaths,
            "interactions": interactions,
            "kd": kills / deaths if deaths else None,
            "kpm": kpm,
            "ipm": ipm,
            "kills_vor": (kpm - repl_kpm) * maps,
            "interactions_vor": (ipm - repl_ipm) * maps,
        })
    out.sort(key=lambda r: (r["kills_vor"], r["interactions_vor"]), reverse=True)
    return {
        "game": game,
        "players_total": len(by_player),
        "players_qualified": len(qualified),
        "events": len({e for b in by_player.values() for e in b["events"]}),
        "rows": sum(b["maps"] for b in by_player.values()),
        "replacement": {"kills_per_map": repl_kpm, "interactions_per_map": repl_ipm},
        "players": out,
    }


def fmt_row(row, metric):
    return (
        f"{row['player']:<14} {metric}={row[metric]:7.1f} "
        f"maps={row['maps']:3d} events={row['events']:2d} "
        f"K={row['kills']:5d} D={row['deaths']:5d} "
        f"K/D={row['kd']:.3f} K/map={row['kpm']:.2f} Int/map={row['ipm']:.2f}"
    )


def main():
    games = sys.argv[1:] or DEFAULT_GAMES
    rows = json.loads(Path("player_stats_participants.json").read_text())
    for game in games:
        result = score_game(rows, game)
        repl = result["replacement"]
        print(f"\n## {game}")
        print(
            f"rows={result['rows']} events={result['events']} "
            f"players={result['players_total']} qualified>={MIN_MAPS}maps={result['players_qualified']}"
        )
        print(f"replacement: K/map={repl['kills_per_map']:.2f}, Int/map={repl['interactions_per_map']:.2f}")

        print("\nTop Kills VOR")
        for row in sorted(result["players"], key=lambda r: r["kills_vor"], reverse=True)[:10]:
            print(fmt_row(row, "kills_vor"))

        print("\nTop Interactions VOR")
        for row in sorted(result["players"], key=lambda r: r["interactions_vor"], reverse=True)[:10]:
            print(fmt_row(row, "interactions_vor"))


if __name__ == "__main__":
    main()
