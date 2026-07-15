# Legacy Player Stat Backfill Investigation

Expanded audit for GitHub issue #18. This discovers Ghosts and Advanced Warfare legacy statistics pages for published leaderboard players, parses codcompstats-backed aggregate rows, and compares them against the committed CoD Esports Wiki `PlayerStats` map rows.

## Summary

- Candidate player/game pages checked: 182
- Existing legacy pages found: 40
- Parsed legacy rows: 401
- Usable aggregate rows with maps and K/D: 391
- Legacy-only usable rows: 126 (40 major matches, 86 non-major/regular-season rows)
- Current-row overlaps where legacy has more maps: 103 (103 major matches)

Key finding: the legacy pages are worth an ingestion design pass, but only as source-badged event aggregates. The biggest value is Advanced Warfare: multiple major rows are absent from current map-level `PlayerStats`, and several current overlaps are visibly partial.

## Game-Level Yield

| Game | legacy rows | usable rows | overlaps current | legacy-only usable | legacy-only majors | legacy-only non-majors | overlaps with more maps | major overlaps with more maps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Advanced Warfare | 110 | 100 | 57 | 43 | 26 | 17 | 39 | 39 |
| Ghosts | 291 | 291 | 208 | 83 | 14 | 69 | 64 | 64 |

## Page-Level Yield

| Player | Game | legacy rows | usable rows | overlaps current | legacy-only usable | legacy-only majors | overlaps with more legacy maps |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Accuracy | Advanced Warfare | 1 | 1 | 0 | 1 | 0 | 0 |
| Attach | Advanced Warfare | 16 | 15 | 10 | 5 | 3 | 7 |
| Censor | Advanced Warfare | 5 | 5 | 3 | 2 | 1 | 3 |
| Clayster | Advanced Warfare | 16 | 15 | 10 | 5 | 3 | 6 |
| FormaL | Advanced Warfare | 17 | 16 | 11 | 5 | 3 | 6 |
| Havok | Advanced Warfare | 8 | 6 | 1 | 5 | 4 | 1 |
| Karma | Advanced Warfare | 14 | 13 | 8 | 5 | 3 | 7 |
| Nadeshot | Advanced Warfare | 6 | 6 | 4 | 2 | 1 | 1 |
| Octane | Advanced Warfare | 11 | 8 | 2 | 6 | 4 | 1 |
| Swanny | Advanced Warfare | 1 | 1 | 0 | 1 | 0 | 0 |
| ZooMaa | Advanced Warfare | 15 | 14 | 8 | 6 | 4 | 7 |
| ACHES | Ghosts | 12 | 12 | 8 | 4 | 1 | 2 |
| Apathy | Ghosts | 13 | 13 | 10 | 3 | 0 | 3 |
| Attach | Ghosts | 8 | 8 | 5 | 3 | 1 | 2 |
| BigTymeR | Ghosts | 2 | 2 | 2 | 0 | 0 | 0 |
| Censor | Ghosts | 13 | 13 | 10 | 3 | 0 | 3 |
| Cheen | Ghosts | 7 | 7 | 5 | 2 | 1 | 1 |
| Classic | Ghosts | 13 | 13 | 9 | 4 | 1 | 2 |
| Crowder | Ghosts | 13 | 13 | 9 | 4 | 1 | 1 |
| Dedo | Ghosts | 11 | 11 | 7 | 4 | 1 | 1 |
| FEARS | Ghosts | 6 | 6 | 3 | 3 | 2 | 2 |
| FormaL | Ghosts | 12 | 12 | 9 | 3 | 0 | 3 |
| JKap | Ghosts | 14 | 14 | 10 | 4 | 1 | 2 |
| Karma | Ghosts | 13 | 13 | 10 | 3 | 0 | 3 |
| KiLLa | Ghosts | 11 | 11 | 7 | 4 | 1 | 1 |
| Loony | Ghosts | 8 | 8 | 4 | 4 | 1 | 2 |
| MadCat | Ghosts | 3 | 3 | 3 | 0 | 0 | 3 |
| MerK | Ghosts | 14 | 14 | 11 | 3 | 0 | 4 |
| MiRx | Ghosts | 11 | 11 | 8 | 3 | 1 | 3 |
| NAMELESS | Ghosts | 14 | 14 | 11 | 3 | 0 | 7 |
| Nadeshot | Ghosts | 12 | 12 | 8 | 4 | 0 | 1 |
| Parasite | Ghosts | 13 | 13 | 10 | 3 | 0 | 5 |
| ProoFy | Ghosts | 14 | 14 | 11 | 3 | 0 | 2 |
| Rambo | Ghosts | 5 | 5 | 4 | 1 | 0 | 2 |
| Ricky | Ghosts | 12 | 12 | 8 | 4 | 1 | 1 |
| Saints | Ghosts | 11 | 11 | 8 | 3 | 0 | 1 |
| Slacked | Ghosts | 6 | 6 | 4 | 2 | 0 | 3 |
| Swanny | Ghosts | 2 | 2 | 1 | 1 | 0 | 0 |
| TeeP | Ghosts | 12 | 12 | 8 | 4 | 1 | 2 |
| ZooMaa | Ghosts | 6 | 6 | 5 | 1 | 0 | 2 |

