#!/usr/bin/env python3
"""Build authored-ranking evidence summaries for issue #16.

This intentionally does not compute a consensus score. Authored rankings,
reported player claims, and creator/media lists are evidence rows with source
identity preserved, not ballots from one comparable population.
"""
import argparse
import json
import os
from collections import defaultdict
from statistics import median

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES_PATH = os.path.join(ROOT, "player_authored_sources.json")
OUT_PATH = os.path.join(ROOT, "player_authored_summary.json")

SEEDED = "seeded"
VERIFICATION_LEAD = "verification_lead"
REQUIRED_SOURCE_FIELDS = {
    "source_id",
    "family",
    "status",
    "title",
    "retrieved_date",
    "author_type",
    "source_quality",
    "methodology_summary",
    "methodology_tags",
    "caveats",
}
SEEDED_SOURCE_FIELDS = REQUIRED_SOURCE_FIELDS | {
    "url",
    "published_date",
}
RANKING_FAMILIES = {
    "authored_all_time_ranking",
    "authored_title_ranking",
    "authored_role_ranking",
    "authored_talent_ranking",
}


def load_json(path):
    with open(path) as f:
        return json.load(f)


def mkey(name):
    return "".join(ch.lower() for ch in name if ch.isalnum())


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def validate(data):
    _require(data.get("schema_version") == 1, "schema_version must be 1")
    sources = data.get("sources") or []
    rankings = data.get("rankings") or []
    claims = data.get("claims") or []
    _require(sources, "at least one source is required")

    source_ids = set()
    seeded_source_ids = set()
    for source in sources:
        missing = sorted(REQUIRED_SOURCE_FIELDS - set(source))
        _require(not missing, f"{source.get('source_id', '<unknown>')}: missing fields {missing}")
        sid = source["source_id"]
        _require(sid not in source_ids, f"{sid}: duplicate source_id")
        source_ids.add(sid)
        _require(source["status"] in {SEEDED, VERIFICATION_LEAD}, f"{sid}: unknown status {source['status']}")
        _require(isinstance(source["methodology_tags"], list) and source["methodology_tags"], f"{sid}: methodology_tags must be non-empty")
        _require(isinstance(source["caveats"], list) and source["caveats"], f"{sid}: caveats must be non-empty")
        if source["status"] == SEEDED:
            missing = sorted(SEEDED_SOURCE_FIELDS - set(source))
            _require(not missing, f"{sid}: seeded source missing fields {missing}")
            seeded_source_ids.add(sid)
        if source["family"] in RANKING_FAMILIES:
            scope = source.get("scope") or {}
            _require(scope.get("ranking_size"), f"{sid}: ranking source needs scope.ranking_size")

    ranked_source_ids = set()
    for ranking in rankings:
        sid = ranking.get("source_id")
        _require(sid in source_ids, f"{sid}: ranking references unknown source")
        _require(sid in seeded_source_ids, f"{sid}: ranking source must be seeded before entries are extracted")
        _require(sid not in ranked_source_ids, f"{sid}: duplicate ranking block")
        ranked_source_ids.add(sid)
        entries = ranking.get("entries") or []
        _require(entries, f"{sid}: ranking entries required")
        ranks = [entry["rank"] for entry in entries]
        players = [entry["player"] for entry in entries]
        _require(len(ranks) == len(set(ranks)), f"{sid}: duplicate ranks")
        _require(len(players) == len(set(players)), f"{sid}: duplicate players")
        for entry in entries:
            _require("rank" in entry and "player" in entry, f"{sid}: every ranking entry needs rank and player")
            _require(entry["rank"] > 0, f"{sid}: rank must be positive")
            _require(isinstance(entry.get("claim_tags"), list) and entry["claim_tags"], f"{sid}: every ranking entry needs claim_tags")

    for source in sources:
        if source["status"] == SEEDED and source["family"] in RANKING_FAMILIES:
            _require(source["source_id"] in ranked_source_ids, f"{source['source_id']}: seeded ranking source needs entries")

    for claim in claims:
        sid = claim.get("source_id")
        _require(sid in seeded_source_ids, f"{sid}: claim source must be seeded")
        for field in ("claimant", "claimant_type", "player", "claim_tags", "rationale_summary"):
            _require(field in claim, f"{sid}: claim missing {field}")
        _require(isinstance(claim["claim_tags"], list) and claim["claim_tags"], f"{sid}: claim_tags must be non-empty")


def source_index(data):
    return {source["source_id"]: source for source in data["sources"]}


def _empty_player_row():
    return {
        "player": None,
        "source_ids": set(),
        "all_time_ranks": [],
        "title_ranks": [],
        "ranking_count": 0,
        "claim_count": 0,
        "claim_tags": set(),
        "families": set(),
    }


def _player_row(player_rows, player):
    row = player_rows[mkey(player)]
    row["player"] = player
    return row


