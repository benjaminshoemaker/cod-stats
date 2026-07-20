#!/usr/bin/env python3
"""Re-pull the committed source JSON from the CoD Esports Wiki Cargo API.

Regenerates (in the repo root):
  * major_events.json      — every Major/Premier tournament + its winner
  * player_event_wins.json — every individual player's 1st-place finish at those
  * champs_wins.json       — CoD Championship winners (raw cargoquery format)
  * team_participation.json— every team result row at those tournaments
  * player_accolades.json  — individual award/accolade rows from the wiki Awards table
  * player_stats_participants.json — canonical slim map observations for all major participants

This is the "fix drift" tool: when scripts/check_live_source.py (or the daily
source-check workflow) reports a mismatch, run this, then:
  1. review the git diff of the four JSON files,
  2. update PUBLISHED in build_data.py if the top-50 list moved
     (run with --published to print the current live list as a paste-able literal),
  3. bump ASOF, re-run `python3 build_data.py`, and commit the lot.

Dates use Tournaments.DateStart (aliased to Date), matching the original pull.
The wiki rate-limits aggressively: requests are retried with backoff and paced
with a courtesy sleep. PlayerStats pulls take longer and are checkpointed.

player_stats_participants.json is deliberately slimmed before commit. Cargo returns many
mode-specific columns, but the site currently aggregates only kills/deaths,
interactions, K/D, map count, and S&D vs respawn splits. Keeping only the
fields needed to reproduce those aggregates avoids committing a ~70 MB raw
Cargo blob while preserving the map-level audit trail.

Run:  python3 scripts/fetch_source.py [--published] [--awards] [--player-stats]
      python3 scripts/fetch_source.py --player-stats-one
      python3 scripts/fetch_source.py --player-stats-participants
      python3 scripts/fetch_source.py --player-stats-participants-one
      python3 scripts/fetch_source.py --player-stats-participants-limit=N
      python3 scripts/fetch_source.py --player-stats-participants-refresh-events
"""
import json, os, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

from source_model import write_source_manifest

UA = "Mozilla/5.0 (compatible; cod-stats-source-fetch/1.0; +https://mapfive.app)"
API = "https://cod-esports.fandom.com/api.php"
PAGE = 500          # cargo API row cap per request
PAUSE = 5           # courtesy sleep between successful requests (seconds)
PLAYER_STATS_BATCH = 10
PLAYER_STATS_FIELDS = (
    "StatId", "Player", "PlayerName", "PlayerLink", "Event", "EventId", "Game", "Mode", "Date",
    "Team", "TeamVs", "Map", "SeriesId", "Win", "Kills", "Deaths",
)

MAJOR_WHERE = 'TO.Tier IN("Major","Premier")'
# players + substitutes, same clause the wiki's own Major Wins list uses
ROLE_WHERE = '(TP.Role IS NULL OR TP.Role="Substitute")'
PLAYER_JOIN = ("TO.OverviewPage=TR.OverviewPage,TR.PageAndTeam=TP.PageAndTeam,"
               "TP.Link=PR.AllName,PR.OverviewPage=PL.OverviewPage")
PLAYER_TABLES = "Tournaments=TO,TournamentResults=TR,TournamentPlayers=TP,PlayerRedirects=PR,Players=PL"
# "20__" (LIKE single-char wildcards) pins the name to end at the year — looser
# prefixes also match qualifiers and regional finals, which are majors by tier
# but not World Championships.
CHAMPS_WHERE = (f'{MAJOR_WHERE} AND '
                '(TO.Name LIKE "Call of Duty Championship 20__" OR '
                'TO.Name LIKE "Call of Duty World League Championship 20__" OR '
                'TO.Name LIKE "Call of Duty League Championship 20__")')


def cargo(params, offset):
    q = dict(params, **{"action": "cargoquery", "format": "json",
                        "limit": str(PAGE), "offset": str(offset)})
    url = API + "?" + urllib.parse.urlencode(q, quote_via=urllib.parse.quote)
    for attempt in range(6):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=45) as r:
                data = json.load(r)
            if "cargoquery" in data:
                return data["cargoquery"]
            print(f"  retry {attempt+1}: API said {list(data)[:3]}", file=sys.stderr)
        except Exception as e:
            print(f"  retry {attempt+1}: {e}", file=sys.stderr)
        time.sleep(12)
    raise SystemExit("giving up: wiki unreachable / rate-limited — try again later")


