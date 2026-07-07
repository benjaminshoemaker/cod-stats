#!/usr/bin/env python3
"""Build cross-title community consensus rollups.

This stays separate from the site build while the #15 UX/data contract is
still being shaped. It consumes the generated per-title consensus data and
adds career-length normalization plus local event-win sanity columns.
"""
import argparse
import json
import os
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.build_community_consensus import build as build_consensus
from build_data import ASOF, DROP_GAMES, DROP_EVENTS

PARTICIPATION_PATH = os.path.join(ROOT, "player_participation.json")
WINS_PATH = os.path.join(ROOT, "player_event_wins.json")
TITLE_POINT_EXPONENT = 2.5
# A played-but-unranked title counts as this rank in "Avg rank (played)" —
# one past the 30-player consensus cutoff. Must stay equal to the site's
# community.html averageRank penalty.
UNRANKED_PLAYED_RANK = 31

TITLES = [
    "Black Ops",
    "Modern Warfare 3",
    "Black Ops 2",
    "Ghosts",
    "Advanced Warfare",
    "Black Ops 3",
    "Infinite Warfare",
    "World War II",
    "Black Ops 4",
    "Modern Warfare",
    "Black Ops Cold War",
    "Vanguard",
    "Modern Warfare II",
    "Modern Warfare III",
    "Black Ops 6",
]

ALIASES = {
    "aBeZy": ["aBeZy", "ABeZy"],
    "iLLeY": ["iLLeY", "ILLeY"],
    "Methodz": ["Methodz", "Methodz (Anthony Zinni)"],
    "SupeR (Diego Escudero)": ["SupeR (Diego Escudero)", "SupeR"],
    "Mercules": ["Mercules", "MercuLes"],
    "ReeaL": ["ReeaL", "Reeal"],
    "GodRx": ["GodRx", "GodRX"],
    "Scrap": ["Scrap", "Scrappy"],
}


def load_json(path):
    with open(path) as f:
        return json.load(f)


def in_universe(row):
    """build_data.py's console-major universe: DROP_GAMES/DROP_EVENTS out,
    rows on/before ASOF only (undated rows kept, matching _played)."""
    return (
        row.get("Game") not in DROP_GAMES
        and row.get("Event") not in DROP_EVENTS
        and (row.get("Date") or "0000") <= ASOF
    )


def labels(player):
    return set(ALIASES.get(player, [player]))


def title_rank_points(rank):
    """Top-heavy normalized title points for a consensus rank."""
    normalized_rank = max(0.0, (31 - rank) / 30)
    return normalized_rank ** TITLE_POINT_EXPONENT


def build_rollup():
    consensus = build_consensus()["games"]
    participation = load_json(PARTICIPATION_PATH)
    wins = load_json(WINS_PATH)
    games = set(TITLES)

    player_rows = defaultdict(lambda: {
        "overall_score": 0.0,
        "ranked_titles": 0,
        "top_1": 0,
        "top_3": 0,
        "top_5": 0,
        "top_10": 0,
        "rank_sum": 0,
        "top_10_title_placements": [],
    })

    for game in TITLES:
        for row in consensus.get(game, []):
            player = row["player"]
            rank = row["consensus_rank"]
            title_points = title_rank_points(rank)
            player_row = player_rows[player]
            player_row["player"] = player
            player_row["overall_score"] += title_points
            player_row["ranked_titles"] += 1
            player_row["rank_sum"] += rank
            player_row["top_1"] += int(rank == 1)
            player_row["top_3"] += int(rank <= 3)
            player_row["top_5"] += int(rank <= 5)
            player_row["top_10"] += int(rank <= 10)
            if rank <= 10:
                player_row["top_10_title_placements"].append(f"{game} #{rank}")

    for player, player_row in player_rows.items():
        player_labels = labels(player)
        played_titles = {
            row["Game"]
            for row in participation
            if row.get("Game") in games and row.get("Player") in player_labels
            and in_universe(row)
        }
        player_row["played_titles"] = max(len(played_titles), player_row["ranked_titles"])
        player_row["event_wins"] = sum(
            1
            for row in wins
            if row.get("Game") in games and row.get("Player") in player_labels
            and in_universe(row)
        )
        player_row["events"] = len({
            (row.get("Game"), row.get("Event"))
            for row in participation
            if row.get("Game") in games and row.get("Player") in player_labels
            and in_universe(row)
        })
        player_row["avg_rank_ranked"] = player_row["rank_sum"] / player_row["ranked_titles"]
        unranked_played = player_row["played_titles"] - player_row["ranked_titles"]
        player_row["avg_rank_played"] = (
            player_row["rank_sum"] + unranked_played * UNRANKED_PLAYED_RANK
        ) / player_row["played_titles"]
        player_row["score_per_played_title"] = (
            player_row["overall_score"] / player_row["played_titles"]
        )
        player_row["score_per_ranked_title"] = (
            player_row["overall_score"] / player_row["ranked_titles"]
        )

    rows = list(player_rows.values())
    return {
        "schema_version": 1,
        "titles": TITLES,
        "rows": rows,
    }


