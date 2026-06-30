"""Build site/data.js (the era-adjusted CoD major-wins dataset) from the source JSON.

Importable: `from build_data import build, PUBLISHED, ASOF` — `build()` returns the
full APP_DATA dict and raises if any player's reconstructed wins != their published
wiki total. Run directly (`python3 build_data.py`) to (re)write site/data.js.
"""
import json, re, os
from collections import defaultdict, Counter

HERE = os.path.dirname(os.path.abspath(__file__))
def _p(*parts): return os.path.join(HERE, *parts)

ASOF = '2026-06-29'              # only majors played on/before this count (drops future BO7 events)
DROP_GAMES = {'Warzone', 'Mobile'}   # separate ecosystems — excluded entirely

# Some seasons structurally restricted how many majors a team could enter, so a
# player's share should divide by what they *could win*, not the raw count held.
# Modern Warfare 2019 (CDL 2020) ran a split "Home Series" format: 13 majors were
# held, but every team played exactly 9 (12 Home Series of 8 teams each = 8 per
# team, plus the 12-team Champs), verified in team_participation.json. Open-era
# seasons are deliberately NOT here — their majors were open/qualified events
# everyone had the opportunity to enter (see team_participation.json analysis).
STRUCTURAL_DENOM = {'Modern Warfare': 9}

# The wiki's published "Major Wins" leaderboard (display name, raw wins). The build
# verifies our reconstruction reproduces every one of these exactly.
PUBLISHED = [("Crimsix",38),("Scump",28),("Karma",24),("FormaL",23),("ACHES",19),("Clayster",18),
 ("TeeP",18),("aBeZy",14),("Simp",14),("Cellium",11),("Shotzzy",10),("Kenny",10),("MerK",10),
 ("JKap",9),("SlasheR",9),("Arcitys",9),("Envoy",9),("Octane",9),("Priestahh",9),("BigTymeR",9),
 ("Huke",8),("Enable",8),("Drazah",8),("HyDra",8),("Dashy",7),("John",7),("Attach",7),("Parasite",7),
 ("Skyz",7),("Jurd",6),("Apathy",6),("Tommey",6),("MadCat",6),("Joshh",6),("Slacked",6),("ZooMaa",6),
 ("Nadeshot",6),("Gunless",6),("Rambo",5),("ProoFy",5),("Swanny",5),("CleanX",5),("Accuracy",5),
 ("Scrap",5),("TJHaLy",5),("Classic",5),("Loony",5),("iLLeY",5),("KiSMET",5),("Bance",4)]

def norm(n): return re.sub(r'\s*\(.*?\)\s*', '', n).strip()   # strip disambiguation parenthetical
def mkey(n): return norm(n).lower()                           # case-insensitive join key (ABeZy vs aBeZy)


