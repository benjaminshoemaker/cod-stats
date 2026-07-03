"""
Derive per-player CAREER-PATH features from player_participation.json.

These exist to attack the teammate confound: wins/titles/champs are *team*
outcomes that teammates share, so distance partly just recovers rosters. Path
features describe the player's own journey — how many squads they played for,
how loyal they were, how deep they ran — so two players with identical trophies
can still separate on *how* they got there.

Split:
  * de-confounding (player-specific): distinct_teams, avg_tenure, loyalty
  * enriching (still team-shared, but richer than wins): attendances,
    finals_rate (top-2), deep_run_rate (top-4), win_conversion, best_place

Writes analysis/out/path_features.json keyed by player (lower-cased).
Run after `player_participation.json` is fetched.
"""
import json, os, re, sys
from collections import defaultdict

# wiki OverviewPage disambiguates same-handle players: "Methodz (Anthony Zinni)".
# The leaderboard uses the bare handle, so strip the parenthetical to join.
_DISAMBIG = re.compile(r"\s*\([^)]*\)\s*$")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import build_data

NONPLAY = {'DNS', 'DNP', 'DQ', '', None}


def _played(date):
    return (date or "0000") <= build_data.ASOF


def _keep(row):
    return (
        row["Game"] not in build_data.DROP_GAMES
        and row["Event"] not in build_data.DROP_EVENTS
        and _played(row.get("Date"))
    )


def _num(place_number, place):
    """Best-effort integer placement (PlaceNumber, else parse '17-24' -> 17)."""
    try:
        return int(place_number)
    except (TypeError, ValueError):
        pass
    if place:
        head = str(place).split("-")[0].strip()
        try:
            return int(head)
        except ValueError:
            return None
    return None


def derive(participation_json=None, events_json=None):
    participation_json = participation_json or os.path.join(
        ROOT, "player_participation.json")
    events_json = events_json or os.path.join(ROOT, "major_events.json")
    rows = json.load(open(participation_json))
    counted_events = {r["Event"] for r in json.load(open(events_json)) if _keep(r)}

    byp = defaultdict(list)
    for r in rows:
        if not _keep(r):
            continue
        if r.get("Event") not in counted_events:
            continue
        if r.get("Place") in NONPLAY:
            continue
        byp[build_data.mkey(r["Player"])].append(r)

    out = {}
    for pl, evs in byp.items():
        # de-dupe on event (a player can appear once per major)
        seen, uniq = set(), []
        for r in sorted(evs, key=lambda x: (x.get("Date") or "", x.get("Event") or "")):
            if r["Event"] in seen:
                continue
            seen.add(r["Event"])
            uniq.append(r)

        teams = [r.get("Team") for r in uniq if r.get("Team")]
        distinct_teams = len(set(teams))
        attendances = len(uniq)
        places = [_num(r.get("PlaceNumber"), r.get("Place")) for r in uniq]
        places = [p for p in places if p is not None]

        wins = sum(1 for p in places if p == 1)
        finals = sum(1 for p in places if p is not None and p <= 2)
        deep = sum(1 for p in places if p is not None and p <= 4)

        out[pl] = {  # keyed by full OverviewPage; consolidated to bare handle below
            # --- de-confounding: the player's own path ---
            "distinct_teams": distinct_teams,
            "avg_tenure": round(attendances / distinct_teams, 2) if distinct_teams else 0,
            # --- enriching: richer than a bare win count ---
            "attendances": attendances,
            "finals_rate": round(finals / attendances, 3) if attendances else 0,
            "deep_run_rate": round(deep / attendances, 3) if attendances else 0,
            "win_conversion": round(wins / attendances, 3) if attendances else 0,
            "best_place": min(places) if places else None,
        }

    # consolidate to bare handle; on collision keep the more-active player
    bare = {}
    for k, v in out.items():
        h = _DISAMBIG.sub("", k).lower()
        if h not in bare or v["attendances"] > bare[h]["attendances"]:
            bare[h] = v
    return bare


def main():
    feats = derive()
    outp = os.path.join(HERE, "out", "path_features.json")
    json.dump(feats, open(outp, "w"), indent=2)
    print(f"Wrote {outp}  ({len(feats)} players)")
    # quick sanity peek on the marquee names
    for who in ["crimsix", "scump", "simp", "abezy", "cellium", "karma",
                "clayster", "formal", "shotzzy"]:
        if who in feats:
            f = feats[who]
            print(f"  {who:9s} teams={f['distinct_teams']} "
                  f"tenure={f['avg_tenure']} att={f['attendances']} "
                  f"finals%={f['finals_rate']} deep%={f['deep_run_rate']} "
                  f"conv={f['win_conversion']} best={f['best_place']}")


if __name__ == "__main__":
    main()
