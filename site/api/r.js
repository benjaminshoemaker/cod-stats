import { computeRows, eraContext } from '../assets/rank.js';
import D from '../data.json';

export const config = { runtime: 'edge' };

// Share wrapper: keeps the main site fully static while giving each shared ranking a
// params-matched og:image (the /api/og card) + title/description. Scrapers read the
// meta; humans are bounced straight into the interactive leaderboard with the filters
// applied. The "Share this ranking" button links here.

const LABEL = { all: 'All seasons', post: 'Post-BO2', prebo2: 'Pre-BO2', mlgcwl: 'MLG–CWL', cdl: 'CDL era' };
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

export default function handler(req){
  const url = new URL(req.url);
  const ctx = eraContext(D);
  const selected = ctx.parseSelection(url.searchParams.get('eras')) || new Set(ctx.PRESETS.all);
  const ring = Math.min(6, Math.max(1, Math.round(+(url.searchParams.get('rings') || 1)) || 1));
  const tok = ctx.selectionToken(selected);
  const top = computeRows(D, selected, ring).sort((a, b) => a.adjRank - b.adjRank).slice(0, 3).map(r => r.name).join(', ');

  const badge = (LABEL[tok] || `${[...selected].length} titles`) + (ring > 1 ? ` · rings ×${ring}` : '');
  const title = `Era-Adjusted CoD Major Wins — ${badge}`;
  const desc = (top ? `Top: ${top}. ` : '') + 'Every season weighted equally — a win counts as its share of that season’s majors.';
  const qs = url.search;                                  // carries eras/rings/hide/sort/q
  const ogImg = esc(`${url.origin}/api/og${qs}`);
  const appUrl = esc(`${url.origin}/${qs}`);

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
<script>location.replace(${JSON.stringify(`${url.origin}/${qs}`)})</script>
<p>Redirecting to the <a href="${appUrl}">era-adjusted leaderboard</a>…</p>
</body></html>`;

  return new Response(html, { headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'public, max-age=600' } });
}