def cargo_all(params):
    """Fetch every row of a cargo query, paginating past the 500-row cap."""
    rows, offset = [], 0
    while True:
        batch = cargo(params, offset)
        rows += batch
        if len(batch) < PAGE:
            return rows
        offset += PAGE
        time.sleep(PAUSE)


def flat(rows):
    return [r["title"] for r in rows]


def save(name, obj):
    path = os.path.join(HERE, name)
    with open(path, "w") as f:
        json.dump(obj, f)
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    write_source_manifest(HERE, timestamp, updated_sources={name})
    print(f"wrote {name} ({len(obj['cargoquery']) if isinstance(obj, dict) else len(obj)} rows)")


def fetch_major_events():
    rows = cargo_all({
        "tables": "Tournaments=TO,TournamentResults=TR",
        "fields": ("TO.Name=Event,TO.OverviewPage=EventId,TO.Game=Game,TO.DateStart=Date,TR.Team=Winner,"
                   "TO.EventType=EventType,TO.Prizepool=Prizepool,TO.Location=Location,TO.Region=Region"),
        "where": MAJOR_WHERE + " AND TR.Place_Number=1",
        "join_on": "TO.OverviewPage=TR.OverviewPage",
        "order_by": "TO.DateStart,TO.Name",
    })
    save("major_events.json", flat(rows))


def fetch_player_event_wins():
    rows = cargo_all({
        "tables": PLAYER_TABLES,
        "fields": "PL.OverviewPage=Player,TO.Name=Event,TO.OverviewPage=EventId,TO.Game=Game,TO.DateStart=Date",
        "where": f"PL.OverviewPage IS NOT NULL AND {ROLE_WHERE} AND {MAJOR_WHERE} AND TR.Place_Number=1",
        "join_on": PLAYER_JOIN,
        "order_by": "TO.DateStart,TO.Name,PL.OverviewPage",
    })
    save("player_event_wins.json", flat(rows))


def fetch_champs_wins():
    rows = cargo_all({
        "tables": PLAYER_TABLES,
        "fields": "PL.OverviewPage=Player,TO.Name=Event,TO.DateStart=Date",
        "where": f"PL.OverviewPage IS NOT NULL AND {ROLE_WHERE} AND ({CHAMPS_WHERE}) AND TR.Place_Number=1",
        "join_on": PLAYER_JOIN,
        "order_by": "TO.DateStart,PL.OverviewPage",
    })
    # champs_wins.json keeps the raw cargoquery wrapper (historical format)
    save("champs_wins.json", {"cargoquery": rows})


def fetch_player_participation():
    """Player-level participation at every major — ALL placements, not just wins.
    This is the roster/path source: it lets us derive per-player features that
    distinguish teammates by their CAREER PATH (teams played for, tenure) and by
    placement depth (finals reached), rather than only shared trophies."""
    rows = cargo_all({
        "tables": PLAYER_TABLES,
        "fields": ("PL.OverviewPage=Player,TO.Name=Event,TO.OverviewPage=EventId,TO.Game=Game,"
                   "TO.DateStart=Date,TR.Team=Team,TR.Place=Place,"
                   "TR.Place_Number=PlaceNumber"),
        "where": f"PL.OverviewPage IS NOT NULL AND {ROLE_WHERE} AND {MAJOR_WHERE}",
        "join_on": PLAYER_JOIN,
        "order_by": "TO.DateStart,TO.Name,PL.OverviewPage",
    })
    save("player_participation.json", flat(rows))


def fetch_team_participation():
    rows = cargo_all({
        "tables": "Tournaments=TO,TournamentResults=TR",
        "fields": "TO.Game=Game,TO.Name=Event,TO.OverviewPage=EventId,TR.Team=Team,TR.Place=Place",
        "where": MAJOR_WHERE,
        "join_on": "TO.OverviewPage=TR.OverviewPage",
        "order_by": "TO.DateStart,TO.Name,TR.Team",
    })
    save("team_participation.json", flat(rows))


