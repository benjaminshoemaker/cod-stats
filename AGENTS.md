# AGENTS.md

Era-adjusted Call of Duty major-tournament-wins site. Static HTML/CSS/JS (no
framework, no build) served from `site/`; data is precomputed by a Python script.

## Commands

```bash
python3 build_data.py            # regenerate site/data.js from source JSON (runs the reconstruction guard)
python3 -m http.server 8765 --directory site   # serve locally → http://localhost:8765/index.html
pytest tests/test_build_data.py -q   # fast data-integrity tests
npx playwright test              # browser/layout tests (desktop + mobile)
./verify.sh                      # build + both test suites (run before pushing)
```

(`pytest`/Playwright live in a local `.venv`/`node_modules`; CI installs them fresh.)

## Structure

- `site/` — the deployed static site. Vercel's **Root Directory is `site`**.
  - `index.html` leaderboard (Tabulator), `player.html`, `games.html`, `game.html`, `methodology.html`,
    `scatter.html` (Peak vs Longevity), `changelog.html`
  - `assets/` (style.css, app.js, favicon.svg, og.png), `vendor/` (Tabulator, committed for offline), `data.js` (**generated**)
- `build_data.py` — pure `build()` returns the data dict; `main()` writes `site/data.js`.
- Source data (committed JSON from the CoD Esports Wiki Cargo API): `major_events.json`,
  `player_event_wins.json`, `champs_wins.json`.
- `tests/` — `test_build_data.py` (pytest), `leaderboard.spec.ts` (Playwright).

## Conventions & boundaries

- **Never hand-edit `site/data.js`** — it's generated. Change `build_data.py` (or the source
  JSON) and re-run it; commit the regenerated file.
- A "major" = wiki `Tier` of `"Major"`/`"Premier"` + 1st place. The build **must** reproduce the
  50 published wiki totals exactly — `build()` raises otherwise, and CI fails. Don't weaken that guard.
- Warzone/Mobile are excluded; only majors played on/before `ASOF` count (drops future BO7 events).
- **Default to TDD for the data/logic** (build_data): add/adjust a test in `tests/test_build_data.py`
  first. For UI changes, add or update a Playwright assertion in `leaderboard.spec.ts` — that suite
  exists because a mobile-layout regression once slipped through manual checks.
- **Log user-facing changes** in the changelog: prepend an entry to the `ENTRIES` array in
  `site/changelog.html` (newest first). Anything that moves the rankings is tagged `Methodology`
  with its rationale **and** impact (who moved) — the numbers must never look arbitrary.
- **Verify objective claims yourself** (run the tests / load the page) before asking the user to verify.
- Fetching wiki data: WebFetch is blocked; use `curl` with a browser User-Agent, expect rate limiting,
  and read wikitext via `api.php?action=query` (the `?action=raw` route is Cloudflare-challenged).

## Deploy

Push to `main` → Vercel auto-deploys to `cod-stats-one.vercel.app` (Root Directory `site`).
Never commit secrets; the Sentry DSN in `app.js` is a public client key and is fine to commit.
