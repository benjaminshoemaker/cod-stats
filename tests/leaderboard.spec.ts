import { test, expect } from '@playwright/test';

const COLUMN_ORDER = ['adjRank', 'name', 'adjusted', 'peak', 'eras', 'rawRank', 'delta', 'raw', 'winsChange', 'champs'];

test.describe('leaderboard', () => {
  test('loads every leaderboard player', async ({ page }) => {
    await page.goto('/index.html');
    const expected = await page.evaluate(() => (window as any).APP_DATA.leaderboard.length);
    expect(expected).toBeGreaterThanOrEqual(50);
    await expect(page.locator('#table .tabulator-row')).toHaveCount(expected);
  });

  test('columns are in the expected order', async ({ page }) => {
    await page.goto('/index.html');
    const fields = await page.$$eval(
      '#table .tabulator-header .tabulator-col[tabulator-field]',
      els => els.filter(e => (e as HTMLElement).offsetWidth > 0).map(e => e.getAttribute('tabulator-field')),
    );
    expect(fields).toEqual(COLUMN_ORDER);   // adjWeighted is hidden until the ring slider is engaged
  });

  test('header is sticky to the window', async ({ page }) => {
    await page.goto('/index.html');
    const pos = await page.$eval('#table .tabulator-header', el => getComputedStyle(el).position);
    expect(pos).toBe('sticky');
  });

  test('URL state (sort, eras, search) round-trips on load', async ({ page }) => {
    await page.goto('/index.html?eras=post&sort=raw&dir=desc&q=s');
    await expect(page.locator('.eramenu .colmenu-btn')).toContainText('Post-BO2');
    await expect(page.locator('#search')).toHaveValue('s');
    // only players containing "s" remain
    const names = await page.$$eval('#table .tabulator-cell[tabulator-field="name"]', els => els.map(e => e.textContent || ''));
    expect(names.length).toBeGreaterThan(0);
    for (const n of names) expect(n.toLowerCase()).toContain('s');
  });
});

test.describe('era filter', () => {
  test('recompute reproduces the baked leaderboard exactly (All & Post-BO2 oracle)', async ({ page }) => {
    await page.goto('/index.html');
    const bad = await page.evaluate(() => {
      const D = (window as any).APP_DATA;
      const cr = (window as any).computeRows as (s: Set<string>) => any[];
      const all = new Set<string>(D.meta.seasonOrder);
      const post = new Set<string>(D.meta.seasonOrder.filter((g: string) => !D.meta.preBo2.includes(g)));
      const byAll = Object.fromEntries(cr(all).map((r: any) => [r.name, r]));
      const byPost = Object.fromEntries(cr(post).map((r: any) => [r.name, r]));
      const out: string[] = [];
      for (const lb of D.leaderboard) {
        const a = byAll[lb.name], p = byPost[lb.name];
        if (!a) { out.push(`${lb.name} missing from All`); continue; }
        if (a.adjRank !== lb.adjRank) out.push(`${lb.name} adjRank`);
        if (a.rawRank !== lb.rawRank) out.push(`${lb.name} rawRank`);
        if (Math.abs(a.adjusted - lb.adjAll) > 0.011) out.push(`${lb.name} adjAll`);
        if (a.champs !== lb.champs) out.push(`${lb.name} champs`);
        // pre-BO2-only players are (correctly) dropped from the post view; ranks of
        // survivors are unaffected since dropped players have share 0.
        if (p) {
          if (p.adjRank !== lb.postRank) out.push(`${lb.name} postRank`);
          if (Math.abs(p.adjusted - lb.adjPost) > 0.011) out.push(`${lb.name} adjPost`);
        } else if (lb.adjPost > 0.011) {
          out.push(`${lb.name} dropped from post but adjPost=${lb.adjPost}`);
        }
      }
      return out;
    });
    expect(bad).toEqual([]);
  });

  test('CDL preset recomputes ranks and round-trips via URL', async ({ page }) => {
    await page.goto('/index.html');
    await page.locator('.eramenu .colmenu-btn').click();
    await page.locator('.era-preset[data-preset="cdl"]').click();
    await expect(page).toHaveURL(/eras=cdl/);
    // CDL-era leader is aBeZy (career #3), i.e. a genuine recompute, not row-hiding
    const first = page.locator('#table .tabulator-row').first();
    await expect(first.locator('[tabulator-field="name"]')).toHaveText('aBeZy');
    // reload from the URL restores the CDL selection
    await page.goto('/index.html?eras=cdl');
    await expect(page.locator('.eramenu .colmenu-btn')).toContainText('CDL');
  });

  test('per-title checkboxes produce a custom (t:) selection', async ({ page }) => {
    await page.goto('/index.html');
    await page.locator('.eramenu .colmenu-btn').click();
    // uncheck one title from the default "all" set → custom selection (colon is URL-encoded)
    await page.locator('.eramenu-panel input[data-title]').first().uncheck();
    await expect(page).toHaveURL(/eras=t(:|%3A)/);
  });

  test('custom selection round-trips by stable slug; malformed t: falls back to All', async ({ page }) => {
    await page.goto('/index.html?eras=t:blackops2-ghosts');
    const expected = await page.evaluate(() =>
      (window as any).computeRows(new Set(['Black Ops 2', 'Ghosts']), 1).length);
    await expect(page.locator('#table .tabulator-row')).toHaveCount(expected);
    await expect(page.locator('.eramenu .colmenu-btn')).toContainText('2 titles');
    // malformed / empty custom token must NOT silently select the first title — fall back to All
    await page.goto('/index.html?eras=t:');
    await expect(page.locator('.eramenu .colmenu-btn')).toContainText('All');
  });
});

