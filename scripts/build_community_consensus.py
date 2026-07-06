#!/usr/bin/env python3
"""Build source-weighted community consensus rankings.

This is the #15 research scorer. It reads the source-first community consensus
JSON files and emits per-title consensus rows. It is intentionally separate from
the main site build until the UX/data contract is settled.
"""
import argparse
import json
import math
import os
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES_PATH = os.path.join(ROOT, "community_consensus_sources.json")
BALLOTS_PATH = os.path.join(ROOT, "community_consensus_ballots.json")


def load_json(path):
    with open(path) as f:
        return json.load(f)


def reddit_score_multiplier(score):
    if score is None:
        return 1.0
    if score >= 50:
        return 1.30
    if score >= 25:
        return 1.20
    if score >= 10:
        return 1.10
    if score >= 3:
        return 1.05
    return 1.0


def coverage_multiplier(coverage):
    if coverage == "contemporaneous":
        return 1.20
    if coverage == "near_contemporaneous":
        return 1.15
    if coverage == "late_retrospective":
        return 0.90
    return 1.0


def season_coverage_multiplier(season_coverage):
    if season_coverage == "end_of_title":
        return 1.0
    if season_coverage == "late_season":
        return 0.85
    if season_coverage == "mid_season":
        return 0.60
    if season_coverage == "early_season":
        return 0.40
    if season_coverage == "partial_split_only":
        return 0.30
    return 1.0


def ballot_points(entries):
    size = len(entries)
    if not size:
        return {}
    points = {}
    for entry in entries:
        rank = float(entry["rank"])
        points[entry["player"]] = (size + 1 - rank) / size
    return points


def comment_reception_raw(score, max_positive_score, max_abs_negative_score):
    """Bounded reception weight from a Reddit comment score snapshot."""
    if score is None:
        return 1.0
    score = float(score)
    if score > 0:
        if max_positive_score <= 0:
            return 1.0
        raw = 1 + 0.25 * math.log1p(score) / math.log1p(max_positive_score)
    elif score < 0:
        if max_abs_negative_score <= 0:
            return 1.0
        raw = 1 - 0.25 * math.log1p(abs(score)) / math.log1p(max_abs_negative_score)
    else:
        raw = 1.0
    return min(1.25, max(0.75, raw))


def comment_reception_weights(ballots):
    scores = [
        ballot.get("comment_score")
        for ballot in ballots
        if ballot.get("comment_score") is not None
    ]
    max_positive_score = max([score for score in scores if score > 0], default=0)
    max_abs_negative_score = max([abs(score) for score in scores if score < 0], default=0)
    raw_weights = [
        comment_reception_raw(
            ballot.get("comment_score"),
            max_positive_score,
            max_abs_negative_score,
        )
        for ballot in ballots
    ]
    average_raw = sum(raw_weights) / len(raw_weights) if raw_weights else 1.0
    if not average_raw:
        average_raw = 1.0
    return [
        {
            "ballot_id": ballot.get("ballot_id"),
            "comment_score": ballot.get("comment_score"),
            "raw_weight": raw,
            "normalized_weight": raw / average_raw,
        }
        for ballot, raw in zip(ballots, raw_weights)
    ]


def average_ballots(ballots):
    scores = defaultdict(float)
    reception = comment_reception_weights(ballots)
    weights = {
        item["ballot_id"]: item["normalized_weight"]
        for item in reception
    }
    total_weight = 0.0
    for ballot in ballots:
        weight = weights.get(ballot.get("ballot_id"), 1.0)
        total_weight += weight
        for player, score in ballot_points(ballot.get("entries", [])).items():
            scores[player] += score * weight
    if not ballots:
        return {}
    return {player: score / total_weight for player, score in scores.items()}


def source_weight(source, ballot_count):
    kind = source["source_kind"]
    if kind == "community_thread_cluster":
        sample = min(1.5, math.sqrt(ballot_count) / 2)
        return sample * reddit_score_multiplier(source.get("reddit_score"))
    if kind == "single_community_ballot":
        return 0.5 * reddit_score_multiplier(source.get("reddit_score"))
    if kind == "community_aggregate_survey":
        valid = source.get("valid_ballots") or source.get("sample_size")
        if valid:
            sample = min(3.0, max(1.5, math.sqrt(valid) / 10))
        else:
            sample = 1.75 if source.get("methodology_notes") else 1.50
        quality = float(source.get("quality_multiplier") or 1.0)
        return sample * quality
    raise ValueError(f"unknown source_kind: {kind}")


def rank_points_from_source(source):
    ranked = source.get("ranked_players") or []
    size = source.get("ranking_size") or len(ranked)
    if not size:
        return {}
    return {
        entry["player"]: (size + 1 - float(entry["rank"])) / size
        for entry in ranked
    }


