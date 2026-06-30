import { test, expect } from '@playwright/test';

const COLUMN_ORDER = ['adjRank', 'name', 'adjusted', 'rawRank', 'delta', 'raw', 'winsChange', 'champs'];

test.describe('leaderboard', () => {
  test('loads all 50 players', async ({ page }) => {
    await page.goto('/index.html');
    await expect(page.locator('#table .tabulator-row')).toHaveCount(50);
  });

  test('columns are in the expected order', async ({ page }) => {
    await page.goto('/index.html');
    const fields = await page.$$eval(
      '#table .tabulator-header .tabulator-col[tabulator-field]',
      els => els.map(e => e.getAttribute('tabulator-field')),
    );
    expect(fields).toEqual(COLUMN_ORDER);
  });

  test('header is sticky to the window', async ({ page }) => {
    await page.goto('/index.html');
    const pos = await page.$eval('#table .tabulator-header', el => getComputedStyle(el).position);
    expect(pos).toBe('sticky');
  });

  test('URL state (sort, exclude, search) round-trips on load', async ({ page }) => {
    await page.goto('/index.html?excl=1&sort=raw&dir=desc&q=s');
    await expect(page.locator('#excl')).toBeChecked();
    await expect(page.locator('#search')).toHaveValue('s');
    // only players containing "s" remain
    const names = await page.$$eval('#table .tabulator-cell[tabulator-field="name"]', els => els.map(e => e.textContent || ''));
    expect(names.length).toBeGreaterThan(0);
    for (const n of names) expect(n.toLowerCase()).toContain('s');
  });

  test('toggling exclude pre-BO2 updates the URL', async ({ page }) => {
    await page.goto('/index.html');
    await page.locator('#excl').check();
    await expect(page).toHaveURL(/excl=1/);
  });
});

test.describe('desktop layout', () => {
  test('table fills its container (no dead whitespace)', async ({ page }) => {
    test.skip(test.info().project.name !== 'desktop', 'desktop only');
    await page.goto('/index.html');
    const { inner, holder } = await page.evaluate(() => {
      const t = document.querySelector('#table .tabulator-table') as HTMLElement;
      const h = document.querySelector('#table .tabulator-tableholder') as HTMLElement;
      return { inner: t.offsetWidth, holder: h.clientWidth };
    });
    expect(inner).toBeGreaterThanOrEqual(holder - 4);
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
});