test.describe('filters + url state', () => {
  test('URL is the sole source of truth — the bare path loads defaults', async ({ page }) => {
    await page.goto('/index.html?eras=cdl&rings=3&hide=peak');
    await expect(page.locator('.eramenu .colmenu-btn')).toContainText('CDL');
    // reload the bare path — must be defaults, not the previous selection (no localStorage carryover)
    await page.goto('/index.html');
    await expect(page.locator('.eramenu .colmenu-btn')).toContainText('All');
    await expect(page.locator('#ringw-val')).toHaveText('×1');
    await expect(page.locator('#table .tabulator-col[tabulator-field="peak"]')).toBeVisible();
    const total = await page.evaluate(() => (window as any).APP_DATA.leaderboard.length);
    await expect(page.locator('#table .tabulator-row')).toHaveCount(total);
  });

  test('"Clear filters" clears the URL and resets everything', async ({ page }) => {
    await page.goto('/index.html?eras=cdl&rings=3&sort=raw&dir=desc');
    const clear = page.locator('#clearfilters');
    await expect(clear).toBeVisible();
    await clear.click();
    await expect(page).toHaveURL(/\/index\.html$/);   // query string gone
    await expect(page.locator('.eramenu .colmenu-btn')).toContainText('All');
    await expect(clear).toBeHidden();                 // nothing active → hidden
  });

  test('Eras "Reset" returns the era filter to all', async ({ page }) => {
    await page.goto('/index.html?eras=cdl');
    await page.locator('.eramenu .colmenu-btn').click();
    await page.locator('.era-preset[data-preset="all"]').click();   // the "Reset" button
    await expect(page.locator('.eramenu .colmenu-btn')).toContainText('All');
    await expect(page).not.toHaveURL(/eras=/);
  });
});

