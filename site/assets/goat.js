// Shared GOAT Builder scoring engine, used by the builder UI (goat-builder.html)
// and the /api/goat-og card + /g share endpoints, so both produce identical
// rankings. Pure JS: takes the data dict `D` (from data.json / window.APP_DATA)
// and the community-consensus payload as parameters. No DOM/global dependencies.

export const CRITERIA = [
  {key:'resume', label:'Resume'},
  {key:'skill', label:'Individual Skill'},
  {key:'longevity', label:'Longevity'},
  {key:'peak', label:'Peak'},
];
export const DEFAULT_WEIGHTS = {resume:50, skill:30, longevity:10, peak:10};
export const DEFAULT_ENABLED = {resume:true, skill:true, longevity:true, peak:true};
export const DEFAULT_RING = 2;

export function clampWeight(value){
  return Math.max(0, Math.min(100, Number(value) || 0));
}
export function playerKey(name){ return String(name || '').replace(/\s*\(.*?\)\s*/g, '').trim().toLowerCase(); }
export function titlePoint(rank){
  const r = Number(rank);
  if(!Number.isFinite(r)) return null;
  return Math.pow(Math.max(0, 31 - r) / 30, 2.5);
}

// Title/era selection helpers derived from the dataset. The preset keys are the
// GOAT Builder's public URL vocabulary (?era=cdl|mlgCwl|postBo2|preBo2).
export function goatContext(D){
  const allGames = D.meta.seasonOrder;
  const gameInfo = new Map(D.games.map(g => [g.game, g]));
  const eventGame = new Map();
  for(const game of D.games){
    for(const event of game.events || []) eventGame.set(event.event, game.game);
  }
  const cdlStart = gameInfo.get('Modern Warfare')?.order || 0;
  const ERA_PRESETS = {
    all: allGames,
    cdl: allGames.filter(g => (gameInfo.get(g)?.order || 0) >= cdlStart),
    mlgCwl: allGames.filter(g => !(gameInfo.get(g)?.preBo2) && (gameInfo.get(g)?.order || 0) < cdlStart),
    postBo2: allGames.filter(g => !(gameInfo.get(g)?.preBo2)),
    preBo2: allGames.filter(g => gameInfo.get(g)?.preBo2),
  };
  const players = Object.values(D.players);
  return {allGames, gameInfo, eventGame, ERA_PRESETS, players};
}

// consensus payload → Map(playerKey → ranked rows with precomputed points)
export function buildConsensusIndex(data){
  const byPlayer = new Map();
  let rowCount = 0;
  for(const [game, rows] of Object.entries(data.games || {})){
    for(const row of rows || []){
      if(!row || row.ranked === false) continue;
      const points = titlePoint(row.consensus_rank);
      if(!Number.isFinite(points)) continue;
      const key = playerKey(row.player);
      const list = byPlayer.get(key) || [];
      list.push({...row, game, rank:Number(row.consensus_rank), points});
      byPlayer.set(key, list);
      rowCount++;
    }
  }
  return {byPlayer, titles:Object.keys(data.games || {}).length, rows:rowCount};
}

// URL params → a full builder config. Shared by the page and the share
// endpoints so a /g link and the live page always read a URL the same way.
export function parseGoatConfig(searchParams, ctx){
  const weights = {...DEFAULT_WEIGHTS};
  const enabled = {...DEFAULT_ENABLED};
  let ring = DEFAULT_RING;
  let selectedGames = new Set(ctx.allGames);
  let eraPreset = 'all';
  if(searchParams.has('criteria')){
    const active = new Set(String(searchParams.get('criteria')).split(',')
      .filter(key => Object.prototype.hasOwnProperty.call(DEFAULT_ENABLED, key)));
    for(const c of CRITERIA) enabled[c.key] = active.has(c.key);
  }
  const weightsParam = searchParams.get('weights');
  if(weightsParam){
    for(const part of weightsParam.split(',')){
      const [key, value] = part.split(':');
      if(Object.prototype.hasOwnProperty.call(DEFAULT_WEIGHTS, key)) weights[key] = clampWeight(value);
    }
  }
  if(searchParams.has('rings')){
    const parsed = Number(searchParams.get('rings'));
    if(Number.isFinite(parsed)) ring = Math.max(1, Math.min(6, parsed));
  }
  const era = searchParams.get('era');
  const titles = searchParams.get('titles');
  if(era && ctx.ERA_PRESETS[era]){
    selectedGames = new Set(ctx.ERA_PRESETS[era]);
    eraPreset = era;
  }else if(titles){
    const wanted = new Set(titles.split(',').map(t => t.trim()).filter(t => ctx.allGames.includes(t)));
    if(wanted.size){
      selectedGames = wanted;
      eraPreset = null;
    }
  }
  return {weights, enabled, ring, selectedGames, eraPreset};
}