def fetch_player_accolades():
    rows = cargo_all({
        "tables": "Awards=A,Tournaments=T",
        "fields": ("A.TournamentPage=Page,A.PlayerName=Player,A.PlayerLink=PlayerLink,"
                   "A.Type=Type,A.KDR=KDR,T.Name=Event,T.Game=Game,T.DateStart=Date,"
                   "T.Tier=Tier,T.EventType=EventType"),
        "where": ('A.Type IN("Event MVP","Grand Finals MVP","Season MVP",'
                  '"Rookie of the Year","CDL First Team","CDL Second Team",'
                  '"CWL All-Star") AND A.TournamentPage NOT LIKE "%Breaking Point Awards%"'),
        "join_on": "A.TournamentPage=T._pageName",
        "order_by": "T.DateStart,A.TournamentPage,A.Type,A.PlayerName",
    })
    save("player_accolades.json", flat(rows))


def _quoted(values):
    return ",".join('"' + str(v).replace('"', '\\"') + '"' for v in values)


def _load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path) as f:
        return json.load(f)


def _write_json(path, obj):
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f)
    os.replace(tmp, path)


def _active_skill_stat_games(players):
    """Return published player-game pairs where the player was active."""
    from build_data import ASOF, DROP_EVENTS, DROP_GAMES, _played, mkey

    ppart = json.load(open(os.path.join(HERE, "player_participation.json")))
    player_set = {mkey(p) for p in players}
    display = {mkey(p): p for p in players}
    active = {p: set() for p in players}
    for r in ppart:
        mk = mkey(r.get("Player") or "")
        if mk not in player_set:
            continue
        if r.get("Game") in DROP_GAMES or r.get("Event") in DROP_EVENTS:
            continue
        if not _played(r.get("Date")):
            continue
        active[display[mk]].add(r.get("Game"))
    return active


def _skill_stat_chunks(players, season_order):
    """Limit stat pulls to player-game chunks where the leaderboard player was active."""
    active = _active_skill_stat_games(players)

    order = {g: i for i, g in enumerate(season_order)}
    chunks = []
    for player in players:
        for game in sorted(active[player], key=lambda g: order.get(g, 999)):
            chunks.append({"player": player, "game": game, "key": f"{player}|{game}"})
    return chunks


def _skill_stat_game_chunks(players, season_order):
    """Fetch stats by game/player batch while preserving player-game checkpoints."""
    active = _active_skill_stat_games(players)
    order = {g: i for i, g in enumerate(season_order)}
    player_order = {p: i for i, p in enumerate(players)}
    by_game = {}
    for player, games in active.items():
        for game in games:
            by_game.setdefault(game, []).append(player)
    chunks = []
    for game in sorted(by_game, key=lambda g: order.get(g, 999)):
        game_players = sorted(by_game[game], key=lambda p: player_order[p])
        for start in range(0, len(game_players), PLAYER_STATS_BATCH):
            batch = game_players[start:start + PLAYER_STATS_BATCH]
            chunks.append({
                "game": game,
                "players": batch,
                "keys": {f"{player}|{game}" for player in batch},
                "batch": f"{start // PLAYER_STATS_BATCH + 1}/{(len(game_players) + PLAYER_STATS_BATCH - 1) // PLAYER_STATS_BATCH}",
            })
    return chunks


def _stat_row_key(row):
    return tuple(row.get(k) or "" for k in PLAYER_STATS_FIELDS)


def _merge_stat_rows(rows, new_rows):
    seen = {_stat_row_key(r) for r in rows}
    for row in new_rows:
        key = _stat_row_key(row)
        if key in seen:
            continue
        seen.add(key)
        rows.append(row)
    return rows


def _stat_int(value):
    text = str(value if value is not None else "").strip().replace(",", "")
    if not text or not text.lstrip("-").isdigit():
        return None
    return int(text)


def slim_player_stat_rows(rows):
    """Keep only committed PlayerStats fields needed for reproducible skill stats.

    Rows without numeric kills/deaths are dropped because the first objective
    skill metric is based on map-level kills and deaths. Blank optional fields
    are omitted per row to keep the committed JSON compact.
    """
    slim = []
    for row in rows:
        kills = _stat_int(row.get("Kills"))
        deaths = _stat_int(row.get("Deaths"))
        if kills is None or deaths is None:
            continue
        out = {}
        for field in PLAYER_STATS_FIELDS:
            value = row.get(field)
            if value in (None, ""):
                continue
            out[field] = value
        out["Kills"] = kills
        out["Deaths"] = deaths
        slim.append(out)
    return slim