test.describe('champs weighting', () => {
  test('ring slider reveals the weighted column and updates the URL', async ({ page }) => {
    await page.goto('/index.html');
    await expect(page.locator('#table .tabulator-col[tabulator-field="adjWeighted"]')).toBeHidden();
    await page.locator('#ringw-range').evaluate((el, v) => {
      (el as HTMLInputElement).value = String(v);
      el.dispatchEvent(new Event('input', { bubbles: true }));
    }, 4);
    await expect(page).toHaveURL(/rings=4/);
    await expect(page.locator('#table .tabulator-col[tabulator-field="adjWeighted"]')).toBeVisible();
  });

  test('weighting = adjusted + champs×(N−1) and re-ranks by it (URL restore)', async ({ page }) => {
    await page.goto('/index.html?rings=4');
    const bad = await page.evaluate(() => {
      const cr = (window as any).computeRows as (s: Set<string>, n?: number) => any[];
      const D = (window as any).APP_DATA;
      const all = new Set<string>(D.meta.seasonOrder);
      const rows = cr(all, 4);
      const base = Object.fromEntries(cr(all, 1).map((r: any) => [r.name, r]));
      const out: string[] = [];
      for (const r of rows) {
        const b = base[r.name];
        const expected = Math.round((b.adjusted + b.champs * 3) * 100) / 100;   // N-1 = 3
        if (Math.abs(r.adjWeighted - expected) > 0.001) out.push(`${r.name} weighted ${r.adjWeighted}!=${expected}`);
      }
      // #1 by weighted rank must hold the max weighted total (re-ranked, not base order)
      const maxW = Math.max(...rows.map((r: any) => r.adjWeighted));
      const top = rows.slice().sort((a: any, b: any) => a.adjRank - b.adjRank)[0];
      if (Math.abs(top.adjWeighted - maxW) > 0.001) out.push('rank #1 is not the max weighted total');
      return out;
    });
    expect(bad).toEqual([]);
  });

  test('ring-weighted ranking is exact, not rounded (regression guard)', async ({ page }) => {
    await page.goto('/index.html');
    const res = await page.evaluate(() => {
      const D = (window as any).APP_DATA;
      const cr = (window as any).computeRows as (s: Set<string>, n?: number) => any[];
      const all = new Set<string>(D.meta.seasonOrder);
      const N = 3;
      // independent exact weighted key (BigInt), derived straight from D.players
      const denom: Record<string, number> = {}; D.games.forEach((g: any) => denom[g.game] = g.denom);
      const games = D.meta.seasonOrder as string[];
      const denomSum = games.reduce((a, g) => a + denom[g], 0), G = games.length;
      const gcd = (a: bigint, b: bigint): bigint => { a = a < 0n ? -a : a; b = b < 0n ? -b : b; while (b) { const t = a % b; a = b; b = t; } return a; };
      const lcm = (a: bigint, b: bigint) => a / gcd(a, b) * b;
      const L = games.reduce((acc, g) => lcm(acc, BigInt(denom[g])), 1n);
      const key: Record<string, bigint> = {};
      for (const name in D.players) {
        const p = D.players[name];
        const sel = p.seasons.filter((s: any) => all.has(s.game));
        if (sel.reduce((a: number, s: any) => a + s.wins, 0) === 0) continue;
        const numer = sel.reduce((a: bigint, s: any) => a + BigInt(s.wins) * (L / BigInt(s.majors)), 0n);
        const won = new Set<string>(); sel.forEach((s: any) => s.events.forEach((e: any) => won.add(e.event)));
        const champs = (p.champ_events || []).filter((c: any) => won.has(c.event)).length;
        key[name] = numer * BigInt(denomSum) + BigInt(champs) * BigInt(N - 1) * L * BigInt(G);
      }
      const rows = cr(all, N);
      let mismatch = 0, roundedDiffers = false;
      for (const r of rows) {
        const exactRank = 1 + rows.filter(o => key[o.name] > key[r.name]).length;
        if (r.adjRank !== exactRank) mismatch++;
        const roundedRank = 1 + rows.filter(o => o.adjWeighted > r.adjWeighted).length;
        if (roundedRank !== exactRank) roundedDiffers = true;
      }
      return { mismatch, roundedDiffers };
    });
    expect(res.mismatch).toBe(0);          // computeRows ranks by the exact weighted total
    expect(res.roundedDiffers).toBe(true); // and a naive rounded ranking would differ — proves we're exact
  });
});

