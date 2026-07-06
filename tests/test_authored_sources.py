import json
import os

import pytest

from scripts.build_authored_sources import build, validate

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_authored_sources_build_keeps_evidence_unscored():
    result = build()
    assert result["meta"]["seeded_source_count"] == 4
    assert result["meta"]["ranking_source_count"] == 3
    assert result["meta"]["claim_count"] == 1
    assert result["meta"]["verification_lead_count"] == 4

    assert "score" not in result["players"][0]
    assert "consensus_rank" not in result["players"][0]
    assert result["meta"]["verdict"] == "Authored rankings and claims are evidence, not a scored consensus model."


def test_authored_all_time_rankings_preserve_source_identity():
    result = build()
    lists = result["ranking_lists"]

    assert lists["nerd_street_2022_top10_all_time"]["entries"][0] == {
        "rank": 1,
        "player": "Crimsix",
        "claim_tags": ["goat", "greatest", "resume_weighted"],
    }
    assert lists["dexerto_2022_top10_all_time"]["entries"][1]["player"] == "Scump"
    assert lists["tacticalrab_2018_codwiki_top10_all_time"]["entries"][3]["player"] == "JKap"


def test_player_summary_counts_all_time_sources_and_claims():
    result = build()
    players = {row["player"]: row for row in result["players"]}

    assert players["Crimsix"]["all_time_list_count"] == 3
    assert players["Crimsix"]["best_all_time_rank"] == 1
    assert players["Crimsix"]["median_all_time_rank"] == 1
    assert players["Crimsix"]["source_ids"] == [
        "dexerto_2022_top10_all_time",
        "nerd_street_2022_top10_all_time",
        "tacticalrab_2018_codwiki_top10_all_time",
    ]

    assert players["Scump"]["all_time_list_count"] == 3
    assert players["Scump"]["best_all_time_rank"] == 2
    assert players["Scump"]["median_all_time_rank"] == 2
    assert players["Scump"]["claim_count"] == 1
    assert "hardest_to_kill" in players["Scump"]["claim_tags"]
    assert "most_talented" in players["Scump"]["claim_tags"]


def test_verification_leads_are_not_ranked_until_extracted():
    result = build()
    lead_ids = {row["source_id"] for row in result["verification_leads"]}
    assert "breaking_point_2024_mw3_top20_series" in lead_ids
    assert "breaking_point_2025_bo6_top20_series" in lead_ids
    assert "tacticalrab_video_goat_debate_leads" in lead_ids

    assert "breaking_point_2024_mw3_top20_series" not in result["ranking_lists"]
    assert "breaking_point_2025_bo6_top20_series" not in result["ranking_lists"]


def test_seeded_ranking_sources_must_have_entries():
    data = json.load(open(os.path.join(ROOT, "player_authored_sources.json")))
    data["rankings"] = [
        ranking
        for ranking in data["rankings"]
        if ranking["source_id"] != "nerd_street_2022_top10_all_time"
    ]
    with pytest.raises(ValueError, match="seeded ranking source needs entries"):
        validate(data)


def test_duplicate_ranks_are_rejected():
    data = json.load(open(os.path.join(ROOT, "player_authored_sources.json")))
    data["rankings"][0]["entries"][1]["rank"] = 1
    with pytest.raises(ValueError, match="duplicate ranks"):
        validate(data)