def build(game=None):
    sources = load_json(SOURCES_PATH)["sources"]
    ballots = load_json(BALLOTS_PATH)["ballots"]
    ballots_by_source = defaultdict(list)
    for ballot in ballots:
        ballots_by_source[ballot["source_id"]].append(ballot)

    source_contributions = {}
    player_sources = defaultdict(set)
    player_source_kinds = defaultdict(lambda: defaultdict(int))

    for source in sources:
        if source.get("status") != "scored":
            continue
        if game and source.get("game") != game:
            continue
        sid = source["source_id"]
        kind = source["source_kind"]
        if kind == "community_aggregate_survey":
            base = rank_points_from_source(source)
            ballot_count = int(source.get("valid_ballots") or source.get("sample_size") or 0)
        else:
            source_ballots = ballots_by_source.get(sid, [])
            if kind == "single_community_ballot" and len(source_ballots) != 1:
                raise ValueError(f"{sid}: single_community_ballot must have exactly one ballot")
            base = average_ballots(source_ballots)
            ballot_count = len(source_ballots)
            ballot_reception = comment_reception_weights(source_ballots)
        base_weight = source_weight(source, ballot_count)
        coverage_weight = coverage_multiplier(source.get("coverage"))
        season_weight = season_coverage_multiplier(source.get("season_coverage"))
        weight = base_weight * coverage_weight * season_weight
        contrib = {player: score * weight for player, score in base.items()}
        source_contributions[sid] = {
            "game": source["game"],
            "source_kind": kind,
            "ballot_count": ballot_count,
            "base_weight": base_weight,
            "coverage_multiplier": coverage_weight,
            "season_coverage_multiplier": season_weight,
            "weight": weight,
            "scores": contrib,
        }
        if kind != "community_aggregate_survey":
            source_contributions[sid]["ballot_reception"] = ballot_reception
        for player in contrib:
            player_sources[(source["game"], player)].add(sid)
            player_source_kinds[(source["game"], player)][kind] += 1

    totals = defaultdict(float)
    for source in source_contributions.values():
        for player, score in source["scores"].items():
            totals[(source["game"], player)] += score

    by_game = defaultdict(list)
    for (g, player), score in totals.items():
        by_game[g].append({
            "game": g,
            "player": player,
            "consensus_score": round(score, 3),
            "source_count": len(player_sources[(g, player)]),
            "aggregate_survey_count": player_source_kinds[(g, player)].get("community_aggregate_survey", 0),
            "thread_cluster_count": player_source_kinds[(g, player)].get("community_thread_cluster", 0),
            "single_ballot_count": player_source_kinds[(g, player)].get("single_community_ballot", 0),
            "ranked": True,
        })

    for rows in by_game.values():
        rows.sort(key=lambda row: (-row["consensus_score"], row["player"].lower()))
        previous_score = None
        previous_rank = 0
        for idx, row in enumerate(rows, start=1):
            if previous_score is None or row["consensus_score"] != previous_score:
                previous_rank = idx
                previous_score = row["consensus_score"]
            row["consensus_rank"] = previous_rank
        for idx, row in enumerate(rows):
            prev_score = rows[idx - 1]["consensus_score"] if idx else None
            next_score = rows[idx + 1]["consensus_score"] if idx + 1 < len(rows) else None
            row["close_race"] = any(
                other is not None and row["consensus_score"] and abs(row["consensus_score"] - other) / row["consensus_score"] <= 0.05
                for other in (prev_score, next_score)
            )
            if row["aggregate_survey_count"] and row["source_count"] >= 1:
                row["confidence"] = "high"
            elif row["source_count"] >= 5:
                row["confidence"] = "high"
            elif row["source_count"] >= 3:
                row["confidence"] = "medium"
            else:
                row["confidence"] = "low"
            rank = row["consensus_rank"]
            row["tier"] = (
                "top_1" if rank == 1 else
                "top_3" if rank <= 3 else
                "top_5" if rank <= 5 else
                "top_10" if rank <= 10 else
                "ranked"
            )

    return {
        "schema_version": 1,
        "source_contributions": source_contributions,
        "games": dict(by_game),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--game", help="Only build one title, e.g. 'Black Ops 2'")
    parser.add_argument("--json", action="store_true", help="Print the full JSON result")
    parser.add_argument("--output", help="Write the full JSON result to this path")
    args = parser.parse_args()

    result = build(args.game)
    if args.output:
        out = args.output
        if not os.path.isabs(out):
            out = os.path.join(ROOT, out)
        with open(out, "w") as f:
            json.dump(result, f, indent=2)
            f.write("\n")
    if args.json:
        print(json.dumps(result, indent=2))
        return
    if args.output:
        print(f"wrote {os.path.relpath(out, ROOT)}")
        return

    games = result["games"]
    for game, rows in sorted(games.items()):
        print(game)
        for row in rows:
            print(f"{row['consensus_rank']:>2}. {row['player']:<10} {row['consensus_score']:.3f} {row['confidence']}")


if __name__ == "__main__":
    main()