test.describe('column selector', () => {
  test('hiding a column updates the URL and the header', async ({ page }) => {
    await page.goto('/index.html');
    await expect(page.locator('#table .tabulator-col[tabulator-field="champs"]')).toBeVisible();
    await page.locator('#colmenu .colmenu-btn').click();
    await page.locator('.colmenu-panel input[data-field="champs"]').uncheck();
    await expect(page).toHaveURL(/hide=champs/);
    await expect(page.locator('#table .tabulator-col[tabulator-field="champs"]')).toBeHidden();
  });

  test('hidden columns restore from the URL on load', async ({ page }) => {
    await page.goto('/index.html?hide=champs,peak');
    await expect(page.locator('#table .tabulator-col[tabulator-field="champs"]')).toBeHidden();
    await expect(page.locator('#table .tabulator-col[tabulator-field="peak"]')).toBeHidden();
    await expect(page.locator('#table .tabulator-col[tabulator-field="adjusted"]')).toBeVisible();
    await page.locator('#colmenu .colmenu-btn').click();
    await expect(page.locator('.colmenu-panel input[data-field="champs"]')).not.toBeChecked();
    await expect(page.locator('.colmenu-panel input[data-field="adjusted"]')).toBeChecked();
  });

  test('Player column stays fixed (not offered in the menu)', async ({ page }) => {
    await page.goto('/index.html');
    await page.locator('#colmenu .colmenu-btn').click();
    await expect(page.locator('.colmenu-panel input[data-field="name"]')).toHaveCount(0);
  });

  test('hiding columns narrows the table (resizes, no ballooning column)', async ({ page }) => {
    await page.goto('/index.html');
    const width = () => page.evaluate(() =>
      (document.querySelector('#table .tabulator-table') as HTMLElement).offsetWidth);
    const full = await width();
    await page.locator('#colmenu .colmenu-btn').click();
    for (const f of ['rawRank', 'delta', 'winsChange', 'peak', 'eras']) {
      await page.locator(`.colmenu-panel input[data-field="${f}"]`).uncheck();
    }
    const reduced = await width();
    expect(reduced).toBeLessThan(full);   // table shrinks to its remaining columns
  });
});

test.describe('desktop layout', () => {
  test('table sizes to content and never overflows the container', async ({ page }) => {
    test.skip(test.info().project.name !== 'desktop', 'desktop only');
    await page.goto('/index.html');
    const { inner, holder } = await page.evaluate(() => {
      const t = document.querySelector('#table .tabulator-table') as HTMLElement;
      const h = document.querySelector('#table .tabulator-tableholder') as HTMLElement;
      return { inner: t.offsetWidth, holder: h.clientWidth };
    });
    // fitData: the table is as wide as its columns, and fits within the container
    expect(inner).toBeLessThanOrEqual(holder + 2);
    expect(inner).toBeGreaterThan(holder * 0.6);
  });
});

test.describe('mobile layout', () => {
  test('all columns reachable via horizontal scroll', async ({ page }) => {
    test.skip(test.info().project.name !== 'mobile', 'mobile only');
    await page.goto('/index.html');
    const { sw, cw } = await page.evaluate(() => {
      const h = document.querySelector('#table .tabulator-tableholder') as HTMLElement;
      return { sw: h.scrollWidth, cw: h.clientWidth };
    });
    expect(sw).toBeGreaterThan(cw); // overflow exists → swipe to see the rest
  });

  test('rank column is compact (not wasting horizontal space)', async ({ page }) => {
    test.skip(test.info().project.name !== 'mobile', 'mobile only');
    await page.goto('/index.html');
    const w = await page.$eval('#table .tabulator-header .tabulator-col[tabulator-field="adjRank"]', el => (el as HTMLElement).offsetWidth);
    expect(w).toBeLessThan(80);
  });

  test('swipe hint is shown', async ({ page }) => {
    test.skip(test.info().project.name !== 'mobile', 'mobile only');
    await page.goto('/index.html');
    await expect(page.locator('.scrollhint')).toBeVisible();
  });
});