def _record_player_source(row, source_id, source):
    row["source_ids"].add(source_id)
    row["families"].add(source["family"])


def _record_ranking_entry(player_rows, source, entry):
    sid = source["source_id"]
    player = entry["player"]
    row = _player_row(player_rows, player)
    _record_player_source(row, sid, source)
    row["ranking_count"] += 1
    row["claim_tags"].update(entry.get("claim_tags", []))
    if source["family"] == "authored_all_time_ranking":
        row["all_time_ranks"].append(entry["rank"])
    elif source["family"] == "authored_title_ranking":
        row["title_ranks"].append({
            "source_id": sid,
            "game": (source.get("scope") or {}).get("game"),
            "rank": entry["rank"],
        })
    return {
        "rank": entry["rank"],
        "player": player,
        "claim_tags": entry.get("claim_tags", []),
    }


def _build_ranking_lists(data, sources_by_id, player_rows):
    ranking_lists = {}
    for ranking in data.get("rankings", []):
        sid = ranking["source_id"]
        source = sources_by_id[sid]
        rows = [_record_ranking_entry(player_rows, source, entry) for entry in ranking["entries"]]
        ranking_lists[sid] = {
            "source_id": sid,
            "family": source["family"],
            "title": source["title"],
            "entries": sorted(rows, key=lambda r: (r["rank"], r["player"].lower())),
        }
    return ranking_lists


def _build_claim_rows(data, sources_by_id, player_rows):
    claim_rows = []
    for claim in data.get("claims", []):
        source = sources_by_id[claim["source_id"]]
        player = claim["player"]
        row = _player_row(player_rows, player)
        _record_player_source(row, claim["source_id"], source)
        row["claim_count"] += 1
        row["claim_tags"].update(claim["claim_tags"])
        claim_rows.append({
            "source_id": claim["source_id"],
            "claimant": claim["claimant"],
            "claimant_type": claim["claimant_type"],
            "player": player,
            "claim_tags": claim["claim_tags"],
            "rationale_summary": claim["rationale_summary"],
            "quote": claim.get("quote"),
            "quote_location": claim.get("quote_location"),
        })
    return claim_rows


def _build_player_summaries(player_rows):
    players = []
    for row in player_rows.values():
        all_time_ranks = sorted(row["all_time_ranks"])
        players.append({
            "player": row["player"],
            "source_count": len(row["source_ids"]),
            "source_ids": sorted(row["source_ids"]),
            "families": sorted(row["families"]),
            "ranking_count": row["ranking_count"],
            "claim_count": row["claim_count"],
            "all_time_list_count": len(all_time_ranks),
            "best_all_time_rank": min(all_time_ranks) if all_time_ranks else None,
            "median_all_time_rank": median(all_time_ranks) if all_time_ranks else None,
            "title_ranks": sorted(row["title_ranks"], key=lambda r: (r["game"] or "", r["rank"])),
            "claim_tags": sorted(row["claim_tags"]),
            "caveat": "Authored evidence preserves source identity and should not be read as objective truth.",
        })
    players.sort(key=lambda row: (
        -(row["all_time_list_count"] or 0),
        row["best_all_time_rank"] if row["best_all_time_rank"] is not None else 999,
        row["player"].lower(),
    ))
    return players


def _build_verification_leads(leads):
    return [
        {
            "source_id": source["source_id"],
            "family": source["family"],
            "title": source["title"],
            "url": source.get("url"),
            "author": source.get("author"),
            "author_type": source.get("author_type"),
            "caveats": source.get("caveats", []),
        }
        for source in leads
    ]


def build(path=SOURCES_PATH):
    data = load_json(path)
    validate(data)
    sources_by_id = source_index(data)
    player_rows = defaultdict(_empty_player_row)
    ranking_lists = _build_ranking_lists(data, sources_by_id, player_rows)
    claim_rows = _build_claim_rows(data, sources_by_id, player_rows)
    players = _build_player_summaries(player_rows)
    seeded_sources = [s for s in data["sources"] if s["status"] == SEEDED]
    leads = [s for s in data["sources"] if s["status"] == VERIFICATION_LEAD]
    return {
        "schema_version": data["schema_version"],
        "meta": {
            "retrieved_date": data.get("retrieved_date"),
            "source_count": len(data["sources"]),
            "seeded_source_count": len(seeded_sources),
            "verification_lead_count": len(leads),
            "ranking_source_count": len(data.get("rankings", [])),
            "claim_count": len(data.get("claims", [])),
            "verdict": data.get("methodology", {}).get("verdict"),
        },
        "ranking_lists": ranking_lists,
        "claims": claim_rows,
        "players": players,
        "verification_leads": _build_verification_leads(leads),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=SOURCES_PATH)
    parser.add_argument("--output", default=OUT_PATH)
    parser.add_argument("--check", action="store_true", help="Validate and build without writing output")
    args = parser.parse_args()

    data = build(args.input)
    if not args.check:
        with open(args.output, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
