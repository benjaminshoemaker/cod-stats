# CoD Major Wins — Era-Adjusted

An interactive site that re-ranks Call of Duty pros by **era-adjusted major tournament wins**.
Early CoD seasons had far more majors (Black Ops 2 = 17) than modern ones (6–7), so raw win
totals flatter early-era players. This weights every season equally: a win is worth
`1 ÷ (majors that season)`, summed across a career, then rescaled to a familiar "wins" number.

## The site (`site/`)

Static, no build step, works offline (the table library is vendored locally).

| Page | What it shows |
|------|----------------|
| `index.html` | Sortable / searchable / filterable leaderboard (every player with 2+ major wins) with Adjusted, Peak, Eras, Raw wins, rank-change, and **Championships** columns. Controls: an **"Eras"** filter (presets + per-title checkboxes; recomputes the ranking for the selected seasons), a **column selector**, and an optional **championship-weighting** slider — all shareable via the URL. Responsive-collapse + keyboard-sortable. Uses [Tabulator](https://tabulator.info). |
| `player.html?p=Name` | A player's every major win, grouped by season, with each win's weight and the running adjusted total — plus their **Call of Duty World Championship** count (unweighted, one per year). |
| `games.html` / `game.html?g=Game` | Per-season pages: how many majors there were, the per-win weight, the full event list with winners, and which leaderboard players won. |
| `scatter.html` | **Peak vs Longevity** scatter: best title-winning season against distinct CoD titles won. |
| `methodology.html` | Visual rationale: the major-count timeline, three scoring options, and a Crimsix-vs-Simp head-to-head. |
| `changelog.html` | What's changed, with **Methodology** entries logging rationale + ranking impact. |

### Run it
```bash
cd site
python3 -m http.server 8765
# open http://localhost:8765/index.html
```
(Opening `index.html` directly via `file://` also works — all data is embedded in `site/data.js`.)

## Deploy (Vercel + GitHub auto-deploy)

The site is static — Vercel just serves the `site/` folder (no build step; `site/data.js` is precomputed by `build_data.py` and committed).

One-time setup:
1. Go to [vercel.com](https://vercel.com) → **Add New… → Project**.
2. Import the **`cod-stats`** GitHub repo (authorize the Vercel GitHub app if prompted).
3. Set **Root Directory** to `site`. Framework Preset: **Other**. Leave Build Command empty.
4. **Deploy.**

After that, every push to `main` auto-deploys to production, and pull requests get preview URLs. To update the data later: run `python3 build_data.py`, commit the regenerated `site/data.js`, and push.

## Method (verified)

- **Major** = a tournament with `Tier` of `"Major"` or `"Premier"` on the
  [CoD Esports Wiki](https://cod-esports.fandom.com), where the player finished **1st** (players + subs).
  This reproduces the wiki's published "Major Wins" totals **exactly** for every listed player
  (everyone with 2+ console major wins).
- **Season** = the game title (Black Ops 2, Ghosts, …). Warzone (battle royale) and Mobile are excluded entirely.
- **Denominator** = majors a team *could win* that season: the majors held, except
  Modern Warfare 2019's split Home Series format (9 playable of 13 held) and in-progress
  seasons, which divide by their full schedule rather than the majors played so far.
- **Adjusted wins** = `(Σ wins ÷ majors_that_season) × avg_majors_per_season`.
  Rescaling by the average majors-per-season (shown in the site footer/methodology; it
  shifts slightly as seasons are added) keeps the ranking but puts it on a wins-like scale.
- **Ranks** are computed on exact fractions (not rounded display values); ties share the
  minimum rank, competition-style.

## Rebuild the data

Raw pulls from the wiki Cargo API are cached as JSON in the repo root. To regenerate `site/data.js`:
```bash
python3 build_data.py          # reads the root JSON snapshots and writes site/data.js
```
To refresh the cached JSON from the live wiki (e.g. after a drift alert):
```bash
python3 scripts/fetch_source.py               # re-pulls all four source JSON files
python3 scripts/fetch_source.py --published   # prints the live list (2+ wins) as a PUBLISHED literal
python3 scripts/fetch_source.py --player-stats # resumable canonical major-event PlayerStats pull
```
Then update `PUBLISHED`/`ASOF` in `build_data.py` if the wiki list moved, re-run the build, and commit.

## Tests

```bash
./verify.sh                        # build + both suites (run before pushing)
pytest tests/test_build_data.py -q # data-integrity tests (reconstruction == wiki totals, denominators, BO7 date filter, champs)
npx playwright test                # browser/layout tests at 1280px + 393px (column order, desktop fill, sticky header, mobile scroll, URL state, sub-pages)
```

Both suites run on every push via GitHub Actions (`.github/workflows/ci.yml`). The data
tests use `build_data.build()`; first-time setup is `python3 -m venv .venv && .venv/bin/pip install pytest`
and `npm install && npx playwright install chromium`.

### Source-of-truth drift check

```bash
python3 scripts/check_live_source.py   # re-query the LIVE wiki; compare Raw Wins to our snapshot
```

The offline tests only prove internal consistency (our data matches the hardcoded `PUBLISHED`
snapshot). This script re-runs the wiki's own Cargo query against the live API and diffs the
per-player Raw Wins, so it catches **source drift** (the wiki changed; our snapshot is stale).
It runs **daily** via `.github/workflows/source-check.yml` — fails (and notifies) only on a real
numeric mismatch, and skips quietly if the wiki is unreachable. On a mismatch, re-pull the data
with `scripts/fetch_source.py` and update `PUBLISHED` (see "Rebuild the data" above).

## Data files (repo root)
- `player_event_wins.json` — every individual major win (player, event, game, date)
- `major_events.json` — every major event (name, game, date, winner, type, prize, location), including future-scheduled ones (used for in-progress season denominators; date-filtered for everything else)
- `champs_wins.json` — Call of Duty World Championship wins per player (2013+)
- `team_participation.json` — every team result row at majors (validates the MW 2019 structural denominator in tests)
- `player_stats_participants.json` — canonical Major/Premier map observations for player profiles, similarity, KOR, and validation; see [`docs/player-stats.md`](docs/player-stats.md)
- `source_manifest.json` — timestamp with honest precision, refresh batch ID, query/schema version, scope, row count, and SHA-256 fingerprint for every source snapshot
- `data_source_policy.json` / `source_conflicts.json` — per-entity authority and merge rules plus the conflict ledger

`player_stats.json` is a deprecated broad audit snapshot and is not consumed by displayed metrics.

These are refreshed by `scripts/fetch_source.py`.