function maxFinite(values){
  const vals = values.filter(v => Number.isFinite(v));
  return vals.length ? Math.max(...vals) : null;
}
function scoreFromMaxValues(values){
  const max = maxFinite(values) || 0;
  return value => {
    if(!Number.isFinite(value) || !max) return null;
    return Math.max(0, (value / max) * 100);
  };
}
function titleResumePeakValue(candidate, ring){
  return candidate.titleAdj + candidate.titleChamps * (ring - 1);
}
function peakFromCandidates(candidates, scales, ring){
  let best = null;
  for(const candidate of candidates || []){
    const resumeInput = titleResumePeakValue(candidate, ring);
    const resumeScore = scales.titleResumePeak(resumeInput) ?? 50;
    const skillScore = scales.titleSkillPeak(candidate.skillPoints) ?? 50;
    const score = (resumeScore + skillScore) / 2;
    const result = {...candidate, resumeInput, resumeScore, skillScore, score};
    if(!best || result.score > best.score) best = result;
  }
  return best || {score:50, game:'-', resumeInput:0, resumeScore:50, skillScore:50};
}

export function activeWeights(weights, enabled){
  const active = CRITERIA.filter(c => enabled[c.key] && weights[c.key] > 0);
  const total = active.reduce((sum,c) => sum + weights[c.key], 0);
  return active.map(c => ({...c, share: total ? weights[c.key] / total : 0, weight:weights[c.key]}));
}

