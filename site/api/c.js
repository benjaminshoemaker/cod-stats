import D from '../data.json';

export const config = { runtime: 'edge' };

// Share wrapper for the compare page: scrapers get a matchup-specific og:image
// (the /api/compare-og card) + title/description, humans are bounced straight
// into the comparison. The compare page's "Copy link" button links here.

const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const BY_LOWER = new Map(Object.keys(D.players).map(n => [n.toLowerCase(), n]));
const ADJ_RANK = new Map(D.leaderboard.map(r => [r.name, r.adjRank]));

function canonical(name){
  const raw = String(name || '').trim();
  if(!raw) return null;
  if(Object.prototype.hasOwnProperty.call(D.players, raw)) return raw;
  return BY_LOWER.get(raw.toLowerCase()) || null;
}

export function compareShareBits(searchParams){
  const raw = searchParams.getAll('p').flatMap(v => v.split(',')).map(v => v.trim()).filter(Boolean);
  const unique = [...new Set(raw.map(canonical).filter(Boolean))].slice(0, 4);
  const names = unique.length ? unique : ['Shotzzy', 'HyDra'];
  const rows = names.map(n => ({
    name: n,
    adj: D.players[n].adj_all,
    raw: D.players[n].raw,
    champs: D.players[n].champs,
    rank: ADJ_RANK.get(n) || null,
  }));
  const sorted = [...rows].sort((a, b) => b.adj - a.adj);
  const leader = sorted[0], runner = sorted[1] || null;
  const decisive = runner && leader.adj - runner.adj >= 0.05;
  return { names, rows, leader, runner, decisive };
}

export default function handler(req){
  const url = new URL(req.url);
  const { names, leader, runner, decisive } = compareShareBits(url.searchParams);

  const title = `${names.join(' vs ')} · Era-Adjusted CoD Compare`;
  const verdictLine = runner
    ? (decisive
      ? `${leader.name} leads on adjusted wins, ${leader.adj.toFixed(1)} to ${runner.adj.toFixed(1)}. `
      : `Dead even on adjusted wins at ${leader.adj.toFixed(1)}. `)
    : '';
  const desc = verdictLine + 'Adjusted wins weight every season equally · a win counts as its share of that season’s majors.';
  const qs = url.search;                                  // carries p/rows
  const ogImg = esc(`${url.origin}/api/compare-og${qs}`);
  const appUrl = esc(`${url.origin}/compare.html${qs}`);

  const html = `<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(title)}</title>
<meta property="og:type" content="website">
<meta property="og:title" content="${esc(title)}">
<meta property="og:description" content="${esc(desc)}">
<meta property="og:image" content="${ogImg}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="${esc(title)}">
<meta name="twitter:description" content="${esc(desc)}">
<meta name="twitter:image" content="${ogImg}">
<meta http-equiv="refresh" content="0;url=${appUrl}">
</head><body>
<script>location.replace(${JSON.stringify(`${url.origin}/compare.html${qs}`)})</script>
<p>Redirecting to the <a href="${appUrl}">player comparison</a>…</p>
</body></html>`;

  return new Response(html, { headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'public, max-age=600' } });
}
