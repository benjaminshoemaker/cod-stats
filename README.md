# CoD Major Wins — Era-Adjusted

An interactive site that re-ranks Call of Duty pros by **era-adjusted major tournament wins**.
Early CoD seasons had far more majors (Black Ops 2 = 17) than modern ones (6–7), so raw win
totals flatter early-era players. This weights every season equally: a win is worth
`1 ÷ (majors that season)`, summed across a career, then rescaled to a familiar "wins" number.

## The site (`site/`)

Static, no build step, works offline (the table library is vendored locally).

| Page | What it shows |
|------|----------------|
| `index.html` | Sortable / searchable / filterable leaderboard (top 50) with Adjusted, Raw wins, rank-change, and **Championships** columns plus an **"Exclude pre-BO2"** toggle (state persists). Responsive-collapse + keyboard-sortable. Uses [Tabulator](https://tabulator.info). |
| `player.html?p=Name` | A player's every major win, grouped by season, with each win's weight and the running adjusted total — plus their **Call of Duty World Championship** count (unweighted, one per year). |
| `games.html` / `game.html?g=Game` | Per-season pages: how many majors there were, the per-win weight, the full event list with winners, and which top-50 players won. |
| `methodology.html` | Visual rationale: the major-count timeline, three scoring options, and a Crimsix-vs-Simp head-to-head. |

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
  This reproduces the wiki's published "Major Wins" totals **exactly** for all 50 players.
- **Season** = the game title (Black Ops 2, Ghosts, …). Warzone (battle royale) and Mobile are excluded entirely.
- **Denominator** = majors per season that have a recorded 1st place (same source as the wins, so they're consistent).
- **Adjusted wins** = `(Σ wins ÷ majors_that_season) × avg_majors_per_season`.
  Rescaling by the average (8.83 all seasons / 9.64 excluding pre-BO2) keeps the ranking but puts it on a wins-like scale.

## Rebuild the data

Raw pulls from the wiki Cargo API are cached as JSON in the repo root. To regenerate `site/data.js`:
```bash
python3 build_data.py          # reads major_events.json + player_event_wins.json + majors_per_game_results.json
```
`era_adjusted_major_wins.csv` is a flat export of the leaderboard with per-season breakdowns.

## Data files (repo root)
- `player_event_wins.json` — every individual major win (player, event, game, date)
- `major_events.json` — every major event (name, game, date, winner, type, prize, location)
- `champs_wins.json` — Call of Duty World Championship wins per player (from the wiki's `{{CHATournaments}}` list, 2013+)
- `majors_per_game_results.json` — majors per season (denominators)
- `era_adjusted_major_wins.csv` — computed leaderboard export
