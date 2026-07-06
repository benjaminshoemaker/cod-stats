import { test, expect } from '@playwright/test';

const COLUMN_ORDER = ['adjRank', 'name', 'adjusted', 'raw', 'winsChange', 'rawRank', 'delta', 'peak', 'eras', 'champs'];
const FULL_COLUMN_ORDER = ['adjRank', 'name', 'adjusted', 'raw', 'winConversion', 'eventsPlaced', 'avgPlace', 'winsChange', 'rawRank', 'delta', 'peak', 'eras', 'champs'];

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

  test('placement columns are opt-in and shareable', async ({ page }) => {
    await page.goto('/index.html');
    await expect(page.locator('#table .tabulator-col[tabulator-field="primaryRole"]')).toBeHidden();
    await expect(page.locator('#table .tabulator-col[tabulator-field="winConversion"]')).toBeHidden();
    await expect(page.locator('#table .tabulator-col[tabulator-field="eventsPlaced"]')).toBeHidden();
    await expect(page.locator('#table .tabulator-col[tabulator-field="avgPlace"]')).toBeHidden();

    await page.locator('#colmenu .colmenu-btn').click();
    await page.locator('.colmenu-panel input[data-field="primaryRole"]').check();
    await page.locator('.colmenu-panel input[data-field="winConversion"]').check();
    await page.locator('.colmenu-panel input[data-field="eventsPlaced"]').check();
    await page.locator('.colmenu-panel input[data-field="avgPlace"]').check();
    await expect(page).toHaveURL(/show=primaryRole%2CwinConversion%2CeventsPlaced%2CavgPlace|show=primaryRole,winConversion,eventsPlaced,avgPlace/);
    await expect(page.locator('#table .tabulator-col[tabulator-field="primaryRole"]')).toBeVisible();
    await expect(page.locator('#table .tabulator-col[tabulator-field="winConversion"]')).toBeVisible();
    await expect(page.locator('#table .tabulator-col[tabulator-field="eventsPlaced"]')).toBeVisible();
    await expect(page.locator('#table .tabulator-col[tabulator-field="avgPlace"]')).toBeVisible();
    await expect(page.locator('#table .tabulator-row').filter({ hasText: 'Scump' }).locator('.pill.role-smg')).toHaveText('SMG');
    await expect(page.locator('#table .tabulator-row').filter({ hasText: 'Shotzzy' }).locator('[tabulator-field="winConversion"]')).toHaveText('23%');

    await page.goto('/index.html?show=winConversion,eventsPlaced,avgPlace');
    const fields = await page.$$eval(
      '#table .tabulator-header .tabulator-col[tabulator-field]',
      els => els.filter(e => (e as HTMLElement).offsetWidth > 0).map(e => e.getAttribute('tabulator-field')),
    );
    expect(fields).toEqual(FULL_COLUMN_ORDER);
  });

  test('stat columns are not exposed on the leaderboard', async ({ page }) => {
    await page.goto('/index.html?hide=adjRank&show=primaryRole%2CwinConversion%2CeventsPlaced%2CavgPlace%2CskillKd%2CskillKills%2CskillDeaths%2CskillInteractions%2CskillEvents');

    for (const field of ['skillKd', 'skillKills', 'skillDeaths', 'skillInteractions', 'skillEvents']) {
      await expect(page.locator(`#table .tabulator-col[tabulator-field="${field}"]`)).toHaveCount(0);
    }

    await page.locator('#colmenu .colmenu-btn').click();
    for (const field of ['skillKd', 'skillKills', 'skillDeaths', 'skillInteractions', 'skillEvents']) {
      await expect(page.locator(`.colmenu-panel input[data-field="${field}"]`)).toHaveCount(0);
    }
    await expect(page).toHaveURL(/show=primaryRole%2CwinConversion%2CeventsPlaced%2CavgPlace|show=primaryRole,winConversion,eventsPlaced,avgPlace/);
    await expect(page).not.toHaveURL(/skillKd|skillKills|skillDeaths|skillInteractions|skillEvents/);
  });

  test('compare mode selects leaderboard players and opens compare page', async ({ page }) => {
    await page.goto('/index.html');
    await page.getByRole('button', { name: 'Compare' }).click();
    await expect(page.locator('#compare-tray')).toBeVisible();
    await page.locator('input[data-compare-name="Shotzzy"]').check();
    await page.locator('input[data-compare-name="HyDra"]').check();
    await expect(page.locator('#compare-count')).toHaveText('2 selected');
    await page.getByRole('button', { name: 'Compare selected' }).click();
    await expect(page).toHaveURL(/compare\.html\?p=Shotzzy&p=HyDra/);
    await expect(page.locator('.compare-summary thead th')).toContainText(['Metric', 'Shotzzy', 'HyDra']);
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

test.describe('insights', () => {
  test('authored-list check publishes the conclusion', async ({ page }) => {
    await page.goto('/authored-vs-community.html');
    await expect(page.getByRole('heading', { name: 'Authored lists mostly confirm the community list' })).toBeVisible();
    await expect(page.getByText('Keep the community list as the ranking.')).toBeVisible();
    await page.getByRole('button', { name: /Insights/ }).click();
    await expect(page.getByRole('link', { name: 'Authored-list check' })).toBeVisible();
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
        if (a.eventsPlaced !== lb.eventsPlaced) out.push(`${lb.name} eventsPlaced`);
        if (Math.abs(a.avgPlace - lb.avgPlace) > 0.011) out.push(`${lb.name} avgPlace`);
        if (Math.abs(a.winConversion - lb.winConversion) > 0.001) out.push(`${lb.name} winConversion`);
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

  test('placement columns recompute with era filters', async ({ page }) => {
    await page.goto('/index.html');
    const res = await page.evaluate(() => {
      const D = (window as any).APP_DATA;
      const cr = (window as any).computeRows as (s: Set<string>) => any[];
      const all = new Set<string>(D.meta.seasonOrder);
      const cdl = new Set<string>(D.meta.seasonOrder.slice(D.meta.seasonOrder.indexOf('Modern Warfare')));
      const allPlayer = cr(all).find((r: any) => r.name === 'aBeZy');
      const cdlPlayer = cr(cdl).find((r: any) => r.name === 'aBeZy');
      return {
        allEvents: allPlayer.eventsPlaced,
        dataEvents: D.players.aBeZy.events_placed,
        allAvg: allPlayer.avgPlace,
        dataAvg: D.players.aBeZy.avg_place,
        allWinConversion: allPlayer.winConversion,
        dataWinConversion: D.players.aBeZy.win_conversion,
        cdlEvents: cdlPlayer.eventsPlaced,
        cdlAvg: cdlPlayer.avgPlace,
        cdlWinConversion: cdlPlayer.winConversion,
      };
    });
    expect(res.allEvents).toBe(res.dataEvents);
    expect(Math.abs(res.allAvg - res.dataAvg)).toBeLessThan(0.011);
    expect(res.allWinConversion).toBe(res.dataWinConversion);
    expect(res.cdlEvents).toBeLessThan(res.allEvents);
    expect(res.cdlAvg).not.toBe(res.allAvg);
    expect(res.cdlWinConversion).not.toBe(res.allWinConversion);
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
    await expect(page.locator('#table .tabulator-col[tabulator-field="primaryRole"]')).toBeHidden();
    await expect(page.locator('#table .tabulator-col[tabulator-field="winConversion"]')).toBeHidden();
    await expect(page.locator('#table .tabulator-col[tabulator-field="avgPlace"]')).toBeHidden();
    await expect(page.locator('#table .tabulator-col[tabulator-field="adjusted"]')).toBeVisible();
    await page.locator('#colmenu .colmenu-btn').click();
    await expect(page.locator('.colmenu-panel input[data-field="champs"]')).not.toBeChecked();
    await expect(page.locator('.colmenu-panel input[data-field="primaryRole"]')).not.toBeChecked();
    await expect(page.locator('.colmenu-panel input[data-field="winConversion"]')).not.toBeChecked();
    await expect(page.locator('.colmenu-panel input[data-field="avgPlace"]')).not.toBeChecked();
    await expect(page.locator('.colmenu-panel input[data-field="adjusted"]')).toBeChecked();
  });

  test('Player column stays fixed (not offered in the menu)', async ({ page }) => {
    await page.goto('/index.html');
    await page.locator('#colmenu .colmenu-btn').click();
    await expect(page.locator('.colmenu-panel input[data-field="name"]')).toHaveCount(0);
  });

  test('hiding columns keeps the filled table within its container', async ({ page }) => {
    test.skip(test.info().project.name !== 'desktop', 'desktop only');
    await page.goto('/index.html');
    await page.locator('#colmenu .colmenu-btn').click();
    for (const f of ['rawRank', 'delta', 'winsChange', 'peak', 'eras']) {
      await page.locator(`.colmenu-panel input[data-field="${f}"]`).uncheck();
    }
    const metrics = await page.evaluate(() => {
      const table = document.querySelector('#table .tabulator-table') as HTMLElement;
      const holder = document.querySelector('#table .tabulator-tableholder') as HTMLElement;
      return { tableWidth: table.offsetWidth, holderWidth: holder.clientWidth, scrollWidth: holder.scrollWidth };
    });
    expect(metrics.tableWidth).toBeLessThanOrEqual(metrics.holderWidth + 2);
    expect(metrics.scrollWidth).toBeLessThanOrEqual(metrics.holderWidth + 2);
  });
});

test.describe('desktop layout', () => {
  test('default desktop table fills its container without overflow', async ({ page }) => {
    test.skip(test.info().project.name !== 'desktop', 'desktop only');
    await page.goto('/index.html');
    const { inner, holder } = await page.evaluate(() => {
      const t = document.querySelector('#table .tabulator-table') as HTMLElement;
      const h = document.querySelector('#table .tabulator-tableholder') as HTMLElement;
      return { inner: t.offsetWidth, holder: h.clientWidth };
    });
    expect(inner).toBeLessThanOrEqual(holder + 2);
    expect(inner).toBeGreaterThanOrEqual(holder - 2);
  });

  test('visible desktop header labels are not clipped', async ({ page }) => {
    test.skip(test.info().project.name !== 'desktop', 'desktop only');
    for (const path of ['/index.html', '/index.html?show=eventsPlaced,avgPlace', '/index.html?rings=3&show=eventsPlaced,avgPlace']) {
      await page.goto(path);
      const clipped = await page.$$eval('#table .tabulator-col[tabulator-field]', els =>
        els.filter(el => (el as HTMLElement).offsetParent !== null).map(el => {
          const title = el.querySelector('.tabulator-col-title') as HTMLElement | null;
          return {
            field: el.getAttribute('tabulator-field'),
            client: title?.clientWidth ?? 0,
            scroll: title?.scrollWidth ?? 0,
          };
        }).filter(col => col.scroll > col.client + 1)
      );
      expect(clipped).toEqual([]);
    }
  });

  test('visible desktop sort arrows do not crowd header text', async ({ page }) => {
    test.skip(test.info().project.name !== 'desktop', 'desktop only');
    for (const path of ['/index.html', '/index.html?rings=3&show=eventsPlaced,avgPlace']) {
      await page.goto(path);
      const crowded = await page.$$eval('#table .tabulator-col[tabulator-field]', els =>
        els.filter(el => (el as HTMLElement).offsetParent !== null).map(el => {
          const title = el.querySelector('.tabulator-col-title') as HTMLElement | null;
          const sorter = el.querySelector('.tabulator-col-sorter') as HTMLElement | null;
          if (!title || !sorter || !title.textContent?.trim()) return null;
          const range = document.createRange();
          range.selectNodeContents(title);
          const textRect = range.getBoundingClientRect();
          const sorterRect = sorter.getBoundingClientRect();
          return {
            field: el.getAttribute('tabulator-field'),
            gap: sorterRect.left - textRect.right,
          };
        }).filter((col): col is { field: string | null; gap: number } => !!col && col.gap < 4)
      );
      expect(crowded).toEqual([]);
    }
  });

  test('expanded desktop table fits without bottom horizontal scroll', async ({ page }) => {
    test.skip(test.info().project.name !== 'desktop', 'desktop only');
    await page.goto('/index.html?rings=3&show=eventsPlaced,avgPlace');
    const metrics = await page.evaluate(() => {
      const holder = document.querySelector('#table .tabulator-tableholder') as HTMLElement;
      const table = document.querySelector('#table .tabulator-table') as HTMLElement;
      const hRect = holder.getBoundingClientRect();
      const offscreen = Array.from(document.querySelectorAll('#table .tabulator-col[tabulator-field]'))
        .filter(el => (el as HTMLElement).offsetParent !== null)
        .map(el => {
          const rect = el.getBoundingClientRect();
          return {
            field: el.getAttribute('tabulator-field'),
            left: rect.left,
            right: rect.right,
          };
        })
        .filter(col => col.left < hRect.left - 1 || col.right > hRect.right + 1);
      return {
        tableWidth: table.offsetWidth,
        holderWidth: holder.clientWidth,
        scrollWidth: holder.scrollWidth,
        offscreen,
      };
    });
    expect(metrics.tableWidth).toBeLessThanOrEqual(metrics.holderWidth + 2);
    expect(metrics.scrollWidth).toBeLessThanOrEqual(metrics.holderWidth + 2);
    expect(metrics.offscreen).toEqual([]);
  });
});

test.describe('mobile layout', () => {
  test('all columns reachable via horizontal scroll', async ({ page }) => {
    test.skip(test.info().project.name !== 'mobile', 'mobile only');
    await page.goto('/index.html');
    const { sw, cw, role, label, tabIndex, enhanced } = await page.evaluate(() => {
      const h = document.querySelector('#table .tabulator-tableholder') as HTMLElement;
      return {
        sw: h.scrollWidth,
        cw: h.clientWidth,
        role: h.getAttribute('role'),
        label: h.getAttribute('aria-label'),
        tabIndex: h.tabIndex,
        enhanced: h.classList.contains('scroll-region'),
      };
    });
    expect(sw).toBeGreaterThan(cw); // overflow exists → swipe to see the rest
    expect(role).toBe('region');
    expect(label).toBe('Leaderboard table');
    expect(tabIndex).toBeGreaterThanOrEqual(0);
    expect(enhanced).toBe(true);

    const holder = page.locator('#table .tabulator-tableholder');
    await holder.evaluate(el => el.dispatchEvent(new KeyboardEvent('keydown', {key:'End', bubbles:true, cancelable:true})));
    await expect.poll(() => holder.evaluate(el => (el as HTMLElement).scrollLeft)).toBeGreaterThan(0);
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

  test('player profile URLs resolve source casing variants', async ({ page }) => {
    await page.goto('/player.html?p=ABeZy');
    await expect(page.getByRole('heading', { name: 'aBeZy', exact: true })).toBeVisible();
    await expect(page.getByRole('heading', { name: /Every major win \(14\)/ })).toBeVisible();

    await page.goto('/player.html?p=ILLeY');
    await expect(page.getByRole('heading', { name: 'iLLeY', exact: true })).toBeVisible();
  });

  test('seasons and methodology pages load', async ({ page }) => {
    await page.goto('/games.html');
    await expect(page.getByRole('heading', { name: /Seasons/ })).toBeVisible();
    await expect(page.locator('.scroll-x[role="region"][tabindex="0"][aria-label="Season major-count table"]')).toBeVisible();
    await expect(page.locator('table.data caption')).toContainText('Major count by Call of Duty season');
    await expect(page.locator('table.data th[scope="col"]')).toHaveCount(6);
    await page.goto('/methodology.html');
    await expect(page.getByRole('heading', { name: 'Methodology' })).toBeVisible();
    await expect(page.getByText('The site has several distinct evidence lanes')).toBeVisible();
    await expect(page.locator('.method-hub .method-card', { hasText: 'Era-adjusted wins' })).toHaveAttribute('href', '#era-adjustment');
    await expect(page.locator('.method-hub .method-card', { hasText: 'Formal accolades' })).toHaveAttribute('href', '#formal-accolades');
    await page.goto('/community.html');
    await expect(page.getByRole('heading', { name: 'Community Consensus' })).toBeVisible();
  });

  test('styleguide documents KOR and data-surface patterns', async ({ page }) => {
    await page.goto('/styleguide.html');
    await expect(page.getByRole('heading', { name: 'Design System' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Data surfaces' })).toHaveAttribute('href', '#data-surfaces');
    await expect(page.getByRole('link', { name: 'KOR widget' })).toHaveAttribute('href', '#kor-widget');
    await expect(page.locator('#data-surfaces .scroll-x[role="region"][tabindex="0"]')).toHaveAttribute('aria-label', 'Example analytical table');
    await expect(page.locator('#data-surfaces table.data caption')).toContainText('Example analytical table with sample context');
    await expect(page.locator('#pills .pill.role-smg')).toHaveText('SMG');
    await expect(page.locator('#kor-widget .kor-bar-row')).toHaveCount(2);
  });

  test('reference pages expose stable section anchors and direct hash links', async ({ page }) => {
    await page.goto('/methodology.html');
    const methodToc = page.getByRole('navigation', { name: 'On this page' });
    await expect(methodToc.getByRole('link', { name: 'Community consensus' })).toHaveAttribute('href', '#community-consensus');
    await expect(methodToc.getByRole('link', { name: 'Kills Over Replacement' })).toHaveAttribute('href', '#kills-over-replacement');
    await expect(methodToc.getByRole('link', { name: 'Formal accolades' })).toHaveAttribute('href', '#formal-accolades');
    await expect(methodToc.getByRole('link', { name: 'Tournament rules' })).toHaveAttribute('href', '#tournaments');
    await expect(page.locator('#community-consensus .anchor-link')).toHaveAttribute('href', '#community-consensus');
    await expect(page.locator('#kills-over-replacement .anchor-link')).toHaveAttribute('href', '#kills-over-replacement');
    await expect(page.locator('#formal-accolades .anchor-link')).toHaveAttribute('href', '#formal-accolades');
    await expect(page.locator('#tournaments .anchor-link')).toHaveAttribute('href', '#tournaments');

    await page.goto('/methodology.html#kills-over-replacement');
    await expect(page.locator('#kills-over-replacement')).toBeInViewport();

    await page.goto('/methodology.html#community-consensus');
    await expect(page.locator('#community-consensus')).toBeInViewport();

    await page.goto('/methodology.html#formal-accolades');
    await expect(page.locator('#formal-accolades')).toBeInViewport();

    await page.goto('/methodology.html#tournaments');
    await expect(page.locator('#tournaments')).toBeInViewport();

    await page.goto('/player.html?p=Scump');
    const playerToc = page.getByRole('navigation', { name: 'On this page' });
    await expect(playerToc.getByRole('link', { name: 'Stats' })).toHaveAttribute('href', '#stats-on-record');
    await expect(playerToc.getByRole('link', { name: 'Honors' })).toHaveAttribute('href', '#honors');
    await expect(playerToc.getByRole('link', { name: 'Similar players' })).toHaveAttribute('href', '#similar');
    await expect(page.locator('#stats-on-record .anchor-link')).toHaveAttribute('href', '#stats-on-record');
    await expect(page.locator('#honors .anchor-link')).toHaveAttribute('href', '#honors');

    await page.goto('/player.html?p=Scump#honors');
    await expect(page.locator('#honors')).toBeInViewport();

    await page.goto('/game.html?g=Black%20Ops%207');
    const gameToc = page.getByRole('navigation', { name: 'On this page' });
    await expect(gameToc.getByRole('link', { name: 'Season events' })).toHaveAttribute('href', '#events');
    await expect(gameToc.getByRole('link', { name: 'Leaderboard players' })).toHaveAttribute('href', '#players');

    await page.goto('/game.html?g=Black%20Ops%207#players');
    await expect(page.locator('#players')).toBeInViewport();
    const targetIsNotCovered = await page.evaluate(() => {
      const target = document.getElementById('players')!;
      const head = document.querySelector('.site-head') as HTMLElement | null;
      if(!head || getComputedStyle(head).position === 'static') return true;
      return target.getBoundingClientRect().top >= head.getBoundingClientRect().bottom - 1;
    });
    expect(targetIsNotCovered).toBe(true);
  });

  test('peak-vs-longevity scatter renders dots', async ({ page }) => {
    await page.goto('/scatter.html');
    await expect(page.getByRole('heading', { name: /Peak vs\.? Longevity/ })).toBeVisible();
    // every leaderboard player with wins should be a dot
    const expected = await page.evaluate(() => (window as any).APP_DATA.leaderboard.length);
    await expect(page.locator('svg.scatter circle.dot')).toHaveCount(expected);
  });

  test('Insights nav dropdown lists the chart pages', async ({ page }) => {
    await page.goto('/index.html');
    await page.click('.navdrop-btn');
    const links = await page.$$eval('.navdrop-menu a', as => as.map(a => (a as HTMLAnchorElement).getAttribute('href')));
    expect(links).toEqual(['kor.html', 'authored-vs-community.html', 'scatter.html', 'heatmap.html', 'trajectory.html', 'map.html', 'signatures.html']);
  });

  test('Kills Over Replacement page renders all-time and title splits', async ({ page }) => {
    await page.goto('/kor.html');
    await expect(page.getByRole('heading', { name: 'Kills Over Replacement' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'All-time Respawn KOR/map' })).toBeVisible();
    await expect(page).toHaveURL(/\/kor\.html$/);
    await expect(page.locator('.kor-method a')).toHaveAttribute('href', 'methodology.html#kills-over-replacement');
    await expect(page.locator('.kor-table thead')).toContainText('Role');
    await expect(page.locator('.kor-table thead')).toContainText('Median opp place');
    await expect(page.locator('.kor-table caption')).toContainText('All-time Respawn KOR/map leaderboard');
    await expect(page.locator('.kor-table th[scope="col"]')).toHaveCount(11);
    await expect(page.locator('.scroll-x[aria-label="All-time Respawn KOR/map leaderboard table"] .kor-table')).toBeVisible();
    await expect(page.getByText('Swipe the table sideways to see role, sample, and opponent context')).toBeAttached();
    await expect(page.locator('.kor-table tbody tr').first()).toContainText('HyDra');
    await expect(page.locator('.kor-table tbody tr').first()).toContainText('Modern Warfare III');
    const splitMinHeight = await page.locator('#kor-split button').first().evaluate(el => Number.parseFloat(getComputedStyle(el).minHeight));
    expect(splitMinHeight).toBeGreaterThanOrEqual(44);

    await page.locator('#kor-game').selectOption('Advanced Warfare');
    await expect(page).toHaveURL(/g=Advanced(\+|%20)Warfare/);
    await expect(page.getByRole('heading', { name: 'Advanced Warfare Respawn KOR/map' })).toBeVisible();
    await expect(page.locator('.kor-baseline-row')).toContainText('Replacement baseline');
    await expect(page.locator('.kor-table tbody tr').first()).toContainText('Scump');
    await expect(page.locator('.kor-table tbody tr').first().locator('.pill.role-smg')).toHaveText('SMG');

    await page.locator('#kor-split button[data-split="snd"]').click();
    await expect(page).toHaveURL(/split=snd/);
    await expect(page.getByRole('heading', { name: 'Advanced Warfare S&D KOR/map' })).toBeVisible();

    await page.goto('/kor.html?g=Black+Ops+7&split=respawn');
    const abezy = page.locator('.kor-table tbody tr').filter({ hasText: 'aBeZy' }).first();
    await expect(abezy.getByRole('link', { name: 'aBeZy' })).toHaveAttribute('href', 'player.html?p=aBeZy');

    await page.goto('/kor.html?g=World+War+II&split=snd');
    const methodzDisambiguated = page.locator('.kor-table tbody tr').filter({ hasText: 'MethodZ (Jorge Bancells)' }).first();
    await expect(methodzDisambiguated).toContainText('MethodZ (Jorge Bancells)');
    await expect(methodzDisambiguated.getByRole('link', { name: /Methodz/i })).toHaveCount(0);
  });

  test('Community Consensus page renders title rankings and source traces', async ({ page }) => {
    await page.goto('/community.html');
    await expect(page.getByRole('heading', { name: 'Community Consensus' })).toBeVisible();
    await expect(page).toHaveURL(/\/community\.html$/);
    await expect(page.locator('.nav a.active')).toHaveText('Community');
    await expect(page.locator('#cc-view-overall')).toHaveClass(/active/);
    await expect(page.locator('#cc-title-field')).toBeHidden();
    await expect(page.locator('#cc-era-field')).toBeVisible();
    await expect(page.locator('#cc-eramenu .colmenu-btn')).toContainText('Eras: All');
    await expect(page.getByRole('heading', { name: 'Career Total Ranking' })).toBeVisible();
    const overallHeaders = await page.locator('#cc-overall-table .tabulator-col-title').allTextContents();
    expect(overallHeaders.at(-1)).toBe('Trace');
    const firstOverallRow = page.locator('#cc-overall-table .tabulator-row').first();
    await expect(firstOverallRow).toContainText('Scump');
    await expect(firstOverallRow.locator('.context-band')).toContainText('28');
    await expect(firstOverallRow).toContainText('not scored');
    await expect(page.locator('#cc-overall-table .tabulator-col[tabulator-field="averageRank"]')).toContainText('Average rank');
    await expect(page.locator('#cc-overall-table .tabulator-col[tabulator-field="total"]')).toHaveCount(0);
    await expect(page.locator('#cc-overall-table .tabulator-col[tabulator-field="perPlayed"]')).toHaveCount(0);
    await expect(page.locator('#cc-overall-table .tabulator-col[tabulator-field="perRanked"]')).toHaveCount(0);
    await expect(page.locator('#cc-overall-table .tabulator-col[tabulator-field="placements"]')).toHaveCount(0);
    await expect(page.getByRole('heading', { name: 'Scump Overall Trace' })).toBeVisible();
    await expect(page.locator('.calc-summary')).toContainText('Total:');
    await expect(page.locator('.cc-calc-table')).toContainText('Title score');
    await expect(page.locator('.cc-calc-table')).toContainText('Sources');
    await expect(page.locator('.cc-calc-table')).toContainText('Overall points');
    await expect(page.locator('.cc-calc-table')).toContainText('((31 - 1) / 30) ** 2.5');
    await expect(page.locator('.cc-calc-table').getByRole('link', { name: 'MW3 #1' })).toHaveAttribute('href', /view=title/);
    const overallLayout = await page.evaluate(() => {
      const table = document.querySelector('#cc-overall-table') as HTMLElement;
      const holder = document.querySelector('#cc-overall-table .tabulator-tableholder') as HTMLElement;
      const trace = document.querySelector('#cc-overall-trace-card') as HTMLElement;
      const tableBox = table.getBoundingClientRect();
      const traceBox = trace.getBoundingClientRect();
      return {
        traceBelowTable: traceBox.top > tableBox.bottom,
        tableUsesMostWidth: tableBox.width > window.innerWidth * 0.75,
        pageOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
        tableScrollsInside: holder.scrollWidth > holder.clientWidth,
      };
    });
    expect(overallLayout.traceBelowTable).toBe(true);
    expect(overallLayout.tableUsesMostWidth).toBe(true);
    expect(overallLayout.pageOverflow).toBe(false);

    await page.locator('#cc-eramenu .colmenu-btn').click();
    await page.locator('#cc-eramenu .era-preset[data-preset="cdl"]').click();
    await expect(page).toHaveURL(/eras=cdl/);
    await expect(page.locator('#cc-eramenu .colmenu-btn')).toContainText('Eras: CDL');
    await expect(page.locator('#cc-overall-table .tabulator-row').first()).toContainText('Simp');

    await page.locator('#cc-mode').selectOption('played');
    await expect(page).toHaveURL(/mode=played/);
    await expect(page).not.toHaveURL(/view=overall/);
    await expect(page.getByRole('heading', { name: 'Per Played Title Ranking' })).toBeVisible();

    await page.locator('#cc-view-title').click();
    await expect(page.locator('#cc-game')).toHaveValue('Black Ops 2');
    await expect(page.getByRole('heading', { name: 'Black Ops 2 Ranking' })).toBeVisible();
    await expect(page.locator('.community-table tbody tr').first()).toContainText('Karma');
    await expect(page.locator('.community-table tbody tr').first().locator('.context-band')).toContainText('4');
    await expect(page.locator('.community-table tbody tr').first().locator('.context-band')).toContainText('not scored');
    await expect(page.getByRole('heading', { name: 'Karma Trace' })).toBeVisible();
    await expect(page.locator('.calc-list')).toContainText('Top 10 Players in BO2');
    await expect(page.locator('.source-ledger')).toContainText('reviewed not scored');
    await expect(page.locator('.source-ledger table caption')).toContainText('Black Ops 2 community consensus source ledger');

    await page.locator('#cc-game').selectOption('Ghosts');
    await expect(page).toHaveURL(/g=Ghosts/);
    await expect(page.getByRole('heading', { name: 'Ghosts Ranking' })).toBeVisible();
    await expect(page.locator('.community-table tbody tr').first()).toContainText('Crimsix');

    await page.goto('/community.html?g=Ghosts&p=Scump');
    await expect(page.getByRole('heading', { name: 'Scump Trace' })).toBeVisible();
    await expect(page.locator('.community-table tr.selected')).toContainText('Scump');

    await page.goto('/community.html?g=Modern+Warfare&p=ABeZy');
    await expect(page.getByRole('heading', { name: 'aBeZy Trace' })).toBeVisible();
    await expect(page.locator('.community-table tr.selected').locator('.context-band')).toContainText('2');
    await expect(page.locator('.community-table tr.selected').locator('.context-band')).toContainText('not scored');
    await expect(page.locator('.community-table tr.selected').locator('.context-band')).toHaveAttribute(
      'title',
      /Call of Duty League 2020 Week 3 - Atlanta/
    );
  });

  test('viz pages render their SVG without JS errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', e => errors.push(e.message));
    for (const [file, sel, heading] of [
      ['heatmap.html', 'svg.hm rect.cell', /Dominance heatmap/],
      ['trajectory.html', 'svg.tj path.vis', /Career trajectories/],
      ['map.html', 'svg#map circle.node', /map of CoD careers/],
    ] as [string, string, RegExp][]) {
      await page.goto('/' + file);
      await expect(page.getByRole('heading', { name: heading })).toBeVisible();
      expect(await page.locator(sel).count()).toBeGreaterThan(0);
    }
    expect(errors).toEqual([]);
  });

  test('heatmap marks championship seasons with a gold dot', async ({ page }) => {
    await page.goto('/heatmap.html');
    // champions exist in the top-16, so at least one marker in the --gold token
    // color must render (resolved at runtime so retoning the token can't break this)
    const gold = await page.evaluate(() =>
      getComputedStyle(document.documentElement).getPropertyValue('--gold').trim());
    expect(await page.locator(`svg.hm circle[fill="${gold}"]`).count()).toBeGreaterThan(0);
  });

  test('heatmap tooltips use scoring denominators, not held event counts', async ({ page }) => {
    await page.goto('/heatmap.html');
    // tooltip text lives in data-tip (rendered via the .charttip HTML tooltip)
    const tips = await page.locator('svg.hm rect.cell').evaluateAll(
      els => els.map(el => el.getAttribute('data-tip')));
    expect(tips).toContain('Shotzzy, MW19: 4/9 majors (44%) · World Champion');
    expect(tips).toContain('HyDra, BO7: 1/6 majors (17%)');
  });

  test('player page links to the wiki and toggles wins vs every major entered', async ({ page }) => {
    await page.goto('/player.html?p=Scump');
    await expect(page.locator('a[href="https://cod-esports.fandom.com/wiki/Scump"]')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Honors' })).toBeVisible();
    await expect(page.locator('.honors-table')).toContainText('CWL All-Star');
    await expect(page.locator('.honors-table')).toContainText('CWL Dallas Open 2017');
    await expect(page.getByText('a blank list means no row in the current source set')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'How adjusted wins work for Scump' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Season-share buildup' })).toBeVisible();
    await expect(page.locator('#ml-title')).toHaveText(/Every major win \(28\)/);
    await expect(page.locator('.stat').filter({ hasText: 'Average placement' })).toContainText(/\d+\.\d/);
    await expect(page.locator('.stat').filter({ hasText: 'Win conversion' })).toContainText('29%');
    await expect(page.locator('.stat').filter({ hasText: 'Finals rate' })).toContainText('40%');
    await expect(page.locator('.stat').filter({ hasText: 'Deep-run rate' })).toContainText('65%');
    await expect(page.getByRole('heading', { name: 'Stats on record' })).toBeVisible();
    await expect(page.locator('.skill-record-row .stat').filter({ hasText: /^Interactions/ })).toHaveCount(0);
    await expect(page.locator('#stats-on-record')).toContainText('Kills + deaths');
    await expect(page.locator('#stats-on-record .pill').filter({ hasText: 'maps' })).toContainText(/\d[\d,]* maps/);
    await expect(page.locator('.skill-record-row .stat').filter({ hasText: /^Kills/ })).toContainText('from stat rows');
    await expect(page.locator('.skill-record-row .stat').filter({ hasText: /^Maps/ })).toHaveCount(0);
    await expect(page.locator('.skill-record-row .stat').filter({ hasText: /^Events w\/ stats/ })).toHaveCount(0);
    await expect(page.locator('.skill-split-card')).toHaveCount(2);
    await expect(page.locator('.skill-split-card').filter({ hasText: 'Overall' })).toHaveCount(0);
    await expect(page.locator('.skill-split-grid')).toHaveCSS('display', 'grid');
    const skillConsistent = await page.evaluate(async () => {
      const s = (window as any).APP_DATA.players.Scump.skillStats;
      const events = await fetch('skill-events.json').then(r => r.json());
      const scumpEvents = events.Scump || [];
      return s.overall.interactions === s.overall.kills + s.overall.deaths &&
        s.coverage.maps === s.overall.maps &&
        s.byGame.length > 0 &&
        scumpEvents.length > 0 &&
        s.byGame.every((g: any) => g.overall.interactions === g.overall.kills + g.overall.deaths);
    });
    expect(skillConsistent).toBe(true);
    await expect(page.locator('.skill-season[open]')).toHaveCount(0);
    await page.locator('.skill-season summary').first().click();
    await expect(page.locator('.skill-season').first()).toContainText('Kills + deaths');
    await expect(page.locator('.skill-season').first().locator('.skill-summary-pills')).toContainText('Respawn');
    await page.locator('#skill-mode button[data-mode="snd"]').click();
    await expect(page.locator('#skill-mode button[data-mode="snd"]')).toHaveAttribute('aria-pressed', 'true');
    await expect(page.locator('.skill-event-table').first()).toContainText('Kills + deaths');
    await expect(page.locator('#team-summary')).toContainText('6 teams');
    await expect(page.locator('#team-strip')).toBeHidden();
    await expect(page.locator('#team-summary img.team-logo').first()).toHaveJSProperty('naturalWidth', 48);
    await page.locator('#team-summary').click();
    await expect(page.locator('#team-strip .team-badge').filter({ hasText: 'OpTic Texas' })).toBeVisible();
    await expect(page.locator('#team-strip img.team-logo[title="OpTic Texas"]')).toHaveJSProperty('naturalWidth', 48);
    await expect(page.getByRole('heading', { name: 'Primary role by season' })).toBeVisible();
    const rolePosition = await page.evaluate(() => {
      const major = document.querySelector('#major-wins')!;
      const honors = document.querySelector('#honors')!;
      const role = document.querySelector('#roles')!;
      const similar = document.querySelector('#similar')!;
      return Boolean(major.compareDocumentPosition(honors) & Node.DOCUMENT_POSITION_FOLLOWING) &&
        Boolean(honors.compareDocumentPosition(role) & Node.DOCUMENT_POSITION_FOLLOWING) &&
        Boolean(role.compareDocumentPosition(similar) & Node.DOCUMENT_POSITION_FOLLOWING);
    });
    expect(rolePosition).toBe(true);
    const bo2Role = page.locator('.role-table tbody tr').filter({ hasText: 'Black Ops 2' }).locator('td').nth(1);
    await expect(bo2Role.locator('.pill.role-smg')).toHaveText('SMG');
    await expect(bo2Role.getByRole('link', { name: 'Dispute' }))
      .toHaveAttribute('href', /template=role_dispute\.yml/);
    await expect(page.locator('#winlist .team-badge').filter({ hasText: 'OpTic Texas' }).first()).toBeVisible();
    await expect(page.locator('#winlist img.team-logo[title="OpTic Texas"]').first()).toHaveJSProperty('naturalWidth', 48);
    const winRows = await page.locator('#winlist tr').count();
    await page.click('#seg-all');
    await expect(page.locator('#ml-title')).toHaveText(/Every major entered \(\d+\)/);
    // participation.json is fetched on first toggle; wait for a losing placement to land
    await expect(page.locator('#winlist tr.faint').first()).toBeVisible();
    expect(await page.locator('#winlist tr').count()).toBeGreaterThan(winRows);
    await expect(page.locator('#winlist .team-badge').filter({ hasText: 'OpTic Texas' }).first()).toBeVisible();
    await expect(page.locator('#winlist img.team-logo[title="OpTic Texas"]').first()).toHaveJSProperty('naturalWidth', 48);
    await expect(page.locator('#ml-note')).toContainText('same normalized list');
    const consistent = await page.evaluate(async () => {
      const D = (window as any).APP_DATA;
      const p = D.players.Scump;
      const all = await fetch('participation.json').then(r => r.json());
      const rows = all.Scump;
      const sum = rows.reduce((a: number, r: any) => a + r.placeX2, 0);
      const avg = Math.floor((sum * 100 + rows.length) / (2 * rows.length)) / 100;
      return rows.length === p.events_placed && sum === p.place_x2_sum &&
        rows.some((r: any) => r.team === 'OpTic Texas') &&
        D.teamLogos['OpTic Texas']?.src?.startsWith('assets/team-logos/') &&
        Math.abs(avg - p.avg_place) < 0.011;
    });
    expect(consistent).toBe(true);
  });

  test('player page can seed a comparison', async ({ page }) => {
    await page.goto('/player.html?p=Scump');
    await page.locator('#root').getByRole('link', { name: 'Compare' }).click();
    await expect(page).toHaveURL(/compare\.html\?p=Scump/);
    await expect(page.locator('.compare-summary thead th')).toContainText(['Metric', 'Scump']);
  });

  test('similar player detail can compare both players', async ({ page }) => {
    await page.goto('/player.html?p=Shotzzy');
    await page.locator('.sim-row[data-comp="Simp"]').click();
    await page.getByRole('link', { name: 'compare both →' }).click();
    await expect(page).toHaveURL(/compare\.html\?p=Shotzzy&p=Simp/);
    await expect(page.locator('.compare-summary thead th')).toContainText(['Metric', 'Shotzzy', 'Simp']);
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

    await page.click('.segbtn[data-preset="clear"]');
    await page.locator('#search').fill('ABeZy');
    await page.locator('#search').dispatchEvent('change');
    await expect(page.locator('#chips')).toContainText('aBeZy');
  });

  test('BO7 season page shows in-progress weighting (1/6)', async ({ page }) => {
    await page.goto('/game.html?g=Black%20Ops%207');
    await expect(page.getByText(/in progress/).first()).toBeVisible();
    await expect(page.getByText('1 / 6')).toBeVisible(); // 6 scheduled majors (Challengers Finals dropped), not the 4 played
    await expect(page.locator('table.data .team-badge').filter({ hasText: 'OpTic Texas' }).first()).toBeVisible();
    await expect(page.locator('table.data img.team-logo[title="OpTic Texas"]').first()).toHaveJSProperty('naturalWidth', 48);
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

test.describe('compare page', () => {
  test('URL and picker player names resolve source casing variants', async ({ page }) => {
    await page.goto('/compare.html?p=ABeZy&p=ILLeY');
    await expect(page.locator('.compare-summary thead th')).toContainText(['Metric', 'aBeZy', 'iLLeY']);
    await expect(page).toHaveURL(/p=aBeZy/);
    await expect(page).toHaveURL(/p=iLLeY/);

    await page.locator('#player-pick').fill('cellium');
    await page.getByRole('button', { name: 'Add player' }).click();
    await expect(page.locator('.compare-summary thead th')).toContainText(['Metric', 'aBeZy', 'iLLeY', 'Cellium']);
    await expect(page).toHaveURL(/p=Cellium/);
  });

  test('URL players render dense comparison with participation denominators', async ({ page }) => {
    await page.goto('/compare.html?p=Shotzzy&p=HyDra');
    await expect(page.getByRole('heading', { name: 'Player Compare', exact: true })).toBeVisible();
    await expect(page.locator('.compare-summary thead th')).toContainText(['Metric', 'Shotzzy', 'HyDra']);
    await expect(page.locator('.compare-card')).toHaveCount(0);
    await expect(page.locator('.compare-summary tbody th')).toContainText([
      'Adjusted wins',
      'Role',
      'Honors',
      'Win conversion',
      'Finals rate',
      'Deep-run rate',
      'Champs',
      'Peak',
      'Eras',
      'Career',
      'Events',
      'Average place',
    ]);
    await expect(page.locator('.compare-summary tbody th', { hasText: 'Raw wins' })).toHaveCount(0);
    await expect(page.locator('.compare-summary tbody th', { hasText: 'Post-BO2 adjusted' })).toHaveCount(0);
    await expect(page.locator('.compare-summary tbody tr', { hasText: 'Adjusted wins' })).not.toContainText(/▲|▼/);
    await expect(page.locator('.compare-summary tbody tr', { hasText: 'Role' }).locator('.pill.role-smg')).toHaveCount(2);
    await expect(page.locator('.compare-summary tbody tr', { hasText: 'Honors' })).toContainText('7');
    await expect(page.locator('.compare-summary tbody tr', { hasText: 'Honors' })).toContainText('Season MVP');
    await expect(page.locator('.compare-summary tbody tr', { hasText: 'Win conversion' })).toContainText('24%');
    await expect(page.locator('.compare-summary tbody tr', { hasText: 'Finals rate' })).toContainText('43%');
    await expect(page.locator('.compare-summary tbody tr', { hasText: 'Deep-run rate' })).toContainText('75%');
    await expect(page.locator('.compare-summary .summary-meter')).toHaveCount(22);
    const adjustedScores = await page.locator('.compare-summary tbody tr', { hasText: 'Adjusted wins' }).locator('td').evaluateAll(
      els => els.map(el => getComputedStyle(el).getPropertyValue('--summary-score').trim()),
    );
    expect(adjustedScores).toEqual(['100%', '0%']);

    const bo7 = page.locator('#season-table tbody tr', { hasText: 'Black Ops 7' });
    await expect(bo7).toContainText('in progress');
    await expect(bo7).toContainText('1 / 4');
    await expect(bo7.locator('td.season-heat')).toHaveCount(2);
    const bo7Heat = await bo7.locator('td.season-heat').first().evaluate(el => getComputedStyle(el).getPropertyValue('--heat').trim());
    expect(bo7Heat).toMatch(/%$/);
    await expect(bo7.locator('.season-teams .team-badge').filter({ hasText: 'OpTic Texas' })).toBeVisible();
    await expect(bo7.locator('.season-role .pill.role-smg').first()).toHaveText('SMG');
    await expect(bo7.locator('.season-role').first().getByRole('link', { name: 'Dispute' }))
      .toHaveAttribute('href', /template=role_dispute\.yml/);
    await expect(bo7.locator('img.team-logo[title="OpTic Texas"]').first()).toHaveJSProperty('naturalWidth', 48);
    const mw19 = page.locator('#season-table tbody tr', { hasText: 'Modern Warfare' });
    await expect(mw19.locator('.season-teams .team-badge').filter({ hasText: 'Dallas Empire' })).toBeVisible();
    await expect(page.locator('#season-table tbody tr', { hasText: 'Black Ops 2' })).toHaveCount(0);
  });

  test('row picker changes summary rows and syncs the URL', async ({ page }) => {
    await page.goto('/compare.html?p=Shotzzy&p=HyDra');
    await page.locator('#rowmenu .colmenu-btn').click();
    await page.locator('#rowmenu input[data-row="raw"]').check();
    await page.locator('#rowmenu input[data-row="skillKd"]').check();
    await page.locator('#rowmenu input[data-row="skillInteractions"]').check();
    await expect(page).toHaveURL(/rows=/);
    await expect(page.locator('.compare-summary tbody th')).toContainText([
      'Adjusted wins',
      'Role',
      'Honors',
      'Win conversion',
      'Finals rate',
      'Deep-run rate',
      'Raw wins',
      'Champs',
      'Peak',
      'Eras',
      'Career',
      'Events',
      'Average place',
      'K/D',
      'Interactions',
    ]);

    const url = page.url();
    await page.goto(url);
    await expect(page.locator('.compare-summary tbody th', { hasText: 'Raw wins' })).toHaveCount(1);
    await expect(page.locator('.compare-summary tbody th', { hasText: 'K/D' })).toHaveCount(1);
    await expect(page.locator('.compare-summary tbody th', { hasText: 'Interactions' })).toHaveCount(1);
  });

  test('picker adds a player and syncs the shareable URL', async ({ page }) => {
    await page.goto('/compare.html?p=Shotzzy&p=HyDra');
    await page.locator('#player-pick').fill('Simp');
    await page.getByRole('button', { name: 'Add player' }).click();
    await expect(page).toHaveURL(/p=Simp/);
    await expect(page.locator('.compare-summary thead th')).toContainText(['Metric', 'Shotzzy', 'HyDra', 'Simp']);
  });

  test('invalid picker input is announced without changing the comparison', async ({ page }) => {
    await page.goto('/compare.html?p=Shotzzy&p=HyDra');
    await page.locator('#player-pick').fill('NotAPlayer');
    await page.getByRole('button', { name: 'Add player' }).click();
    await expect(page.locator('#compare-status')).toHaveText('No player matched that name.');
    await expect(page.locator('.compare-summary thead th')).toContainText(['Metric', 'Shotzzy', 'HyDra']);
  });

  test('similar-player suggestions add players to the comparison', async ({ page }) => {
    await page.goto('/compare.html?p=Shotzzy&p=HyDra');
    await expect(page.locator('.suggestion-btn[data-add="Simp"]')).toBeVisible();
    await page.locator('.suggestion-btn[data-add="Simp"]').click();
    await expect(page).toHaveURL(/p=Simp/);
    await expect(page.locator('.compare-summary thead th')).toContainText(['Metric', 'Shotzzy', 'HyDra', 'Simp']);
  });

  test('season matrix remains horizontally scrollable on mobile', async ({ page }) => {
    test.skip(test.info().project.name !== 'mobile', 'mobile only');
    await page.goto('/compare.html?p=Shotzzy&p=HyDra&p=Simp&p=aBeZy');
    const { sw, cw } = await page.evaluate(() => {
      const h = document.querySelector('.compare-table-wrap') as HTMLElement;
      return { sw: h.scrollWidth, cw: h.clientWidth };
    });
    expect(sw).toBeGreaterThan(cw);
  });
});

test.describe('GOAT Builder', () => {
  test('loads with real community consensus skill values', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.goto('/goat-builder.html');

    await expect(page.getByRole('heading', { name: 'GOAT Ranking Builder' })).toBeVisible();
    await expect(page).toHaveURL(/\/goat-builder\.html$/);
    await expect(page.locator('#skillCoverage')).toHaveText('15');
    await expect(page.locator('#laneCount')).toHaveText('4');
    await expect(page.locator('#activeShare')).toHaveText('100 pts');
    await expect(page.locator('#ringStat')).toHaveText('2.0x');

    await expect(page.locator('#goatTable .tabulator-row').first()).toBeVisible();
    const skills = await page.locator('#goatTable .tabulator-cell[tabulator-field="skill"]').evaluateAll(cells =>
      cells.slice(0, 8).map(cell => cell.textContent?.trim()));
    expect(new Set(skills)).not.toEqual(new Set(['50']));
    expect(skills).toContain('100');
    expect(errors).toEqual([]);
  });

  test('default GOAT Builder URL params canonicalize to the bare path', async ({ page }) => {
    await page.goto('/goat-builder.html?criteria=resume%2Cskill%2Clongevity%2Cpeak&weights=resume%3A25%2Cskill%3A25%2Clongevity%3A25%2Cpeak%3A25&rings=2&era=all&view=rank&sort=rank&dir=asc');

    await expect(page.getByRole('heading', { name: 'GOAT Ranking Builder' })).toBeVisible();
    await expect(page.locator('#laneCount')).toHaveText('4');
    await expect(page.locator('#activeShare')).toHaveText('100 pts');
    await expect(page.locator('#ringStat')).toHaveText('2.0x');
    await expect(page).toHaveURL(/\/goat-builder\.html$/);
  });

  test('primary criteria can be removed and round-trip through the URL', async ({ page }) => {
    await page.goto('/goat-builder.html');
    await page.locator('[data-enabled="skill"]').uncheck();

    await expect(page.locator('#laneCount')).toHaveText('3');
    await expect(page.locator('#activeShare')).toHaveText('75 pts');
    await expect(page.locator('#budgetStatus')).toHaveText('Remaining: 25');
    await expect(page.locator('#scoreNote')).toContainText('Resume 33% / Longevity 33% / Peak 33%');
    await expect(page).toHaveURL(/criteria=resume%2Clongevity%2Cpeak|criteria=resume,longevity,peak/);

    const url = page.url();
    await page.goto(url);
    await expect(page.locator('[data-enabled="skill"]')).not.toBeChecked();
    await expect(page.locator('[data-weight="skill"]')).toBeDisabled();
    await expect(page.locator('#laneCount')).toHaveText('3');
  });

  test('criterion scoring preserves raw input magnitude', async ({ page }) => {
    await page.goto('/goat-builder.html?criteria=resume%2Cskill%2Clongevity%2Cpeak&weights=resume%3A50%2Cskill%3A25%2Clongevity%3A15%2Cpeak%3A10&rings=3&era=all&view=rank');
    await expect(page.locator('#goatTable .tabulator-row').first()).toBeVisible();

    const comparison = await page.evaluate(() => {
      const rows = rowsFor(activeWeights(), renderScales, state.ring);
      const pick = (name: string) => {
        const row = rows.find((r: any) => r.player.name === name);
        const stats = row.stats;
        return {
          rank: rows.findIndex((r: any) => r.player.name === name) + 1,
          resumeScore: row.lane.resume,
          resumeInput: stats.adj + stats.champs * (state.ring - 1),
          skillScore: row.lane.skill,
          skillInput: stats.consensus?.totalPoints,
        };
      };
      return {crim: pick('Crimsix'), scump: pick('Scump')};
    });

    expect(comparison.crim.resumeInput).toBeGreaterThan(32);
    expect(comparison.scump.resumeInput).toBeLessThan(26);
    expect(comparison.crim.resumeScore - comparison.scump.resumeScore).toBeGreaterThan(20);
    expect(comparison.scump.skillInput).toBeGreaterThan(comparison.crim.skillInput);
    expect(comparison.scump.skillScore - comparison.crim.skillScore).toBeGreaterThan(35);
  });

  test('ranking columns sort and expose header explanations', async ({ page }) => {
    await page.goto('/goat-builder.html');
    await expect(page.locator('#goatTable .tabulator-col[tabulator-field="skill"]'))
      .toHaveAttribute('title', /community-consensus points/);

    await page.locator('#goatTable .tabulator-col[tabulator-field="skill"]').click();
    await expect(page).toHaveURL(/sort=skill/);
    const firstSkillSort = page.locator('#goatTable .tabulator-row').first();
    await expect(firstSkillSort.locator('.gb-name')).toHaveText('Scump');

    await page.locator('#goatTable .tabulator-col[tabulator-field="player"]').click();
    const firstPlayerSort = page.locator('#goatTable .tabulator-row').first();
    await expect(firstPlayerSort.locator('.gb-name')).toHaveText('aBeZy');
  });

  test('ranking table scrolls inside the table container', async ({ page }) => {
    await page.goto('/goat-builder.html');
    await expect(page.locator('#goatTable .tabulator-row').first()).toBeVisible();

    const metrics = await page.evaluate(() => {
      const holder = document.querySelector('#goatTable .tabulator-tableholder') as HTMLElement;
      return {
        pageScrollWidth: document.documentElement.scrollWidth,
        viewportWidth: window.innerWidth,
        tableClientWidth: holder.clientWidth,
        tableScrollWidth: holder.scrollWidth,
      };
    });

    expect(metrics.pageScrollWidth).toBeLessThanOrEqual(metrics.viewportWidth);
    expect(metrics.tableScrollWidth).toBeGreaterThan(metrics.tableClientWidth);
  });

  test('expanded player row explains peak and consensus inputs without fact-card clutter', async ({ page }) => {
    await page.goto('/goat-builder.html?criteria=resume%2Cskill%2Clongevity%2Cpeak&weights=resume%3A40%2Cskill%3A30%2Clongevity%3A20%2Cpeak%3A10&rings=3&era=postBo2&view=rank');
    const crimsixRow = page.locator('#goatTable .tabulator-row').filter({ hasText: 'Crimsix' });
    await crimsixRow.evaluate(row => row.scrollIntoView({ block: 'center' }));
    await crimsixRow.click();
    const detail = page.locator('#goatTable .gb-row-detail[data-detail="Crimsix"]');
    await expect(detail).toBeVisible();
    await expect(detail.locator('.gb-explain-table')).toBeVisible();
    await expect(detail).toContainText('Crimsix score build');
    await expect(detail).toContainText('4.30 consensus points');
    await expect(detail).toContainText('Rank points use ((31 - rank) / 30)^2.5');
    await expect(detail).toContainText('Title resume input 6.1 = 4.1 title-adjusted wins + 1 Champs ring x 2.0 extra');
    await expect(detail.locator('.gb-fact')).toHaveCount(0);
  });

  test('is available directly but not linked from global navigation', async ({ page }) => {
    await page.goto('/goat-builder.html');
    await expect(page.locator('.site-head .nav').getByRole('link', { name: /GOAT/i })).toHaveCount(0);

    await page.goto('/index.html');
    await expect(page.locator('.site-head .nav').getByRole('link', { name: /GOAT/i })).toHaveCount(0);
  });
});