## Legacy-Only Major Rows

These are the strongest additive candidates because the row maps to the site's major universe and no current map-level `PlayerStats` aggregate exists for that player/event.

| Player | Game | Event | legacy maps | legacy K/D | source |
| --- | --- | --- | --- | --- | --- |
| Attach | Advanced Warfare | MLG World Finals | 33 | 1.08 | Attach/Statistics/Advanced Warfare |
| Clayster | Advanced Warfare | MLG World Finals | 33 | 1.13 | Clayster/Statistics/Advanced Warfare |
| FormaL | Advanced Warfare | MLG World Finals | 34 | 1.19 | FormaL/Statistics/Advanced Warfare |
| Havok | Advanced Warfare | MLG World Finals | 12 | 1 | Havok/Statistics/Advanced Warfare |
| Karma | Advanced Warfare | MLG World Finals | 34 | 0.94 | Karma/Statistics/Advanced Warfare |
| Octane | Advanced Warfare | MLG World Finals | 33 | 1.14 | Octane/Statistics/Advanced Warfare |
| ZooMaa | Advanced Warfare | MLG World Finals | 33 | 1.17 | ZooMaa/Statistics/Advanced Warfare |
| FormaL | Advanced Warfare | UMG California 2015 | 32 | 1.26 | FormaL/Statistics/Advanced Warfare |
| Havok | Advanced Warfare | UMG California 2015 | 9 | 0.97 | Havok/Statistics/Advanced Warfare |
| Karma | Advanced Warfare | UMG California 2015 | 32 | 0.86 | Karma/Statistics/Advanced Warfare |
| Octane | Advanced Warfare | UMG California 2015 | 21 | 1.2 | Octane/Statistics/Advanced Warfare |
| ZooMaa | Advanced Warfare | UMG California 2015 | 40 | 1.13 | ZooMaa/Statistics/Advanced Warfare |
| Havok | Advanced Warfare | UMG Dallas 2015 | 12 | 0.94 | Havok/Statistics/Advanced Warfare |
| Octane | Advanced Warfare | UMG Dallas 2015 | 22 | 1.12 | Octane/Statistics/Advanced Warfare |
| Attach | Advanced Warfare | UMG Orlando 2015 | 32 | 1.03 | Attach/Statistics/Advanced Warfare |
| Censor | Advanced Warfare | UMG Orlando 2015 | 18 | 0.87 | Censor/Statistics/Advanced Warfare |
| Clayster | Advanced Warfare | UMG Orlando 2015 | 22 | 1.01 | Clayster/Statistics/Advanced Warfare |
| FormaL | Advanced Warfare | UMG Orlando 2015 | 27 | 1.12 | FormaL/Statistics/Advanced Warfare |
| Karma | Advanced Warfare | UMG Orlando 2015 | 25 | 1.18 | Karma/Statistics/Advanced Warfare |
| Nadeshot | Advanced Warfare | UMG Orlando 2015 | 27 | 0.94 | Nadeshot/Statistics/Advanced Warfare |
| ZooMaa | Advanced Warfare | UMG Orlando 2015 | 32 | 1.01 | ZooMaa/Statistics/Advanced Warfare |
| Attach | Advanced Warfare | UMG Washington D.C. 2015 | 26 | 1 | Attach/Statistics/Advanced Warfare |
| Clayster | Advanced Warfare | UMG Washington D.C. 2015 | 26 | 1.19 | Clayster/Statistics/Advanced Warfare |
| Havok | Advanced Warfare | UMG Washington D.C. 2015 | 20 | 0.99 | Havok/Statistics/Advanced Warfare |
| Octane | Advanced Warfare | UMG Washington D.C. 2015 | 33 | 1.13 | Octane/Statistics/Advanced Warfare |
| ZooMaa | Advanced Warfare | UMG Washington D.C. 2015 | 26 | 1.14 | ZooMaa/Statistics/Advanced Warfare |
| Attach | Ghosts | UGC Niagara | 5 | 0.96 | Attach/Statistics/Ghosts |
| Cheen | Ghosts | UGC Niagara | 3 | 0.91 | Cheen/Statistics/Ghosts |
| Classic | Ghosts | UGC Niagara | 9 | 0.9 | Classic/Statistics/Ghosts |
| Crowder | Ghosts | UGC Niagara | 9 | 1.2 | Crowder/Statistics/Ghosts |
| FEARS | Ghosts | UGC Niagara | 1 | 1.11 | FEARS/Statistics/Ghosts |
| JKap | Ghosts | UGC Niagara | 9 | 1.18 | JKap/Statistics/Ghosts |
| Loony | Ghosts | UGC Niagara | 1 | 0.55 | Loony/Statistics/Ghosts |
| ACHES | Ghosts | UMG Nashville 2014 | 17 | 0.93 | ACHES/Statistics/Ghosts |
| Dedo | Ghosts | UMG Nashville 2014 | 17 | 0.95 | Dedo/Statistics/Ghosts |
| FEARS | Ghosts | UMG Nashville 2014 | 11 | 0.95 | FEARS/Statistics/Ghosts |
| KiLLa | Ghosts | UMG Nashville 2014 | 20 | 0.98 | KiLLa/Statistics/Ghosts |
| MiRx | Ghosts | UMG Nashville 2014 | 20 | 1.04 | MiRx/Statistics/Ghosts |
| Ricky | Ghosts | UMG Nashville 2014 | 20 | 0.88 | Ricky/Statistics/Ghosts |
| TeeP | Ghosts | UMG Nashville 2014 | 17 | 0.87 | TeeP/Statistics/Ghosts |

