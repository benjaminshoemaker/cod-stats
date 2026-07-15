# Player Stats Source

`player_stats.json` is the committed source for objective individual-skill stats.
It is pulled from the CoD Esports Wiki Cargo `PlayerStats` table for published
leaderboard players, joined through `PlayerRedirects`.

## Why The File Is Slim

The raw Cargo pull includes many mode-specific columns and was about 70 MB for
the first full import. The site currently needs a smaller, stable first version:

- kills
- deaths
- K/D
- interactions, meaning `kills + deaths`
- map count
- map result when the wiki `PlayerStats.Win` field is present
- S&D split
- respawn split, meaning every non-S&D mode

For that reason, `scripts/fetch_source.py --player-stats` writes a slim
`player_stats.json` instead of the full Cargo rows. It keeps map-level rows, but
only the fields needed to reproduce the current aggregates:

```text
Player, PlayerName, PlayerLink, Event, EventId, Game, Mode, Date,
Team, TeamVs, Map, SeriesId, Win, Kills, Deaths
```

Rows without numeric `Kills` and `Deaths` are dropped. Blank optional fields are
omitted per row. This keeps the source auditable and reproducible without
committing a large raw export. If future work needs hardpoint time, S&D first
bloods, plants, defuses, or other mode-specific columns, add those fields
intentionally and update this document with the new use case.

## Runtime Impact

The browser does not load `player_stats.json`. `build_data.py` aggregates the
source into runtime files:

- `site/data.js` keeps career totals, S&D/respawn splits, and by-season stats so
  the leaderboard, compare page, and player header can render without another
  stats request.
- `site/skill-events.json` keeps tournament-level stat rows and is lazy-loaded
  only by `player.html` when a profile needs the tournament drilldown.

This split keeps the main site payload quick while still making tournament
stats auditable. After adding season and tournament stats, `site/data.js` was
862,834 bytes uncompressed / 112,020 bytes gzipped, and the lazy
`site/skill-events.json` was 1,917,510 bytes uncompressed / 228,252 bytes
gzipped. The committed `player_stats.json` source was 23.5 MB because it keeps
81,773 reproducible map rows with numeric kills/deaths.

## Coverage

The wiki has usable kills/deaths back to September 3, 2011 in this pull. There
are no usable PlayerStats rows for CoD4/MW2-era 2008-2010 events in the current
source. Some early players also have blank or missing stat rows, so absence of
`skillStats` means "no usable numeric PlayerStats rows in this source", not a
true zero.

As of the initial import, `skillStats` built for 85 of 91 published leaderboard
players. Missing usable stats were:

```text
Mak, DopedGoat, Jake, Methodz, Tobi, VeXeL
```

This coverage should be treated as source availability, not player evaluation.

## Similarity Use

The similarity and clustering pipeline includes only rate-based skill inputs:
overall K/D, respawn K/D, S&D K/D, and interactions per map. Each split/source
bucket must have at least 25 scored map rows before it is used; otherwise that
feature is masked as missing for that player. Missing or sparse stats are not
imputed and are never scored as zero.

Kills, deaths, total interactions, maps, and event counts remain display/sample
context. They are excluded from the similarity score because source coverage,
season length, and career length drive those counts.

## Aggregation Contract

`build_data.py` applies the same tournament universe as the rest of the site:
console Major/Premier events, Warzone/Mobile excluded, explicit dropped events
excluded, and rows after `ASOF` ignored.

For each player it emits:

- `coverage`: first/last stat date, counted event count, and games represented
- `overall`: kills, deaths, interactions, K/D, maps
- `splits.snd`: same metrics for Search and Destroy only
- `splits.respawn`: same metrics for every non-S&D mode
- `modes`: same metrics by wiki mode label
- `byGame`: same metrics by season/title, plus stat coverage dates and event count

`site/skill-events.json` is keyed by player display name. Each row has the same
metrics by tournament within a season/title, plus stat coverage dates and teams.
`eventId` is the CoD Esports Wiki tournament overview page and is the canonical
join key across participation, wins, and stats; `event` remains the display name.

`maps` means count of scored map rows in the source. `interactions` means
`kills + deaths`.

When `Win` is available on the source row, each emitted metric bucket also gains
`mapWins`, `mapLosses`, and `mapWinRate`. Older source snapshots without `Win`
still build without those fields; absence means the source row did not carry
map result data, not that the player went winless.

## Legacy Aggregate Backfill

`legacy_player_event_stats.json` is a separate, major-only source for legacy
codcompstats-backed wiki pages. These rows are event aggregates, not map-level
`PlayerStats` rows. They can show that a Ghosts or Advanced Warfare event has
broader K/D coverage than the committed map rows, but they do not include
per-map kills/deaths, opponents, series IDs, or map results.

`build_data.py` keeps this source out of `skillStats` career totals, similarity
features, KOR, same-map validation, and map-win reconstruction. It emits a
lightweight `legacySkillStats` summary in `site/data.js` and attaches legacy
aggregate details only to the lazy `site/skill-events.json` player drilldown.
The player page labels those rows as `Legacy aggregate` and keeps `Map rows`
visibly separate.

Regular-season and non-major league aggregates discovered during the audit are
not committed to the source file. They should stay quarantined unless the site
adds a separate broader stat-context surface.
