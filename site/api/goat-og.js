import { ImageResponse } from '@vercel/og';
import { goatShareBits } from './g.js';

export const config = { runtime: 'edge' };

// Social card for shared GOAT Builder lists: top 5 of the exact ranking the
// shared settings produce, with the builder's lane-colored contribution bars.

const h = (type, props, ...children) => ({ type, props: { ...(props || {}), children } });

const ACCENT = '#2563eb', INK = '#0b1220', MUTED = '#64748b';
const LANE_COLORS = { resume:'#2563eb', skill:'#047857', longevity:'#b45309', peak:'#6d28d9' };
const flex = extra => ({ display: 'flex', ...(extra || {}) });
const diamond = (size, color) => h('div', { style: { width: size, height: size, background: color, transform: 'rotate(45deg)', display: 'flex' } });

export default function handler(req){
  const { searchParams } = new URL(req.url);
  const { rows, active, isDefault, badge, weightsText } = goatShareBits(searchParams);
  const top = rows.slice(0, 5);

  const rowEl = r => h('div', { style: flex({ alignItems: 'center', margin: '7px 0' }) },
    h('div', { style: flex({ justifyContent: 'flex-end', width: 64, fontSize: 34, fontWeight: 800, color: '#94a3b8' }) }, String(r.goatRank)),
    h('div', { style: flex({ alignItems: 'center', flex: 1, marginLeft: 20, fontSize: 38, fontWeight: 700, color: INK }) },
      r.player.name, r.stats.champs ? h('div', { style: flex({ marginLeft: 12 }) }, diamond(14, '#b8860b')) : ''),
    h('div', { style: flex({ width: 360, height: 18, background: '#eef2f7', borderRadius: 9, overflow: 'hidden' }) },
      ...active.map(c => h('div', { style: flex({
        width: `${Math.max(1, r.lane[c.key] * c.share / 100 * 100)}%`,
        height: '100%', background: LANE_COLORS[c.key],
      }) }))),
    h('div', { style: flex({ justifyContent: 'flex-end', width: 96, marginLeft: 20, fontSize: 38, fontWeight: 800, color: INK }) }, r.score.toFixed(1)),
  );

  const card = h('div', { style: flex({ width: '1200px', height: '630px', background: '#fff', flexDirection: 'column', padding: '64px 72px' }) },
    h('div', { style: { position: 'absolute', top: 0, left: 0, right: 0, height: 8, background: ACCENT, display: 'flex' } }),
    h('div', { style: flex({ justifyContent: 'space-between', alignItems: 'center' }) },
      h('div', { style: flex({ alignItems: 'center', fontSize: 26, fontWeight: 700, color: INK }) },
        'CoD Major Wins', h('div', { style: flex({ margin: '0 10px' }) }, diamond(16, ACCENT)), 'GOAT Builder'),
      h('div', { style: flex({ fontSize: 22, fontWeight: 600, color: '#1e40af', background: '#eef4ff', border: '1px solid #d7e3ff', borderRadius: 999, padding: '10px 22px' }) }, badge)),
    h('div', { style: flex({ fontSize: 52, fontWeight: 800, color: INK, margin: '26px 0 8px' }) },
      isDefault ? 'The site-default GOAT list' : 'My GOAT list'),
    top.length
      ? h('div', { style: flex({ flex: 1, flexDirection: 'column', justifyContent: 'center' }) }, ...top.map(rowEl))
      : h('div', { style: flex({ flex: 1, alignItems: 'center', fontSize: 34, color: MUTED }) }, 'No players match these settings.'),
    h('div', { style: flex({ justifyContent: 'space-between', color: MUTED, fontSize: 22, marginTop: 14 }) },
      h('div', { style: flex({}) }, `Weighted by ${weightsText}`),
      h('div', { style: flex({ color: ACCENT, fontWeight: 700 }) }, 'cod-stats-one.vercel.app')),
  );

  return new ImageResponse(card, { width: 1200, height: 630 });
}
