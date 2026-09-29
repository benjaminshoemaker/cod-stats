// Shared season semantics for Insights. Winning seasons alone cannot describe
// a career: placements also retain zero-win participation. Missing participation
// is left explicit, rather than inferred from the first/last appearance.
export function careerSeasons(D, name){
  const player = D.players[name];
  if(!player) return [];
  const wins = new Map(player.seasons.map(s => [s.game, s]));
  const places = new Map((player.placements || []).map(s => [s.game, s]));
  let cum = 0, active = 0;
  const rows = D.meta.seasonOrder.map((game, idx) => {
    const season = wins.get(game), placement = places.get(game);
    const played = Boolean(season?.wins || placement?.events);
    const share = season ? season.wins / season.majors : 0;
    cum += share * (D.meta.referenceMajors || 10);
    if(played) active++;
    return {season:game, idx, played, active:played ? active : null,
      wins:season?.wins || 0, events:placement?.events || season?.events?.length || 0,
      share, cum};
  });
  const first = rows.findIndex(s => s.played);
  if(first < 0) return [];
  const last = rows.findLastIndex(s => s.played);
  return rows.slice(first, last + 1);
}

// Equal weight per title, including zero-win titles in a consecutive window.
// Require a complete three-title window within the observed career.
export function careerPeak(seasons, windowSize = 1){
  if(seasons.length < windowSize) return null;
  let best = null;
  for(let i = 0; i <= seasons.length - windowSize; i++){
    const window = seasons.slice(i, i + windowSize);
    const share = window.reduce((sum, s) => sum + s.share, 0) / windowSize;
    if(!best || share > best.share) best = {share, seasons:window};
  }
  return best;
}