// Full recompute for one config. Returns ranked rows (each with per-lane 0-100
// scores, the raw stats behind them, and the winning peak candidate) plus the
// era-leader scales the lanes were normalized against.
export function computeGoat(ctx, consensusByPlayer, config){
  const {selectedGames, ring} = config;
  const selectedList = ctx.allGames.filter(g => selectedGames.has(g));
  const mbar = selectedList.length
    ? selectedList.reduce((sum,g) => sum + (ctx.gameInfo.get(g)?.denom || 0), 0) / selectedList.length
    : 0;

  const consensusFor = p => {
    const rows = (consensusByPlayer.get(playerKey(p.name)) || []).filter(r => selectedGames.has(r.game));
    if(!rows.length) return null;
    const totalPoints = rows.reduce((sum,r) => sum + r.points, 0);
    const bestRank = Math.min(...rows.map(r => r.rank));
    const top3 = rows.filter(r => r.rank <= 3).length;
    const top5 = rows.filter(r => r.rank <= 5).length;
    return {
      rows,
      rankedTitles:rows.length,
      totalPoints,
      quality:totalPoints / rows.length,
      bestRank,
      bestRankScore:31 - bestRank,
      top3Rate:top3 / rows.length,
      top5Rate:top5 / rows.length,
    };
  };

  const cache = new Map();
  const statsFor = p => {
    if(cache.has(p.name)) return cache.get(p.name);
    const seasons = (p.seasons || []).filter(s => selectedGames.has(s.game));
    const placementTitles = new Set((p.placements || [])
      .filter(row => selectedGames.has(row.game) && Number(row.events || 0) > 0)
      .map(row => row.game)).size;
    const share = seasons.reduce((sum,s) => sum + (s.majors ? s.wins / s.majors : 0), 0);
    const adj = share * mbar;
    const champs = (p.champ_events || []).filter(ev => selectedGames.has(ctx.eventGame.get(ev.event))).length;
    const consensus = consensusFor(p);
    const seasonByGame = new Map(seasons.map(s => [s.game, s]));
    const consensusByGame = new Map((consensus?.rows || []).map(row => [row.game, row]));
    const champsByGame = new Map();
    for(const ev of p.champ_events || []){
      const game = ctx.eventGame.get(ev.event);
      if(selectedGames.has(game)) champsByGame.set(game, (champsByGame.get(game) || 0) + 1);
    }
    const titlePeaks = selectedList
      .filter(game => seasonByGame.has(game) || consensusByGame.has(game))
      .map(game => {
        const season = seasonByGame.get(game);
        const consensusRow = consensusByGame.get(game);
        return {
          game,
          titleAdj: season?.majors ? (season.wins / season.majors) * mbar : 0,
          titleWins: season?.wins || 0,
          titleMajors: season?.majors || 0,
          titleChamps: champsByGame.get(game) || 0,
          skillPoints: consensusRow?.points,
          consensusRank: consensusRow?.rank,
        };
      });
    const out = {
      seasons,
      consensus,
      adj,
      champs,
      titles:placementTitles,
      winningTitles:seasons.length,
      titlePeaks,
    };
    cache.set(p.name, out);
    return out;
  };

  const titleCandidates = ctx.players.flatMap(p => statsFor(p).titlePeaks.map(c => ({...c, owner:p.name})));
  const resumeValues = ctx.players.map(p => {
    const s = statsFor(p);
    return s.adj + s.champs * (ring - 1);
  });
  const consensusValues = ctx.players.map(p => statsFor(p).consensus?.totalPoints);
  const titleValues = ctx.players.map(p => statsFor(p).titles);
  const titleResumeValues = titleCandidates.map(candidate => titleResumePeakValue(candidate, ring));
  const titleSkillValues = titleCandidates.map(candidate => candidate.skillPoints);
  // the player who owns each lane's max — the explain layer names the person a
  // lane is scaled against, not just the number
  const leaderName = (values, names) => {
    let best = null, name = null;
    values.forEach((v, i) => {
      if(Number.isFinite(v) && (best === null || v > best)){ best = v; name = names[i]; }
    });
    return name;
  };
  const playerNames = ctx.players.map(p => p.name);
  const candidateOwners = titleCandidates.map(c => c.owner);
  const scales = {
    ringBonusResume: scoreFromMaxValues(resumeValues),
    consensusTotal: scoreFromMaxValues(consensusValues),
    titles: scoreFromMaxValues(titleValues),
    titleResumePeak: scoreFromMaxValues(titleResumeValues),
    titleSkillPeak: scoreFromMaxValues(titleSkillValues),
    maxes:{
      resume:maxFinite(resumeValues),
      skill:maxFinite(consensusValues),
      longevity:maxFinite(titleValues),
      titleResumePeak:maxFinite(titleResumeValues),
      titleSkillPeak:maxFinite(titleSkillValues),
    },
    leaders:{
      resume:leaderName(resumeValues, playerNames),
      skill:leaderName(consensusValues, playerNames),
      longevity:leaderName(titleValues, playerNames),
      titleResumePeak:leaderName(titleResumeValues, candidateOwners),
      titleSkillPeak:leaderName(titleSkillValues, candidateOwners),
      peak:null,
    },
  };

  const active = activeWeights(config.weights, config.enabled);
  const scored = ctx.players.map(p => {
    const s = statsFor(p);
    const lane = {
      resume: scales.ringBonusResume(s.adj + s.champs * (ring - 1)) ?? 50,
      skill: scales.consensusTotal(s.consensus?.totalPoints) ?? 50,
      longevity: scales.titles(s.titles) ?? 50,
      peak: peakFromCandidates(s.titlePeaks, scales, ring).score,
    };
    const score = active.length ? active.reduce((sum,c) => sum + lane[c.key] * c.share, 0) : 0;
    return {player:p, stats:s, lane, score, peakDetail:peakFromCandidates(s.titlePeaks, scales, ring)};
  });
  let bestPeak = -Infinity;
  for(const row of scored){
    if(row.lane.peak > bestPeak){ bestPeak = row.lane.peak; scales.leaders.peak = row.player.name; }
  }
  const rows = scored
    .filter(row => row.stats.seasons.length || row.stats.consensus)
    .sort((a,b) => b.score - a.score || b.stats.adj - a.stats.adj)
    .map((row, i) => ({...row, goatRank:i + 1}));

  return {rows, scales, active, mbar};
}
