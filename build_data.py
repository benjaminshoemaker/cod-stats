"""Build site/data.js (the era-adjusted CoD major-wins dataset) from the source JSON.

Importable: `from build_data import build, PUBLISHED, ASOF` — `build()` returns the
full APP_DATA dict and raises if any player's reconstructed wins != their published
wiki total. Run directly (`python3 build_data.py`) to (re)write site/data.js.
"""
import json, re, os
from collections import defaultdict, Counter
from dataclasses import dataclass
from fractions import Fraction
from types import SimpleNamespace

from source_model import (
    canonicalize_map_observations,
    load_conflict_resolutions,
    load_source_policy,
    validate_conflict_quarantine,
    validate_source_manifest,
)

HERE = os.path.dirname(os.path.abspath(__file__))
def _p(*parts): return os.path.join(HERE, *parts)

ASOF = '2026-07-19'              # only majors played on/before this count as wins; future-dated
                                 # events still count toward an in-progress season's denominator
DROP_GAMES = {'Warzone', 'Mobile'}   # separate ecosystems — excluded entirely

# One-off corrections for events the wiki's Majors portal tiers as Major/Premier but
# that aren't top-level pro majors. Dropped by exact event name, so the fix survives a
# re-pull from the wiki (fetch_source.py) and becomes a harmless no-op once the wiki
# reclassifies the event upstream.
#  * "Call of Duty Challengers Finals 2026" — a Challengers (amateur) event, not a pro
#    major. It inflated the Black Ops 7 denominator to 7; BO7 has 6 real majors (4 CDL
#    Majors + Champs + EWC). Flagged by u/BcDownes on r/CoDCompetitive, 2026-07.
#  * "CWL Pro League 2019" — the league/match-bonus page, not a tournament with a
#    champion. BO4 has 6 top-level pro majors: Vegas, Fort Worth, London, Anaheim,
#    Pro League Playoffs, and Champs. The source row had a blank winner but still
#    inflated BO4's season denominator to 7.
DROP_EVENTS = {'Call of Duty Challengers Finals 2026', 'CWL Pro League 2019'}
VALID_PRIMARY_ROLES = {'AR', 'Flex', 'SMG', 'Unknown'}
FORMAL_ACCOLADE_TYPES = {
    'Event MVP',
    'Grand Finals MVP',
    'Season MVP',
    'Rookie of the Year',
    'CDL First Team',
    'CDL Second Team',
    'CWL All-Star',
}
ACCOLADE_LABELS = {
    'event_mvp': 'Event MVP',
    'champs_mvp': 'Champs MVP',
    'grand_finals_mvp': 'Grand Finals MVP',
    'season_mvp': 'Season MVP',
    'rookie_of_the_year': 'Rookie of the Year',
    'cdl_first_team': 'CDL First Team',
    'cdl_second_team': 'CDL Second Team',
    'cwl_all_star': 'CWL All-Star',
}
ACCOLADE_SOURCE_TIER = 2
REQUIRED_CORE_SOURCE_FILES = {
    'major_events.json',
    'player_event_wins.json',
    'champs_wins.json',
    'player_participation.json',
    'team_participation.json',
    'player_accolades.json',
    'player_stats_participants.json',
    'player_stats_participants.events.json',
    'legacy_player_event_stats.json',
    'player_roles.json',
    'team_logos.json',
    'community_consensus_sources.json',
    'community_consensus_ballots.json',
    'player_authored_sources.json',
    'source_conflict_resolutions.json',
}

# A player's share divides by what a team *could win* that season, which is not
# always the number of majors played so far:
#  * Structural restriction — Modern Warfare 2019 (CDL 2020) ran a split "Home
#    Series" format: 13 majors were held, but every team played exactly 9 (12 Home
#    Series of 8 teams each = 8 per team, plus the 12-team Champs), verified in
#    team_participation.json. Open-era seasons are deliberately NOT here — their
#    majors were open/qualified events everyone had the opportunity to enter.
#  * In-progress season — the denominator is the number of *scheduled* majors
#    (counted from major_events.json ignoring the ASOF date filter), not the
#    number played so far; otherwise current-season wins are overstated until
#    the season completes (a Black Ops 7 win counting 1/4 instead of 1/7).
STRUCTURAL_DENOM = {'Modern Warfare': 9}

# The wiki's published "Major Wins" leaderboard (display name, raw wins), everyone
# with >=2 console major wins. The build verifies our reconstruction reproduces
# every one of these exactly. Warzone/Mobile events (DROP_GAMES) and future-dated
# events (> ASOF) are excluded, so counts are console majors played to date.
PUBLISHED = [("Crimsix",38),("Scump",28),("Karma",24),("FormaL",23),("ACHES",19),("Clayster",18),
 ("TeeP",18),("Simp",15),("aBeZy",14),("Cellium",11),("Shotzzy",10),("Kenny",10),("MerK",10),
 ("JKap",9),("SlasheR",9),("Arcitys",9),("Envoy",9),("Octane",9),("Priestahh",9),("BigTymeR",9),("Drazah",9),
 ("Huke",8),("Enable",8),("HyDra",8),("Dashy",7),("John",7),("Attach",7),("Parasite",7),
 ("Skyz",7),("Jurd",6),("Apathy",6),("Tommey",6),("MadCat",6),("Joshh",6),("Slacked",6),("ZooMaa",6),
 ("Nadeshot",6),("Gunless",6),("Rambo",5),("ProoFy",5),("Swanny",5),("CleanX",5),("Accuracy",5),
 ("Scrap",5),("TJHaLy",5),("Classic",5),("Loony",5),("iLLeY",5),("KiSMET",5),("Bance",4),
 ("Censor",4),("Dedo",4),("Fero",4),("GunShy",4),("Insight",4),("KiLLa",4),
 ("MiRx",4),("NAMELESS",4),("Prestinni",4),("Saints",4),("XLNC",4),("Cammy",3),
 ("Crowder",3),("Frosty",3),("Ghosty",3),("Havok",3),("MajorManiak",3),("Mak",3),
 ("Mercules",3),("Pred",3),("Sib",3),("ASSASS1N",2),("Bissell",2),("Bobby",2),
 ("04",2),("Abuzah",2),("Cheen",2),("DopedGoat",2),("FEARS",2),("Jake",2),("Mack",2),("Methodz",2),
 ("MuTaTioN",2),("Owakening",2),("PHiZZURP",2),("Ricky",2),("SiLLY",2),("StaiNViLLe",2),
 ("Theory",2),("Tobi",2),("Vengeance",2),("VeXeL",2),("VintaGe",2)]

# Player-specific data-provenance footnotes surfaced on the player page. Kept rare —
# only where a player's total is commonly disputed against other trackers.
PLAYER_NOTES = {
 "Scump": ("Counted here as 28 major wins, following the CoD Esports Wiki's Major/Premier "
           "classification. Some trackers (e.g. breakingpoint, Dexerto) list 30 by including "
           "sub-major or legacy events the wiki treats as minors; the exact events differ by "
           "source and often aren't itemized, so this site defers to the wiki's classification "
           "rather than hand-picking tournaments."),
}

PLAYER_ALIASES = {
    # The wiki awards table uses C6 for Crimsix's 2020 Champs Grand Finals MVP.
    'c6': 'crimsix',
    # Disambiguated wiki names must be explicit: stripping every parenthetical
    # would merge different players who share a display base.
    'jake (jake dalton)': 'jake',
    'methodz (anthony zinni)': 'methodz',
}

def norm(n): return re.sub(r'\s*\(.*?\)\s*', '', n).strip()   # strip disambiguation parenthetical
def mkey(n):                                                   # case-insensitive join key (ABeZy vs aBeZy)
    raw = (n or '').strip().lower()
    if raw in PLAYER_ALIASES:
        return PLAYER_ALIASES[raw]
    if '(' in raw and ')' in raw:
        return raw
    k = norm(n).lower()
    return PLAYER_ALIASES.get(k, k)
def compact_key(n): return re.sub(r'[^a-z0-9]+', '', norm(n or '').lower())

def _played(d): return (d or '0000') <= ASOF
def _keep(x): return x['Game'] not in DROP_GAMES and x['Event'] not in DROP_EVENTS


def validate_source_inputs():
    """Fail closed when source provenance or conflict state is incomplete."""
    load_source_policy(HERE)
    validate_conflict_quarantine(HERE)
    validate_source_manifest(HERE, required=REQUIRED_CORE_SOURCE_FILES)


# --------------------------------------------------------------------------- #
# Source loading + season math
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class SourceBundle:
    events_all: list
    events: list
    player_wins: list
    champs_wins: list
    player_participation: list
    team_participation: list
    accolades: list
    canonical_map_stats: list
    event_pages: list
    deprecated_player_stats: list


def load_source_bundle():
    """Load named source entities for the console-major universe.

    ``events_all`` retains future scheduled majors for in-progress season
    denominators. Participation rows are filtered later because their DNS and
    placement rules are entity-specific. The deprecated broad PlayerStats
    snapshot remains available only as an explicitly named audit source.
    """
    events = json.load(open(_p('major_events.json')))        # [{Event,Game,Date,Winner,...}]
    pwins  = json.load(open(_p('player_event_wins.json')))   # [{Player,Event,Game,Date}]
    champs_rows = json.load(open(_p('champs_wins.json')))['cargoquery']  # [{Player,Event,Date}]
    ppart  = json.load(open(_p('player_participation.json')))  # [{Player,Event,Game,Date,Place,...}] ALL placements
    tpart  = json.load(open(_p('team_participation.json')))    # [{Team,Event,Game,Place}] ALL team placements
    apath = _p('player_accolades.json')
    accolades = json.load(open(apath))
    # Deprecated audit snapshot. It is returned for compatibility with analysis
    # scripts but is never allowed to feed a displayed metric.
    spath = _p('player_stats.json')
    player_stats = json.load(open(spath)) if os.path.exists(spath) else []
    pspath = _p('player_stats_participants.json')
    player_stats_participants = json.load(open(pspath))
    epath = _p('player_stats_participants.events.json')
    event_pages = json.load(open(epath))

    events_all = [e for e in events if _keep(e)]                         # incl. future-dated (scheduled)
    events = [e for e in events_all if _played(e.get('Date'))]
    pwins  = [r for r in pwins if _keep(r) and _played(r.get('Date'))]
    return SourceBundle(
        events_all=events_all,
        events=events,
        player_wins=pwins,
        champs_wins=champs_rows,
        player_participation=ppart,
        team_participation=tpart,
        accolades=accolades,
        canonical_map_stats=player_stats_participants,
        event_pages=event_pages,
        deprecated_player_stats=player_stats,
    )