def _completed_chunks_from_rows(rows):
    return {f"{r.get('Player')}|{r.get('Game')}" for r in rows if r.get("Player") and r.get("Game")}


def fetch_player_stats(max_chunks=None):
    sys.path.insert(0, HERE)
    from build_data import ASOF, PUBLISHED, load_sources, season_context

    players = [name for name, _ in PUBLISHED]
    partial_path = os.path.join(HERE, "player_stats.partial.json")
    progress_path = os.path.join(HERE, "player_stats.progress.json")
    rows = _load_json(partial_path, [])
    progress = _load_json(progress_path, {"schema": 1, "completed": []})
    done = set(progress.get("completed", [])) | _completed_chunks_from_rows(rows)
    events_all, events, *_ = load_sources()
    season_order = season_context(events, events_all).order
    player_game_chunks = _skill_stat_chunks(players, season_order)
    game_chunks = _skill_stat_game_chunks(players, season_order)

    def params_for(players_for_game, game):
        return {
        "tables": "PlayerStats=PS,PlayerRedirects=PR,Tournaments=TO",
        "fields": ("PR.OverviewPage=Player,PS.PlayerName=PlayerName,PS.PlayerLink=PlayerLink,"
                   "PS._ID=StatId,TO.Name=Event,PS.TournamentPage=EventId,PS.GameTitle=Game,PS.Gamemode=Mode,"
                   "PS.Date=Date,PS.Team=Team,PS.TeamVs=TeamVs,PS.Kills=Kills,"
                   "PS.Deaths=Deaths,PS.KDRatio=KDRatio,PS.Map=Map,PS.SeriesId=SeriesId,PS.Win=Win,"
                   "PS.SDKills=SDKills,PS.SDDeaths=SDDeaths,PS.SDFirstKill=SDFirstKill,"
                   "PS.SDFirstDeath=SDFirstDeath,PS.SDPlants=SDPlants,PS.SDDefuses=SDDefuses,"
                   "PS.HPKills=HPKills,PS.HPDeaths=HPDeaths,PS.HPTime=HPTime,"
                   "PS.ConKills=ConKills,PS.ConDeaths=ConDeaths,PS.ConCaptures=ConCaptures,"
                   "PS.OVRKills=OVRKills,PS.OVRDeaths=OVRDeaths,PS.OVRCaps=OVRCaps,"
                   "PS.CTFKills=CTFKills,PS.CTFDeaths=CTFDeaths,PS.CTFCaptures=CTFCaptures,"
                   "PS.UPKills=UPKills,PS.UPDeaths=UPDeaths,"
                   "PS.BLIKills=BLIKills,PS.BLIDeaths=BLIDeaths,PS.BLICaps=BLICaps,"
                   "PS.DomKills=DomKills,PS.DomDeaths=DomDeaths,PS.DomCaptures=DomCaptures"),
        "where": (f"PR.OverviewPage IN({_quoted(players_for_game)}) AND PS.GameTitle IS NOT NULL "
                  f"AND PS.GameTitle={_quoted([game])} "
                  f"AND PS.Date <= \"{ASOF}\""),
        "join_on": "PS.PlayerLink=PR.AllName,PS.TournamentPage=TO.OverviewPage",
        "order_by": "PS.Date,PS.TournamentPage,PR.OverviewPage,PS.Gamemode",
        }

    for i, chunk in enumerate(game_chunks, 1):
        remaining_keys = chunk["keys"] - done
        if not remaining_keys:
            print(f"[{i}/{len(game_chunks)}] skipping {chunk['game']} batch {chunk['batch']} (already in partial)")
            continue
        if max_chunks is not None and max_chunks <= 0:
            break
        print(f"[{i}/{len(game_chunks)}] fetching {chunk['game']} batch {chunk['batch']} ({len(remaining_keys)} player-game chunks)")
        rows = _merge_stat_rows(rows, flat(cargo_all(params_for(chunk["players"], chunk["game"]))))
        done |= chunk["keys"]
        _write_json(partial_path, rows)
        progress = {"schema": 1, "completed": sorted(done)}
        _write_json(progress_path, progress)
        if max_chunks is not None:
            max_chunks -= 1
        time.sleep(PAUSE)

    all_done = {c["key"] for c in player_game_chunks} <= done
    if all_done:
        save("player_stats.json", slim_player_stat_rows(rows))
        if os.path.exists(partial_path):
            os.remove(partial_path)
        if os.path.exists(progress_path):
            os.remove(progress_path)
    else:
        print(f"checkpointed {len(rows)} rows for {len(done)}/{len(player_game_chunks)} chunks in player_stats.partial.json")


