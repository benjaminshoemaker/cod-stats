import pytest

from scripts.build_community_consensus import build
from scripts.build_community_consensus_rollup import (
    build_rollup,
    sort_per_played,
    sort_per_ranked,
    sort_total,
    title_rank_points,
)


def test_bo2_community_consensus_reproduces_research_table():
    rows = build("Black Ops 2")["games"]["Black Ops 2"]
    top = rows[:10]
    assert [(r["consensus_rank"], r["player"]) for r in top] == [
        (1, "Karma"),
        (2, "Crimsix"),
        (3, "Clayster"),
        (4, "ACHES"),
        (5, "Parasite"),
        (6, "MiRx"),
        (7, "TeeP"),
        (8, "Scump"),
        (9, "KiLLa"),
        (10, "JKap"),
    ]
    assert [r["consensus_score"] for r in top] == pytest.approx([
        5.421,
        5.276,
        3.720,
        2.944,
        2.913,
        1.188,
        1.100,
        0.921,
        0.691,
        0.469,
    ])


def test_bo2_comment_scores_reweight_ballots_inside_thread_only():
    result = build("Black Ops 2")
    source = result["source_contributions"]["bo2_reddit_2016_top10_thread"]
    reception = {row["ballot_id"]: row for row in source["ballot_reception"]}

    assert source["weight"] == pytest.approx(1.484924240)
    assert reception["bo2_2016_top10_002"]["comment_score"] == 7
    assert reception["bo2_2016_top10_002"]["normalized_weight"] == pytest.approx(1.135892, abs=0.000001)
    assert reception["bo2_2016_top10_008"]["comment_score"] == -11
    assert reception["bo2_2016_top10_008"]["normalized_weight"] == pytest.approx(0.681535, abs=0.000001)
    assert sum(row["normalized_weight"] for row in reception.values()) == pytest.approx(8.0)
    assert source["scores"]["Karma"] == pytest.approx(1.362638, abs=0.000001)


def test_bo2_keeps_ranked_players_outside_top_10():
    rows = build("Black Ops 2")["games"]["Black Ops 2"]
    by_player = {r["player"]: r for r in rows}
    assert "ProoFy" in by_player
    assert "Jurd" in by_player
    assert "Sharp" in by_player
    assert by_player["ProoFy"]["consensus_rank"] == 11


def test_black_ops_community_consensus_reproduces_research_table():
    rows = build("Black Ops")["games"]["Black Ops"]
    top = rows[:10]
    assert [(r["consensus_rank"], r["player"]) for r in top] == [
        (1, "JKap"),
        (2, "Scump"),
        (3, "ProoFy"),
        (4, "ACHES"),
        (5, "ASSASS1N"),
        (6, "John"),
        (7, "MerK"),
        (8, "TeeP"),
        (9, "BigTymeR"),
        (10, "StaiNViLLe"),
    ]
    assert [r["consensus_score"] for r in top] == pytest.approx([
        8.045,
        3.875,
        1.839,
        1.563,
        1.034,
        0.926,
        0.744,
        0.572,
        0.508,
        0.476,
    ])


def test_black_ops_keeps_ranked_players_outside_top_10():
    rows = build("Black Ops")["games"]["Black Ops"]
    by_player = {r["player"]: r for r in rows}
    assert "Dedo" in by_player
    assert "Rambo" in by_player
    assert "Virus" in by_player
    assert by_player["Dedo"]["consensus_rank"] == 11


def test_mw3_community_consensus_reproduces_research_table():
    rows = build("Modern Warfare 3")["games"]["Modern Warfare 3"]
    top = rows[:10]
    assert [(r["consensus_rank"], r["player"]) for r in top] == [
        (1, "Scump"),
        (2, "ProoFy"),
        (3, "MerK"),
        (4, "BigTymeR"),
        (5, "Rambo"),
        (6, "JKap"),
        (7, "Parasite"),
        (7, "TeeP"),
        (9, "ACHES"),
        (10, "PHiZZURP"),
    ]
    assert [r["consensus_score"] for r in top] == pytest.approx([
        4.242,
        0.828,
        0.813,
        0.717,
        0.585,
        0.300,
        0.156,
        0.156,
        0.150,
        0.050,
    ])


