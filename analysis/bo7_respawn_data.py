#!/usr/bin/env python3
"""Load and validate BO7 Major/Premier respawn player-map rows with team results."""
import json
import time
from collections import Counter, defaultdict
from pathlib import Path

from build_data import ASOF
from scripts import fetch_source


ROOT = Path(__file__).resolve().parents[1]
GAME = "Black Ops 7"
CACHE_PATH = ROOT / "analysis/bo7_respawn_player_maps.json"
PROGRESS_PATH = ROOT / "analysis/bo7_respawn_player_maps.progress.json"
LEGACY_CACHE_PATH = ROOT / "analysis/recent_titles_player_kd_win_stats.json"
EVENTS_PATH = ROOT / "player_stats_participants.events.json"
PARTICIPANT_STATS_PATH = ROOT / "player_stats_participants.json"
VOR_WIN_CACHE_PATH = ROOT / "analysis/vor_mapwin_target_stats.json"
RESULT_QUERY_PAUSE = 30


def stat_bool(value):
    text = str(value if value is not None else "").strip().lower()
    if text in {"1", "true", "t", "yes", "y", "win", "won"}:
        return 1
    if text in {"0", "false", "f", "no", "n", "loss", "lost"}:
        return 0
    return None


def stat_int(value):
    try:
        return int(str(value).strip().replace(",", ""))
    except (TypeError, ValueError):
        return None


def is_respawn(mode):
    text = str(mode or "").lower().replace("&", "and")
    return not ("search" in text and "destroy" in text)


def player_name(row):
    return row.get("Player") or row.get("PlayerLink") or row.get("PlayerName") or ""


def event_key(row):
    return row.get("EventId") or row.get("Event") or ""


def map_key(row):
    return (
        row.get("Game") or "", event_key(row), row.get("SeriesId") or "",
        row.get("Mode") or "", row.get("Map") or "", row.get("Date") or "",
    )


def normalize_rows(raw_rows):
    rows = []
    rejected = {"non_target_game": 0, "non_respawn": 0, "invalid_stats_or_result": 0}
    for raw in raw_rows:
        if raw.get("Game") != GAME:
            rejected["non_target_game"] += 1
            continue
        if not is_respawn(raw.get("Mode")):
            rejected["non_respawn"] += 1
            continue
        kills = stat_int(raw.get("Kills"))
        deaths = stat_int(raw.get("Deaths"))
        win = stat_bool(raw.get("Win"))
        player = player_name(raw)
        if kills is None or deaths is None or win is None or not player:
            rejected["invalid_stats_or_result"] += 1
            continue
        row = dict(raw)
        row.update({"player": player, "kills": kills, "deaths": deaths, "win": win})
        rows.append(row)
    return rows, rejected