def build():
    """Compute the full APP_DATA dict. Raises RuntimeError if any player's
    reconstructed wins do not equal their published wiki total."""
    events = json.load(open(_p('major_events.json')))        # [{Event,Game,Date,Winner,...}]
    pwins  = json.load(open(_p('player_event_wins.json')))   # [{Player,Event,Game,Date}]
    champs_rows = json.load(open(_p('champs_wins.json')))['cargoquery']  # [{Player,Event,Date}]

    played = lambda d: (d or '0000') <= ASOF
    events = [e for e in events if e['Game'] not in DROP_GAMES and played(e.get('Date'))]
    pwins  = [r for r in pwins  if r['Game'] not in DROP_GAMES and played(r.get('Date'))]

    # held = majors actually held that season; denom = majors a team could win
    # (reduced for structurally-restricted seasons). Shares/peak/rescale use denom.
    majors = Counter(e['Game'] for e in events)
    held = dict(majors)
    denom = {g: STRUCTURAL_DENOM.get(g, held[g]) for g in held}
    first_date = {}
    for e in events:
        g = e['Game']; d = e.get('Date') or '9999'
        if g not in first_date or d < first_date[g]: first_date[g] = d
    season_order = sorted(majors, key=lambda g: first_date[g])
    order_idx = {g: i for i, g in enumerate(season_order)}

    console_seasons = list(season_order)
    bo2_date = first_date['Black Ops 2']
    pre_bo2 = {g for g in season_order if first_date[g] < bo2_date}

    def mbar(games): return sum(denom[g] for g in games) / len(games)
    MBAR_ALL  = mbar(console_seasons)
    MBAR_POST = mbar([g for g in console_seasons if g not in pre_bo2])

    top50_mkeys  = {mkey(n) for n, _ in PUBLISHED}
    disp_by_mkey = {mkey(n): n for n, _ in PUBLISHED}

    player_wins = defaultdict(list)
    for r in pwins:
        k = mkey(r['Player'])
        if k in top50_mkeys:
            player_wins[k].append(r)

    def weight(g): return 1.0 / denom[g]

    champs_by = defaultdict(list)
    for r in champs_rows:
        t = r['title']
        champs_by[mkey(t['Player'])].append({'event': t['Event'], 'year': (t.get('Date') or '')[:4]})
    for k in champs_by:
        champs_by[k].sort(key=lambda e: e['year'])

    players_out = {}   # keyed by display name (what player.html / leaderboard links use)
    for n, pub in PUBLISHED:
        mk = mkey(n)
        wins = sorted(player_wins.get(mk, []), key=lambda r: (r.get('Date') or ''))
        by_season = defaultdict(lambda: {'count': 0, 'events': []})
        for w in wins:
            g = w['Game']
            by_season[g]['count'] += 1
            by_season[g]['events'].append({'event': w['Event'], 'date': w.get('Date') or '', 'weight': round(weight(g), 4)})
        seasons = []
        for g in sorted(by_season, key=lambda x: order_idx[x]):
            c = by_season[g]['count']
            seasons.append({'game': g, 'wins': c, 'majors': denom[g], 'held': held[g],
                            'share': round(c / denom[g], 4),
                            'pre_bo2': g in pre_bo2, 'events': by_season[g]['events']})
        share_all  = sum(s['share'] for s in seasons)
        share_post = sum(s['share'] for s in seasons if not s['pre_bo2'])

        # Peak (best single season's share, rescaled to a wins-like number) + Longevity
        # (distinct titles won, plus career span in years). Computed for both modes.
        def peak_of(slist, mb):
            if not slist: return {'adj': 0.0, 'season': None, 'wins': 0, 'majors': 0}
            best = max(slist, key=lambda s: s['share'])
            return {'adj': round(best['share'] * mb, 2), 'season': best['game'], 'wins': best['wins'], 'majors': best['majors']}
        def span_of(slist):
            yrs = [int(e['date'][:4]) for s in slist for e in s['events'] if e['date']]
            return (max(yrs) - min(yrs) + 1, min(yrs), max(yrs)) if yrs else (0, None, None)
        seasons_post = [s for s in seasons if not s['pre_bo2']]
        pk_all, pk_post = peak_of(seasons, MBAR_ALL), peak_of(seasons_post, MBAR_POST)
        span_all, first_all, last_all = span_of(seasons)
        span_post, first_post, last_post = span_of(seasons_post)

        players_out[n] = {'name': n, 'raw': pub, 'seasons': seasons,
                          'share_all': round(share_all, 4), 'adj_all': round(share_all * MBAR_ALL, 2),
                          'share_post': round(share_post, 4), 'adj_post': round(share_post * MBAR_POST, 2),
                          'champs': len(champs_by.get(mk, [])), 'champ_events': champs_by.get(mk, []),
                          'peak_all': pk_all, 'peak_post': pk_post,
                          'titles_all': len(seasons), 'titles_post': len(seasons_post),
                          'span_all': span_all, 'span_post': span_post,
                          'first_year': first_all, 'last_year': last_all}

    # GUARD: reconstructed wins must equal the published wiki total for every player
    mismatch = [(n, pub, sum(s['wins'] for s in players_out[n]['seasons'])) for n, pub in PUBLISHED
                if sum(s['wins'] for s in players_out[n]['seasons']) != pub]
    if mismatch:
        raise RuntimeError('reconstruction != published total: ' +
                           ', '.join(f'{n} ({pub} vs {rec})' for n, pub, rec in mismatch))

    def rank(metric):
        order = sorted(players_out.values(), key=lambda p: -p[metric])
        return {p['name']: i + 1 for i, p in enumerate(order)}
    raw_rank  = {n: i + 1 for i, (n, _) in enumerate(PUBLISHED)}
    adj_rank  = rank('adj_all')
    post_rank = rank('adj_post')

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
        })

    games_out = []
    for g in season_order:
        evs = sorted([e for e in events if e['Game'] == g], key=lambda x: (x.get('Date') or ''))
        wc = Counter()
        for r in pwins:
            if r['Game'] == g and mkey(r['Player']) in top50_mkeys:
                wc[disp_by_mkey[mkey(r['Player'])]] += 1
        games_out.append({'game': g, 'majors': held[g], 'denom': denom[g], 'weight': round(1.0 / denom[g], 4),
            'order': order_idx[g], 'preBo2': g in pre_bo2, 'firstDate': first_date[g],
            'events': [{'event': e['Event'], 'date': e.get('Date') or '', 'winner': e.get('Winner') or '',
                        'type': e.get('EventType') or '', 'prize': e.get('Prizepool') or '', 'location': e.get('Location') or '',
                        'region': e.get('Region') or ''} for e in evs],
            'topPlayers': [{'name': p, 'wins': c} for p, c in wc.most_common(8)]})

    meta = {'mbarAll': round(MBAR_ALL, 4), 'mbarPost': round(MBAR_POST, 4), 'asOf': ASOF,
            'consoleSeasons': len(console_seasons), 'preBo2': sorted(pre_bo2, key=lambda g: order_idx[g]),
            'seasonOrder': season_order, 'totalMajors': sum(majors.values()),
            'consoleMajors': sum(majors[g] for g in console_seasons), 'numEvents': len(events)}

    return {'meta': meta, 'leaderboard': leaderboard, 'players': players_out, 'games': games_out, 'majors': dict(majors)}


def write(data, path=None):
    path = path or _p('site', 'data.js')
    with open(path, 'w') as f:
        f.write('window.APP_DATA='); json.dump(data, f); f.write(';')


def main():
    data = build()
    write(data)
    print('OK: all %d players reconstruct to their published totals' % len(PUBLISHED))
    print('MBAR_ALL=%.4f  MBAR_POST=%.4f  (as of %s)' % (data['meta']['mbarAll'], data['meta']['mbarPost'], ASOF))
    print('Black Ops 7 majors counted:', data['majors'].get('Black Ops 7'))
    print('wrote', _p('site', 'data.js'))


if __name__ == '__main__':
    main()
