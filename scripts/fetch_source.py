#!/usr/bin/env python3
"""Re-pull the committed source JSON from the CoD Esports Wiki Cargo API.

Regenerates (in the repo root):
  * major_events.json      — every Major/Premier tournament + its winner
  * player_event_wins.json — every individual player's 1st-place finish at those
  * champs_wins.json       — CoD Championship winners (raw cargoquery format)
  * team_participation.json— every team result row at those tournaments

This is the "fix drift" tool: when scripts/check_live_source.py (or the daily
source-check workflow) reports a mismatch, run this, then:
  1. review the git diff of the four JSON files,
  2. update PUBLISHED in build_data.py if the top-50 list moved
     (run with --published to print the current live list as a paste-able literal),
  3. bump ASOF, re-run `python3 build_data.py`, and commit the lot.

Dates use Tournaments.DateStart (aliased to Date), matching the original pull.
The wiki rate-limits aggressively: requests are retried with backoff and paced
with a courtesy sleep, so a full pull takes a couple of minutes.

Run:  python3 scripts/fetch_source.py [--published]
"""
import json, os, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

UA = "Mozilla/5.0 (compatible; cod-stats-source-fetch/1.0; +https://cod-stats-one.vercel.app)"
API = "https://cod-esports.fandom.com/api.php"
PAGE = 500          # cargo API row cap per request
PAUSE = 5           # courtesy sleep between successful requests (seconds)

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
    print(f"wrote {name} ({len(obj['cargoquery']) if isinstance(obj, dict) else len(obj)} rows)")


def fetch_major_events():
    rows = cargo_all({
        "tables": "Tournaments=TO,TournamentResults=TR",
        "fields": ("TO.Name=Event,TO.Game=Game,TO.DateStart=Date,TR.Team=Winner,"
                   "TO.EventType=EventType,TO.Prizepool=Prizepool,TO.Location=Location,TO.Region=Region"),
        "where": MAJOR_WHERE + " AND TR.Place_Number=1",
        "join_on": "TO.OverviewPage=TR.OverviewPage",
        "order_by": "TO.DateStart,TO.Name",
    })
    save("major_events.json", flat(rows))


def fetch_player_event_wins():
    rows = cargo_all({
        "tables": PLAYER_TABLES,
        "fields": "PL.OverviewPage=Player,TO.Name=Event,TO.Game=Game,TO.DateStart=Date",
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
        "fields": ("PL.OverviewPage=Player,TO.Name=Event,TO.Game=Game,"
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
        "fields": "TO.Game=Game,TO.Name=Event,TR.Team=Team,TR.Place=Place",
        "where": MAJOR_WHERE,
        "join_on": "TO.OverviewPage=TR.OverviewPage",
        "order_by": "TO.DateStart,TO.Name,TR.Team",
    })
    save("team_participation.json", flat(rows))


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
    for step in (fetch_major_events, fetch_player_event_wins, fetch_champs_wins,
                 fetch_player_participation, fetch_team_participation):
        step()
        time.sleep(PAUSE)
    print("\nNow: review `git diff`, update PUBLISHED/ASOF in build_data.py if needed,")
    print("re-run `python3 build_data.py`, then `./verify.sh`.")


if __name__ == "__main__":
    main()