def load_sources():
    """Compatibility tuple for older analysis scripts; prefer load_source_bundle()."""
    s = load_source_bundle()
    return (
        s.events_all, s.events, s.player_wins, s.champs_wins,
        s.player_participation, s.team_participation, s.accolades,
        s.deprecated_player_stats, s.canonical_map_stats, s.event_pages,
    )


def load_legacy_player_event_stats():
    path = _p('legacy_player_event_stats.json')
    return json.load(open(path))


def build_event_registry(events_all, event_pages, *row_groups):
    """Map tournament display names and page IDs to one canonical event ID.

    New source pulls store Tournaments.OverviewPage as EventId. Existing local
    snapshots can still be bridged through player_stats_participants.events.json,
    which stores {event: display name, page: OverviewPage}.
    """
    by_name, name_by_id = {}, {}

    def add(game, event, event_id):
        game, event, event_id = str(game or ''), str(event or ''), str(event_id or '')
        if not game or not event or not event_id:
            return
        # Explicitly excluded entities cannot influence canonical identity. Their
        # raw rows remain auditable and their resolution is recorded in
        # source_conflicts.json.
        if game in DROP_GAMES or event in DROP_EVENTS:
            return
        old_id = by_name.get((game, event))
        if old_id is not None and old_id != event_id:
            raise RuntimeError(
                f"conflicting event IDs for {game} / {event!r}: {old_id!r} vs {event_id!r}"
            )
        old_name = name_by_id.get((game, event_id))
        if old_name is not None and old_name != event:
            raise RuntimeError(
                f"conflicting event names for {game} / {event_id!r}: {old_name!r} vs {event!r}"
            )
        by_name[(game, event)] = event_id
        by_name[(game, event_id)] = event_id
        name_by_id[(game, event_id)] = event

    for r in event_pages:
        add(r.get('game') or r.get('Game'), r.get('event') or r.get('Event'), r.get('page') or r.get('EventId'))
    for rows in (events_all, *row_groups):
        for r in rows:
            add(r.get('Game'), r.get('Event'), r.get('EventId') or r.get('OverviewPage') or r.get('Page'))
    return {'byName': by_name, 'nameById': name_by_id}


def event_id_for(row, registry):
    event = row.get('Event') or ''
    game = row.get('Game') or ''
    return (row.get('EventId') or row.get('OverviewPage') or row.get('Page') or
            registry['byName'].get((game, event)) or event)


def event_name_for(row, registry):
    event_id = event_id_for(row, registry)
    game = row.get('Game') or ''
    return registry['nameById'].get((game, event_id)) or row.get('Event') or event_id


def validate_cross_source_consistency(events, pwins, champs_rows, ppart, tpart, registry):
    """Reconcile independent winner/placement/championship representations."""
    major_ids = {event_id_for(row, registry) for row in events}
    event_by_id = {event_id_for(row, registry): row for row in events}
    team_winners = defaultdict(set)
    for row in tpart:
        event_id = event_id_for(row, registry)
        if event_id not in major_ids or str(row.get('Place') or '').strip() != '1':
            continue
        team = str(row.get('Team') or '').strip()
        if team:
            team_winners[event_id].add(team)
    for event_id, event in event_by_id.items():
        winners = team_winners.get(event_id, set())
        if len(winners) != 1:
            raise RuntimeError(f"{event_id}: expected exactly one authoritative team winner, got {sorted(winners)}")
        event_winner = str(event.get('Winner') or '').strip()
        if event_winner and compact_key(event_winner) not in {compact_key(team) for team in winners}:
            raise RuntimeError(
                f"{event_id}: event winner {event_winner!r} conflicts with team results {sorted(winners)}"
            )

    win_facts = {
        (mkey(row.get('Player')), event_id_for(row, registry))
        for row in pwins if event_id_for(row, registry) in major_ids
    }
    placement_wins = {
        (mkey(row.get('Player')), event_id_for(row, registry))
        for row in ppart
        if event_id_for(row, registry) in major_ids
        and str(row.get('PlaceNumber') or row.get('Place') or '').strip() == '1'
    }
    if win_facts != placement_wins:
        raise RuntimeError(
            "player-win sources conflict: "
            f"wins-only={sorted(win_facts - placement_wins)[:5]}, "
            f"placements-only={sorted(placement_wins - win_facts)[:5]}"
        )

    champs = set()
    for row in champs_rows:
        raw_player = str(row['title'].get('Player') or '').strip()
        raw_key = raw_player.lower()
        base_key = PLAYER_ALIASES.get(norm(raw_player).lower(), norm(raw_player).lower())
        if raw_key not in PLAYER_ALIASES and base_key in {mkey(n) for n, _ in PUBLISHED} and norm(raw_player) != raw_player:
            raise RuntimeError(f"ambiguous championship player needs review: {raw_player!r}")
        champs.add((mkey(raw_player), row['title'].get('Event')))
    named_wins = {(mkey(row.get('Player')), row.get('Event')) for row in pwins}
    missing_champs = champs - named_wins
    if missing_champs:
        raise RuntimeError(f"championship sources conflict: champs-only={sorted(missing_champs)[:5]}")


def season_context(events, events_all):
    """Per-season counts, chronological order, the pre-BO2 split, and the era
    weights (mbar). held = majors played so far that season; scheduled = all
    majors on the calendar (same file, no date filter); denom = majors a team
    could win. Shares/peak/rescale use denom, so an in-progress season divides
    by its full schedule."""
    majors = Counter(e['Game'] for e in events)
    held = dict(majors)
    scheduled = Counter(e['Game'] for e in events_all)
    denom = {g: STRUCTURAL_DENOM.get(g, scheduled[g]) for g in held}
    first_date = {}
    for e in events:
        g = e['Game']; d = e.get('Date') or '9999'
        if g not in first_date or d < first_date[g]: first_date[g] = d
    season_order = sorted(majors, key=lambda g: first_date[g])
    order_idx = {g: i for i, g in enumerate(season_order)}

    bo2_date = first_date['Black Ops 2']
    pre_bo2 = {g for g in season_order if first_date[g] < bo2_date}

    def mbar(games): return sum(denom[g] for g in games) / len(games)
    return SimpleNamespace(
        majors=majors, held=held, denom=denom, first_date=first_date,
        order=season_order, order_idx=order_idx, pre_bo2=pre_bo2,
        mbar_all=mbar(season_order),
        mbar_post=mbar([g for g in season_order if g not in pre_bo2]))


# --------------------------------------------------------------------------- #
# Source indexing (keyed by mkey, restricted to the published leaderboard)
# --------------------------------------------------------------------------- #
# A player rostered but who did not actually take the stage doesn't count as
# having competed. The wiki marks these 'DNS' (did not start); a blank place is
# likewise not a result. Everything else — including ">12"-style open placements —
# means they played. (Only 'MLG National Championship 2009' DNS rows exist today,
# for SiLLY and NAMELESS, but the guard survives a re-pull.)
NONPLAY = {'DNS', 'DNP', 'DQ', '', None}


def place_x2(r):
    """Return 2x the numeric placement so tied ranges keep exact .5 midpoints."""
    place = str(r.get('Place') or '').strip().replace('*', '')
    m = re.fullmatch(r'(\d+)\s*-\s*(\d+)', place)
    if m:
        return int(m.group(1)) + int(m.group(2))
    m = re.fullmatch(r'>(\d+)', place)
    if m:
        return 2 * (int(m.group(1)) + 1)
    if re.fullmatch(r'\d+', place):
        return 2 * int(place)
    pn = str(r.get('PlaceNumber') or '').strip()
    if re.fullmatch(r'\d+', pn):
        return 2 * int(pn)
    return None


def place_number(r):
    """Return the wiki placement number used for top-2/top-4 rate buckets."""
    pn = str(r.get('PlaceNumber') or '').strip()
    if re.fullmatch(r'\d+', pn):
        return int(pn)
    place = str(r.get('Place') or '').strip().replace('*', '')
    m = re.fullmatch(r'(\d+)\s*-\s*\d+', place)
    if m:
        return int(m.group(1))
    m = re.fullmatch(r'>(\d+)', place)
    if m:
        return int(m.group(1)) + 1
    if re.fullmatch(r'\d+', place):
        return int(place)
    return None


