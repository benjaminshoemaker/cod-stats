"""Build site/data.js (the era-adjusted CoD major-wins dataset) from the source JSON.

Importable: `from build_data import build, PUBLISHED, ASOF` — `build()` returns the
full APP_DATA dict and raises if any player's reconstructed wins != their published
wiki total. Run directly (`python3 build_data.py`) to (re)write site/data.js.
"""
import json, re, os
from collections import defaultdict, Counter
from fractions import Fraction
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
def _p(*parts): return os.path.join(HERE, *parts)

ASOF = '2026-06-29'              # only majors played on/before this count as wins; future-dated
                                 # events still count toward an in-progress season's denominator
DROP_GAMES = {'Warzone', 'Mobile'}   # separate ecosystems — excluded entirely

# One-off corrections for events the wiki's Majors portal tiers as Major/Premier but
# that aren't top-level pro majors. Dropped by exact event name, so the fix survives a
# re-pull from the wiki (fetch_source.py) and becomes a harmless no-op once the wiki
# reclassifies the event upstream.
#  * "Call of Duty Challengers Finals 2026" — a Challengers (amateur) event, not a pro
#    major. It inflated the Black Ops 7 denominator to 7; BO7 has 6 real majors (4 CDL
#    Majors + Champs + EWC). Flagged by u/BcDownes on r/CoDCompetitive, 2026-07.
DROP_EVENTS = {'Call of Duty Challengers Finals 2026'}

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
 ("TeeP",18),("aBeZy",14),("Simp",14),("Cellium",11),("Shotzzy",10),("Kenny",10),("MerK",10),
 ("JKap",9),("SlasheR",9),("Arcitys",9),("Envoy",9),("Octane",9),("Priestahh",9),("BigTymeR",9),
 ("Huke",8),("Enable",8),("Drazah",8),("HyDra",8),("Dashy",7),("John",7),("Attach",7),("Parasite",7),
 ("Skyz",7),("Jurd",6),("Apathy",6),("Tommey",6),("MadCat",6),("Joshh",6),("Slacked",6),("ZooMaa",6),
 ("Nadeshot",6),("Gunless",6),("Rambo",5),("ProoFy",5),("Swanny",5),("CleanX",5),("Accuracy",5),
 ("Scrap",5),("TJHaLy",5),("Classic",5),("Loony",5),("iLLeY",5),("KiSMET",5),("Bance",4),
 ("Censor",4),("Dedo",4),("Fero",4),("GunShy",4),("Insight",4),("KiLLa",4),
 ("MiRx",4),("NAMELESS",4),("Prestinni",4),("Saints",4),("XLNC",4),("Cammy",3),
 ("Crowder",3),("Frosty",3),("Ghosty",3),("Havok",3),("MajorManiak",3),("Mak",3),
 ("Mercules",3),("Pred",3),("Sib",3),("ASSASS1N",2),("Bissell",2),("Bobby",2),
 ("Cheen",2),("DopedGoat",2),("FEARS",2),("Jake",2),("Mack",2),("Methodz",2),
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

def norm(n): return re.sub(r'\s*\(.*?\)\s*', '', n).strip()   # strip disambiguation parenthetical
def mkey(n): return norm(n).lower()                           # case-insensitive join key (ABeZy vs aBeZy)

def _played(d): return (d or '0000') <= ASOF
def _keep(x): return x['Game'] not in DROP_GAMES and x['Event'] not in DROP_EVENTS


# --------------------------------------------------------------------------- #
# Source loading + season math
# --------------------------------------------------------------------------- #
def load_sources():
    """Load the four wiki source files, restricted to the console-major universe
    (DROP_GAMES / DROP_EVENTS out; wins on/before ASOF). Returns
    (events_all, events, pwins, champs_rows, ppart) — events_all keeps
    future-dated scheduled majors for in-progress denominators; ppart is
    filtered per-row later (it also needs the DNS/place rules)."""
    events = json.load(open(_p('major_events.json')))        # [{Event,Game,Date,Winner,...}]
    pwins  = json.load(open(_p('player_event_wins.json')))   # [{Player,Event,Game,Date}]
    champs_rows = json.load(open(_p('champs_wins.json')))['cargoquery']  # [{Player,Event,Date}]
    ppart  = json.load(open(_p('player_participation.json')))  # [{Player,Event,Game,Date,Place,...}] ALL placements

    events_all = [e for e in events if _keep(e)]                         # incl. future-dated (scheduled)
    events = [e for e in events_all if _played(e.get('Date'))]
    pwins  = [r for r in pwins if _keep(r) and _played(r.get('Date'))]
    return events_all, events, pwins, champs_rows, ppart


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