def _participant_stat_events(refresh=False):
    sys.path.insert(0, HERE)
    from build_data import DROP_EVENTS, DROP_GAMES, _played

    cache_path = os.path.join(HERE, "player_stats_participants.events.json")
    if not refresh and os.path.exists(cache_path):
        return _load_json(cache_path, [])

    rows = flat(cargo_all({
        "tables": "Tournaments=TO",
        "fields": "TO.Name=Event,TO.OverviewPage=OverviewPage,TO.Game=Game,TO.DateStart=Date",
        "where": MAJOR_WHERE,
        "order_by": "TO.DateStart,TO.Name",
    }))
    out, seen = [], set()
    for r in rows:
        event, game, page = r.get("Event"), r.get("Game"), r.get("OverviewPage")
        if not event or not game or not page:
            continue
        if game in DROP_GAMES or event in DROP_EVENTS:
            continue
        if not _played(r.get("Date")):
            continue
        key = (page, game)
        if key in seen:
            continue
        seen.add(key)
        out.append({"event": event, "page": page, "game": game, "date": r.get("Date") or ""})
    _write_json(cache_path, out)
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    write_source_manifest(
        HERE, timestamp, updated_sources={"player_stats_participants.events.json"}
    )
    return out


def _completed_event_pages_from_rows(rows):
    return {r.get("Event") for r in rows if r.get("Event")}


