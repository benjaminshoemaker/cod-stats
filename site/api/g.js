import { goatContext, buildConsensusIndex, parseGoatConfig, computeGoat, activeWeights, CRITERIA, DEFAULT_WEIGHTS, DEFAULT_ENABLED, DEFAULT_RING } from '../assets/goat.js';
import D from '../data.json';
import C from '../community-consensus.json';

export const config = { runtime: 'edge' };

// Share wrapper for the GOAT Builder: scrapers get a params-matched og:image
// (the /api/goat-og card) + title/description, humans are bounced straight into
// the builder with the settings applied. The "Share list" button links here.

const ERA_LABEL = { all: 'All titles', cdl: 'CDL era', mlgCwl: 'MLG–CWL era', postBo2: 'Post-BO2', preBo2: 'Pre-BO2' };
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

export function goatShareBits(searchParams){
  const ctx = goatContext(D);
  const cfg = parseGoatConfig(searchParams, ctx);
  const consensus = buildConsensusIndex(C.consensus || C);
  const { rows } = computeGoat(ctx, consensus.byPlayer, cfg);
  const active = activeWeights(cfg.weights, cfg.enabled);
  const isDefault = cfg.ring === DEFAULT_RING && cfg.eraPreset === 'all'
    && CRITERIA.every(c => cfg.enabled[c.key] === DEFAULT_ENABLED[c.key] && cfg.weights[c.key] === DEFAULT_WEIGHTS[c.key]);
  const eraBadge = cfg.eraPreset ? ERA_LABEL[cfg.eraPreset] : `${cfg.selectedGames.size} titles`;
  const badge = eraBadge + (cfg.ring !== 1 ? ` · rings ×${cfg.ring}` : '');
  const weightsText = active.map(c => `${c.label} ${Math.round(c.share * 100)}%`).join(' · ') || 'no active criteria';
  return { cfg, rows, active, isDefault, badge, weightsText };
}

export default function handler(req){
  const url = new URL(req.url);
  const { rows, isDefault, badge, weightsText } = goatShareBits(url.searchParams);
  const top = rows.slice(0, 3).map(r => r.player.name).join(', ');

  const title = (isDefault ? 'CoD GOAT Ranking Builder' : 'My CoD GOAT List') + ` · ${badge}`;
  const desc = (top ? `Top: ${top}. ` : '') + `Weighted by ${weightsText}. Build your own list from era-adjusted wins and community skill rankings.`;
  const qs = url.search;                                  // carries criteria/weights/rings/era/titles/view/sort
  const ogImg = esc(`${url.origin}/api/goat-og${qs}`);
  const appUrl = esc(`${url.origin}/goat-builder.html${qs}`);

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
<script>location.replace(${JSON.stringify(`${url.origin}/goat-builder.html${qs}`)})</script>
<p>Redirecting to the <a href="${appUrl}">GOAT Ranking Builder</a>…</p>
</body></html>`;

  return new Response(html, { headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'public, max-age=600' } });
}