def index_participation(ppart, top50_mkeys):
    """Career span from PARTICIPATION (every major entered, won or not), not just
    wins: first-win-to-last-win understates how long a player actually competed.
    Uses the same console-major universe (drop Warzone/Mobile & dropped events,
    on/before ASOF) so a player who kept competing after their last win — e.g.
    BigTymeR played through 2014 but last won in 2012 — has an honest active
    span, and majors_played gives a real denominator for win rate."""
    part_dates = defaultdict(list)
    part_rows = defaultdict(dict)   # mk -> {event: {event,game,date,place}} — every major entered (won or not)
    for r in ppart:
        if mkey(r['Player']) not in top50_mkeys: continue
        if not _keep(r) or not _played(r.get('Date')): continue
        if r.get('Place') in NONPLAY: continue
        k = mkey(r['Player'])
        if r.get('Date'): part_dates[k].append(r['Date'])
        part_rows[k].setdefault(r['Event'], {'event': r['Event'], 'game': r['Game'],
                                             'date': r.get('Date') or '', 'place': str(r.get('Place') or '').strip()})
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
        # GUARD: the champs join is by normalized name, so a wiki disambiguation like
        # "Scump (someone else)" would silently merge into the listed player's count.
        if mkey(t['Player']) in top50_mkeys and norm(t['Player']) != t['Player'].strip():
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


def player_seasons(wins, S):
    """Group a player's (date-sorted) wins into per-season rows, chronological."""
    by_season = defaultdict(lambda: {'count': 0, 'events': []})
    for w in wins:
        g = w['Game']
        by_season[g]['count'] += 1
        by_season[g]['events'].append({'event': w['Event'], 'date': w.get('Date') or '', 'weight': round(1.0 / S.denom[g], 4)})
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
    seasons = player_seasons(wins, S)
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
    won_events = {w['Event'] for w in wins}
    all_majors = [dict(r, won=(r['event'] in won_events)) for r in idx.part_rows.get(mk, {}).values()]
    seen_ev = {r['event'] for r in all_majors}
    for w in wins:
        if w['Event'] not in seen_ev:
            all_majors.append({'event': w['Event'], 'game': w['Game'], 'date': w.get('Date') or '', 'place': '1', 'won': True})
    all_majors.sort(key=lambda r: r['date'])

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
           'note': PLAYER_NOTES.get(n)}
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
        })
    return leaderboard


def build_games(events, pwins, S, top50_mkeys, disp_by_mkey):
    games_out = []
    for g in S.order:
        evs = sorted([e for e in events if e['Game'] == g], key=lambda x: (x.get('Date') or ''))
        wc = Counter()
        for r in pwins:
            if r['Game'] == g and mkey(r['Player']) in top50_mkeys:
                wc[disp_by_mkey[mkey(r['Player'])]] += 1
        games_out.append({'game': g, 'majors': S.held[g], 'denom': S.denom[g], 'weight': round(1.0 / S.denom[g], 4),
            'order': S.order_idx[g], 'preBo2': g in S.pre_bo2, 'firstDate': S.first_date[g],
            'events': [{'event': e['Event'], 'date': e.get('Date') or '', 'winner': e.get('Winner') or '',
                        'type': e.get('EventType') or '', 'prize': e.get('Prizepool') or '', 'location': e.get('Location') or '',
                        'region': e.get('Region') or ''} for e in evs],
            'topPlayers': [{'name': p, 'wins': c} for p, c in wc.most_common(8)]})
    return games_out


def build_meta(S, events):
    return {'mbarAll': round(S.mbar_all, 4), 'mbarPost': round(S.mbar_post, 4), 'asOf': ASOF,
            'consoleSeasons': len(S.order), 'preBo2': sorted(S.pre_bo2, key=lambda g: S.order_idx[g]),
            'seasonOrder': S.order, 'totalMajors': sum(S.majors.values()),
            'consoleMajors': sum(S.majors[g] for g in S.order), 'numEvents': len(events)}


# --------------------------------------------------------------------------- #
# Assembly
# --------------------------------------------------------------------------- #
def build():
    """Compute the full APP_DATA dict. Raises RuntimeError if any player's
    reconstructed wins do not equal their published wiki total."""
    events_all, events, pwins, champs_rows, ppart = load_sources()
    S = season_context(events, events_all)

    top50_mkeys  = {mkey(n) for n, _ in PUBLISHED}
    disp_by_mkey = {mkey(n): n for n, _ in PUBLISHED}
    part_dates, part_rows = index_participation(ppart, top50_mkeys)
    player_wins, wiki_name = index_wins(pwins, top50_mkeys)
    idx = SimpleNamespace(
        part_dates=part_dates, part_rows=part_rows,
        player_wins=player_wins, wiki_name=wiki_name,
        champs_by=index_champs(champs_rows, top50_mkeys, disp_by_mkey, player_wins))

    players_out = {}   # keyed by display name (what player.html / leaderboard links use)
    participation = {} # name -> every major entered (won or not); emitted to a separate file
    exact_share = {}   # name -> (all, post) as exact Fractions; ranking must not use rounded values
    for n, pub in PUBLISHED:
        players_out[n], participation[n], exact_share[n] = build_player(n, pub, S, idx)
    check_reconstruction(players_out)

    return {'meta': build_meta(S, events),
            'leaderboard': build_leaderboard(players_out, exact_share),
            'players': players_out,
            'games': build_games(events, pwins, S, top50_mkeys, disp_by_mkey),
            'majors': dict(S.majors), '_participation': participation}


def write(data, path=None):
    path = path or _p('site', 'data.js')
    # the full major-entry list per player is large (~0.5 MB) and only shown when a
    # player page's "All entered" toggle is opened, so it's plain JSON the page
    # fetches on demand instead of a script that would block every page load.
    participation = data.pop('_participation', {})
    with open(_p('site', 'participation.json'), 'w') as f:
        json.dump(participation, f)
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