def test_ghosts_community_consensus_reproduces_research_table():
    rows = build("Ghosts")["games"]["Ghosts"]
    top = rows[:10]
    assert [(r["consensus_rank"], r["player"]) for r in top] == [
        (1, "Crimsix"),
        (2, "ACHES"),
        (3, "Karma"),
        (4, "Scump"),
        (5, "TeeP"),
        (6, "Clayster"),
        (7, "Nadeshot"),
        (8, "Apathy"),
        (9, "Nameless"),
        (10, "ProoFy"),
    ]
    assert [r["consensus_score"] for r in top] == pytest.approx([
        8.712,
        7.418,
        6.940,
        6.670,
        6.189,
        5.641,
        5.334,
        5.290,
        5.246,
        5.116,
    ])


def test_midseason_aggregate_sources_are_discounted():
    result = build("Ghosts")
    midseason = result["source_contributions"]["ghosts_reddit_2014_midseason_top30_poll"]
    end_of_title = result["source_contributions"]["ghosts_reddit_2014_end_top50_poll"]
    assert midseason["season_coverage_multiplier"] == pytest.approx(0.60)
    assert end_of_title["season_coverage_multiplier"] == pytest.approx(1.00)
    assert midseason["weight"] < end_of_title["weight"] / 2


def test_ghosts_keeps_ranked_players_outside_top_10():
    rows = build("Ghosts")["games"]["Ghosts"]
    by_player = {r["player"]: r for r in rows}
    assert "FormaL" in by_player
    assert "Muddawg" in by_player
    assert "Vade" in by_player
    assert by_player["FormaL"]["consensus_rank"] == 14


def test_advanced_warfare_community_consensus_reproduces_research_table():
    rows = build("Advanced Warfare")["games"]["Advanced Warfare"]
    top = rows[:10]
    assert [(r["consensus_rank"], r["player"]) for r in top] == [
        (1, "Scump"),
        (2, "Clayster"),
        (3, "FormaL"),
        (4, "Huke"),
        (5, "ZooMaa"),
        (6, "Crimsix"),
        (7, "SlasheR"),
        (8, "Saints"),
        (9, "Enable"),
        (10, "Karma"),
    ]
    assert [r["consensus_score"] for r in top] == pytest.approx([
        5.030,
        3.655,
        3.402,
        1.386,
        1.238,
        0.585,
        0.455,
        0.420,
        0.153,
        0.138,
    ])


def test_advanced_warfare_keeps_ranked_players_outside_top_10():
    rows = build("Advanced Warfare")["games"]["Advanced Warfare"]
    by_player = {r["player"]: r for r in rows}
    assert "Jurd" in by_player
    assert "Parasite" in by_player
    assert "Attach" in by_player
    assert by_player["Jurd"]["consensus_rank"] == 11


def test_black_ops_3_community_consensus_reproduces_research_table():
    rows = build("Black Ops 3")["games"]["Black Ops 3"]
    top = rows[:10]
    assert [(r["consensus_rank"], r["player"]) for r in top] == [
        (1, "Scump"),
        (2, "FormaL"),
        (3, "John"),
        (4, "SlasheR"),
        (5, "Apathy"),
        (6, "Crimsix"),
        (7, "Octane"),
        (8, "AquA"),
        (9, "Karma"),
        (10, "Slacked"),
    ]
    assert [r["consensus_score"] for r in top] == pytest.approx([
        6.603,
        6.025,
        5.087,
        3.984,
        3.425,
        2.782,
        2.439,
        2.313,
        2.072,
        1.964,
    ])


def test_black_ops_3_keeps_ranked_players_outside_top_10():
    rows = build("Black Ops 3")["games"]["Black Ops 3"]
    by_player = {r["player"]: r for r in rows}
    assert "JKap" in by_player
    assert "Clayster" in by_player
    assert "Parasite" in by_player
    assert by_player["JKap"]["consensus_rank"] == 11