test.describe('pages', () => {
  test('player page renders wins + championships (aBeZy regression guard)', async ({ page }) => {
    await page.goto('/player.html?p=aBeZy');
    await expect(page.getByRole('heading', { name: 'aBeZy', exact: true })).toBeVisible();
    await expect(page.getByText('Call of Duty World Champion')).toBeVisible(); // champs > 0
    await expect(page.getByRole('heading', { name: /Every major win \(14\)/ })).toBeVisible(); // raw wins reconstructed
  });

  test('seasons and methodology pages load', async ({ page }) => {
    await page.goto('/games.html');
    await expect(page.getByRole('heading', { name: /Seasons/ })).toBeVisible();
    await page.goto('/methodology.html');
    await expect(page.getByRole('heading', { name: /Why weight/ })).toBeVisible();
  });

  test('peak-vs-longevity scatter renders dots', async ({ page }) => {
    await page.goto('/scatter.html');
    await expect(page.getByRole('heading', { name: /Peak vs\.? Longevity/ })).toBeVisible();
    // every leaderboard player with wins should be a dot
    const expected = await page.evaluate(() => (window as any).APP_DATA.leaderboard.length);
    await expect(page.locator('svg.scatter circle.dot')).toHaveCount(expected);
  });

  test('Visualizations nav dropdown lists all four charts', async ({ page }) => {
    await page.goto('/index.html');
    await page.click('.navdrop-btn');
    const links = await page.$$eval('.navdrop-menu a', as => as.map(a => (a as HTMLAnchorElement).getAttribute('href')));
    expect(links).toEqual(['scatter.html', 'heatmap.html', 'trajectory.html']);
  });

  test('viz pages render their SVG without JS errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', e => errors.push(e.message));
    for (const [file, sel, heading] of [
      ['heatmap.html', 'svg.hm rect.cell', /Dominance heatmap/],
      ['trajectory.html', 'svg.tj path.vis', /Career trajectories/],
    ] as [string, string, RegExp][]) {
      await page.goto('/' + file);
      await expect(page.getByRole('heading', { name: heading })).toBeVisible();
      expect(await page.locator(sel).count()).toBeGreaterThan(0);
    }
    expect(errors).toEqual([]);
  });

  test('heatmap marks championship seasons with a gold dot', async ({ page }) => {
    await page.goto('/heatmap.html');
    // champions exist in the top-16, so at least one gold marker must render
    expect(await page.locator('svg.hm circle[fill="#b8860b"]').count()).toBeGreaterThan(0);
  });

  test('trajectory picker: Clear empties the highlight, presets change it', async ({ page }) => {
    await page.goto('/trajectory.html');
    await expect(page.locator('svg.tj g.line.sel')).toHaveCount(8);       // default Top 8
    await page.click('.segbtn[data-preset="clear"]');
    await expect(page.locator('svg.tj g.line.sel')).toHaveCount(0);
    await page.click('.segbtn[data-preset="champ"]');
    await expect(page.locator('svg.tj g.line.sel')).toHaveCount(8);
    // every highlighted player keeps a removable chip
    expect(await page.locator('#chips .chip').count()).toBe(8);
  });

  test('BO7 season page shows in-progress weighting (1/6)', async ({ page }) => {
    await page.goto('/game.html?g=Black%20Ops%207');
    await expect(page.getByText(/in progress/).first()).toBeVisible();
    await expect(page.getByText('1 / 6')).toBeVisible(); // 6 scheduled majors (Challengers Finals dropped), not the 4 played
  });

  test('exact ties share a leaderboard rank (aBeZy & Simp both #3)', async ({ page }) => {
    await page.goto('/index.html');
    const ranks = await page.$$eval('#table .tabulator-cell[tabulator-field="adjRank"]', els => els.map(e => e.textContent?.trim()));
    expect(ranks.filter(r => r === '3')).toHaveLength(2);
    expect(ranks).not.toContain('4'); // competition ranking: 1,2,3,3,5,…
  });

  test('changelog renders entries incl. the MW methodology change', async ({ page }) => {
    await page.goto('/changelog.html');
    await expect(page.getByRole('heading', { name: 'Changelog', exact: true })).toBeVisible();
    await expect(page.locator('.cl-entry').first()).toBeVisible();
    await expect(page.getByRole('heading', { name: /Modern Warfare 2019 scored by opportunity/ })).toBeVisible();
  });
});