def fetch_player_stats_participants(max_events=None, refresh_events=False):
    """Fetch PlayerStats by major-event page for replacement/VOR baselines."""
    sys.path.insert(0, HERE)
    from build_data import ASOF

    partial_path = os.path.join(HERE, "player_stats_participants.partial.json")
    progress_path = os.path.join(HERE, "player_stats_participants.progress.json")
    rows = _load_json(partial_path, [])
    progress = _load_json(progress_path, {"schema": 1, "completed": [], "failed": {}})
    done = set(progress.get("completed", [])) | _completed_event_pages_from_rows(rows)
    failed = dict(progress.get("failed", {}))
    events = _participant_stat_events(refresh=refresh_events)

    def params_for(event):
        return {
        "tables": "PlayerStats=PS,PlayerRedirects=PR,Tournaments=TO",
        # Keep the live Cargo query aligned with PLAYER_STATS_FIELDS. Asking
        # for unused mode-specific columns makes large event pages much more
        # likely to time out and none of those columns survive slim_player_stat_rows().
        "fields": ("PR.OverviewPage=Player,PS.PlayerName=PlayerName,PS.PlayerLink=PlayerLink,"
                   "PS._ID=StatId,TO.Name=Event,PS.TournamentPage=EventId,PS.GameTitle=Game,"
                   "PS.Gamemode=Mode,PS.Date=Date,PS.Team=Team,PS.TeamVs=TeamVs,"
                   "PS.Map=Map,PS.SeriesId=SeriesId,PS.Win=Win,PS.Kills=Kills,PS.Deaths=Deaths"),
        "where": (f"PS.TournamentPage={_quoted([event['page']])} "
                  f"AND PS.GameTitle={_quoted([event['game']])} "
                  f"AND PS.Date <= \"{ASOF}\""),
        "join_on": "PS.PlayerLink=PR.AllName,PS.TournamentPage=TO.OverviewPage",
        "order_by": "PS.Date,PS.TournamentPage,PR.OverviewPage,PS.Gamemode",
        }

    for i, event in enumerate(events, 1):
        if event["page"] in done:
            print(f"[{i}/{len(events)}] skipping {event['event']} (already in partial)")
            continue
        if max_events is not None and max_events <= 0:
            break
        print(f"[{i}/{len(events)}] fetching {event['event']} ({event['page']})")
        try:
            rows = _merge_stat_rows(rows, flat(cargo_all(params_for(event))))
        except SystemExit as e:
            prior = failed.get(event["page"], {})
            failed[event["page"]] = {
                "event": event["event"],
                "game": event["game"],
                "date": event["date"],
                "attempts": int(prior.get("attempts", 0)) + 1,
                "error": str(e),
                "lastAttempt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            progress = {"schema": 1, "completed": sorted(done), "failed": failed}
            _write_json(progress_path, progress)
            print(f"  failed {event['event']}: {e}; checkpointed and continuing")
            time.sleep(PAUSE * 2)
            continue
        done.add(event["page"])
        failed.pop(event["page"], None)
        _write_json(partial_path, rows)
        progress = {"schema": 1, "completed": sorted(done), "failed": failed}
        _write_json(progress_path, progress)
        if max_events is not None:
            max_events -= 1
        time.sleep(PAUSE)

    all_done = {e["page"] for e in events} <= done
    if all_done:
        slim = slim_player_stat_rows(rows)
        # Validation is deliberately separate from serialization: observation
        # IDs are deterministic build-time fields, while this file remains a
        # faithful slim source snapshot.
        from source_model import canonicalize_map_observations
        canonicalize_map_observations(slim)
        save("player_stats_participants.json", slim)
        if os.path.exists(partial_path):
            os.remove(partial_path)
        if os.path.exists(progress_path):
            os.remove(progress_path)
    else:
        print(f"checkpointed {len(rows)} rows for {len(done)}/{len(events)} events in player_stats_participants.partial.json")


def print_published():
    """Print the live Major Wins list (everyone with >=2 wins, matching the
    PUBLISHED inclusion rule) as a paste-able literal for build_data.py."""
    sys.path.insert(0, os.path.join(HERE, "scripts"))
    from check_live_source import live_major_wins   # same query the wiki's list uses
    live = live_major_wins()
    if live is None:
        raise SystemExit("wiki unreachable — try again later")
    top = sorted((w for w in live.values() if w[0] >= 2), key=lambda w: -w[0])
    print("PUBLISHED = [", end="")
    for i, (wins, name) in enumerate(top):
        print(("" if i % 6 else "\n ") + f"({name!r},{wins}),", end="")
    print("]")


def main():
    if "--published" in sys.argv:
        return print_published()
    if "--awards" in sys.argv:
        return fetch_player_accolades()
    if "--player-stats-one" in sys.argv:
        return fetch_player_stats_participants(max_events=1)
    if "--player-stats-participants-one" in sys.argv:
        return fetch_player_stats_participants(
            max_events=1,
            refresh_events="--player-stats-participants-refresh-events" in sys.argv)
    for arg in sys.argv:
        if arg.startswith("--player-stats-participants-limit="):
            return fetch_player_stats_participants(
                max_events=int(arg.split("=", 1)[1]),
                refresh_events="--player-stats-participants-refresh-events" in sys.argv)
        if arg.startswith("--player-stats-limit="):
            return fetch_player_stats_participants(max_events=int(arg.split("=", 1)[1]))
        if arg.startswith("--player-stats-chunks="):
            raise SystemExit("--player-stats-chunks is retired; use --player-stats-limit for canonical event pages")
    if "--player-stats-participants" in sys.argv:
        return fetch_player_stats_participants(
            refresh_events="--player-stats-participants-refresh-events" in sys.argv)
    if "--player-stats" in sys.argv:
        return fetch_player_stats_participants(
            refresh_events="--player-stats-participants-refresh-events" in sys.argv)
    for step in (fetch_major_events, fetch_player_event_wins, fetch_champs_wins,
                 fetch_player_participation, fetch_team_participation,
                 fetch_player_accolades, fetch_player_stats_participants):
        step()
        time.sleep(PAUSE)
    print("\nNow: review `git diff`, update PUBLISHED/ASOF in build_data.py if needed,")
    print("re-run `python3 build_data.py`, then `./verify.sh`.")


if __name__ == "__main__":
    main()
