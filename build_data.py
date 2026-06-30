import json, re, sys
from collections import defaultdict, Counter

ASOF = '2026-06-29'   # data-freshness cutoff: only majors played on/before this count

events = json.load(open('major_events.json'))          # [{Event,Game,Date,Winner,EventType,Prizepool,Location,Region}]
pwins  = json.load(open('player_event_wins.json'))     # [{Player,Event,Game,Date}]
champs_rows = json.load(open('champs_wins.json'))['cargoquery']   # [{Player,Event,Date}]

# Warzone (battle royale) and Mobile are separate ecosystems — excluded entirely.
DROP_GAMES = {'Warzone','Mobile'}
# A major only counts once it has actually been played (date <= ASOF). This drops
# scheduled-but-uncontested events (e.g. the 3 future Black Ops 7 majors) from the denominator.
def played(d): return (d or '0000') <= ASOF
events = [e for e in events if e['Game'] not in DROP_GAMES and played(e.get('Date'))]
pwins  = [r for r in pwins  if r['Game'] not in DROP_GAMES and played(r.get('Date'))]

def norm(n):                                   # strip disambiguation parenthetical
    return re.sub(r'\s*\(.*?\)\s*','',n).strip()
def mkey(n):                                   # case-insensitive join key (wiki data varies case: ABeZy vs aBeZy)
    return norm(n).lower()

# ---- denominators + chronological season order ----
majors = Counter(e['Game'] for e in events)
first_date = {}
for e in events:
    g=e['Game']; d=e.get('Date') or '9999'
    if g not in first_date or d < first_date[g]: first_date[g]=d
season_order = sorted(majors, key=lambda g: first_date[g])
order_idx = {g:i for i,g in enumerate(season_order)}

console_seasons = list(season_order)
bo2_date = first_date['Black Ops 2']
pre_bo2 = {g for g in season_order if first_date[g] < bo2_date}

def mbar(games): return sum(majors[g] for g in games)/len(games)
MBAR_ALL  = mbar(console_seasons)
MBAR_POST = mbar([g for g in console_seasons if g not in pre_bo2])

# ---- published top-50 (display name, raw wins) ----
published = [("Crimsix",38),("Scump",28),("Karma",24),("FormaL",23),("ACHES",19),("Clayster",18),
 ("TeeP",18),("aBeZy",14),("Simp",14),("Cellium",11),("Shotzzy",10),("Kenny",10),("MerK",10),
 ("JKap",9),("SlasheR",9),("Arcitys",9),("Envoy",9),("Octane",9),("Priestahh",9),("BigTymeR",9),
 ("Huke",8),("Enable",8),("Drazah",8),("HyDra",8),("Dashy",7),("John",7),("Attach",7),("Parasite",7),
 ("Skyz",7),("Jurd",6),("Apathy",6),("Tommey",6),("MadCat",6),("Joshh",6),("Slacked",6),("ZooMaa",6),
 ("Nadeshot",6),("Gunless",6),("Rambo",5),("ProoFy",5),("Swanny",5),("CleanX",5),("Accuracy",5),
 ("Scrap",5),("TJHaLy",5),("Classic",5),("Loony",5),("iLLeY",5),("KiSMET",5),("Bance",4)]
top50_mkeys  = {mkey(n) for n,_ in published}
disp_by_mkey = {mkey(n):n for n,_ in published}

# ---- per-player individual wins (top 50), case-insensitive join ----
player_wins = defaultdict(list)
for r in pwins:
    k=mkey(r['Player'])
    if k in top50_mkeys:
        player_wins[k].append(r)

def weight(g): return 1.0/majors[g]

champs_by=defaultdict(list)
for r in champs_rows:
    t=r['title']
    champs_by[mkey(t['Player'])].append({'event':t['Event'],'year':(t.get('Date') or '')[:4]})
for k in champs_by:
    champs_by[k].sort(key=lambda e:e['year'])