def avg_place_from_x2(place_x2_sum, events):
    if not events:
        return None
    return ((place_x2_sum * 100 + events) // (2 * events)) / 100


def median(values):
    values = sorted(v for v in values if v is not None)
    if not values:
        return None
    mid = len(values) // 2
    if len(values) % 2:
        return values[mid]
    return (values[mid - 1] + values[mid]) / 2


def rate_from_counts(numer, denom):
    """Unrounded rate — displays round exactly once, so the shown percent always
    matches the numerator/denominator rendered beside it (no double rounding)."""
    if not denom:
        return None
    return numer / denom


def select_participation_row(rows, player_key, event_id, resolutions):
    """Choose one player/event fact without using source row order."""
    parsed = [(place_x2(row), row) for row in rows]
    if any(place is None for place, _ in parsed):
        bad = next(row for place, row in parsed if place is None)
        raise RuntimeError(
            f"unparseable placement for {bad['Player']} at {bad['Event']}: {bad.get('Place')!r}"
        )
    best_place = min(place for place, _ in parsed)
    candidates = [row for place, row in parsed if place == best_place]
    teams = {str(row.get('Team') or '').strip() for row in candidates}
    if len(teams) == 1:
        return candidates[0]

    conflict_id = f"participation:{player_key}:{event_id}"
    decision = (resolutions.get('participation') or {}).get(conflict_id)
    if not decision:
        raise RuntimeError(
            f"{conflict_id}: equal best placements have conflicting teams {sorted(teams)}; "
            "add an explicit reviewed resolution"
        )
    chosen_team = decision.get('chosenTeam')
    chosen = [row for row in candidates if str(row.get('Team') or '').strip() == chosen_team]
    if len(chosen) != 1:
        raise RuntimeError(
            f"{conflict_id}: reviewed team {chosen_team!r} does not select exactly one fact"
        )
    if not decision.get('rationale') or not decision.get('evidence') or not decision.get('reviewedAt'):
        raise RuntimeError(f"{conflict_id}: reviewed resolution lacks rationale, evidence, or review date")
    return chosen[0]


def index_participation(ppart, top50_mkeys, event_registry, resolutions):
    """Career span from PARTICIPATION (every major entered, won or not), not just
    wins: first-win-to-last-win understates how long a player actually competed.
    Uses the same console-major universe (drop Warzone/Mobile & dropped events,
    on/before ASOF) so a player who kept competing after their last win — e.g.
    BigTymeR played through 2014 but last won in 2012 — has an honest active
    span, and majors_played gives a real denominator for win rate."""
    grouped = defaultdict(list)
    for r in ppart:
        if mkey(r['Player']) not in top50_mkeys: continue
        if not _keep(r) or not _played(r.get('Date')): continue
        if r.get('Place') in NONPLAY: continue
        k = mkey(r['Player'])
        eid = event_id_for(r, event_registry)
        grouped[(k, eid)].append(r)

    part_rows = defaultdict(dict)   # mk -> {event: {event,game,date,place}} — every major entered (won or not)
    for (k, eid), rows in grouped.items():
        r = select_participation_row(rows, k, eid, resolutions)
        px2 = place_x2(r)
        row = {'event': event_name_for(r, event_registry), 'eventId': eid, 'game': r['Game'],
               'date': r.get('Date') or '', 'place': str(r.get('Place') or '').strip(),
               'placeX2': px2, 'placeNumber': place_number(r),
               'team': str(r.get('Team') or '').strip()}
        part_rows[k][eid] = row
    part_dates = defaultdict(list)
    for k, rows in part_rows.items():
        part_dates[k] = [r['date'] for r in rows.values() if r.get('date')]
    return part_dates, part_rows


def career_of(mk, part_dates, part_rows):
    ds = sorted(part_dates.get(mk, []))
    if not ds: return (None, None, 0, 0, None, None)
    y0, y1 = int(ds[0][:4]), int(ds[-1][:4])
    # exact first/last dates feed the career-timeline signature (when wins land
    # across the whole career, not just the winning window); years feed span.
    return (y0, y1, y1 - y0, len(part_rows.get(mk, {})), ds[0], ds[-1])


def index_wins(pwins, top50_mkeys):
    player_wins = defaultdict(list)
    wiki_name = {}   # mk -> raw wiki player id (for the per-player Fandom link)
    for r in pwins:
        k = mkey(r['Player'])
        if k in top50_mkeys:
            player_wins[k].append(r)
            wiki_name.setdefault(k, r['Player'])
    return player_wins, wiki_name


def index_champs(champs_rows, top50_mkeys, disp_by_mkey, player_wins):
    champs_by = defaultdict(list)
    for r in champs_rows:
        t = r['title']
        raw_player = (t['Player'] or '').strip()
        raw_key = raw_player.lower()
        base_key = PLAYER_ALIASES.get(norm(raw_player).lower(), norm(raw_player).lower())
        # GUARD: unknown disambiguated champs names whose base matches a listed
        # player must be reviewed instead of silently merging into that player.
        if raw_key not in PLAYER_ALIASES and base_key in top50_mkeys and norm(raw_player) != raw_player:
            raise RuntimeError(f"ambiguous champs name needs review: {t['Player']!r}")
        champs_by[mkey(t['Player'])].append({'event': t['Event'], 'year': (t.get('Date') or '')[:4]})
    for k in champs_by:
        champs_by[k].sort(key=lambda e: e['year'])

    # GUARD: every championship is itself a major, so a listed player's champ events
    # must appear among their reconstructed major wins (unlike the wins join, the
    # champs join has no published-total check — this is its integrity anchor).
    for mk in top50_mkeys:
        won = {w['Event'] for w in player_wins.get(mk, [])}
        for ce in champs_by.get(mk, []):
            if ce['event'] not in won:
                raise RuntimeError(f"champ event not among {disp_by_mkey[mk]}'s major wins: {ce['event']!r}")
    return champs_by


def _wiki_url(page):
    return 'https://cod-esports.fandom.com/wiki/' + urllib_quote(page)


def urllib_quote(page):
    from urllib.parse import quote
    return quote(str(page or '').replace(' ', '_'), safe='/')


def is_champs_event(event):
    return bool(re.fullmatch(r'Call of Duty (?:World League |League )?Championship 20\d\d', event or ''))


def accolade_type(row):
    t = row.get('Type')
    if t == 'Event MVP' and is_champs_event(row.get('Event') or row.get('Page')):
        return 'champs_mvp'
    return {
        'Event MVP': 'event_mvp',
        'Grand Finals MVP': 'grand_finals_mvp',
        'Season MVP': 'season_mvp',
        'Rookie of the Year': 'rookie_of_the_year',
        'CDL First Team': 'cdl_first_team',
        'CDL Second Team': 'cdl_second_team',
        'CWL All-Star': 'cwl_all_star',
    }.get(t)


def accolade_year(row):
    text = ' '.join(str(row.get(k) or '') for k in ('Page', 'Event'))
    m = re.search(r'(?:^|/)20(\d\d) Season\b', text)
    if m:
        return '20' + m.group(1)
    m = re.search(r'\b(20\d\d)\b', text)
    if m:
        return m.group(1)
    return (row.get('Date') or '')[:4]


def keep_accolade(row):
    t = row.get('Type')
    if t not in FORMAL_ACCOLADE_TYPES:
        return False
    if not row.get('Player') or not row.get('Page') or not row.get('Date'):
        return False
    if not _keep(row) or not _played(row.get('Date')):
        return False
    page = row.get('Page') or ''
    if 'Breaking Point Awards' in page:
        return False
    if t in {'Event MVP', 'Grand Finals MVP'}:
        return row.get('Tier') in {'Major', 'Premier'}
    if t in {'Season MVP', 'Rookie of the Year', 'CDL First Team', 'CDL Second Team'}:
        return bool(re.fullmatch(r'Call of Duty League/20\d\d Season', page))
    if t == 'CWL All-Star':
        return page.startswith('CWL/')
    return False


def index_accolades(rows, top50_mkeys):
    """Normalize honors from the CoD Esports Wiki awards table.

    Media rankings, Breaking Point awards, blank award types, minors, Warzone, and
    Mobile rows stay in the raw source file but are deliberately not emitted here.
    """
    by_player = defaultdict(list)
    for r in rows:
        if not keep_accolade(r):
            continue
        player = r.get('PlayerLink') or r.get('Player')
        mk = mkey(player)
        if mk not in top50_mkeys:
            continue
        atype = accolade_type(r)
        if not atype:
            continue
        event = r.get('Event') or r.get('Page') or ''
        page = r.get('Page') or event
        by_player[mk].append({
            'type': atype,
            'label': ACCOLADE_LABELS[atype],
            'event': event,
            'page': page,
            'game': r.get('Game') or '',
            'date': r.get('Date') or '',
            'year': accolade_year(r),
            'sourceTier': int(r.get('SourceTier') or ACCOLADE_SOURCE_TIER),
            'source': r.get('Source') or 'CoD Esports Wiki',
            'sourceUrl': r.get('SourceUrl') or _wiki_url(page),
        })
    for rows in by_player.values():
        rows.sort(key=lambda r: (r['date'], r['label'], r['event']))
    return by_player


def _stat_int(value):
    text = str(value if value is not None else '').strip().replace(',', '')
    if not text or not re.fullmatch(r'-?\d+', text):
        return None
    return int(text)


def _stat_bool(value):
    if isinstance(value, bool):
        return value
    text = str(value if value is not None else '').strip().lower()
    if text in {'1', 'true', 't', 'yes', 'y', 'win', 'won'}:
        return True
    if text in {'0', 'false', 'f', 'no', 'n', 'loss', 'lost'}:
        return False
    return None


def _empty_stat_bucket():
    return {'kills': 0, 'deaths': 0, 'maps': 0, 'mapWins': 0, 'mapsWithResult': 0}


def _add_stat(bucket, kills, deaths, win=None):
    bucket['kills'] += kills
    bucket['deaths'] += deaths
    bucket['maps'] += 1
    if win is not None:
        bucket['mapsWithResult'] += 1
        if win:
            bucket['mapWins'] += 1


def _finish_stat_bucket(bucket):
    kills, deaths = bucket['kills'], bucket['deaths']
    out = {'kills': kills, 'deaths': deaths, 'interactions': kills + deaths, 'maps': bucket['maps']}
    out['kd'] = round(kills / deaths, 3) if deaths else None
    if bucket.get('mapsWithResult'):
        out['mapWins'] = bucket['mapWins']
        out['mapLosses'] = bucket['mapsWithResult'] - bucket['mapWins']
        out['mapWinRate'] = rate_from_counts(bucket['mapWins'], bucket['mapsWithResult'])
    return out


def _empty_stat_split():
    return {
        'overall': _empty_stat_bucket(),
        'splits': {'snd': _empty_stat_bucket(), 'respawn': _empty_stat_bucket()},
    }


def _add_stat_split(group, split, kills, deaths, win=None):
    _add_stat(group['overall'], kills, deaths, win)
    _add_stat(group['splits'][split], kills, deaths, win)


def _finish_stat_split(group):
    return {
        'overall': _finish_stat_bucket(group['overall']),
        'splits': {k: _finish_stat_bucket(v) for k, v in group['splits'].items()},
    }


def _is_snd_mode(mode):
    text = str(mode or '').lower().replace('&', 'and')
    return 'search' in text and 'destroy' in text


def index_skill_stats(rows, top50_mkeys, S, event_registry, major_event_ids):
    """Aggregate objective PlayerStats rows into simple, source-backed splits.

    The stable cross-era denominator is map rows with kills/deaths. S&D gets its
    own split; every other mode is grouped as respawn while remaining available
    by individual mode for later UI detail.
    """
    work = {}
    for r in rows:
        player = r.get('Player') or r.get('PlayerLink') or r.get('PlayerName')
        mk = mkey(player or '')
        if mk not in top50_mkeys:
            continue
        if not _keep(r) or not _played(r.get('Date')):
            continue
        if event_id_for(r, event_registry) not in major_event_ids:
            continue
        kills, deaths = _stat_int(r.get('Kills')), _stat_int(r.get('Deaths'))
        if kills is None or deaths is None:
            continue
        win = _stat_bool(r.get('Win'))
        mode = str(r.get('Mode') or r.get('Gamemode') or 'Unknown').strip() or 'Unknown'
        split = 'snd' if _is_snd_mode(mode) else 'respawn'
        row = work.setdefault(mk, {
            **_empty_stat_split(),
            'modes': defaultdict(_empty_stat_bucket),
            'events': set(),
            'games': set(),
            'dates': [],
            'by_game': {},
            'by_event': {},
        })
        _add_stat_split(row, split, kills, deaths, win)
        _add_stat(row['modes'][mode], kills, deaths, win)
        game = r.get('Game') or ''
        event_id = event_id_for(r, event_registry)
        event = event_name_for(r, event_registry)
        date = r.get('Date') or ''
        team = r.get('Team') or ''
        if event_id:
            row['events'].add(event_id)
        if game:
            row['games'].add(game)
            game_group = row['by_game'].setdefault(game, {
                **_empty_stat_split(), 'dates': [], 'events': set(),
            })
            _add_stat_split(game_group, split, kills, deaths, win)
            if date:
                game_group['dates'].append(date)
            if event_id:
                game_group['events'].add(event_id)
        if game and event_id:
            event_group = row['by_event'].setdefault((game, event_id), {
                **_empty_stat_split(), 'event': event, 'dates': [], 'teams': set(),
            })
            _add_stat_split(event_group, split, kills, deaths, win)
            if date:
                event_group['dates'].append(date)
            if team:
                event_group['teams'].add(team)
        if date:
            row['dates'].append(date)

    out = {}
    for mk, row in work.items():
        dates = sorted(row['dates'])
        games = sorted(row['games'], key=lambda g: S.order_idx.get(g, 999))
        by_game = []
        for game in games:
            group = row['by_game'][game]
            group_dates = sorted(group['dates'])
            by_game.append({
                'game': game,
                'firstDate': group_dates[0] if group_dates else None,
                'lastDate': group_dates[-1] if group_dates else None,
                'events': len(group['events']),
                **_finish_stat_split(group),
            })
        by_event = []
        for (game, event_id), group in row['by_event'].items():
            group_dates = sorted(group['dates'])
            by_event.append({
                'game': game,
                'event': group.get('event') or event_id,
                'eventId': event_id,
                'firstDate': group_dates[0] if group_dates else None,
                'lastDate': group_dates[-1] if group_dates else None,
                'teams': sorted(group['teams']),
                **_finish_stat_split(group),
            })
        by_event.sort(key=lambda r: (S.order_idx.get(r['game'], 999), r['firstDate'] or '', r['event']))
        out[mk] = {
            'source': 'CoD Esports Wiki PlayerStats',
            'coverage': {
                'firstDate': dates[0] if dates else None,
                'lastDate': dates[-1] if dates else None,
                'events': len(row['events']),
                'maps': row['overall']['maps'],
                'games': games,
            },
            'overall': _finish_stat_bucket(row['overall']),
            'splits': {k: _finish_stat_bucket(v) for k, v in row['splits'].items()},
            'modes': {k: _finish_stat_bucket(v) for k, v in sorted(row['modes'].items())},
            'byGame': by_game,
            'byEvent': by_event,
        }
    return out


def _stat_float(value):
    if value in (None, ''):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def index_legacy_skill_stats(rows, top50_mkeys, S, event_registry, major_event_ids):
    """Index codcompstats legacy event aggregates separately from map rows."""
    work = {}
    for r in rows:
        player = r.get('Player')
        mk = mkey(player or '')
        if mk not in top50_mkeys:
            continue
        if not _keep(r) or not _played(r.get('Date')):
            continue
        event_id = event_id_for(r, event_registry)
        if event_id not in major_event_ids:
            continue
        maps = _stat_int(r.get('Maps'))
        kd = _stat_float(r.get('KD'))
        if not maps or kd is None:
            continue
        game = r.get('Game') or ''
        if not game:
            continue
        event = event_name_for(r, event_registry)
        date = r.get('Date') or ''
        team = str(r.get('Team') or '').strip()
        row = work.setdefault(mk, {
            'events': set(),
            'games': set(),
            'maps': 0,
            'by_game': {},
            'by_event': {},
        })
        row['events'].add(event_id)
        row['games'].add(game)
        row['maps'] += maps
        game_group = row['by_game'].setdefault(game, {'events': set(), 'maps': 0})
        game_group['events'].add(event_id)
        game_group['maps'] += maps
        row['by_event'][(game, event_id)] = {
            'game': game,
            'event': event,
            'eventId': event_id,
            'firstDate': date or None,
            'lastDate': date or None,
            'teams': [team] if team else [],
            'sourceType': 'legacyAggregate',
            'sourceLabel': 'Legacy aggregate',
            'granularity': r.get('Granularity') or 'eventAggregate',
            'source': r.get('Source') or 'codcompstats legacy wiki page',
            'sourceUrl': r.get('SourceUrl') or '',
            'sourcePage': r.get('SourcePage') or '',
            'legacyEvent': r.get('LegacyEvent') or event,
            'overall': {'maps': maps, 'kd': round(kd, 3)},
            'splits': {'snd': _finish_stat_bucket(_empty_stat_bucket()), 'respawn': _finish_stat_bucket(_empty_stat_bucket())},
        }
    out = {}
    for mk, row in work.items():
        games = sorted(row['games'], key=lambda g: S.order_idx.get(g, 999))
        by_game = []
        for game in games:
            group = row['by_game'][game]
            by_game.append({
                'game': game,
                'events': len(group['events']),
                'maps': group['maps'],
            })
        by_event = sorted(
            row['by_event'].values(),
            key=lambda r: (S.order_idx.get(r['game'], 999), r['firstDate'] or '', r['event']),
        )
        out[mk] = {
            'source': 'codcompstats legacy wiki pages',
            'coverage': {
                'events': len(row['events']),
                'maps': row['maps'],
                'games': games,
            },
            'byGame': by_game,
            'byEvent': by_event,
        }
    return out


KOR_SPLITS = {
    'respawn': {'label': 'Respawn', 'minMaps': 28},
    'snd': {'label': 'S&D', 'minMaps': 10},
}
KOR_REPLACEMENT_PERCENTILE = Fraction(1, 4)


def _kor_empty_bucket():
    return {'kills': 0, 'deaths': 0, 'maps': 0, 'events': set(), 'opponentPlaces': [], 'top8Maps': 0, 'opponentMaps': 0,
            'perEvent': {}}


def _kor_percentile(values, pct):
    values = sorted(values)
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    pos = Fraction(len(values) - 1, 1) * pct
    lo = pos.numerator // pos.denominator
    hi = (pos.numerator + pos.denominator - 1) // pos.denominator
    if lo == hi:
        return values[lo]
    weight = pos - lo
    return values[lo] + (values[hi] - values[lo]) * weight


def _kor_add(bucket, row, kills, deaths, opponent_place, own_place=None, event_name=None):
    bucket['kills'] += kills
    bucket['deaths'] += deaths
    bucket['maps'] += 1
    event_id = row.get('EventId') or row.get('Event')
    if event_id:
        bucket['events'].add(event_id)
        ev = bucket['perEvent'].setdefault(event_id, {
            'event': str(event_name or row.get('Event') or event_id), 'id': str(event_id),
            'date': None, 'kills': 0, 'deaths': 0, 'maps': 0, 'place': None})
        ev['kills'] += kills
        ev['deaths'] += deaths
        ev['maps'] += 1
        date = str(row.get('Date') or '')
        if date and (ev['date'] is None or date < ev['date']):
            ev['date'] = date
        if own_place is not None:
            ev['place'] = own_place
    if opponent_place is not None:
        bucket['opponentPlaces'].append(opponent_place)
        bucket['opponentMaps'] += 1
        if opponent_place <= 8:
            bucket['top8Maps'] += 1


def _kor_finish_bucket(bucket):
    maps, kills, deaths = bucket['maps'], bucket['kills'], bucket['deaths']
    return {
        'maps': maps,
        'kills': kills,
        'deaths': deaths,
        'events': len(bucket['events']),
        'kpm': Fraction(kills, maps) if maps else None,
        'kd': Fraction(kills, deaths) if deaths else None,
        'medianOpponentPlace': median(bucket['opponentPlaces']),
        'top8OpponentPct': Fraction(bucket['top8Maps'], bucket['opponentMaps']) if bucket['opponentMaps'] else None,
        'opponentMaps': bucket['opponentMaps'],
    }


def index_opponent_places(tpart, event_registry, major_event_ids=None):
    places = {}
    for r in tpart:
        if not _keep(r):
            continue
        event_id = event_id_for(r, event_registry)
        if major_event_ids is not None and event_id not in major_event_ids:
            continue
        team = str(r.get('Team') or '').strip()
        if not team:
            continue
        px2 = place_x2({'Place': r.get('Place'), 'PlaceNumber': r.get('PlaceNumber')})
        if px2 is None:
            continue
        places[(event_id, compact_key(team))] = px2 / 2
    return places


def kor_role_for_game(player, game, S, role_stints):
    if not role_stints or game not in S.order_idx:
        return 'Unknown'
    gi = S.order_idx[game]
    matches = [s for s in role_stints.get(mkey(player), []) if s['start'] <= gi <= s['end']]
    return matches[0]['role'] if matches else 'Unknown'


def build_kor(player_stat_rows, tpart, S, event_registry, major_event_ids, role_stints=None, disp_by_mkey=None):
    """Build title/mode Kills Over Replacement tables from major-event stats.

    KOR is deliberately title/mode-only: no role adjustment, no overall split.
    """
    opponent_places = index_opponent_places(tpart, event_registry, major_event_ids)
    by_game_player = defaultdict(lambda: defaultdict(lambda: {split: _kor_empty_bucket() for split in KOR_SPLITS}))
    map_rows_by_game = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for r in player_stat_rows:
        if not _keep(r) or not _played(r.get('Date')):
            continue
        game = r.get('Game') or ''
        if game not in S.order_idx:
            continue
        player = r.get('Player') or r.get('PlayerLink') or r.get('PlayerName')
        if not player:
            continue
        if disp_by_mkey:
            player = disp_by_mkey.get(mkey(player), player)
        kills, deaths = _stat_int(r.get('Kills')), _stat_int(r.get('Deaths'))
        if kills is None or deaths is None:
            continue
        split = 'snd' if _is_snd_mode(r.get('Mode') or r.get('Gamemode')) else 'respawn'
        event_id = event_id_for(r, event_registry)
        if event_id not in major_event_ids:
            continue
        opponent_place = opponent_places.get((event_id, compact_key(r.get('TeamVs') or '')))
        own_place = opponent_places.get((event_id, compact_key(r.get('Team') or '')))
        _kor_add(by_game_player[game][player][split], r, kills, deaths, opponent_place, own_place,
                 event_name_for(r, event_registry))
        map_rows_by_game[game][player][str(event_id)].append({
            '_sort': (str(r.get('Date') or ''), str(r.get('SeriesId') or '')),
            'ser': str(r.get('SeriesId') or '') or None,
            'map': str(r.get('Map') or '') or None,
            'mode': str(r.get('Mode') or r.get('Gamemode') or '') or None,
            'snd': split == 'snd',
            'vs': str(r.get('TeamVs') or '') or None,
            'k': kills, 'd': deaths,
        })

    out = {'meta': {
        'replacementPercentile': float(KOR_REPLACEMENT_PERCENTILE),
        'splits': KOR_SPLITS,
        'description': 'Major-event kills per map above the 25th-percentile qualified player in the same title/mode split.',
    }, 'games': {}}
    detail_players = {}
    for game in S.order:
        if game not in by_game_player:
            continue
        game_out = {'splits': {}}
        for split, cfg in KOR_SPLITS.items():
            finished = []
            players_with_maps = 0
            for player, splits in by_game_player[game].items():
                b = _kor_finish_bucket(splits[split])
                if b['maps']:
                    players_with_maps += 1
                if b['maps'] >= cfg['minMaps'] and b['kpm'] is not None:
                    finished.append((player, b, splits[split]))
            replacement = _kor_percentile([b['kpm'] for _, b, _ in finished], KOR_REPLACEMENT_PERCENTILE)
            rows = []
            if replacement is not None:
                for player, b, raw in finished:
                    events = sorted(raw['perEvent'].values(), key=lambda e: (e['date'] or '', e['event']))
                    detail_players.setdefault(player, {}).setdefault(game, {})[split] = [
                        {'event': e['event'], 'id': e['id'], 'date': e['date'],
                         'kills': e['kills'], 'deaths': e['deaths'], 'maps': e['maps'],
                         **({'place': int(e['place']) if e['place'] == int(e['place']) else e['place']}
                            if e['place'] is not None else {})}
                        for e in events]
                    kor = b['kpm'] - replacement
                    rows.append({
                        'player': player,
                        'role': kor_role_for_game(player, game, S, role_stints),
                        'korPerMap': round(float(kor), 3),
                        'kpm': round(float(b['kpm']), 2),
                        'totalKor': round(float(kor * b['maps']), 1),
                        'maps': b['maps'],
                        'events': b['events'],
                        'kd': round(float(b['kd']), 3) if b['kd'] is not None else None,
                        'medianOpponentPlace': round(b['medianOpponentPlace'], 1) if b['medianOpponentPlace'] is not None else None,
                        'top8OpponentPct': round(float(b['top8OpponentPct']), 3) if b['top8OpponentPct'] is not None else None,
                        'opponentMaps': b['opponentMaps'],
                    })
                rows.sort(key=lambda r: (-r['korPerMap'], -r['maps'], r['player']))
                for i, row in enumerate(rows, 1):
                    row['rank'] = i
            game_out['splits'][split] = {
                'label': cfg['label'],
                'minMaps': cfg['minMaps'],
                'replacementKpm': round(float(replacement), 2) if replacement is not None else None,
                'playersWithMaps': players_with_maps,
                'qualified': len(rows),
                'rows': rows,
            }
        out['games'][game] = game_out
    # map-level shards ship one file per title and only for qualified rows, so a
    # tournament expand downloads that title's maps once instead of 77k rows
    maps_by_game, map_files = {}, {}
    for player, games in detail_players.items():
        for game in games:
            rows_by_event = map_rows_by_game[game][player]
            game_maps = maps_by_game.setdefault(game, {})
            game_maps[player] = {
                event_id: [{k: v for k, v in m.items() if k != '_sort'}
                           for m in sorted(rows, key=lambda m: m['_sort'])]
                for event_id, rows in rows_by_event.items()}
    for game in maps_by_game:
        slug = re.sub(r'[^a-z0-9]+', '-', game.lower()).strip('-')
        map_files[game] = f'kor-maps-{slug}.json'
    out['_detail'] = {
        'meta': {'description': 'Per-event kills/deaths/maps for each qualified KOR row (major events only). '
                                'K/map and KOR per event derive from these against kor.json baselines.',
                 'mapFiles': map_files},
        'players': detail_players,
        'mapsByGame': maps_by_game,
    }
    return out


def load_role_stints():
    """Load curated primary-role stints.

    Rows may be career-wide ({player, role}) or game-bounded with inclusive
    start_game/end_game. The generated output expands these into active-season
    rows, so future role switches can be added without changing the schema.
    """
    path = _p('player_roles.json')
    if not os.path.exists(path):
        return []
    return json.load(open(path)).get('roles', [])


def load_team_logos():
    """Load cached Fandom team-logo URLs.

    This stays separate from the main wiki source pull so a rate-limited logo
    lookup never blocks the rankings build. Missing teams fall back to text.
    """
    path = _p('team_logos.json')
    if not os.path.exists(path):
        return {}
    return json.load(open(path))


def build_team_logos(participation, logos):
    """Return only logo metadata used by the generated player pages."""
    teams = {r.get('team') for rows in participation.values() for r in rows if r.get('team')}
    return {t: logos[t] for t in sorted(teams) if t in logos and logos[t].get('src')}


def _game_bound(stint, key, S, default_idx):
    g = stint.get(key)
    if not g:
        return default_idx
    if g not in S.order_idx:
        raise RuntimeError(f"unknown role stint {key}: {g!r}")
    return S.order_idx[g]


def index_role_stints(stints, disp_by_mkey, S):
    """Validate curated stints and index them by normalized player name."""
    by_player = defaultdict(list)
    for stint in stints:
        player = stint.get('player')
        role = stint.get('role')
        mk = mkey(player or '')
        if mk not in disp_by_mkey:
            raise RuntimeError(f"unknown role player: {player!r}")
        if role not in VALID_PRIMARY_ROLES - {'Unknown'}:
            raise RuntimeError(f"invalid primary role for {player}: {role!r}")
        start = _game_bound(stint, 'start_game', S, 0)
        end = _game_bound(stint, 'end_game', S, len(S.order) - 1)
        if start > end:
            raise RuntimeError(f"role stint starts after it ends for {player}: {stint!r}")
        by_player[mk].append({'role': role, 'start': start, 'end': end})

    for mk, rows in by_player.items():
        rows.sort(key=lambda r: (r['start'], r['end']))
        prev = None
        for row in rows:
            if prev and row['start'] <= prev['end']:
                raise RuntimeError(f"overlapping role stints for {disp_by_mkey[mk]}")
            prev = row
    return by_player


def role_by_game(name, active_games, S, role_stints):
    """Expand a player's role stints into one row per active game/season."""
    rows = []
    for g in sorted(set(active_games), key=lambda x: S.order_idx[x]):
        gi = S.order_idx[g]
        matches = [s for s in role_stints.get(mkey(name), []) if s['start'] <= gi <= s['end']]
        role = matches[0]['role'] if matches else 'Unknown'
        rows.append({'game': g, 'year': int(S.first_date[g][:4]), 'role': role})
    return rows


def primary_role(rows):
    roles = {r['role'] for r in rows if r['role'] != 'Unknown'}
    return roles.pop() if len(roles) == 1 else 'Unknown'


# --------------------------------------------------------------------------- #
# Per-player record
# --------------------------------------------------------------------------- #
def _sfrac(s): return Fraction(s['wins'], s['majors'])


def peak_of(slist, mb):
    """Best single season's share, rescaled to a wins-like number."""
    if not slist: return {'adj': 0.0, 'season': None, 'wins': 0, 'majors': 0}
    best = max(slist, key=_sfrac)
    return {'adj': round(float(_sfrac(best)) * mb, 2), 'season': best['game'], 'wins': best['wins'], 'majors': best['majors']}


def span_of(slist):
    """(span in years, first year, last year) across a season list's win events."""
    yrs = [int(e['date'][:4]) for s in slist for e in s['events'] if e['date']]
    return (max(yrs) - min(yrs) + 1, min(yrs), max(yrs)) if yrs else (0, None, None)


def placement_of(rows, S):
    by_game = defaultdict(lambda: {'events': 0, 'placeX2Sum': 0, 'wins': 0, 'finals': 0, 'deepRuns': 0})
    for r in rows:
        g = by_game[r['game']]
        g['events'] += 1
        g['placeX2Sum'] += r['placeX2']
        if r.get('won'):
            g['wins'] += 1
        pn = r.get('placeNumber')
        if pn is not None and pn <= 2:
            g['finals'] += 1
        if pn is not None and pn <= 4:
            g['deepRuns'] += 1
    placements = []
    for g in sorted(by_game, key=lambda x: S.order_idx[x]):
        v = by_game[g]
        placements.append({'game': g, 'events': v['events'], 'placeX2Sum': v['placeX2Sum'],
                           'avgPlace': avg_place_from_x2(v['placeX2Sum'], v['events']),
                           'wins': v['wins'], 'finals': v['finals'], 'deepRuns': v['deepRuns']})
    events = sum(r['events'] for r in placements)
    px2_sum = sum(r['placeX2Sum'] for r in placements)
    wins = sum(r['wins'] for r in placements)
    finals = sum(r['finals'] for r in placements)
    deep_runs = sum(r['deepRuns'] for r in placements)
    avg = avg_place_from_x2(px2_sum, events)
    return placements, events, px2_sum, avg, wins, finals, deep_runs


def teams_of(rows):
    teams = []
    seen = set()
    for r in rows:
        team = r.get('team')
        if team and team not in seen:
            teams.append(team)
            seen.add(team)
    return teams


def player_seasons(wins, S, event_registry, part_by_event=None):
    """Group a player's (date-sorted) wins into per-season rows, chronological."""
    part_by_event = part_by_event or {}
    by_season = defaultdict(lambda: {'count': 0, 'events': []})
    for w in wins:
        g = w['Game']
        eid = event_id_for(w, event_registry)
        by_season[g]['count'] += 1
        part = part_by_event.get(eid, {})
        by_season[g]['events'].append({'event': event_name_for(w, event_registry), 'eventId': eid,
                                       'date': w.get('Date') or '',
                                       'team': part.get('team', ''),
                                       'weight': round(1.0 / S.denom[g], 4)})
    seasons = []
    for g in sorted(by_season, key=lambda x: S.order_idx[x]):
        c = by_season[g]['count']
        seasons.append({'game': g, 'wins': c, 'majors': S.denom[g], 'held': S.held[g],
                        'share': round(c / S.denom[g], 4),
                        'pre_bo2': g in S.pre_bo2, 'events': by_season[g]['events']})
    return seasons


def build_player(n, pub, S, idx):
    """One player's full record. Returns (record, all_majors_entered,
    (share_all, share_post) as exact Fractions — ranking must not use rounded
    values)."""
    mk = mkey(n)
    wins = sorted(idx.player_wins.get(mk, []), key=lambda r: (r.get('Date') or ''))
    seasons = player_seasons(wins, S, idx.event_registry, idx.part_rows.get(mk, {}))
    share_all  = sum((_sfrac(s) for s in seasons), Fraction(0))
    share_post = sum((_sfrac(s) for s in seasons if not s['pre_bo2']), Fraction(0))

    # Peak (best single season's share, rescaled to a wins-like number) + Longevity
    # (distinct titles won, plus career span in years). Computed for both modes.
    seasons_post = [s for s in seasons if not s['pre_bo2']]
    pk_all, pk_post = peak_of(seasons, S.mbar_all), peak_of(seasons_post, S.mbar_post)
    span_all, first_all, last_all = span_of(seasons)
    span_post, first_post, last_post = span_of(seasons_post)
    first_played, last_played, career_span, majors_played, first_pdate, last_pdate = \
        career_of(mk, idx.part_dates, idx.part_rows)

    # Every major ENTERED (won or not), for the auditable "all majors" toggle on the
    # player page. Built from participation placements; wins are flagged. Any won
    # event missing a participation row is added so all_majors always covers the wins.
    won_event_ids = {event_id_for(w, idx.event_registry) for w in wins}
    all_majors = [dict(r, won=(r['eventId'] in won_event_ids)) for r in idx.part_rows.get(mk, {}).values()]
    seen_ev = {r['eventId'] for r in all_majors}
    for w in wins:
        eid = event_id_for(w, idx.event_registry)
        if eid not in seen_ev:
            all_majors.append({'event': event_name_for(w, idx.event_registry), 'eventId': eid,
                               'game': w['Game'], 'date': w.get('Date') or '',
                               'place': '1', 'placeX2': 2, 'placeNumber': 1, 'won': True})
    all_majors.sort(key=lambda r: r['date'])
    placements, events_placed, place_x2_sum, avg_place, placement_wins, finals, deep_runs = placement_of(all_majors, S)
    win_conversion = rate_from_counts(placement_wins, events_placed)
    finals_rate = rate_from_counts(finals, events_placed)
    deep_run_rate = rate_from_counts(deep_runs, events_placed)

    rec = {'name': n, 'raw': pub, 'seasons': seasons,
           'wiki': idx.wiki_name.get(mk, n),
           'share_all': round(float(share_all), 4), 'adj_all': round(float(share_all) * S.mbar_all, 2),
           'share_post': round(float(share_post), 4), 'adj_post': round(float(share_post) * S.mbar_post, 2),
           'champs': len(idx.champs_by.get(mk, [])), 'champ_events': idx.champs_by.get(mk, []),
           'peak_all': pk_all, 'peak_post': pk_post,
           'titles_all': len(seasons), 'titles_post': len(seasons_post),
           'span_all': span_all, 'span_post': span_post,
           'first_year': first_all, 'last_year': last_all,
           'first_post': first_post, 'last_post': last_post,
           'first_played': first_played, 'last_played': last_played,
           'first_played_date': first_pdate, 'last_played_date': last_pdate,
           'career_span': career_span, 'majors_played': majors_played,
           'placements': placements, 'events_placed': events_placed,
           'place_x2_sum': place_x2_sum, 'avg_place': avg_place,
           'placement_wins': placement_wins, 'finals': finals, 'deep_runs': deep_runs,
           'win_conversion': win_conversion, 'finals_rate': finals_rate, 'deep_run_rate': deep_run_rate,
           'teams': teams_of(all_majors),
           'honors': idx.accolades_by.get(mk, []),
           'skillStats': idx.skill_stats_by.get(mk),
           'legacySkillStats': idx.legacy_skill_stats_by.get(mk),
           'note': PLAYER_NOTES.get(n)}
    rec['role_by_game'] = role_by_game(n, [r['game'] for r in all_majors], S, idx.role_stints)
    rec['primary_role'] = primary_role(rec['role_by_game'])
    return rec, all_majors, (share_all, share_post)


# --------------------------------------------------------------------------- #
# Guards, ranking, and output sections
# --------------------------------------------------------------------------- #
def check_reconstruction(players_out):
    """GUARD: reconstructed wins must equal the published wiki total for every player."""
    recon = {n: sum(s['wins'] for s in players_out[n]['seasons']) for n, _ in PUBLISHED}
    mismatch = [(n, pub, recon[n]) for n, pub in PUBLISHED if recon[n] != pub]
    if mismatch:
        raise RuntimeError('reconstruction != published total: ' +
                           ', '.join(f'{n} ({pub} vs {rec})' for n, pub, rec in mismatch))


def crank(vals):
    """Competition ranking on exact values: rank = 1 + (players strictly better),
    so genuine ties share the minimum rank instead of getting arbitrary order."""
    return {n: 1 + sum(1 for w in vals.values() if w > v) for n, v in vals.items()}


def build_leaderboard(players_out, exact_share):
    raw_rank  = crank(dict(PUBLISHED))
    adj_rank  = crank({n: s[0] for n, s in exact_share.items()})
    post_rank = crank({n: s[1] for n, s in exact_share.items()})

    leaderboard = []
    for n, pub in PUBLISHED:
        p = players_out[n]
        leaderboard.append({
            'name': n, 'raw': pub, 'rawRank': raw_rank[n],
            'shareAll': p['share_all'], 'adjAll': p['adj_all'], 'adjRank': adj_rank[n], 'delta': raw_rank[n] - adj_rank[n],
            'sharePost': p['share_post'], 'adjPost': p['adj_post'], 'postRank': post_rank[n], 'deltaPost': raw_rank[n] - post_rank[n],
            'champs': p['champs'],
            'peakAll': p['peak_all']['adj'], 'peakPost': p['peak_post']['adj'],
            'peakInfoAll': p['peak_all'], 'peakInfoPost': p['peak_post'],
            'titlesAll': p['titles_all'], 'titlesPost': p['titles_post'],
            'spanAll': p['span_all'], 'spanPost': p['span_post'],
            'firstYear': p['first_year'], 'lastYear': p['last_year'],
            'firstYearPost': p['first_post'], 'lastYearPost': p['last_post'],
            'firstPlayed': p['first_played'], 'lastPlayed': p['last_played'],
            'firstPlayedDate': p['first_played_date'], 'lastPlayedDate': p['last_played_date'],
            'careerSpan': p['career_span'], 'majorsPlayed': p['majors_played'],
            'eventsPlaced': p['events_placed'], 'placeX2Sum': p['place_x2_sum'], 'avgPlace': p['avg_place'],
            'winConversion': p['win_conversion'],
            'primaryRole': p['primary_role'],
        })
    return leaderboard


def index_event_winners(tpart, event_registry):
    winners = {}
    for r in tpart:
        if not _keep(r):
            continue
        if str(r.get('Place') or '').strip() == '1':
            winners[event_id_for(r, event_registry)] = str(r.get('Team') or '').strip()
    return winners


def build_games(events, pwins, tpart, S, top50_mkeys, disp_by_mkey, event_registry):
    event_winners = index_event_winners(tpart, event_registry)
    games_out = []
    for g in S.order:
        evs = sorted([e for e in events if e['Game'] == g], key=lambda x: (x.get('Date') or ''))
        wc = Counter()
        for r in pwins:
            if r['Game'] == g and mkey(r['Player']) in top50_mkeys:
                wc[disp_by_mkey[mkey(r['Player'])]] += 1
        games_out.append({'game': g, 'majors': S.held[g], 'denom': S.denom[g], 'weight': round(1.0 / S.denom[g], 4),
            'order': S.order_idx[g], 'preBo2': g in S.pre_bo2, 'firstDate': S.first_date[g],
            'events': [{'event': event_name_for(e, event_registry), 'eventId': event_id_for(e, event_registry),
                        'date': e.get('Date') or '', 'winner': e.get('Winner') or '',
                        'winnerTeam': event_winners.get(event_id_for(e, event_registry), e.get('Winner') or ''),
                        'type': e.get('EventType') or '', 'prize': e.get('Prizepool') or '', 'location': e.get('Location') or '',
                        'region': e.get('Region') or ''} for e in evs],
            'topPlayers': [{'name': p, 'wins': c} for p, c in wc.most_common(8)]})
    return games_out


def build_meta(S, events):
    return {'mbarAll': round(S.mbar_all, 4), 'mbarPost': round(S.mbar_post, 4), 'asOf': ASOF,
            'consoleSeasons': len(S.order), 'preBo2': sorted(S.pre_bo2, key=lambda g: S.order_idx[g]),
            'seasonOrder': S.order, 'totalMajors': sum(S.majors.values()),
            'consoleMajors': sum(S.majors[g] for g in S.order), 'numEvents': len(events)}


def build_stakes(events_all, ppart, pwins, players_out, exact_share, S, event_registry, disp_by_mkey):
    """Precompute what-if rank movement for the next scheduled major.

    The scenario roster comes from the latest played same-title major for all
    participants. Existing ranked players and one-win current players who would
    reach the leaderboard cutoff get exact-fraction scenario ranks.
    """
    future = sorted(
        [e for e in events_all if not _played(e.get('Date')) and e.get('Game') in S.denom],
        key=lambda e: (e.get('Date') or '9999', e.get('Event') or ''),
    )
    if not future:
        return {'status': 'unavailable', 'reason': 'No future scheduled console majors in the source snapshot.'}

    event = next((e for e in future if not (e.get('Winner') or '').strip()), future[0])
    game = event['Game']
    denom = S.denom[game]
    win_delta = Fraction(1, denom)
    adjusted_delta = round(float(win_delta) * S.mbar_all, 2)
    before_ranks = crank({n: s[0] for n, s in exact_share.items()})
    is_champs = is_champs_event(event_name_for(event, event_registry))

    raw_by_mkey = Counter()
    share_by_mkey = defaultdict(Fraction)
    wins_by_mkey_game = defaultdict(Counter)
    champs_by_mkey = Counter()
    for r in pwins:
        if not _keep(r) or not _played(r.get('Date')):
            continue
        row_game = r.get('Game')
        if row_game not in S.denom:
            continue
        raw_name = str(r.get('Player') or '').strip()
        if not raw_name:
            continue
        mk = mkey(raw_name)
        raw_by_mkey[mk] += 1
        share_by_mkey[mk] += Fraction(1, S.denom[row_game])
        wins_by_mkey_game[mk][row_game] += 1
        if is_champs_event(event_name_for(r, event_registry)):
            champs_by_mkey[mk] += 1

    roster_candidates = []
    for r in ppart:
        if not _keep(r) or r.get('Game') != game or not _played(r.get('Date')):
            continue
        if str(r.get('Place') or '').strip() in NONPLAY:
            continue
        roster_candidates.append(r)
    if not roster_candidates:
        return {'status': 'unavailable', 'reason': f'No played {game} roster source is available.'}

    latest_key = max((r.get('Date') or '', event_name_for(r, event_registry)) for r in roster_candidates)
    roster_rows = [
        r for r in roster_candidates
        if (r.get('Date') or '', event_name_for(r, event_registry)) == latest_key
    ]

    by_team = defaultdict(list)
    for r in roster_rows:
        team = str(r.get('Team') or '').strip()
        if team:
            raw_name = str(r.get('Player') or '').strip()
            mk = mkey(raw_name)
            name = disp_by_mkey.get(mk, raw_name)
            by_team[team].append((name, mk, mk in disp_by_mkey, r))

    scenarios = []
    for team, roster in sorted(by_team.items()):
        ranked_names = {name for name, _, ranked, _ in roster if ranked}
        entrant_names = set()
        scenario_shares = dict((n, s[0]) for n, s in exact_share.items())
        for name in ranked_names:
            scenario_shares[name] += win_delta
        for name, mk, ranked, _ in roster:
            if ranked:
                continue
            raw_before = raw_by_mkey.get(mk, 0)
            if raw_before + 1 >= 2:
                entrant_names.add(name)
                scenario_shares[name] = share_by_mkey.get(mk, Fraction(0)) + win_delta
        after_ranks = crank(scenario_shares)
        rows = []
        def roster_sort_key(item):
            name, _, ranked, _ = item
            if ranked:
                return (0, before_ranks[name], name)
            if name in entrant_names:
                return (1, after_ranks[name], name.lower())
            return (2, 9999, name.lower())
        for name, mk, ranked, r in sorted(roster, key=roster_sort_key):
            raw_before = raw_by_mkey.get(mk, 0)
            champs_before = champs_by_mkey.get(mk, 0)
            before_share = exact_share[name][0] if ranked else share_by_mkey.get(mk, Fraction(0))
            after_share = scenario_shares.get(name, before_share + win_delta)
            row = {
                'name': name,
                'team': team,
                'ranked': ranked,
                'entersLeaderboard': name in entrant_names,
                'rawBefore': raw_before if not ranked else players_out[name]['raw'],
                'rawAfter': (raw_before if not ranked else players_out[name]['raw']) + 1,
                'champsBefore': champs_before if not ranked else players_out[name]['champs'],
                'champsAfter': (champs_before if not ranked else players_out[name]['champs']) + (1 if is_champs else 0),
            }
            if ranked:
                row.update({
                    'rankBefore': before_ranks[name],
                    'rankAfter': after_ranks[name],
                    'rankDelta': before_ranks[name] - after_ranks[name],
                    'adjustedBefore': round(float(before_share) * S.mbar_all, 2),
                    'adjustedAfter': round(float(after_share) * S.mbar_all, 2),
                    'adjustedDelta': adjusted_delta,
                })
            elif name in entrant_names:
                row.update({
                    'rankBefore': None,
                    'rankAfter': after_ranks[name],
                    'rankDelta': None,
                    'adjustedBefore': round(float(before_share) * S.mbar_all, 2),
                    'adjustedAfter': round(float(after_share) * S.mbar_all, 2),
                    'adjustedDelta': adjusted_delta,
                    'seasonsBefore': [
                        {'game': g, 'wins': wins, 'majors': S.denom[g]}
                        for g, wins in sorted(wins_by_mkey_game.get(mk, {}).items(), key=lambda item: S.order_idx.get(item[0], 999))
                        if g in S.denom and wins
                    ],
                })
            rows.append(row)
        drops = []
        scenario_player_names = ranked_names | entrant_names
        for name in players_out:
            if name in scenario_player_names:
                continue
            rank_delta = before_ranks[name] - after_ranks[name]
            if rank_delta >= 0:
                continue
            before_share = exact_share[name][0]
            drops.append({
                'name': name,
                'rankBefore': before_ranks[name],
                'rankAfter': after_ranks[name],
                'rankDelta': rank_delta,
                'adjustedBefore': round(float(before_share) * S.mbar_all, 2),
                'adjustedAfter': round(float(before_share) * S.mbar_all, 2),
            })
        drops.sort(key=lambda r: (r['rankDelta'], r['rankBefore'], r['name']))
        latest_row = roster[0][3]
        scenarios.append({
            'team': team,
            'playerCount': len(rows),
            'rankedPlayerCount': sum(1 for r in rows if r['ranked']),
            'entrantCount': sum(1 for r in rows if r.get('entersLeaderboard')),
            'bestRankGain': max(((r.get('rankDelta') or 0) for r in rows), default=0),
            'rosterAsOf': {
                'event': event_name_for(latest_row, event_registry),
                'date': latest_row.get('Date') or '',
                'game': latest_row.get('Game') or game,
            },
            'players': rows,
            'drops': drops[:2],
        })

    scenarios.sort(key=lambda s: (-s['bestRankGain'], s['team']))
    return {
        'status': 'ready',
        'asOf': ASOF,
        'event': {
            'event': event_name_for(event, event_registry),
            'eventId': event_id_for(event, event_registry),
            'game': game,
            'date': event.get('Date') or '',
            'location': event.get('Location') or '',
            'region': event.get('Region') or '',
            'denominator': denom,
            'playedMajors': S.held[game],
            'scheduledMajors': denom,
            'winShareDelta': round(float(win_delta), 4),
            'adjustedDelta': adjusted_delta,
            'isChamps': is_champs,
        },
        'scenarios': scenarios,
    }


def load_community_consensus_payload():
    """Bundle the manually curated community-consensus sources for static serving.

    The raw source files live at the repo root, but Vercel serves site/ as the
    deployment root. Keep this as a lazy JSON artifact so ballots and source
    traces do not inflate every page's data.js payload.
    """
    paths = {
        'consensus': _p('community_consensus.json'),
        'sources': _p('community_consensus_sources.json'),
        'ballots': _p('community_consensus_ballots.json'),
    }
    if not all(os.path.exists(p) for p in paths.values()):
        return {'schema_version': 1, 'consensus': {}, 'sources': [], 'ballots': []}
    consensus = json.load(open(paths['consensus']))
    sources = json.load(open(paths['sources']))
    ballots = json.load(open(paths['ballots']))
    disp_by_mkey = {mkey(n): n for n, _ in PUBLISHED}
    def canon_player(player):
        return disp_by_mkey.get(mkey(player or ''), player)
    def canon_scores(scores):
        out = defaultdict(float)
        for player, score in (scores or {}).items():
            out[canon_player(player)] += score
        return dict(out)
    for rows in (consensus.get('games') or {}).values():
        for row in rows:
            row['player'] = canon_player(row.get('player'))
    for contribution in (consensus.get('source_contributions') or {}).values():
        contribution['scores'] = canon_scores(contribution.get('scores'))
    for source in sources.get('sources', []):
        for row in source.get('ranked_players') or []:
            row['player'] = canon_player(row.get('player'))
    for ballot in ballots.get('ballots', []):
        for row in ballot.get('entries') or []:
            row['player'] = canon_player(row.get('player'))
    return {
        'schema_version': 1,
        'consensus': consensus,
        'sources': sources.get('sources', []),
        'ballots': ballots.get('ballots', []),
        'resumeWins': build_community_resume_wins(),
    }


def build_community_resume_wins():
    """Raw major wins by title for players appearing in consensus tables.

    This intentionally uses the full player_event_wins source, not only the
    published 2+ win leaderboard, so a consensus top-10 player with a single win
    is not displayed as zero.
    """
    path = _p('player_event_wins.json')
    if not os.path.exists(path):
        return {}
    disp_by_mkey = {mkey(n): n for n, _ in PUBLISHED}
    wins = defaultdict(Counter)
    for r in json.load(open(path)):
        if not _keep(r) or not _played(r.get('Date')):
            continue
        raw_player = r.get('Player') or ''
        player = disp_by_mkey.get(mkey(raw_player), raw_player.strip())
        game = r.get('Game') or ''
        if player and game:
            wins[game][player] += 1
    return {game: dict(rows) for game, rows in wins.items()}


# --------------------------------------------------------------------------- #
# Assembly
# --------------------------------------------------------------------------- #
def build():
    """Compute the full APP_DATA dict. Raises RuntimeError if any player's
    reconstructed wins do not equal their published wiki total."""
    validate_source_inputs()
    sources = load_source_bundle()
    events_all, events = sources.events_all, sources.events
    pwins, champs_rows = sources.player_wins, sources.champs_wins
    ppart, tpart, accolades = sources.player_participation, sources.team_participation, sources.accolades
    event_pages = sources.event_pages
    player_stats = canonicalize_map_observations(sources.canonical_map_stats)
    conflict_resolutions = load_conflict_resolutions(HERE)
    S = season_context(events, events_all)
    event_registry = build_event_registry(events_all, event_pages, pwins, ppart, tpart, player_stats, accolades)
    major_event_ids = {event_id_for(e, event_registry) for e in events}
    validate_cross_source_consistency(events, pwins, champs_rows, ppart, tpart, event_registry)

    top50_mkeys  = {mkey(n) for n, _ in PUBLISHED}
    disp_by_mkey = {mkey(n): n for n, _ in PUBLISHED}
    part_dates, part_rows = index_participation(
        ppart, top50_mkeys, event_registry, conflict_resolutions
    )
    player_wins, wiki_name = index_wins(pwins, top50_mkeys)
    idx = SimpleNamespace(
        part_dates=part_dates, part_rows=part_rows,
        player_wins=player_wins, wiki_name=wiki_name,
        champs_by=index_champs(champs_rows, top50_mkeys, disp_by_mkey, player_wins),
        accolades_by=index_accolades(accolades, top50_mkeys),
        skill_stats_by=index_skill_stats(player_stats, top50_mkeys, S, event_registry, major_event_ids),
        legacy_skill_stats_by=index_legacy_skill_stats(load_legacy_player_event_stats(), top50_mkeys, S, event_registry, major_event_ids),
        event_registry=event_registry,
        role_stints=index_role_stints(load_role_stints(), disp_by_mkey, S))

    players_out = {}   # keyed by display name (what player.html / leaderboard links use)
    participation = {} # name -> every major entered (won or not); emitted to a separate file
    exact_share = {}   # name -> (all, post) as exact Fractions; ranking must not use rounded values
    for n, pub in PUBLISHED:
        players_out[n], participation[n], exact_share[n] = build_player(n, pub, S, idx)
    check_reconstruction(players_out)

    return {'meta': build_meta(S, events),
            'leaderboard': build_leaderboard(players_out, exact_share),
            'players': players_out,
            'games': build_games(events, pwins, tpart, S, top50_mkeys, disp_by_mkey, event_registry),
            'majors': dict(S.majors),
            'teamLogos': build_team_logos(participation, load_team_logos()),
            '_participation': participation,
            '_kor': build_kor(
                player_stats,
                tpart,
                S,
                event_registry,
                major_event_ids,
                idx.role_stints,
                disp_by_mkey,
            )}


def write(data, path=None):
    path = path or _p('site', 'data.js')
    # the full major-entry list per player is large (~0.5 MB) and only shown when a
    # player page's "All entered" toggle is opened, so it's plain JSON the page
    # fetches on demand instead of a script that would block every page load.
    participation = data.pop('_participation', {})
    with open(_p('site', 'participation.json'), 'w') as f:
        json.dump(participation, f)
    kor = data.pop('_kor', {})
    # event-by-event traces are only needed when a row is expanded, so they ship
    # as a separate lazy-loaded file instead of inflating every kor.html visit;
    # map-level rows split further into one shard per title (see build_kor)
    kor_detail = kor.pop('_detail', {})
    maps_by_game = kor_detail.pop('mapsByGame', {})
    for game, players in maps_by_game.items():
        with open(_p('site', kor_detail['meta']['mapFiles'][game]), 'w') as f:
            json.dump({'game': game, 'players': players}, f)
    with open(_p('site', 'kor-detail.json'), 'w') as f:
        json.dump(kor_detail, f)
    with open(_p('site', 'kor.json'), 'w') as f:
        json.dump(kor, f)
    with open(_p('site', 'community-consensus.json'), 'w') as f:
        json.dump(load_community_consensus_payload(), f)
    # Tournament-level stat rows are useful only on player profiles. Keep the
    # leaderboard payload focused on career and season aggregates, then lazy-load
    # the event drilldown from player.html.
    skill_events = {}
    order_idx = {g: i for i, g in enumerate(data.get('meta', {}).get('seasonOrder', []))}
    for name, player in data.get('players', {}).items():
        rows = []
        stats = player.get('skillStats')
        if stats and 'byEvent' in stats:
            rows.extend({**event, 'sourceType': 'mapRows', 'sourceLabel': 'Map rows'} for event in stats.pop('byEvent'))
        legacy_stats = player.get('legacySkillStats')
        legacy_events = legacy_stats.pop('byEvent') if legacy_stats and 'byEvent' in legacy_stats else []
        legacy_by_key = {(event.get('game'), event.get('eventId')): event for event in legacy_events}
        current_keys = {(event.get('game'), event.get('eventId')) for event in rows}
        for row in rows:
            key = (row.get('game'), row.get('eventId'))
            legacy = legacy_by_key.get(key)
            current_maps = ((row.get('overall') or {}).get('maps') or 0)
            legacy_maps = ((legacy or {}).get('overall') or {}).get('maps') or 0
            if legacy and legacy_maps > current_maps:
                row['legacyAggregate'] = legacy
        rows.extend(event for key, event in legacy_by_key.items() if key not in current_keys)
        if rows:
            rows.sort(key=lambda r: (order_idx.get(r.get('game'), 999), r.get('firstDate') or '', r.get('event') or '', r.get('sourceType') or ''))
            skill_events[name] = rows
    with open(_p('site', 'skill-events.json'), 'w') as f:
        json.dump(skill_events, f)
    with open(path, 'w') as f:
        f.write('window.APP_DATA='); json.dump(data, f); f.write(';')
    # also emit pure JSON so the /api/og edge function (and any module) can import it
    with open(_p('site', 'data.json'), 'w') as f:
        json.dump(data, f)


def main():
    data = build()
    write(data)
    print('OK: all %d players reconstruct to their published totals' % len(PUBLISHED))
    print('MBAR_ALL=%.4f  MBAR_POST=%.4f  (as of %s)' % (data['meta']['mbarAll'], data['meta']['mbarPost'], ASOF))
    print('Black Ops 7 majors counted:', data['majors'].get('Black Ops 7'))
    print('wrote', _p('site', 'data.js'))


if __name__ == '__main__':
    main()
