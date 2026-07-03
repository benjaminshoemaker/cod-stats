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

  test('BO7 season page shows in-progress weighting (1/7)', async ({ page }) => {
    await page.goto('/game.html?g=Black%20Ops%207');
    await expect(page.getByText(/in progress/).first()).toBeVisible();
    await expect(page.getByText('1 / 7')).toBeVisible(); // scheduled majors, not the 4 played
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