players_out={}   # keyed by display name (what player.html / leaderboard links use)
for n,pub in published:
    mk=mkey(n)
    wins=sorted(player_wins.get(mk,[]), key=lambda r:(r.get('Date') or ''))
    by_season=defaultdict(lambda:{'count':0,'events':[]})
    for w in wins:
        g=w['Game']
        by_season[g]['count']+=1
        by_season[g]['events'].append({'event':w['Event'],'date':w.get('Date') or '','weight':round(weight(g),4)})
    seasons=[]
    for g in sorted(by_season, key=lambda x:order_idx[x]):
        c=by_season[g]['count']
        seasons.append({'game':g,'wins':c,'majors':majors[g],'share':round(c/majors[g],4),
                        'pre_bo2': g in pre_bo2,
                        'events':by_season[g]['events']})
    share_all = sum(s['share'] for s in seasons)
    share_post= sum(s['share'] for s in seasons if not s['pre_bo2'])
    players_out[n]={'name':n,'raw':pub,'seasons':seasons,
                    'share_all':round(share_all,4),'adj_all':round(share_all*MBAR_ALL,2),
                    'share_post':round(share_post,4),'adj_post':round(share_post*MBAR_POST,2),
                    'champs':len(champs_by.get(mk,[])),'champ_events':champs_by.get(mk,[])}

# ---- GUARD: reconstructed wins must equal the published wiki total for every player ----
mismatch=[(n,pub,sum(s['wins'] for s in players_out[n]['seasons'])) for n,pub in published
          if sum(s['wins'] for s in players_out[n]['seasons'])!=pub]
if mismatch:
    print('BUILD FAILED — reconstruction != published total:', file=sys.stderr)
    for n,pub,rec in mismatch: print(f'  {n}: published {pub} vs reconstructed {rec}', file=sys.stderr)
    sys.exit(1)
print('OK: all %d players reconstruct to their published totals'%len(published))

# ---- rankings + deltas for both modes ----
def rank(metric):
    order=sorted(players_out.values(), key=lambda p:-p[metric])
    return {p['name']:i+1 for i,p in enumerate(order)}
raw_rank  = {n:i+1 for i,(n,_) in enumerate(published)}
adj_rank  = rank('adj_all')
post_rank = rank('adj_post')

leaderboard=[]
for n,pub in published:
    p=players_out[n]
    leaderboard.append({
        'name':n,'raw':pub,'rawRank':raw_rank[n],
        'shareAll':p['share_all'],'adjAll':p['adj_all'],'adjRank':adj_rank[n],'delta':raw_rank[n]-adj_rank[n],
        'sharePost':p['share_post'],'adjPost':p['adj_post'],'postRank':post_rank[n],'deltaPost':raw_rank[n]-post_rank[n],
        'champs':p['champs'],
    })

# ---- games/seasons data ----
games_out=[]
for g in season_order:
    evs=sorted([e for e in events if e['Game']==g], key=lambda x:(x.get('Date') or ''))
    wc=Counter()
    for r in pwins:
        if r['Game']==g and mkey(r['Player']) in top50_mkeys:
            wc[disp_by_mkey[mkey(r['Player'])]]+=1
    games_out.append({'game':g,'majors':majors[g],'weight':round(1.0/majors[g],4),
        'order':order_idx[g],'preBo2':g in pre_bo2,'firstDate':first_date[g],
        'events':[{'event':e['Event'],'date':e.get('Date') or '','winner':e.get('Winner') or '',
                   'type':e.get('EventType') or '','prize':e.get('Prizepool') or '','location':e.get('Location') or '',
                   'region':e.get('Region') or ''} for e in evs],
        'topPlayers':[{'name':p,'wins':c} for p,c in wc.most_common(8)]})

meta={'mbarAll':round(MBAR_ALL,4),'mbarPost':round(MBAR_POST,4),'asOf':ASOF,
      'consoleSeasons':len(console_seasons),'preBo2':sorted(pre_bo2,key=lambda g:order_idx[g]),
      'seasonOrder':season_order,'totalMajors':sum(majors.values()),
      'consoleMajors':sum(majors[g] for g in console_seasons),'numEvents':len(events)}

data={'meta':meta,'leaderboard':leaderboard,'players':players_out,'games':games_out,'majors':dict(majors)}
with open('site/data.js','w') as f:
    f.write('window.APP_DATA=')
    json.dump(data,f)
    f.write(';')
print('MBAR_ALL=%.4f  MBAR_POST=%.4f  (as of %s)'%(MBAR_ALL,MBAR_POST,ASOF))
print('Black Ops 7 majors counted:', majors['Black Ops 7'])
print('wrote site/data.js (%d bytes)'%len(open('site/data.js').read()))