def sort_total(row):
    return (
        -row["overall_score"],
        -row["top_1"],
        -row["top_3"],
        -row["top_5"],
        -row["top_10"],
        row["avg_rank_ranked"],
        -row["event_wins"],
        row["player"].lower(),
    )


def sort_per_played(row):
    return (
        -row["score_per_played_title"],
        -row["overall_score"],
        -row["top_1"],
        -row["top_3"],
        row["avg_rank_ranked"],
        row["player"].lower(),
    )


def sort_per_ranked(row):
    return (
        -row["score_per_ranked_title"],
        -row["overall_score"],
        -row["top_1"],
        -row["top_3"],
        row["avg_rank_ranked"],
        row["player"].lower(),
    )


def table(rows, rank_label, limit):
    lines = [
        f"| {rank_label} | Player | Total score | Score/title played | Score/ranked title | Event wins | Played titles | Ranked titles | Top 1 | Top 3 | Top 5 | Top 10 | Avg rank (ranked) | Avg rank (played) | Top-10 title placements |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for idx, row in enumerate(rows[:limit], start=1):
        placements = "; ".join(row["top_10_title_placements"]) or "none"
        lines.append(
            f"| {idx} | {row['player']} | {row['overall_score']:.3f} | "
            f"{row['score_per_played_title']:.3f} | "
            f"{row['score_per_ranked_title']:.3f} | "
            f"{row['event_wins']} | {row['played_titles']} | "
            f"{row['ranked_titles']} | {row['top_1']} | {row['top_3']} | "
            f"{row['top_5']} | {row['top_10']} | "
            f"{row['avg_rank_ranked']:.2f} | {row['avg_rank_played']:.2f} | {placements} |"
        )
    return "\n".join(lines)


def markdown(result, limit):
    rows = result["rows"]
    by_total = sorted(rows, key=sort_total)
    by_played = sorted(
        [row for row in rows if row["played_titles"] >= 3],
        key=sort_per_played,
    )
    by_ranked = sorted(
        [row for row in rows if row["ranked_titles"] >= 3],
        key=sort_per_ranked,
    )

    return "\n\n".join([
        "# Community Consensus Cross-Title Rollup",
        "Includes titles currently pulled into #15 consensus data.",
        (
            "Method: each title rank becomes `((31 - rank) / 30) ** 2.5`. "
            "Every title has the same maximum value, but the curve is "
            "intentionally top-heavy so elite title ranks matter far more than "
            "lower top-30 placements. Source quality is handled within each "
            "title's consensus construction and confidence notes, not as a "
            "cross-title season multiplier. Played-but-unranked titles add no "
            "score, so `Score/title played` is the career-length normalized "
            "view. `Score/ranked title` is the peak/quality view. "
            "`Avg rank (ranked)` averages over ranked titles only; "
            "`Avg rank (played)` averages over all played titles with "
            "played-but-unranked titles counted as rank 31 — the same "
            "definition the site's Community page uses for its Average rank "
            "column. Event wins and played titles use the site's console-major "
            "universe (drop games/events and as-of cutoff from build_data.py)."
        ),
        "Title weights: every included title = 1.00.",
        (
            "Site note: the `Score/title played` and `Score/ranked title` "
            "columns are analysis-only views. The community page's overall "
            "table intentionally shows one headline score per player (total "
            "score) with average rank, title count, event wins (context "
            "only), and top-N counts; the per-title normalizations stay in "
            "this report."
        ),
        "## Overall Total Score",
        table(by_total, "Overall", limit),
        "## Normalized By Played Titles",
        "Minimum 3 played titles.",
        table(by_played, "Rank", limit),
        "## Peak: Score Per Ranked Title",
        "Minimum 3 ranked titles.",
        table(by_ranked, "Rank", limit),
        "",
    ])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output", help="Write markdown output to this path")
    parser.add_argument("--limit", type=int, default=60)
    args = parser.parse_args()

    result = build_rollup()
    if args.json:
        print(json.dumps(result, indent=2))
        return
    output = markdown(result, args.limit)
    if args.output:
        out = args.output
        if not os.path.isabs(out):
            out = os.path.join(ROOT, out)
        with open(out, "w") as f:
            f.write(output)
        print(f"wrote {os.path.relpath(out, ROOT)}")
        return
    print(output)


if __name__ == "__main__":
    main()