def test_infinite_warfare_community_consensus_reproduces_research_table():
    rows = build("Infinite Warfare")["games"]["Infinite Warfare"]
    top = rows[:10]
    assert [(r["consensus_rank"], r["player"]) for r in top] == [
        (1, "FormaL"),
        (2, "Gunless"),
        (2, "Scump"),
        (4, "Octane"),
        (5, "Zer0"),
        (6, "Classic"),
        (7, "Arcitys"),
        (8, "Bance"),
        (9, "Crimsix"),
        (10, "Dqvee"),
    ]
    assert [r["consensus_score"] for r in top] == pytest.approx([
        7.245,
        5.094,
        5.094,
        4.311,
        2.867,
        2.235,
        2.193,
        1.955,
        1.898,
        1.701,
    ])


def test_infinite_warfare_partial_sources_are_discounted():
    result = build("Infinite Warfare")
    midseason = result["source_contributions"]["iw_reddit_2017_midseason_top10_poll"]
    late_season = result["source_contributions"]["iw_reddit_2017_heading_into_champs_top10_thread"]
    retrospective = result["source_contributions"]["iw_reddit_2021_top5_each_game_thread"]
    assert midseason["season_coverage_multiplier"] == pytest.approx(0.60)
    assert late_season["season_coverage_multiplier"] == pytest.approx(0.85)
    assert retrospective["season_coverage_multiplier"] == pytest.approx(1.00)


def test_infinite_warfare_keeps_ranked_players_outside_top_10():
    rows = build("Infinite Warfare")["games"]["Infinite Warfare"]
    by_player = {r["player"]: r for r in rows}
    assert "Karma" in by_player
    assert "SlasheR" in by_player
    assert "AquA" in by_player
    assert by_player["Karma"]["consensus_rank"] == 11


def test_world_war_ii_community_consensus_reproduces_research_table():
    rows = build("World War II")["games"]["World War II"]
    top = rows[:10]
    assert [(r["consensus_rank"], r["player"]) for r in top] == [
        (1, "Kenny"),
        (2, "Gunless"),
        (3, "SlasheR"),
        (4, "Accuracy"),
        (5, "ZooMaa"),
        (6, "John"),
        (7, "TJHaLy"),
        (8, "Dashy"),
        (9, "Methodz"),
        (10, "Crimsix"),
    ]
    assert [r["consensus_score"] for r in top] == pytest.approx([
        6.268,
        5.804,
        5.097,
        3.728,
        2.921,
        2.872,
        2.572,
        2.317,
        2.200,
        2.199,
    ])


def test_world_war_ii_inclusion_frequency_survey_is_discounted_for_quality():
    result = build("World War II")
    aggregate = result["source_contributions"]["ww2_reddit_2018_end_top10_inclusion_poll"]
    top5_thread = result["source_contributions"]["ww2_reddit_2018_top5_thread"]
    assert aggregate["ballot_count"] == 666
    assert aggregate["base_weight"] == pytest.approx(2.194, abs=0.001)
    assert aggregate["weight"] == pytest.approx(2.632, abs=0.001)
    assert top5_thread["weight"] == pytest.approx(1.800)


def test_world_war_ii_keeps_ranked_players_outside_top_10():
    rows = build("World War II")["games"]["World War II"]
    by_player = {r["player"]: r for r in rows}
    assert "Octane" in by_player
    assert "Skrapz" in by_player
    assert "Assault" in by_player
    assert by_player["Octane"]["consensus_rank"] == 11


@pytest.mark.parametrize(
    ("game", "expected"),
    [
        (
            "Black Ops 4",
            ["Dashy", "Simp", "Octane", "aBeZy", "Dylan", "Envoy", "Priestahh", "SlasheR", "Skrapz", "Temp"],
        ),
        (
            "Modern Warfare",
            ["Simp", "Envoy", "Shotzzy", "aBeZy", "Cellium", "Octane", "Arcitys", "Huke", "Skyz", "Scump"],
        ),
        (
            "Black Ops Cold War",
            ["Simp", "aBeZy", "Cammy", "Cellium", "Insight", "Shotzzy", "Scump", "Standy", "HyDra", "CleanX"],
        ),
        (
            "Vanguard",
            ["Cellium", "Pred", "Dashy", "HyDra", "Simp", "Kenny", "Shotzzy", "Sib", "Attach", "aBeZy"],
        ),
        (
            "Modern Warfare II",
            ["HyDra", "aBeZy", "Scrap", "Cellium", "Pred", "Octane", "KiSMET", "Dashy", "Shotzzy", "Simp"],
        ),
        (
            "Modern Warfare III",
            ["Simp", "Shotzzy", "HyDra", "Scrap", "Dashy", "Cellium", "Drazah", "Pred", "aBeZy", "Ghosty"],
        ),
        (
            "Black Ops 6",
            ["Scrap", "Shotzzy", "Mercules", "HyDra", "Dashy", "Huke", "Neptune", "Cellium", "JoeDeceives", "Simp"],
        ),
    ],
)
def test_late_cdl_era_annual_surveys_reproduce_top_10(game, expected):
    rows = build(game)["games"][game]
    assert [r["player"] for r in rows[:10]] == expected
    assert [r["consensus_rank"] for r in rows[:10]] == list(range(1, 11))


