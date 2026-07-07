import { ImageResponse } from '@vercel/og';
import { compareShareBits } from './c.js';

export const config = { runtime: 'edge' };

// Social card for shared comparisons: each compared player's adjusted wins as a
// bar in their on-page compare color, so the unfurl *is* the verdict screenshot.

const h = (type, props, ...children) => ({ type, props: { ...(props || {}), children } });

const ACCENT = '#2563eb', INK = '#0b1220', MUTED = '#64748b', GOLD = '#b8860b';
const PLAYER_COLORS = ['#2563eb', '#059669', '#d97706', '#7c3aed'];
const flex = extra => ({ display: 'flex', ...(extra || {}) });
const diamond = (size, color) => h('div', { style: { width: size, height: size, background: color, transform: 'rotate(45deg)', display: 'flex' } });

export default function handler(req){
  const { searchParams } = new URL(req.url);
  const { rows, leader, runner, decisive } = compareShareBits(searchParams);
  const max = Math.max(...rows.map(r => r.adj), 0.1);

  const rowEl = (r, i) => h('div', { style: flex({ alignItems: 'center', margin: '9px 0' }) },
    h('div', { style: flex({ alignItems: 'center', width: 320, fontSize: 40, fontWeight: 700, color: INK }) },
      r.name, r.champs ? h('div', { style: flex({ marginLeft: 12 }) }, diamond(14, GOLD)) : ''),
    h('div', { style: flex({ flex: 1, height: 22, background: '#eef2f7', borderRadius: 11 }) },
      h('div', { style: flex({ width: `${Math.max(6, r.adj / max * 100)}%`, height: '100%', background: PLAYER_COLORS[i % PLAYER_COLORS.length], borderRadius: 11 }) })),
    h('div', { style: flex({ justifyContent: 'flex-end', width: 110, marginLeft: 20, fontSize: 40, fontWeight: 800, color: INK }) }, r.adj.toFixed(1)),
    h('div', { style: flex({ justifyContent: 'flex-end', width: 90, marginLeft: 12, fontSize: 24, fontWeight: 600, color: MUTED }) }, r.rank ? `#${r.rank}` : ''),
  );

  const title = runner
    ? (decisive ? `${leader.name} leads, era-adjusted` : 'Dead even, era-adjusted')
    : `${leader.name}, era-adjusted`;

  const card = h('div', { style: flex({ width: '1200px', height: '630px', background: '#fff', flexDirection: 'column', padding: '64px 72px' }) },
    h('div', { style: { position: 'absolute', top: 0, left: 0, right: 0, height: 8, background: ACCENT, display: 'flex' } }),
    h('div', { style: flex({ justifyContent: 'space-between', alignItems: 'center' }) },
      h('div', { style: flex({ alignItems: 'center', fontSize: 26, fontWeight: 700, color: INK }) },
        'CoD Major Wins', h('div', { style: flex({ margin: '0 10px' }) }, diamond(16, ACCENT)), 'Player Compare'),
      h('div', { style: flex({ fontSize: 22, fontWeight: 600, color: '#1e40af', background: '#eef4ff', border: '1px solid #d7e3ff', borderRadius: 999, padding: '10px 22px' }) },
        decisive ? `+${(leader.adj - runner.adj).toFixed(1)} adjusted wins` : 'Adjusted wins')),
    h('div', { style: flex({ fontSize: 52, fontWeight: 800, color: INK, margin: '26px 0 8px' }) }, title),
    h('div', { style: flex({ flex: 1, flexDirection: 'column', justifyContent: 'center' }) }, ...rows.map(rowEl)),
    h('div', { style: flex({ justifyContent: 'space-between', color: MUTED, fontSize: 22, marginTop: 14 }) },
      h('div', { style: flex({}) }, "Every season weighted equally · a win = its share of that season's majors"),
      h('div', { style: flex({ color: ACCENT, fontWeight: 700 }) }, 'cod-stats-one.vercel.app')),
  );

  return new ImageResponse(card, { width: 1200, height: 630 });
}
