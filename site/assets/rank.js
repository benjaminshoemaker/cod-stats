// Shared era-adjustment ranking engine — used by the leaderboard UI (index.html)
// and the /api/og card endpoint, so both produce identical numbers. Pure JS: takes
// the data dict `D` (from data.json / window.APP_DATA) as a parameter, no DOM/global
// dependencies. Mirrors build_data.py's exact-Fraction shares + competition ranks;
// guarded by the Playwright oracle test that computeRows(all)/(post) match the build.

// BigInt gcd/lcm so exact-share numerators can't overflow Number's 2^53.
function gcd(a, b){ a = a < 0n ? -a : a; b = b < 0n ? -b : b; while(b){ const t = a % b; a = b; b = t; } return a; }
function lcm(a, b){ return a / gcd(a, b) * b; }

// Era/title selection helpers derived from the dataset (title order, presets, slug
// encoding for shareable custom sets). One place so UI and endpoint agree.
export function eraContext(D){
  const ORDER = D.meta.seasonOrder;
  const PRE = new Set(D.meta.preBo2);
  const CDL_START = ORDER.indexOf('Modern Warfare');            // first CDL season (2020)
  const eraOf = g => PRE.has(g) ? 'prebo2' : (ORDER.indexOf(g) >= CDL_START ? 'cdl' : 'mlgcwl');
  const PRESETS = {
    all:    ORDER.slice(),
    post:   ORDER.filter(g => !PRE.has(g)),
    prebo2: ORDER.filter(g => eraOf(g) === 'prebo2'),
    mlgcwl: ORDER.filter(g => eraOf(g) === 'mlgcwl'),
    cdl:    ORDER.filter(g => eraOf(g) === 'cdl'),
  };
  const DENOM = {}; D.games.forEach(g => { DENOM[g.game] = g.denom; });
  const slugOf = g => g.toLowerCase().replace(/[^a-z0-9]/g, '');
  const BY_SLUG = {}; ORDER.forEach(g => { BY_SLUG[slugOf(g)] = g; });
  const sameSet = (set, arr) => set.size === arr.length && arr.every(g => set.has(g));
  const selectionToken = sel => {
    for(const k of ['all','post','prebo2','mlgcwl','cdl']) if(sameSet(sel, PRESETS[k])) return k;
    return 't:' + ORDER.filter(g => sel.has(g)).map(slugOf).join('-');
  };
  const parseSelection = token => {
    if(!token) return null;
    if(PRESETS[token]) return new Set(PRESETS[token]);
    if(token.startsWith('t:')){
      const gs = token.slice(2).split('-').map(s => BY_SLUG[s]).filter(Boolean);   // unknown/empty dropped
      return gs.length ? new Set(gs) : null;
    }
    return null;
  };
  return { ORDER, PRE, eraOf, PRESETS, DENOM, slugOf, BY_SLUG, selectionToken, parseSelection };
}

// Recompute the leaderboard for a subset of titles. `selected` is a Set of title
// names; `ringWeight` (default 1 = off) counts a championship as N majors via a flat
// (N-1) bonus on top of the adjusted total. Returns rows with exact-integer ranking
// keys plus display fields. Zero-win players in the selection are dropped.
export function computeRows(D, selected, ringWeight){
  const N = ringWeight || 1;
  const ORDER = D.meta.seasonOrder;
  const DENOM = {}; D.games.forEach(g => { DENOM[g.game] = g.denom; });
  const games = ORDER.filter(g => selected.has(g));
  if(!games.length) return [];
  const denomSum = games.reduce((a, g) => a + DENOM[g], 0);
  const G = games.length;
  const MBAR = denomSum / G;
  const L = games.reduce((acc, g) => lcm(acc, BigInt(DENOM[g])), 1n);
  const Lnum = Number(L);
  const rows = [];
  for(const name in D.players){
    const p = D.players[name];
    const sel = p.seasons.filter(s => selected.has(s.game));
    const raw = sel.reduce((a, s) => a + s.wins, 0);
    if(raw === 0) continue;
    const numer = sel.reduce((a, s) => a + BigInt(s.wins) * (L / BigInt(s.majors)), 0n);
    const adjusted = Math.round(Number(numer) / Lnum * MBAR * 100) / 100;
    let best = sel[0];
    for(const s of sel){ if(s.wins * best.majors > best.wins * s.majors) best = s; }
    const yrs = [];
    for(const s of sel) for(const e of s.events) if(e.date) yrs.push(+e.date.slice(0, 4));
    const won = new Set(); sel.forEach(s => s.events.forEach(e => won.add(e.event)));
    rows.push({
      name, raw, _numer: numer,
      champs: (p.champ_events || []).filter(c => won.has(c.event)).length,
      adjusted,
      peak: best.wins / best.majors,
      peakInfo: { adj: Math.round(best.wins / best.majors * MBAR * 100) / 100, season: best.game, wins: best.wins, majors: best.majors },
      eras: sel.length,
      firstYear: yrs.length ? Math.min(...yrs) : null,
      lastYear:  yrs.length ? Math.max(...yrs) : null,
    });
  }
  const weighted = N > 1;
  const bExtra = BigInt(N - 1), bSum = BigInt(denomSum), bG = BigInt(G);
  for(const r of rows){
    r.adjWeighted = Math.round((r.adjusted + r.champs * (N - 1)) * 100) / 100;   // display
    r._wnumer = r._numer * bSum + BigInt(r.champs) * bExtra * L * bG;             // exact ranking key
  }
  for(const r of rows){
    r.adjRank = weighted
      ? 1 + rows.filter(o => o._wnumer > r._wnumer).length
      : 1 + rows.filter(o => o._numer > r._numer).length;
    r.rawRank = 1 + rows.filter(o => o.raw > r.raw).length;
    r.delta = r.rawRank - r.adjRank;
    r.winsChange = Math.round((r.adjusted - r.raw) * 10) / 10;
  }
  return rows;
}