def validate_maps(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[map_key(row)].append(row)
    valid_keys = []
    invalid = []
    for key, group in sorted(groups.items()):
        reasons = []
        if len(group) != 8:
            reasons.append(f"expected 8 player rows, found {len(group)}")
        if len({row["player"] for row in group}) != len(group):
            reasons.append("duplicate player rows")
        teams = {row.get("Team") or "" for row in group}
        if len(teams) != 2 or "" in teams:
            reasons.append(f"expected 2 named teams, found {len(teams - {''})}")
        wins = Counter(row["win"] for row in group)
        if wins != Counter({0: 4, 1: 4}):
            reasons.append(f"expected four win and four loss rows, found {dict(wins)}")
        for team in teams - {""}:
            if len({row["win"] for row in group if row.get("Team") == team}) != 1:
                reasons.append(f"inconsistent result within team {team}")
        if reasons:
            invalid.append({"key": list(key), "rows": len(group), "reasons": reasons})
        else:
            valid_keys.append(key)
    valid_set = set(valid_keys)
    valid_rows = [row for row in rows if map_key(row) in valid_set]
    return {
        "maps": len(groups), "validMaps": len(valid_keys), "validRows": len(valid_rows),
        "validMapKeys": valid_keys, "invalidMaps": invalid, "rows": valid_rows,
    }


def target_events():
    events = json.loads(EVENTS_PATH.read_text())
    stats = json.loads(PARTICIPANT_STATS_PATH.read_text())
    recorded = {
        (row.get("Game"), row.get("EventId") or row.get("Event"))
        for row in stats if row.get("Game") == GAME and is_respawn(row.get("Mode"))
    }
    return [
        event for event in events
        if event.get("game") == GAME
        and (event.get("date") or "") <= ASOF
        and "challengers" not in f"{event.get('event') or ''} {event.get('page') or ''}".lower()
        and (event.get("game"), event.get("page")) in recorded
    ]


def result_key(row):
    return (
        row.get("Game") or "", row.get("EventId") or row.get("Event") or "",
        row.get("SeriesId") or "", row.get("Mode") or row.get("Gamemode") or "",
        row.get("Map") or "", row.get("Date") or "", row.get("Team") or "",
    )


def result_query_params(events, mode):
    pages = [event["page"] for event in events]
    return {
        "tables": "PlayerStats=PS",
        "fields": (
            "PS.TournamentPage=EventId,PS.GameTitle=Game,PS.Gamemode=Mode,PS.Date=Date,"
            "PS.Team=Team,PS.TeamVs=TeamVs,PS.Map=Map,PS.SeriesId=SeriesId,PS.Win=Win"
        ),
        "where": (
            f"PS.TournamentPage IN({fetch_source._quoted(pages)}) "
            f"AND PS.GameTitle={fetch_source._quoted([GAME])} "
            f"AND PS.Gamemode={fetch_source._quoted([mode])} "
            f'AND PS.Date <= "{ASOF}" AND PS.Win IS NOT NULL'
        ),
        "group_by": (
            "PS.TournamentPage,PS.GameTitle,PS.Gamemode,PS.Date,PS.Team,PS.TeamVs,"
            "PS.Map,PS.SeriesId,PS.Win"
        ),
        "order_by": "PS.Date,PS.TournamentPage,PS.SeriesId,PS.Gamemode,PS.Team",
    }


def seed_result_index(paths):
    result_index = {}
    conflicts = []
    for path in paths:
        if not path.exists():
            continue
        for row in json.loads(path.read_text()):
            if row.get("Game") != GAME or not is_respawn(row.get("Mode")):
                continue
            win = stat_bool(row.get("Win"))
            if win is None:
                continue
            key = result_key(row)
            if key in result_index and result_index[key] != win:
                conflicts.append(key)
            result_index[key] = win
    if conflicts:
        raise RuntimeError(f"Conflicting cached team-map results for {len(conflicts)} keys")
    return result_index


def materialize_rows(local_rows, pages, result_index):
    rows, missing = [], []
    for raw in local_rows:
        if raw.get("Game") != GAME or not is_respawn(raw.get("Mode")):
            continue
        event = raw.get("EventId") or raw.get("Event") or ""
        if event not in pages:
            continue
        row = dict(raw)
        row["EventId"] = event
        win = result_index.get(result_key(row))
        if win is None:
            missing.append(result_key(row))
            continue
        row["Win"] = win
        rows.append(row)
    return rows, missing


def load_or_fetch_rows():
    events = target_events()
    pages = {event["page"] for event in events}
    if CACHE_PATH.exists():
        rows = json.loads(CACHE_PATH.read_text())
        cached_pages = {event_key(row) for row in rows}
        if rows and cached_pages == pages and all(stat_bool(row.get("Win")) is not None for row in rows):
            return rows, {"completed": ["team-map-results"], "failed": {}}

    local_rows = json.loads(PARTICIPANT_STATS_PATH.read_text())
    result_index = seed_result_index([CACHE_PATH, LEGACY_CACHE_PATH, VOR_WIN_CACHE_PATH])
    completed, failed, needed = [], {}, []
    modes = sorted({
        row.get("Mode") for row in local_rows
        if row.get("Game") == GAME and event_key(row) in pages and is_respawn(row.get("Mode"))
    })
    for mode in modes:
        expected = {
            result_key(row) for row in local_rows
            if row.get("Game") == GAME and row.get("Mode") == mode and event_key(row) in pages
        }
        key = f"{GAME}|{mode}"
        if expected <= result_index.keys():
            completed.append(key)
        else:
            needed.append((mode, key))

    for index, (mode, key) in enumerate(needed, 1):
        print(f"[{index}/{len(needed)}] fetching team-map results for {GAME} {mode}")
        try:
            result_rows = fetch_source.flat(fetch_source.cargo_all(result_query_params(events, mode)))
        except SystemExit as exc:
            failed[key] = {"error": str(exc)}
            PROGRESS_PATH.write_text(json.dumps({"completed": completed, "failed": failed}))
            continue
        for row in result_rows:
            win = stat_bool(row.get("Win"))
            if win is not None:
                result_index[result_key(row)] = win
        completed.append(key)
        rows, _ = materialize_rows(local_rows, pages, result_index)
        CACHE_PATH.write_text(json.dumps(rows))
        PROGRESS_PATH.write_text(json.dumps({"completed": completed, "failed": failed}))
        if index < len(needed):
            time.sleep(RESULT_QUERY_PAUSE)

    rows, missing = materialize_rows(local_rows, pages, result_index)
    if missing:
        raise RuntimeError(f"Missing team-map result for {len(missing)} local player rows")
    CACHE_PATH.write_text(json.dumps(rows))
    progress = {"completed": completed, "failed": failed, "playerRows": len(rows)}
    PROGRESS_PATH.write_text(json.dumps(progress))
    return rows, progress
