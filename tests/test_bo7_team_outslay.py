import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "analysis" / "bo7_team_outslay.py"
SPEC = importlib.util.spec_from_file_location("bo7_team_outslay", MODULE_PATH)
team_analysis = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(team_analysis)


def player_row(player, team, opponent, kills, deaths, win, *, series="s1", mode="Hardpoint"):
    return {
        "Player": player,
        "PlayerName": player,
        "Event": "Call of Duty League/2026 Season/Major 1",
        "EventId": "Call of Duty League/2026 Season/Major 1",
        "Game": "Black Ops 7",
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


def complete_map(*, series="s1", winner_kills=(25, 24, 23, 22), loser_kills=(20, 19, 18, 17)):
    rows = []
    for index in range(4):
        rows.append(player_row(f"Winner{index}", "W", "L", winner_kills[index], 20, 1, series=series))
        rows.append(player_row(f"Loser{index}", "L", "W", loser_kills[index], 24, 0, series=series))
    return rows


def normalized(rows):
    result, _ = team_analysis.respawn_data.normalize_rows(rows)
    return result


def test_aggregate_team_maps_builds_opposing_totals_and_kill_differentials():
    team_maps, audit = team_analysis.aggregate_team_maps(normalized(complete_map()))

    assert audit == {"maps": 1, "validMaps": 1, "teamMaps": 2, "invalidMaps": []}
    by_team = {row["team"]: row for row in team_maps}
    assert by_team["W"]["kills"] == 94
    assert by_team["W"]["opponentKills"] == 74
    assert by_team["W"]["killDiff"] == 20
    assert by_team["W"]["slayBucket"] == "outslay"
    assert by_team["L"]["killDiff"] == -20
    assert by_team["L"]["slayBucket"] == "outslayed"


def test_aggregate_team_maps_rejects_bad_team_opponent_resolution():
    rows = complete_map()
    rows[0]["TeamVs"] = "SomeoneElse"
    team_maps, audit = team_analysis.aggregate_team_maps(normalized(rows))

    assert team_maps == []
    assert audit["validMaps"] == 0
    assert "opponent fields do not resolve to the other team" in audit["invalidMaps"][0]["reasons"]


def test_team_summary_keeps_requested_denominators_and_exception_counts():
    rows = []
    rows += complete_map(series="a")
    rows += complete_map(series="b", winner_kills=(15, 15, 15, 15), loser_kills=(20, 20, 20, 20))
    rows += complete_map(series="c", winner_kills=(20, 20, 20, 20), loser_kills=(20, 20, 20, 20))
    team_maps, _ = team_analysis.aggregate_team_maps(normalized(rows))
    summary = {row["team"]: row for row in team_analysis.aggregate_teams(team_maps)}["W"]

    assert summary["maps"] == 3
    assert summary["outslayMaps"] == 1
    assert summary["winGivenOutslay"] == 1
    assert summary["outslayFailures"] == 0
    assert summary["outslayedMaps"] == 1
    assert summary["negativeSlayWins"] == 1
    assert summary["winGivenOutslayed"] == 1
    assert summary["tiedMaps"] == 1
    assert summary["winGivenTied"] == 1
    assert summary["outslayGivenWin"] == 1 / 3
    assert summary["winGivenNonOutslay"] == 1
    assert summary["outslayWinUplift"] == 0


def test_every_team_is_included_and_small_samples_are_flagged():
    team_maps, _ = team_analysis.aggregate_team_maps(normalized(complete_map()))
    summaries = team_analysis.aggregate_teams(team_maps)

    assert {row["team"] for row in summaries} == {"W", "L"}
    assert all(row["maps"] == 1 for row in summaries)
    assert all(row["stability"] == "very small sample" for row in summaries)


def test_challengers_qualified_teams_and_their_maps_are_excluded():
    league_map, _ = team_analysis.aggregate_team_maps(normalized(complete_map(series="league")))
    challenger_raw = complete_map(series="challenger")
    for row in challenger_raw:
        if row["Team"] == "L":
            row["Team"] = "OMiT"
            row["TeamVs"] = "W"
        else:
            row["TeamVs"] = "OMiT"
    challenger_map, _ = team_analysis.aggregate_team_maps(normalized(challenger_raw))

    filtered, excluded_maps = team_analysis.exclude_challengers_teams(league_map + challenger_map)

    assert excluded_maps == 1
    assert len(filtered) == 2
    assert {row["team"] for row in filtered} == {"W", "L"}


def test_kill_differential_bands_keep_zero_separate():
    assert team_analysis.diff_band(-20) == "-20 or worse"
    assert team_analysis.diff_band(-10) == "-19 to -10"
    assert team_analysis.diff_band(-1) == "-9 to -1"
    assert team_analysis.diff_band(0) == "Tied (0)"
    assert team_analysis.diff_band(1) == "+1 to +9"
    assert team_analysis.diff_band(10) == "+10 to +19"
    assert team_analysis.diff_band(20) == "+20 or better"


def test_committed_bo7_cache_produces_complete_team_report():
    raw = json.loads(team_analysis.respawn_data.CACHE_PATH.read_text())
    player_rows, _ = team_analysis.respawn_data.normalize_rows(raw)
    player_audit = team_analysis.respawn_data.validate_maps(player_rows)
    team_maps, team_audit = team_analysis.aggregate_team_maps(player_audit["rows"])

    assert team_audit["maps"] == 223
    assert team_audit["validMaps"] == 223
    assert team_audit["teamMaps"] == 446
    assert team_audit["invalidMaps"] == []
    filtered, excluded_maps = team_analysis.exclude_challengers_teams(team_maps)
    assert excluded_maps > 0
    assert not ({row["team"] for row in filtered} & team_analysis.CHALLENGERS_TEAMS)

    report = team_analysis.OUT_PATH.read_text()
    assert "Black Ops 7: team outslaying and respawn map wins" in report
    assert "P(team outslayed | team won)" in report
    assert "Slaying reliance: most to least" in report
    assert 'id="summary-table"' in report
    assert 'id="drilldown-table"' in report
    assert "sorter:percentageSorter" in report
    assert "pct(rate)+' · '+num+'/'+den" in report
    assert 'id="bucket-table"' not in report
    assert 'id="conversion-table"' not in report
    assert 'id="failure-table"' not in report
    assert 'id="negative-slay-table"' not in report
    assert 'id="differential-table"' not in report
    assert 'id="band-table"' not in report
    assert "GitHub #27" in report
