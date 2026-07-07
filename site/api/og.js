import { ImageResponse } from '@vercel/og';
import { computeRows, eraContext } from '../assets/rank.js';
import D from '../data.json';

export const config = { runtime: 'edge' };

// hyperscript helper → satori accepts the { type, props:{ children } } element shape,
// so we avoid needing JSX transpilation (and can keep this a plain .js function file).
const h = (type, props, ...children) => ({ type, props: { ...(props || {}), children } });

const ACCENT = '#2f6df6', INK = '#0b1220', MUTED = '#64748b', GOLD = '#b8860b';
const TITLE = {
  all: 'Era-Adjusted Major Wins', post: 'Era-Adjusted Major Wins',
  prebo2: 'Who dominated the pre-BO2 era?', mlgcwl: 'Who dominated the MLG–CWL era?',
  cdl: 'Who dominated the CDL era?',
};
const LABEL = { all: 'All seasons', post: 'Post-BO2', prebo2: 'Pre-BO2', mlgcwl: 'MLG–CWL', cdl: 'CDL era' };

// a rotated square stands in for the ◆ glyph (renders without needing a special font)
const diamond = (size, color) => h('div', { style: { width: size, height: size, background: color, transform: 'rotate(45deg)', display: 'flex' } });

export default function handler(req){
  const { searchParams } = new URL(req.url);
  const ctx = eraContext(D);
  const selected = ctx.parseSelection(searchParams.get('eras')) || new Set(ctx.PRESETS.all);
  const ring = Math.min(6, Math.max(1, Math.round(+(searchParams.get('rings') || 1)) || 1));
  const rows = computeRows(D, selected, ring).sort((a, b) => a.adjRank - b.adjRank).slice(0, 5);

  const tok = ctx.selectionToken(selected);
  const title = TITLE[tok] || 'Era-Adjusted Major Wins';
  const badge = (LABEL[tok] || `${[...selected].length} titles`) + (ring > 1 ? ` · rings ×${ring}` : '');
  const val = r => (ring > 1 ? r.adjWeighted : r.adjusted);
  const max = Math.max(...rows.map(val), 1);
  const flex = extra => ({ display: 'flex', ...extra });

  const rowEl = r => h('div', { style: flex({ alignItems: 'center', margin: '7px 0' }) },
    h('div', { style: flex({ justifyContent: 'flex-end', width: 64, fontSize: 34, fontWeight: 800, color: '#94a3b8' }) }, String(r.adjRank)),
    h('div', { style: flex({ alignItems: 'center', flex: 1, marginLeft: 20, fontSize: 38, fontWeight: 700, color: INK }) },
      r.name, r.champs ? h('div', { style: flex({ marginLeft: 12 }) }, diamond(14, GOLD)) : ''),
    h('div', { style: flex({ width: 360, height: 18, background: '#eef2f7', borderRadius: 9 }) },
      h('div', { style: flex({ width: `${Math.max(6, val(r) / max * 100)}%`, height: '100%', background: ACCENT, borderRadius: 9 }) })),
    h('div', { style: flex({ justifyContent: 'flex-end', width: 96, marginLeft: 20, fontSize: 38, fontWeight: 800, color: INK }) }, val(r).toFixed(1)),
  );

  const card = h('div', { style: flex({ width: '1200px', height: '630px', background: '#fff', flexDirection: 'column', padding: '64px 72px' }) },
    h('div', { style: { position: 'absolute', top: 0, left: 0, right: 0, height: 8, background: ACCENT, display: 'flex' } }),
    h('div', { style: flex({ justifyContent: 'space-between', alignItems: 'center' }) },
      h('div', { style: flex({ alignItems: 'center', fontSize: 26, fontWeight: 700, color: INK }) },
        'Map Five', h('div', { style: flex({ margin: '0 10px' }) }, diamond(16, ACCENT)), 'Era-Adjusted Records'),
      h('div', { style: flex({ fontSize: 22, fontWeight: 600, color: '#1e40af', background: '#eef4ff', border: '1px solid #d7e3ff', borderRadius: 999, padding: '10px 22px' }) }, badge)),
    h('div', { style: flex({ fontSize: 52, fontWeight: 800, color: INK, margin: '26px 0 8px' }) }, title),
    h('div', { style: flex({ flex: 1, flexDirection: 'column', justifyContent: 'center' }) }, ...rows.map(rowEl)),
    h('div', { style: flex({ justifyContent: 'space-between', color: MUTED, fontSize: 22, marginTop: 14 }) },
      h('div', { style: flex({}) }, "Every season weighted equally · a win = its share of that season's majors"),
      h('div', { style: flex({ color: ACCENT, fontWeight: 700 }) }, 'mapfive.app')),
  );

  return new ImageResponse(card, { width: 1200, height: 630 });
}
