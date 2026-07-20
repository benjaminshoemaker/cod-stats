import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "analysis" / "recent_titles_player_kd_win.py"
SPEC = importlib.util.spec_from_file_location("recent_titles_player_kd_win", MODULE_PATH)
recent = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(recent)


def row(player, team, opponent, kills, deaths, win, *, series="s1", mode="Hardpoint",
        game="Black Ops 7", event="Call of Duty League/2026 Season/Major 1"):
    return {
        "Player": player,
        "PlayerName": player,
        "Event": event,
        "EventId": event,
        "Game": game,
        "Mode": mode,
        "Date": "2026-01-29",
        "Team": team,
        "TeamVs": opponent,
        "Map": "Scar",
        "SeriesId": series,
        "Win": str(win),
        "Kills": str(kills),
        "Deaths": str(deaths),
    }


def complete_map(series="s1", mode="Hardpoint"):
    rows = []
    for i in range(4):
        rows.append(row(f"Winner{i}", "W", "L", 25 + i, 20, 1, series=series, mode=mode))
        rows.append(row(f"Loser{i}", "L", "W", 18 + i, 24, 0, series=series, mode=mode))
    return rows


def test_normalize_rows_keeps_only_bo7_respawn_and_parses_result():
    rows = complete_map()
    rows.append(row("SearchPlayer", "W", "L", 8, 5, 1, series="s2", mode="Search and Destroy"))
    rows.append(row("BO6Player", "W", "L", 20, 19, 1, series="s3", game="Black Ops 6"))
    rows.append(row("OldGame", "W", "L", 20, 20, 1, series="s4", game="Black Ops Cold War"))

    normalized, rejected = recent.normalize_rows(rows)

    assert len(normalized) == 8
    assert rejected == {"non_target_game": 2, "non_respawn": 1, "invalid_stats_or_result": 0}
    assert normalized[0]["win"] in {0, 1}
    assert normalized[0]["kd"] == normalized[0]["kills"] / normalized[0]["deaths"]


def test_validate_maps_requires_complete_balanced_player_rows():
    normalized, _ = recent.normalize_rows(complete_map())
    audit = recent.validate_maps(normalized)
    assert audit["maps"] == 1
    assert audit["validMaps"] == 1
    assert audit["validRows"] == 8
    assert audit["invalidMaps"] == []

    incomplete, _ = recent.normalize_rows(complete_map()[:-1])
    bad = recent.validate_maps(incomplete)
    assert bad["validMaps"] == 0
    assert "expected 8 player rows, found 7" in bad["invalidMaps"][0]["reasons"]


def test_player_summary_preserves_the_three_requested_denominators():
    raw = [
        row("Alpha", "W", "L", 30, 20, 1, series="a"),
        row("Alpha", "W", "L", 22, 22, 1, series="b"),
        row("Alpha", "W", "L", 25, 20, 0, series="c"),
        row("Alpha", "W", "L", 18, 25, 0, series="d"),
    ]
    normalized, _ = recent.normalize_rows(raw)
    summary = recent.aggregate_players(normalized)[0]

    assert summary["player"] == "Alpha"
    assert summary["maps"] == 4
    assert summary["positiveMaps"] == 2
    assert summary["positiveWins"] == 1
    assert summary["winGivenPositive"] == 0.5
    assert summary["positiveGivenWin"] == 0.5
    assert summary["positiveGivenLoss"] == 0.5
    assert summary["positiveLosses"] == 1
    assert summary["negativeWins"] == 0


def test_all_players_remain_in_output_without_a_minimum_map_filter():
    raw = [
        row("OneMap", "W", "L", 30, 20, 1, series="a"),
        row("TwoMaps", "W", "L", 24, 20, 1, series="b"),
        row("TwoMaps", "W", "L", 18, 22, 0, series="c"),
    ]
    normalized, _ = recent.normalize_rows(raw)
    summaries = {p["player"]: p for p in recent.aggregate_players(normalized)}

    assert set(summaries) == {"OneMap", "TwoMaps"}
    assert summaries["OneMap"]["maps"] == 1
    assert summaries["OneMap"]["kdWinCorr"] is None
    assert summaries["OneMap"]["stability"] == "very small sample"
    assert summaries["TwoMaps"]["maps"] == 2


def test_summaries_include_all_respawn_and_each_bo7_respawn_mode():
    raw = [
        row("Alpha", "W", "L", 30, 20, 1, series="a"),
        row("Alpha", "W", "L", 25, 20, 0, series="b", mode="Overload"),
    ]
    normalized, _ = recent.normalize_rows(raw)
    summaries = recent.build_summaries(normalized)

    assert set(summaries) == {"All respawn", "Hardpoint", "Overload"}
    assert summaries["All respawn"][0]["maps"] == 2
    assert summaries["Hardpoint"][0]["maps"] == 1
    assert summaries["Overload"][0]["maps"] == 1


def test_kd_bands_keep_exactly_even_separate_and_report_win_rates():
    raw = [
        row("Alpha", "W", "L", 15, 20, 0, series="a"),
        row("Alpha", "W", "L", 18, 20, 1, series="b"),
        row("Alpha", "W", "L", 20, 20, 1, series="c"),
        row("Alpha", "W", "L", 22, 20, 0, series="d"),
        row("Alpha", "W", "L", 25, 20, 1, series="e"),
    ]
    normalized, _ = recent.normalize_rows(raw)
    bands = {entry["band"]: entry for entry in recent.aggregate_kd_bands(normalized)}

    assert bands["Below 0.80"]["maps"] == 1
    assert bands["0.80–0.99"]["winRate"] == 1
    assert bands["Exactly 1.00"]["maps"] == 1
    assert bands["1.01–1.19"]["winRate"] == 0
    assert bands["1.20+"]["winRate"] == 1


def test_association_context_marks_no_outcome_variation_unavailable():
    raw = [
        row("AlwaysWins", "W", "L", 20 + i, 20, 1, series=str(i))
        for i in range(6)
    ]
    normalized, _ = recent.normalize_rows(raw)
    summary = recent.aggregate_players(normalized)[0]

    assert summary["kdWinCorr"] is None
    assert summary["associationStatus"] == "unavailable — no outcome variation"
    assert summary["kdWinCiLow"] is None
    assert summary["kdWinCiHigh"] is None


def test_committed_recent_titles_cache_is_complete_and_report_is_generated():
    raw = json.loads(recent.CACHE_PATH.read_text())
    normalized, rejected = recent.normalize_rows(raw)
    audit = recent.validate_maps(normalized)

    assert rejected["non_respawn"] == 0
    assert rejected["invalid_stats_or_result"] == 0
    events = recent.target_events()
    assert {row.get("EventId") for row in normalized} == {event["page"] for event in events}
    assert not any("Challengers" in event["page"] for event in events)
    assert {row["Game"] for row in normalized} == {recent.GAME}
    assert audit["maps"] == 261
    assert audit["validMaps"] == 261
    assert audit["validRows"] == 2088
    assert audit["invalidMaps"] == []

    report = recent.OUT_PATH.read_text()
    assert "Black Ops 7: player K/D and respawn map wins" in report
    assert "const summaries=" in report
    assert "All respawn" in report
    assert 'id="mode"' in report
    assert 'id="association-table"' in report
    assert 'id="band-table"' in report
    assert 'id="drilldown-table"' in report
    assert "GitHub #26" in report
    assert "Challengers events are excluded" in report