## Partial Current Major Rows

These rows already have some map-level `PlayerStats`, but the legacy aggregate has more maps. They are useful for event-level display coverage and for identifying source gaps, not for map-row reconstruction.

| Player | Game | Event | legacy maps | current maps | map delta | legacy K/D | current K/D |
| --- | --- | --- | --- | --- | --- | --- | --- |
| FormaL | Advanced Warfare | UMG Dallas 2015 | 39 | 7 | 32 | 1.2 | 1.068 |
| Karma | Advanced Warfare | UMG Dallas 2015 | 39 | 7 | 32 | 0.85 | 0.643 |
| FormaL | Advanced Warfare | UMG Washington D.C. 2015 | 27 | 3 | 24 | 1.15 | 1.088 |
| Karma | Advanced Warfare | UMG Washington D.C. 2015 | 27 | 3 | 24 | 0.88 | 0.953 |
| KiLLa | Ghosts | UGC Niagara | 26 | 3 | 23 | 0.99 | 0.754 |
| Ricky | Ghosts | UGC Niagara | 26 | 3 | 23 | 1.03 | 0.754 |
| MiRx | Ghosts | UGC Niagara 2014 | 26 | 3 | 23 | 1 | 0.673 |
| FormaL | Ghosts | UMG Nashville 2014 | 30 | 7 | 23 | 1.1 | 0.964 |
| JKap | Ghosts | UMG Nashville 2014 | 30 | 7 | 23 | 1.02 | 1.11 |
| MerK | Ghosts | UMG Nashville 2014 | 30 | 7 | 23 | 1.15 | 0.946 |
| NAMELESS | Ghosts | UMG Nashville 2014 | 30 | 7 | 23 | 1.02 | 0.833 |
| Attach | Advanced Warfare | UMG Dallas 2015 | 26 | 6 | 20 | 1.11 | 0.957 |
| Clayster | Advanced Warfare | UMG Dallas 2015 | 26 | 6 | 20 | 1.15 | 1.206 |
| ZooMaa | Advanced Warfare | UMG Dallas 2015 | 26 | 6 | 20 | 1.13 | 1.376 |
| Nadeshot | Ghosts | UMG Nashville 2014 | 24 | 4 | 20 | 0.95 | 1.077 |
| ProoFy | Ghosts | UMG Nashville 2014 | 24 | 4 | 20 | 1.04 | 1.113 |
| Attach | Advanced Warfare | MLG Columbus Open 2014 | 25 | 8 | 17 | 1 | 0.931 |
| Karma | Advanced Warfare | MLG Columbus Open 2014 | 18 | 1 | 17 | 1.03 | 0.75 |
| ZooMaa | Advanced Warfare | MLG Columbus Open 2014 | 25 | 8 | 17 | 1.02 | 1.029 |
| Apathy | Ghosts | UMG Nashville 2014 | 37 | 21 | 16 | 1.19 | 1.19 |
| Attach | Ghosts | UMG Nashville 2014 | 19 | 3 | 16 | 1.15 | 1.035 |
| Censor | Ghosts | UMG Nashville 2014 | 37 | 21 | 16 | 0.99 | 1.018 |
| Karma | Ghosts | UMG Nashville 2014 | 37 | 21 | 16 | 1.06 | 1.036 |
| Loony | Ghosts | UMG Nashville 2014 | 19 | 3 | 16 | 1.03 | 1.054 |
| Parasite | Ghosts | UMG Nashville 2014 | 37 | 21 | 16 | 1.03 | 0.925 |
| Censor | Advanced Warfare | MLG Columbus Open 2014 | 42 | 28 | 14 | 0.96 | 0.998 |
| Clayster | Advanced Warfare | MLG Columbus Open 2014 | 27 | 13 | 14 | 0.96 | 0.971 |
| Censor | Advanced Warfare | Call of Duty Championship 2015 | 22 | 10 | 12 | 0.92 | 0.734 |
| Cheen | Ghosts | UMG Nashville 2014 | 14 | 3 | 11 | 0.96 | 1.119 |
| Attach | Advanced Warfare | Call of Duty Championship 2015 | 31 | 21 | 10 | 1.19 | 1.154 |
| Clayster | Advanced Warfare | Call of Duty Championship 2015 | 31 | 21 | 10 | 1.31 | 1.236 |
| Censor | Ghosts | UGC Niagara | 17 | 7 | 10 | 0.87 | 0.83 |
| Dedo | Ghosts | UGC Niagara | 17 | 7 | 10 | 1.29 | 1.436 |
| FormaL | Ghosts | UGC Niagara | 17 | 7 | 10 | 1.15 | 1.136 |
| MerK | Ghosts | UGC Niagara | 24 | 14 | 10 | 0.93 | 0.995 |
| NAMELESS | Ghosts | UGC Niagara | 24 | 14 | 10 | 1.03 | 1.061 |
| Parasite | Ghosts | UGC Niagara | 24 | 14 | 10 | 1.04 | 0.98 |
| Slacked | Ghosts | UGC Niagara | 18 | 8 | 10 | 1.14 | 1.049 |
| Crowder | Ghosts | UMG Nashville 2014 | 27 | 17 | 10 | 1.02 | 0.912 |
| Saints | Ghosts | UMG Nashville 2014 | 27 | 17 | 10 | 1.21 | 1.183 |
| ZooMaa | Ghosts | UMG Nashville 2014 | 27 | 17 | 10 | 1.05 | 1.02 |
| FormaL | Advanced Warfare | Call of Duty Championship 2015 | 28 | 19 | 9 | 1.14 | 1.07 |
| Nadeshot | Advanced Warfare | Call of Duty Championship 2015 | 28 | 19 | 9 | 0.96 | 0.845 |
| Karma | Advanced Warfare | Call of Duty Championship 2015 | 18 | 10 | 8 | 1.21 | 1.13 |
| ZooMaa | Advanced Warfare | Call of Duty Championship 2015 | 20 | 12 | 8 | 1.11 | 0.917 |
| Classic | Ghosts | UMG Nashville 2014 | 19 | 11 | 8 | 0.93 | 0.797 |
| Slacked | Ghosts | UMG Nashville 2014 | 19 | 11 | 8 | 1.2 | 1.232 |
| Attach | Advanced Warfare | Call of Duty Championship 2015: NA Regional Finals | 34 | 28 | 6 | 1.06 | 1.003 |
| Clayster | Advanced Warfare | Call of Duty Championship 2015: NA Regional Finals | 34 | 28 | 6 | 1.33 | 1.3 |
| MadCat | Ghosts | UGC Niagara | 10 | 4 | 6 | 1.08 | 1.135 |
| Apathy | Ghosts | MLG Fall Championship | 10 | 5 | 5 | 0.9 | 0.727 |
| Censor | Ghosts | MLG Fall Championship | 10 | 5 | 5 | 1 | 1.176 |
| FEARS | Ghosts | MLG Fall Championship | 10 | 5 | 5 | 1.11 | 1.118 |
| NAMELESS | Ghosts | MLG Fall Championship | 11 | 6 | 5 | 1.06 | 1.089 |
| Parasite | Ghosts | MLG Fall Championship | 11 | 6 | 5 | 1.1 | 1.299 |
| MiRx | Ghosts | MLG Fall Championship 2013 | 11 | 6 | 5 | 1.09 | 1.045 |
| Censor | Advanced Warfare | Call of Duty Championship 2015: NA Regional Finals | 11 | 7 | 4 | 0.94 | 0.92 |
| Karma | Advanced Warfare | Call of Duty Championship 2015: NA Regional Finals | 18 | 14 | 4 | 1.08 | 1.072 |
| ZooMaa | Advanced Warfare | Call of Duty Championship 2015: NA Regional Finals | 17 | 13 | 4 | 1.08 | 1.077 |
| Attach | Advanced Warfare | ESWC 2015 | 22 | 18 | 4 | 0.93 | 0.979 |
| Clayster | Advanced Warfare | ESWC 2015 | 22 | 18 | 4 | 1.33 | 1.333 |
| FormaL | Advanced Warfare | ESWC 2015 | 19 | 15 | 4 | 1.24 | 1.348 |
| FEARS | Ghosts | Call of Duty Championship 2014 | 29 | 25 | 4 | 1.29 | 1.287 |
| Loony | Ghosts | Call of Duty Championship 2014 | 29 | 25 | 4 | 1.05 | 0.987 |
| Attach | Advanced Warfare | Gfinity Summer Championship | 21 | 18 | 3 | 1 | 0.99 |
| Clayster | Advanced Warfare | Gfinity Summer Championship | 21 | 18 | 3 | 1.21 | 1.231 |
| ZooMaa | Advanced Warfare | Gfinity Summer Championship | 21 | 18 | 3 | 1.16 | 1.127 |
| ACHES | Ghosts | UGC Niagara | 25 | 22 | 3 | 1.21 | 1.203 |
| Karma | Ghosts | UGC Niagara | 25 | 22 | 3 | 1.14 | 1.106 |
| TeeP | Ghosts | UGC Niagara 2014 | 25 | 22 | 3 | 0.98 | 0.966 |
| Octane | Advanced Warfare | Gfinity Summer Championship | 15 | 13 | 2 | 1.29 | 1.382 |
| ACHES | Ghosts | UMG Philadelphia | 21 | 19 | 2 | 1.08 | 1.063 |
| Karma | Ghosts | UMG Philadelphia | 21 | 19 | 2 | 1.33 | 1.271 |
| TeeP | Ghosts | UMG Philadelphia | 21 | 19 | 2 | 0.93 | 0.902 |
| FormaL | Advanced Warfare | Gfinity Summer Championship | 22 | 21 | 1 | 1.09 | 1.106 |
| Karma | Advanced Warfare | Gfinity Summer Championship | 22 | 21 | 1 | 0.95 | 0.951 |
| FormaL | Advanced Warfare | MLG Pro League Season 2 Playoffs | 18 | 17 | 1 | 1.15 | 1.159 |
| Karma | Advanced Warfare | MLG Pro League Season 2 Playoffs | 18 | 17 | 1 | 0.97 | 0.982 |
| ZooMaa | Advanced Warfare | MLG Pro League Season 2 Playoffs | 24 | 23 | 1 | 1.03 | 1.05 |
| Attach | Advanced Warfare | MLG Pro League Season 3 Playoffs | 39 | 38 | 1 | 0.99 | 1.001 |
| Havok | Advanced Warfare | MLG Pro League Season 3 Playoffs | 24 | 23 | 1 | 0.93 | 0.907 |
| ZooMaa | Advanced Warfare | MLG Pro League Season 3 Playoffs | 39 | 38 | 1 | 1.04 | 1.04 |
| MadCat | Ghosts | Call of Duty Championship 2014 | 21 | 20 | 1 | 1.32 | 1.332 |
| MerK | Ghosts | Call of Duty Championship 2014 | 44 | 43 | 1 | 1.05 | 1.059 |
| NAMELESS | Ghosts | Call of Duty Championship 2014 | 44 | 43 | 1 | 1.07 | 1.08 |
| Rambo | Ghosts | Call of Duty Championship 2014 | 44 | 43 | 1 | 0.93 | 0.936 |
| MadCat | Ghosts | MLG Fall Championship | 5 | 4 | 1 | 1.23 | 1.203 |
| ProoFy | Ghosts | MLG Fall Championship | 20 | 19 | 1 | 1.21 | 1.245 |
| Rambo | Ghosts | MLG Fall Championship | 20 | 19 | 1 | 0.81 | 0.797 |
| Apathy | Ghosts | MLG X Games Invitational | 18 | 17 | 1 | 1.13 | 1.108 |
| NAMELESS | Ghosts | MLG X Games Invitational | 19 | 18 | 1 | 1.03 | 1.073 |
| Parasite | Ghosts | MLG X Games Invitational | 19 | 18 | 1 | 0.96 | 1.01 |
| Classic | Ghosts | UMG Dallas 2014 | 11 | 10 | 1 | 1.13 | 1.167 |
| FormaL | Ghosts | UMG Dallas 2014 | 20 | 19 | 1 | 1.1 | 1.064 |
| JKap | Ghosts | UMG Dallas 2014 | 20 | 19 | 1 | 1.18 | 1.177 |
| MerK | Ghosts | UMG Dallas 2014 | 20 | 19 | 1 | 0.9 | 0.839 |
| NAMELESS | Ghosts | UMG Dallas 2014 | 20 | 19 | 1 | 1.08 | 1.062 |
| Slacked | Ghosts | UMG Dallas 2014 | 11 | 10 | 1 | 1.24 | 1.261 |
| Attach | Ghosts | UMG Philadelphia | 11 | 10 | 1 | 1.22 | 1.165 |
| NAMELESS | Ghosts | UMG Philadelphia | 15 | 14 | 1 | 1.26 | 1.272 |
| Parasite | Ghosts | UMG Philadelphia | 15 | 14 | 1 | 1.09 | 1.086 |
| ZooMaa | Ghosts | UMG Philadelphia | 3 | 2 | 1 | 0.86 | 1.333 |
| MiRx | Ghosts | UMG Philadelphia 2014 | 15 | 14 | 1 | 1.03 | 1.018 |
## Interpretation

- The pages are parseable through `api.php?action=query`; direct page HTML may be Cloudflare-challenged.
- Legacy rows are event aggregates with map counts, K/D, K/R, and mode-level aggregate splits. They do not expose per-map kills/deaths, maps, opponents, series IDs, or map results.
- Several Advanced Warfare regular-season rows are non-major or league-stage aggregates. They should not enter the site's major-only skill surface unless the product explicitly adds a broader stat context panel.
- Some overlap deltas are large because current `PlayerStats` has partial map rows for that player/event while codcompstats has a complete event aggregate. That is useful for display coverage but not for KOR, map-win reconstruction, or same-map replacement baselines.

## Recommended Next Steps

1. Design `legacy_player_event_stats.json` as a separate event-aggregate source with provenance fields before adding ingestion.
2. Start with Advanced Warfare because this audit found the clearest major-only and partial-current gains there.
3. Keep regular-season and non-major league aggregates quarantined unless a separate broader stat-context UI is explicitly designed.
4. If surfaced in the UI, show source badges such as `Map rows` vs `Legacy aggregate`; do not mix aggregate rows into map-row counts, KOR baselines, same-map validation, or map-win reconstruction.