def test_late_cdl_era_aggregate_sources_are_scored_as_surveys():
    result = build()
    for source_id in [
        "bo4_reddit_2019_end_top10_inclusion_poll",
        "mw2019_reddit_2020_end_top30_survey",
        "bocw_reddit_2021_end_top30_survey",
        "vanguard_reddit_2022_end_top30_survey",
        "mwii_reddit_2023_end_top30_survey",
        "mwiii_reddit_2024_end_top30_survey",
        "bo6_reddit_2025_end_top30_survey",
    ]:
        contribution = result["source_contributions"][source_id]
        assert contribution["source_kind"] == "community_aggregate_survey"
        assert contribution["season_coverage_multiplier"] == pytest.approx(1.00)
        assert contribution["coverage_multiplier"] == pytest.approx(1.20)


def test_cross_title_rollup_total_score_order():
    rows = sorted(build_rollup()["rows"], key=sort_total)
    assert [row["player"] for row in rows[:10]] == [
        "Scump",
        "Simp",
        "Dashy",
        "Cellium",
        "aBeZy",
        "Shotzzy",
        "Crimsix",
        "Octane",
        "HyDra",
        "FormaL",
    ]
    assert rows[0]["overall_score"] == pytest.approx(7.636, abs=0.001)
    assert rows[0]["score_per_played_title"] == pytest.approx(0.587, abs=0.001)


def test_cross_title_rollup_career_length_normalized_order():
    rows = sorted(
        [row for row in build_rollup()["rows"] if row["played_titles"] >= 3],
        key=sort_per_played,
    )
    assert [row["player"] for row in rows[:10]] == [
        "Simp",
        "HyDra",
        "Shotzzy",
        "Scrap",
        "Cellium",
        "Scump",
        "aBeZy",
        "Pred",
        "Dashy",
        "FormaL",
    ]
    assert rows[0]["score_per_played_title"] == pytest.approx(0.777, abs=0.001)


def test_cross_title_rollup_ranked_title_peak_order():
    rows = sorted(
        [row for row in build_rollup()["rows"] if row["ranked_titles"] >= 3],
        key=sort_per_ranked,
    )
    assert [row["player"] for row in rows[:10]] == [
        "Scrap",
        "Simp",
        "HyDra",
        "Shotzzy",
        "Dashy",
        "Cellium",
        "aBeZy",
        "ProoFy",
        "TeeP",
        "Scump",
    ]
    assert rows[0]["score_per_ranked_title"] == pytest.approx(0.870, abs=0.001)


def test_cross_title_rollup_uses_equal_top_heavy_season_weighting():
    result = build_rollup()
    assert result["titles"] == [
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
    rows = {row["player"]: row for row in result["rows"]}
    assert title_rank_points(1) == pytest.approx(1.000, abs=0.001)
    assert title_rank_points(5) == pytest.approx(0.699, abs=0.001)
    assert title_rank_points(10) == pytest.approx(0.410, abs=0.001)
    assert title_rank_points(20) == pytest.approx(0.081, abs=0.001)
    assert title_rank_points(31) == pytest.approx(0.000, abs=0.001)
    assert rows["Scump"]["overall_score"] == pytest.approx(7.636, abs=0.001)
    assert rows["Scump"]["score_per_played_title"] == pytest.approx(7.636 / 13, abs=0.001)
    assert rows["Simp"]["overall_score"] == pytest.approx(5.438, abs=0.001)
    assert rows["Simp"]["score_per_played_title"] == pytest.approx(5.438 / 7, abs=0.001)
