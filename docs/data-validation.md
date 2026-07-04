# Data Validation

The main build guard proves internal consistency: the committed source snapshots
reconstruct the published CoD Esports Wiki major-win leaderboard exactly. External
benchmarks answer a different question: whether the same snapshots reproduce a
claim from another stat source as of the claim date.

Run the current external benchmarks with:

```bash
python3 scripts/validate_benchmarks.py
```

Run live Breaking Point benchmarks separately:

```bash
python3 scripts/validate_benchmarks.py --fixtures validation/breaking-point-benchmarks.json --include-live
```

Benchmarks live in `validation/benchmarks.json`. Each active row has a source,
URL, source date, player, metric, expected value, and optional filters. Pending
or manual rows can be kept in the file without failing CI.

Supported metrics:

- `raw_major_wins`: console Major/Premier wins through `asOf`
- `finals_record`: first-place and second-place finishes through `asOf`
- `championship_wins`: World Championship wins through `asOf`
- `overall_kd`: kills/deaths/maps/KD through `asOf`, with optional event, game,
  or mode filters
- `breaking_point_season_kd`: compares local `player_stats.json` to a live
  Breaking Point player-page aggregate. Live checks are skipped by default.

BrianStats1 posts are useful benchmark fixtures because many are precise, dated
claims. Treat them as regression checks, not as the source of truth: if a fixture
fails, classify the mismatch as a definition difference, source drift, repo bug,
ambiguous claim, or a claim that needs map/VOD-level data the current snapshots
do not carry.

Breaking Point is the strongest modern K/D benchmark found so far. Use it with
strictly aligned scopes: player page, season id, title/game, and optionally event
type or event ids. Current-season comparisons can fail simply because either
source has refreshed before the other.
