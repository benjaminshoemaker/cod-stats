# Community Consensus Cross-Title Rollup

Includes titles currently pulled into #15 consensus data.

Method: each title rank becomes `((31 - rank) / 30) ** 2.5`. Every title has the same maximum value, but the curve is intentionally top-heavy so elite title ranks matter far more than lower top-30 placements. Source quality is handled within each title's consensus construction and confidence notes, not as a cross-title season multiplier. Played-but-unranked titles add no score, so `Score/title played` is the career-length normalized view. `Score/ranked title` is the peak/quality view. `Avg rank (ranked)` averages over ranked titles only; `Avg rank (played)` averages over all played titles with played-but-unranked titles counted as rank 31 — the same definition the site's Community page uses for its Average rank column. Event wins and played titles use the site's console-major universe (drop games/events and as-of cutoff from build_data.py).

Title weights: every included title = 1.00.

Site note: the `Score/title played` and `Score/ranked title` columns are analysis-only views. The community page's overall table intentionally shows one headline score per player (total score) with average rank, title count, event wins (context only), and top-N counts; the per-title normalizations stay in this report.

## Overall Total Score

| Overall | Player | Total score | Score/title played | Score/ranked title | Event wins | Played titles | Ranked titles | Top 1 | Top 3 | Top 5 | Top 10 | Avg rank (ranked) | Avg rank (played) | Top-10 title placements |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | Scump | 7.636 | 0.587 | 0.587 | 28 | 13 | 13 | 3 | 5 | 6 | 9 | 8.54 | 8.54 | Black Ops #2; Modern Warfare 3 #1; Black Ops 2 #8; Ghosts #4; Advanced Warfare #1; Black Ops 3 #1; Infinite Warfare #2; Modern Warfare #10; Black Ops Cold War #7 |
| 2 | Simp | 5.438 | 0.777 | 0.777 | 13 | 7 | 7 | 3 | 4 | 5 | 7 | 4.29 | 4.29 | Black Ops 4 #2; Modern Warfare #1; Black Ops Cold War #1; Vanguard #5; Modern Warfare II #10; Modern Warfare III #1; Black Ops 6 #10 |
| 3 | Dashy | 4.632 | 0.515 | 0.662 | 6 | 9 | 7 | 1 | 2 | 4 | 6 | 5.86 | 11.44 | World War II #8; Black Ops 4 #1; Vanguard #3; Modern Warfare II #8; Modern Warfare III #5; Black Ops 6 #5 |
| 4 | Cellium | 4.533 | 0.648 | 0.648 | 11 | 7 | 7 | 1 | 1 | 4 | 6 | 6.43 | 6.43 | Modern Warfare #5; Black Ops Cold War #4; Vanguard #1; Modern Warfare II #4; Modern Warfare III #6; Black Ops 6 #8 |
| 5 | aBeZy | 4.524 | 0.565 | 0.646 | 13 | 8 | 7 | 0 | 2 | 4 | 6 | 6.29 | 9.38 | Black Ops 4 #4; Modern Warfare #4; Black Ops Cold War #2; Vanguard #10; Modern Warfare II #2; Modern Warfare III #9 |
| 6 | Shotzzy | 4.346 | 0.724 | 0.724 | 9 | 6 | 6 | 0 | 3 | 3 | 6 | 4.83 | 4.83 | Modern Warfare #3; Black Ops Cold War #6; Vanguard #7; Modern Warfare II #9; Modern Warfare III #2; Black Ops 6 #2 |
| 7 | Crimsix | 4.305 | 0.430 | 0.478 | 38 | 10 | 9 | 1 | 2 | 2 | 6 | 11.11 | 13.10 | Black Ops 2 #2; Ghosts #1; Advanced Warfare #6; Black Ops 3 #6; Infinite Warfare #9; World War II #10 |
| 8 | Octane | 4.193 | 0.419 | 0.524 | 9 | 10 | 8 | 0 | 1 | 2 | 5 | 8.62 | 13.10 | Black Ops 3 #7; Infinite Warfare #4; Black Ops 4 #3; Modern Warfare #6; Modern Warfare II #6 |
| 9 | HyDra | 3.839 | 0.768 | 0.768 | 7 | 5 | 5 | 1 | 2 | 4 | 5 | 4.20 | 4.20 | Black Ops Cold War #9; Vanguard #4; Modern Warfare II #1; Modern Warfare III #3; Black Ops 6 #4 |
| 10 | FormaL | 3.682 | 0.460 | 0.460 | 23 | 8 | 8 | 1 | 3 | 3 | 3 | 12.00 | 12.00 | Advanced Warfare #3; Black Ops 3 #2; Infinite Warfare #1 |
| 11 | Clayster | 3.498 | 0.250 | 0.350 | 18 | 14 | 10 | 0 | 2 | 2 | 3 | 13.70 | 18.64 | Black Ops 2 #3; Ghosts #6; Advanced Warfare #2 |
| 12 | Karma | 3.124 | 0.347 | 0.521 | 24 | 9 | 6 | 1 | 2 | 2 | 4 | 9.33 | 16.56 | Black Ops 2 #1; Ghosts #3; Advanced Warfare #10; Black Ops 3 #9 |
| 13 | SlasheR | 3.041 | 0.234 | 0.338 | 9 | 13 | 9 | 0 | 1 | 2 | 4 | 15.11 | 20.00 | Advanced Warfare #7; Black Ops 3 #4; World War II #3; Black Ops 4 #8 |
| 14 | ACHES | 2.947 | 0.295 | 0.421 | 19 | 10 | 7 | 0 | 1 | 3 | 4 | 14.14 | 19.20 | Black Ops #4; Modern Warfare 3 #9; Black Ops 2 #4; Ghosts #2 |
| 15 | Envoy | 2.714 | 0.302 | 0.388 | 8 | 9 | 7 | 0 | 1 | 1 | 2 | 11.71 | 16.00 | Black Ops 4 #6; Modern Warfare #2 |
| 16 | JKap | 2.687 | 0.269 | 0.448 | 9 | 10 | 6 | 1 | 1 | 1 | 3 | 11.67 | 19.40 | Black Ops #1; Modern Warfare 3 #6; Black Ops 2 #10 |
| 17 | Scrap | 2.610 | 0.653 | 0.870 | 4 | 4 | 3 | 1 | 2 | 3 | 3 | 2.67 | 9.75 | Modern Warfare II #3; Modern Warfare III #4; Black Ops 6 #1 |
| 18 | ProoFy | 2.533 | 0.317 | 0.633 | 4 | 8 | 4 | 0 | 2 | 2 | 3 | 6.50 | 18.75 | Black Ops #3; Modern Warfare 3 #2; Ghosts #10 |
| 19 | Kenny | 2.463 | 0.274 | 0.352 | 10 | 9 | 7 | 1 | 1 | 1 | 2 | 14.43 | 18.11 | World War II #1; Vanguard #6 |
| 20 | TeeP | 2.359 | 0.393 | 0.590 | 18 | 6 | 4 | 0 | 0 | 1 | 4 | 6.75 | 14.83 | Black Ops #8; Modern Warfare 3 #7; Black Ops 2 #7; Ghosts #5 |
| 21 | John | 2.317 | 0.211 | 0.463 | 7 | 11 | 5 | 0 | 1 | 1 | 3 | 13.40 | 23.00 | Black Ops #6; Black Ops 3 #3; World War II #6 |
| 22 | Arcitys | 2.186 | 0.219 | 0.364 | 9 | 10 | 6 | 0 | 0 | 0 | 2 | 11.50 | 19.30 | Infinite Warfare #7; Modern Warfare #7 |
| 23 | Huke | 2.136 | 0.214 | 0.356 | 7 | 10 | 6 | 0 | 0 | 1 | 3 | 13.33 | 20.40 | Advanced Warfare #4; Modern Warfare #8; Black Ops 6 #6 |
| 24 | Pred | 2.136 | 0.534 | 0.534 | 3 | 4 | 4 | 0 | 1 | 2 | 3 | 10.75 | 10.75 | Vanguard #2; Modern Warfare II #5; Modern Warfare III #8 |
| 25 | Gunless | 2.048 | 0.256 | 0.512 | 6 | 8 | 4 | 0 | 2 | 2 | 2 | 11.75 | 21.38 | Infinite Warfare #2; World War II #2 |
| 26 | Saints | 1.683 | 0.168 | 0.281 | 4 | 10 | 6 | 0 | 0 | 0 | 1 | 13.33 | 20.40 | Advanced Warfare #8 |
| 27 | Parasite | 1.655 | 0.166 | 0.331 | 7 | 10 | 5 | 0 | 0 | 1 | 2 | 15.20 | 23.10 | Modern Warfare 3 #7; Black Ops 2 #5 |
| 28 | MerK | 1.622 | 0.270 | 0.541 | 10 | 6 | 3 | 0 | 1 | 1 | 2 | 8.33 | 19.67 | Black Ops #7; Modern Warfare 3 #3 |
| 29 | ZooMaa | 1.613 | 0.202 | 0.230 | 6 | 8 | 7 | 0 | 0 | 2 | 2 | 18.29 | 19.88 | Advanced Warfare #5; World War II #5 |
| 30 | Apathy | 1.604 | 0.160 | 0.401 | 6 | 10 | 4 | 0 | 0 | 1 | 2 | 11.00 | 23.00 | Ghosts #8; Black Ops 3 #5 |
| 31 | Attach | 1.545 | 0.119 | 0.155 | 7 | 13 | 10 | 0 | 0 | 0 | 1 | 17.90 | 20.92 | Vanguard #9 |
| 32 | Drazah | 1.353 | 0.226 | 0.271 | 7 | 6 | 5 | 0 | 0 | 0 | 1 | 14.20 | 17.00 | Modern Warfare III #7 |
| 33 | CleanX | 1.325 | 0.189 | 0.221 | 5 | 7 | 6 | 0 | 0 | 0 | 1 | 16.17 | 18.29 | Black Ops Cold War #10 |
| 34 | BigTymeR | 1.247 | 0.312 | 0.416 | 8 | 4 | 3 | 0 | 0 | 1 | 2 | 12.67 | 17.25 | Black Ops #9; Modern Warfare 3 #4 |
| 35 | Sib | 1.112 | 0.278 | 0.278 | 2 | 4 | 4 | 0 | 0 | 0 | 1 | 14.50 | 14.50 | Vanguard #8 |
| 36 | Rambo | 1.018 | 0.255 | 0.339 | 4 | 4 | 3 | 0 | 0 | 1 | 1 | 18.67 | 21.75 | Modern Warfare 3 #5 |
| 37 | Classic | 0.953 | 0.106 | 0.318 | 5 | 9 | 3 | 0 | 0 | 0 | 1 | 22.00 | 28.00 | Infinite Warfare #6 |
| 38 | Insight | 0.925 | 0.132 | 0.231 | 4 | 7 | 4 | 0 | 0 | 1 | 1 | 17.75 | 23.43 | Black Ops Cold War #5 |
| 39 | Cammy | 0.906 | 0.113 | 0.226 | 3 | 8 | 4 | 0 | 1 | 1 | 1 | 19.75 | 25.38 | Black Ops Cold War #3 |
| 40 | Priestahh | 0.895 | 0.081 | 0.149 | 9 | 11 | 6 | 0 | 0 | 0 | 1 | 19.17 | 24.55 | Black Ops 4 #7 |
| 41 | Skyz | 0.887 | 0.111 | 0.148 | 7 | 8 | 6 | 0 | 0 | 0 | 1 | 19.67 | 22.50 | Modern Warfare #9 |
| 42 | TJHaLy | 0.869 | 0.087 | 0.290 | 5 | 10 | 3 | 0 | 0 | 0 | 1 | 15.00 | 26.20 | World War II #7 |
| 43 | Jurd | 0.865 | 0.096 | 0.216 | 6 | 9 | 4 | 0 | 0 | 0 | 0 | 15.50 | 24.11 | none |
| 44 | Mercules | 0.842 | 0.842 | 0.842 | 2 | 1 | 1 | 0 | 1 | 1 | 1 | 3.00 | 3.00 | Black Ops 6 #3 |
| 45 | Bance | 0.794 | 0.072 | 0.198 | 4 | 11 | 4 | 0 | 0 | 0 | 1 | 20.25 | 27.09 | Infinite Warfare #8 |
| 46 | Skrapz | 0.786 | 0.112 | 0.262 | 0 | 7 | 3 | 0 | 0 | 0 | 1 | 16.00 | 24.57 | Black Ops 4 #9 |
| 47 | Accuracy | 0.768 | 0.070 | 0.768 | 5 | 11 | 1 | 0 | 0 | 1 | 1 | 4.00 | 28.55 | World War II #4 |
| 48 | KiSMET | 0.729 | 0.104 | 0.182 | 5 | 7 | 4 | 0 | 0 | 0 | 1 | 18.75 | 24.00 | Modern Warfare II #7 |
| 49 | Slacked | 0.729 | 0.073 | 0.365 | 6 | 10 | 2 | 0 | 0 | 0 | 1 | 11.00 | 27.00 | Black Ops 3 #10 |
| 50 | Zer0 | 0.714 | 0.089 | 0.238 | 1 | 8 | 3 | 0 | 0 | 1 | 1 | 19.67 | 26.75 | Infinite Warfare #5 |
| 51 | Dylan | 0.699 | 0.175 | 0.699 | 0 | 4 | 1 | 0 | 0 | 1 | 1 | 5.00 | 24.50 | Black Ops 4 #5 |
| 52 | ASSASS1N | 0.699 | 0.140 | 0.350 | 1 | 5 | 2 | 0 | 0 | 1 | 1 | 25.00 | 28.60 | Black Ops #5 |
| 53 | Dedo | 0.682 | 0.097 | 0.341 | 4 | 7 | 2 | 0 | 0 | 0 | 0 | 11.50 | 25.43 | none |
| 54 | Enable | 0.674 | 0.084 | 0.135 | 8 | 8 | 5 | 0 | 0 | 0 | 1 | 23.40 | 26.25 | Advanced Warfare #9 |
| 55 | Ghosty | 0.660 | 0.220 | 0.220 | 2 | 3 | 3 | 0 | 0 | 0 | 1 | 15.33 | 15.33 | Modern Warfare III #10 |
| 56 | MiRx | 0.635 | 0.091 | 0.318 | 4 | 7 | 2 | 0 | 0 | 0 | 1 | 17.50 | 27.14 | Black Ops 2 #6 |
| 57 | Neptune | 0.622 | 0.155 | 0.311 | 0 | 4 | 2 | 0 | 0 | 0 | 1 | 14.50 | 22.75 | Black Ops 6 #7 |
| 58 | Temp | 0.608 | 0.076 | 0.203 | 1 | 8 | 3 | 0 | 0 | 0 | 1 | 16.33 | 25.50 | Black Ops 4 #10 |
| 59 | KiLLa | 0.584 | 0.065 | 0.292 | 4 | 9 | 2 | 0 | 0 | 0 | 1 | 13.50 | 27.11 | Black Ops 2 #9 |
| 60 | Nadeshot | 0.572 | 0.114 | 0.572 | 6 | 5 | 1 | 0 | 0 | 0 | 1 | 7.00 | 26.20 | Ghosts #7 |

## Normalized By Played Titles

Minimum 3 played titles.

| Rank | Player | Total score | Score/title played | Score/ranked title | Event wins | Played titles | Ranked titles | Top 1 | Top 3 | Top 5 | Top 10 | Avg rank (ranked) | Avg rank (played) | Top-10 title placements |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | Simp | 5.438 | 0.777 | 0.777 | 13 | 7 | 7 | 3 | 4 | 5 | 7 | 4.29 | 4.29 | Black Ops 4 #2; Modern Warfare #1; Black Ops Cold War #1; Vanguard #5; Modern Warfare II #10; Modern Warfare III #1; Black Ops 6 #10 |
| 2 | HyDra | 3.839 | 0.768 | 0.768 | 7 | 5 | 5 | 1 | 2 | 4 | 5 | 4.20 | 4.20 | Black Ops Cold War #9; Vanguard #4; Modern Warfare II #1; Modern Warfare III #3; Black Ops 6 #4 |
| 3 | Shotzzy | 4.346 | 0.724 | 0.724 | 9 | 6 | 6 | 0 | 3 | 3 | 6 | 4.83 | 4.83 | Modern Warfare #3; Black Ops Cold War #6; Vanguard #7; Modern Warfare II #9; Modern Warfare III #2; Black Ops 6 #2 |
| 4 | Scrap | 2.610 | 0.653 | 0.870 | 4 | 4 | 3 | 1 | 2 | 3 | 3 | 2.67 | 9.75 | Modern Warfare II #3; Modern Warfare III #4; Black Ops 6 #1 |
| 5 | Cellium | 4.533 | 0.648 | 0.648 | 11 | 7 | 7 | 1 | 1 | 4 | 6 | 6.43 | 6.43 | Modern Warfare #5; Black Ops Cold War #4; Vanguard #1; Modern Warfare II #4; Modern Warfare III #6; Black Ops 6 #8 |
| 6 | Scump | 7.636 | 0.587 | 0.587 | 28 | 13 | 13 | 3 | 5 | 6 | 9 | 8.54 | 8.54 | Black Ops #2; Modern Warfare 3 #1; Black Ops 2 #8; Ghosts #4; Advanced Warfare #1; Black Ops 3 #1; Infinite Warfare #2; Modern Warfare #10; Black Ops Cold War #7 |
| 7 | aBeZy | 4.524 | 0.565 | 0.646 | 13 | 8 | 7 | 0 | 2 | 4 | 6 | 6.29 | 9.38 | Black Ops 4 #4; Modern Warfare #4; Black Ops Cold War #2; Vanguard #10; Modern Warfare II #2; Modern Warfare III #9 |
| 8 | Pred | 2.136 | 0.534 | 0.534 | 3 | 4 | 4 | 0 | 1 | 2 | 3 | 10.75 | 10.75 | Vanguard #2; Modern Warfare II #5; Modern Warfare III #8 |
| 9 | Dashy | 4.632 | 0.515 | 0.662 | 6 | 9 | 7 | 1 | 2 | 4 | 6 | 5.86 | 11.44 | World War II #8; Black Ops 4 #1; Vanguard #3; Modern Warfare II #8; Modern Warfare III #5; Black Ops 6 #5 |
| 10 | FormaL | 3.682 | 0.460 | 0.460 | 23 | 8 | 8 | 1 | 3 | 3 | 3 | 12.00 | 12.00 | Advanced Warfare #3; Black Ops 3 #2; Infinite Warfare #1 |
| 11 | Crimsix | 4.305 | 0.430 | 0.478 | 38 | 10 | 9 | 1 | 2 | 2 | 6 | 11.11 | 13.10 | Black Ops 2 #2; Ghosts #1; Advanced Warfare #6; Black Ops 3 #6; Infinite Warfare #9; World War II #10 |
| 12 | Octane | 4.193 | 0.419 | 0.524 | 9 | 10 | 8 | 0 | 1 | 2 | 5 | 8.62 | 13.10 | Black Ops 3 #7; Infinite Warfare #4; Black Ops 4 #3; Modern Warfare #6; Modern Warfare II #6 |
| 13 | TeeP | 2.359 | 0.393 | 0.590 | 18 | 6 | 4 | 0 | 0 | 1 | 4 | 6.75 | 14.83 | Black Ops #8; Modern Warfare 3 #7; Black Ops 2 #7; Ghosts #5 |
| 14 | Karma | 3.124 | 0.347 | 0.521 | 24 | 9 | 6 | 1 | 2 | 2 | 4 | 9.33 | 16.56 | Black Ops 2 #1; Ghosts #3; Advanced Warfare #10; Black Ops 3 #9 |
| 15 | ProoFy | 2.533 | 0.317 | 0.633 | 4 | 8 | 4 | 0 | 2 | 2 | 3 | 6.50 | 18.75 | Black Ops #3; Modern Warfare 3 #2; Ghosts #10 |
| 16 | BigTymeR | 1.247 | 0.312 | 0.416 | 8 | 4 | 3 | 0 | 0 | 1 | 2 | 12.67 | 17.25 | Black Ops #9; Modern Warfare 3 #4 |
| 17 | Envoy | 2.714 | 0.302 | 0.388 | 8 | 9 | 7 | 0 | 1 | 1 | 2 | 11.71 | 16.00 | Black Ops 4 #6; Modern Warfare #2 |
| 18 | ACHES | 2.947 | 0.295 | 0.421 | 19 | 10 | 7 | 0 | 1 | 3 | 4 | 14.14 | 19.20 | Black Ops #4; Modern Warfare 3 #9; Black Ops 2 #4; Ghosts #2 |
| 19 | Sib | 1.112 | 0.278 | 0.278 | 2 | 4 | 4 | 0 | 0 | 0 | 1 | 14.50 | 14.50 | Vanguard #8 |
| 20 | Kenny | 2.463 | 0.274 | 0.352 | 10 | 9 | 7 | 1 | 1 | 1 | 2 | 14.43 | 18.11 | World War II #1; Vanguard #6 |
| 21 | MerK | 1.622 | 0.270 | 0.541 | 10 | 6 | 3 | 0 | 1 | 1 | 2 | 8.33 | 19.67 | Black Ops #7; Modern Warfare 3 #3 |
| 22 | JKap | 2.687 | 0.269 | 0.448 | 9 | 10 | 6 | 1 | 1 | 1 | 3 | 11.67 | 19.40 | Black Ops #1; Modern Warfare 3 #6; Black Ops 2 #10 |
| 23 | Gunless | 2.048 | 0.256 | 0.512 | 6 | 8 | 4 | 0 | 2 | 2 | 2 | 11.75 | 21.38 | Infinite Warfare #2; World War II #2 |
| 24 | Rambo | 1.018 | 0.255 | 0.339 | 4 | 4 | 3 | 0 | 0 | 1 | 1 | 18.67 | 21.75 | Modern Warfare 3 #5 |
| 25 | Clayster | 3.498 | 0.250 | 0.350 | 18 | 14 | 10 | 0 | 2 | 2 | 3 | 13.70 | 18.64 | Black Ops 2 #3; Ghosts #6; Advanced Warfare #2 |
| 26 | SlasheR | 3.041 | 0.234 | 0.338 | 9 | 13 | 9 | 0 | 1 | 2 | 4 | 15.11 | 20.00 | Advanced Warfare #7; Black Ops 3 #4; World War II #3; Black Ops 4 #8 |
| 27 | Drazah | 1.353 | 0.226 | 0.271 | 7 | 6 | 5 | 0 | 0 | 0 | 1 | 14.20 | 17.00 | Modern Warfare III #7 |
| 28 | Ghosty | 0.660 | 0.220 | 0.220 | 2 | 3 | 3 | 0 | 0 | 0 | 1 | 15.33 | 15.33 | Modern Warfare III #10 |
| 29 | Arcitys | 2.186 | 0.219 | 0.364 | 9 | 10 | 6 | 0 | 0 | 0 | 2 | 11.50 | 19.30 | Infinite Warfare #7; Modern Warfare #7 |
| 30 | Huke | 2.136 | 0.214 | 0.356 | 7 | 10 | 6 | 0 | 0 | 1 | 3 | 13.33 | 20.40 | Advanced Warfare #4; Modern Warfare #8; Black Ops 6 #6 |
| 31 | John | 2.317 | 0.211 | 0.463 | 7 | 11 | 5 | 0 | 1 | 1 | 3 | 13.40 | 23.00 | Black Ops #6; Black Ops 3 #3; World War II #6 |
| 32 | ZooMaa | 1.613 | 0.202 | 0.230 | 6 | 8 | 7 | 0 | 0 | 2 | 2 | 18.29 | 19.88 | Advanced Warfare #5; World War II #5 |
| 33 | CleanX | 1.325 | 0.189 | 0.221 | 5 | 7 | 6 | 0 | 0 | 0 | 1 | 16.17 | 18.29 | Black Ops Cold War #10 |
| 34 | Nameless | 0.526 | 0.175 | 0.175 | 0 | 3 | 3 | 0 | 0 | 0 | 1 | 19.67 | 19.67 | Ghosts #9 |
| 35 | Dylan | 0.699 | 0.175 | 0.699 | 0 | 4 | 1 | 0 | 0 | 1 | 1 | 5.00 | 24.50 | Black Ops 4 #5 |
| 36 | Saints | 1.683 | 0.168 | 0.281 | 4 | 10 | 6 | 0 | 0 | 0 | 1 | 13.33 | 20.40 | Advanced Warfare #8 |
| 37 | JoeDeceives | 0.497 | 0.166 | 0.249 | 0 | 3 | 2 | 0 | 0 | 0 | 1 | 16.00 | 21.00 | Black Ops 6 #9 |
| 38 | Parasite | 1.655 | 0.166 | 0.331 | 7 | 10 | 5 | 0 | 0 | 1 | 2 | 15.20 | 23.10 | Modern Warfare 3 #7; Black Ops 2 #5 |
| 39 | Apathy | 1.604 | 0.160 | 0.401 | 6 | 10 | 4 | 0 | 0 | 1 | 2 | 11.00 | 23.00 | Ghosts #8; Black Ops 3 #5 |
| 40 | Neptune | 0.622 | 0.155 | 0.311 | 0 | 4 | 2 | 0 | 0 | 0 | 1 | 14.50 | 22.75 | Black Ops 6 #7 |
| 41 | ASSASS1N | 0.699 | 0.140 | 0.350 | 1 | 5 | 2 | 0 | 0 | 1 | 1 | 25.00 | 28.60 | Black Ops #5 |
| 42 | Insight | 0.925 | 0.132 | 0.231 | 4 | 7 | 4 | 0 | 0 | 1 | 1 | 17.75 | 23.43 | Black Ops Cold War #5 |
| 43 | Abuzah | 0.483 | 0.121 | 0.242 | 0 | 4 | 2 | 0 | 0 | 0 | 0 | 14.00 | 22.50 | none |
| 44 | Attach | 1.545 | 0.119 | 0.155 | 7 | 13 | 10 | 0 | 0 | 0 | 1 | 17.90 | 20.92 | Vanguard #9 |
| 45 | Nadeshot | 0.572 | 0.114 | 0.572 | 6 | 5 | 1 | 0 | 0 | 0 | 1 | 7.00 | 26.20 | Ghosts #7 |
| 46 | Cammy | 0.906 | 0.113 | 0.226 | 3 | 8 | 4 | 0 | 1 | 1 | 1 | 19.75 | 25.38 | Black Ops Cold War #3 |
| 47 | Skrapz | 0.786 | 0.112 | 0.262 | 0 | 7 | 3 | 0 | 0 | 0 | 1 | 16.00 | 24.57 | Black Ops 4 #9 |
| 48 | Skyz | 0.887 | 0.111 | 0.148 | 7 | 8 | 6 | 0 | 0 | 0 | 1 | 19.67 | 22.50 | Modern Warfare #9 |
| 49 | Classic | 0.953 | 0.106 | 0.318 | 5 | 9 | 3 | 0 | 0 | 0 | 1 | 22.00 | 28.00 | Infinite Warfare #6 |
| 50 | KiSMET | 0.729 | 0.104 | 0.182 | 5 | 7 | 4 | 0 | 0 | 0 | 1 | 18.75 | 24.00 | Modern Warfare II #7 |
| 51 | Standy | 0.515 | 0.103 | 0.257 | 1 | 5 | 2 | 0 | 0 | 0 | 1 | 19.00 | 26.20 | Black Ops Cold War #8 |
| 52 | Dqvee | 0.410 | 0.102 | 0.410 | 0 | 4 | 1 | 0 | 0 | 0 | 1 | 10.00 | 25.75 | Infinite Warfare #10 |
| 53 | Dedo | 0.682 | 0.097 | 0.341 | 4 | 7 | 2 | 0 | 0 | 0 | 0 | 11.50 | 25.43 | none |
| 54 | Jurd | 0.865 | 0.096 | 0.216 | 6 | 9 | 4 | 0 | 0 | 0 | 0 | 15.50 | 24.11 | none |
| 55 | Vengeance | 0.279 | 0.093 | 0.279 | 2 | 3 | 1 | 0 | 0 | 0 | 0 | 13.00 | 25.00 | none |
| 56 | MiRx | 0.635 | 0.091 | 0.318 | 4 | 7 | 2 | 0 | 0 | 0 | 1 | 17.50 | 27.14 | Black Ops 2 #6 |
| 57 | Zer0 | 0.714 | 0.089 | 0.238 | 1 | 8 | 3 | 0 | 0 | 1 | 1 | 19.67 | 26.75 | Infinite Warfare #5 |
| 58 | TJHaLy | 0.869 | 0.087 | 0.290 | 5 | 10 | 3 | 0 | 0 | 0 | 1 | 15.00 | 26.20 | World War II #7 |
| 59 | Fero | 0.258 | 0.086 | 0.129 | 4 | 3 | 2 | 0 | 0 | 0 | 0 | 18.00 | 22.33 | none |
| 60 | Enable | 0.674 | 0.084 | 0.135 | 8 | 8 | 5 | 0 | 0 | 0 | 1 | 23.40 | 26.25 | Advanced Warfare #9 |

## Peak: Score Per Ranked Title

Minimum 3 ranked titles.

| Rank | Player | Total score | Score/title played | Score/ranked title | Event wins | Played titles | Ranked titles | Top 1 | Top 3 | Top 5 | Top 10 | Avg rank (ranked) | Avg rank (played) | Top-10 title placements |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | Scrap | 2.610 | 0.653 | 0.870 | 4 | 4 | 3 | 1 | 2 | 3 | 3 | 2.67 | 9.75 | Modern Warfare II #3; Modern Warfare III #4; Black Ops 6 #1 |
| 2 | Simp | 5.438 | 0.777 | 0.777 | 13 | 7 | 7 | 3 | 4 | 5 | 7 | 4.29 | 4.29 | Black Ops 4 #2; Modern Warfare #1; Black Ops Cold War #1; Vanguard #5; Modern Warfare II #10; Modern Warfare III #1; Black Ops 6 #10 |
| 3 | HyDra | 3.839 | 0.768 | 0.768 | 7 | 5 | 5 | 1 | 2 | 4 | 5 | 4.20 | 4.20 | Black Ops Cold War #9; Vanguard #4; Modern Warfare II #1; Modern Warfare III #3; Black Ops 6 #4 |
| 4 | Shotzzy | 4.346 | 0.724 | 0.724 | 9 | 6 | 6 | 0 | 3 | 3 | 6 | 4.83 | 4.83 | Modern Warfare #3; Black Ops Cold War #6; Vanguard #7; Modern Warfare II #9; Modern Warfare III #2; Black Ops 6 #2 |
| 5 | Dashy | 4.632 | 0.515 | 0.662 | 6 | 9 | 7 | 1 | 2 | 4 | 6 | 5.86 | 11.44 | World War II #8; Black Ops 4 #1; Vanguard #3; Modern Warfare II #8; Modern Warfare III #5; Black Ops 6 #5 |
| 6 | Cellium | 4.533 | 0.648 | 0.648 | 11 | 7 | 7 | 1 | 1 | 4 | 6 | 6.43 | 6.43 | Modern Warfare #5; Black Ops Cold War #4; Vanguard #1; Modern Warfare II #4; Modern Warfare III #6; Black Ops 6 #8 |
| 7 | aBeZy | 4.524 | 0.565 | 0.646 | 13 | 8 | 7 | 0 | 2 | 4 | 6 | 6.29 | 9.38 | Black Ops 4 #4; Modern Warfare #4; Black Ops Cold War #2; Vanguard #10; Modern Warfare II #2; Modern Warfare III #9 |
| 8 | ProoFy | 2.533 | 0.317 | 0.633 | 4 | 8 | 4 | 0 | 2 | 2 | 3 | 6.50 | 18.75 | Black Ops #3; Modern Warfare 3 #2; Ghosts #10 |
| 9 | TeeP | 2.359 | 0.393 | 0.590 | 18 | 6 | 4 | 0 | 0 | 1 | 4 | 6.75 | 14.83 | Black Ops #8; Modern Warfare 3 #7; Black Ops 2 #7; Ghosts #5 |
| 10 | Scump | 7.636 | 0.587 | 0.587 | 28 | 13 | 13 | 3 | 5 | 6 | 9 | 8.54 | 8.54 | Black Ops #2; Modern Warfare 3 #1; Black Ops 2 #8; Ghosts #4; Advanced Warfare #1; Black Ops 3 #1; Infinite Warfare #2; Modern Warfare #10; Black Ops Cold War #7 |
| 11 | MerK | 1.622 | 0.270 | 0.541 | 10 | 6 | 3 | 0 | 1 | 1 | 2 | 8.33 | 19.67 | Black Ops #7; Modern Warfare 3 #3 |
| 12 | Pred | 2.136 | 0.534 | 0.534 | 3 | 4 | 4 | 0 | 1 | 2 | 3 | 10.75 | 10.75 | Vanguard #2; Modern Warfare II #5; Modern Warfare III #8 |
| 13 | Octane | 4.193 | 0.419 | 0.524 | 9 | 10 | 8 | 0 | 1 | 2 | 5 | 8.62 | 13.10 | Black Ops 3 #7; Infinite Warfare #4; Black Ops 4 #3; Modern Warfare #6; Modern Warfare II #6 |
| 14 | Karma | 3.124 | 0.347 | 0.521 | 24 | 9 | 6 | 1 | 2 | 2 | 4 | 9.33 | 16.56 | Black Ops 2 #1; Ghosts #3; Advanced Warfare #10; Black Ops 3 #9 |
| 15 | Gunless | 2.048 | 0.256 | 0.512 | 6 | 8 | 4 | 0 | 2 | 2 | 2 | 11.75 | 21.38 | Infinite Warfare #2; World War II #2 |
| 16 | Crimsix | 4.305 | 0.430 | 0.478 | 38 | 10 | 9 | 1 | 2 | 2 | 6 | 11.11 | 13.10 | Black Ops 2 #2; Ghosts #1; Advanced Warfare #6; Black Ops 3 #6; Infinite Warfare #9; World War II #10 |
| 17 | John | 2.317 | 0.211 | 0.463 | 7 | 11 | 5 | 0 | 1 | 1 | 3 | 13.40 | 23.00 | Black Ops #6; Black Ops 3 #3; World War II #6 |
| 18 | FormaL | 3.682 | 0.460 | 0.460 | 23 | 8 | 8 | 1 | 3 | 3 | 3 | 12.00 | 12.00 | Advanced Warfare #3; Black Ops 3 #2; Infinite Warfare #1 |
| 19 | JKap | 2.687 | 0.269 | 0.448 | 9 | 10 | 6 | 1 | 1 | 1 | 3 | 11.67 | 19.40 | Black Ops #1; Modern Warfare 3 #6; Black Ops 2 #10 |
| 20 | ACHES | 2.947 | 0.295 | 0.421 | 19 | 10 | 7 | 0 | 1 | 3 | 4 | 14.14 | 19.20 | Black Ops #4; Modern Warfare 3 #9; Black Ops 2 #4; Ghosts #2 |
| 21 | BigTymeR | 1.247 | 0.312 | 0.416 | 8 | 4 | 3 | 0 | 0 | 1 | 2 | 12.67 | 17.25 | Black Ops #9; Modern Warfare 3 #4 |
| 22 | Apathy | 1.604 | 0.160 | 0.401 | 6 | 10 | 4 | 0 | 0 | 1 | 2 | 11.00 | 23.00 | Ghosts #8; Black Ops 3 #5 |
| 23 | Envoy | 2.714 | 0.302 | 0.388 | 8 | 9 | 7 | 0 | 1 | 1 | 2 | 11.71 | 16.00 | Black Ops 4 #6; Modern Warfare #2 |
| 24 | Arcitys | 2.186 | 0.219 | 0.364 | 9 | 10 | 6 | 0 | 0 | 0 | 2 | 11.50 | 19.30 | Infinite Warfare #7; Modern Warfare #7 |
| 25 | Huke | 2.136 | 0.214 | 0.356 | 7 | 10 | 6 | 0 | 0 | 1 | 3 | 13.33 | 20.40 | Advanced Warfare #4; Modern Warfare #8; Black Ops 6 #6 |
| 26 | Kenny | 2.463 | 0.274 | 0.352 | 10 | 9 | 7 | 1 | 1 | 1 | 2 | 14.43 | 18.11 | World War II #1; Vanguard #6 |
| 27 | Clayster | 3.498 | 0.250 | 0.350 | 18 | 14 | 10 | 0 | 2 | 2 | 3 | 13.70 | 18.64 | Black Ops 2 #3; Ghosts #6; Advanced Warfare #2 |
| 28 | Rambo | 1.018 | 0.255 | 0.339 | 4 | 4 | 3 | 0 | 0 | 1 | 1 | 18.67 | 21.75 | Modern Warfare 3 #5 |
| 29 | SlasheR | 3.041 | 0.234 | 0.338 | 9 | 13 | 9 | 0 | 1 | 2 | 4 | 15.11 | 20.00 | Advanced Warfare #7; Black Ops 3 #4; World War II #3; Black Ops 4 #8 |
| 30 | Parasite | 1.655 | 0.166 | 0.331 | 7 | 10 | 5 | 0 | 0 | 1 | 2 | 15.20 | 23.10 | Modern Warfare 3 #7; Black Ops 2 #5 |
| 31 | Classic | 0.953 | 0.106 | 0.318 | 5 | 9 | 3 | 0 | 0 | 0 | 1 | 22.00 | 28.00 | Infinite Warfare #6 |
| 32 | TJHaLy | 0.869 | 0.087 | 0.290 | 5 | 10 | 3 | 0 | 0 | 0 | 1 | 15.00 | 26.20 | World War II #7 |
| 33 | Saints | 1.683 | 0.168 | 0.281 | 4 | 10 | 6 | 0 | 0 | 0 | 1 | 13.33 | 20.40 | Advanced Warfare #8 |
| 34 | Sib | 1.112 | 0.278 | 0.278 | 2 | 4 | 4 | 0 | 0 | 0 | 1 | 14.50 | 14.50 | Vanguard #8 |
| 35 | Drazah | 1.353 | 0.226 | 0.271 | 7 | 6 | 5 | 0 | 0 | 0 | 1 | 14.20 | 17.00 | Modern Warfare III #7 |
| 36 | Skrapz | 0.786 | 0.112 | 0.262 | 0 | 7 | 3 | 0 | 0 | 0 | 1 | 16.00 | 24.57 | Black Ops 4 #9 |
| 37 | Zer0 | 0.714 | 0.089 | 0.238 | 1 | 8 | 3 | 0 | 0 | 1 | 1 | 19.67 | 26.75 | Infinite Warfare #5 |
| 38 | Insight | 0.925 | 0.132 | 0.231 | 4 | 7 | 4 | 0 | 0 | 1 | 1 | 17.75 | 23.43 | Black Ops Cold War #5 |
| 39 | ZooMaa | 1.613 | 0.202 | 0.230 | 6 | 8 | 7 | 0 | 0 | 2 | 2 | 18.29 | 19.88 | Advanced Warfare #5; World War II #5 |
| 40 | Cammy | 0.906 | 0.113 | 0.226 | 3 | 8 | 4 | 0 | 1 | 1 | 1 | 19.75 | 25.38 | Black Ops Cold War #3 |
| 41 | CleanX | 1.325 | 0.189 | 0.221 | 5 | 7 | 6 | 0 | 0 | 0 | 1 | 16.17 | 18.29 | Black Ops Cold War #10 |
| 42 | Ghosty | 0.660 | 0.220 | 0.220 | 2 | 3 | 3 | 0 | 0 | 0 | 1 | 15.33 | 15.33 | Modern Warfare III #10 |
| 43 | Jurd | 0.865 | 0.096 | 0.216 | 6 | 9 | 4 | 0 | 0 | 0 | 0 | 15.50 | 24.11 | none |
| 44 | Temp | 0.608 | 0.076 | 0.203 | 1 | 8 | 3 | 0 | 0 | 0 | 1 | 16.33 | 25.50 | Black Ops 4 #10 |
| 45 | Bance | 0.794 | 0.072 | 0.198 | 4 | 11 | 4 | 0 | 0 | 0 | 1 | 20.25 | 27.09 | Infinite Warfare #8 |
| 46 | KiSMET | 0.729 | 0.104 | 0.182 | 5 | 7 | 4 | 0 | 0 | 0 | 1 | 18.75 | 24.00 | Modern Warfare II #7 |
| 47 | Nameless | 0.526 | 0.175 | 0.175 | 0 | 3 | 3 | 0 | 0 | 0 | 1 | 19.67 | 19.67 | Ghosts #9 |
| 48 | Loony | 0.508 | 0.056 | 0.169 | 5 | 9 | 3 | 0 | 0 | 0 | 0 | 16.33 | 26.11 | none |
| 49 | Methodz | 0.485 | 0.044 | 0.162 | 2 | 11 | 3 | 0 | 0 | 0 | 1 | 20.33 | 28.09 | World War II #9 |
| 50 | Attach | 1.545 | 0.119 | 0.155 | 7 | 13 | 10 | 0 | 0 | 0 | 1 | 17.90 | 20.92 | Vanguard #9 |
| 51 | Priestahh | 0.895 | 0.081 | 0.149 | 9 | 11 | 6 | 0 | 0 | 0 | 1 | 19.17 | 24.55 | Black Ops 4 #7 |
| 52 | Skyz | 0.887 | 0.111 | 0.148 | 7 | 8 | 6 | 0 | 0 | 0 | 1 | 19.67 | 22.50 | Modern Warfare #9 |
| 53 | Enable | 0.674 | 0.084 | 0.135 | 8 | 8 | 5 | 0 | 0 | 0 | 1 | 23.40 | 26.25 | Advanced Warfare #9 |
| 54 | Owakening | 0.340 | 0.049 | 0.113 | 2 | 7 | 3 | 0 | 0 | 0 | 0 | 18.67 | 25.71 | none |
| 55 | iLLeY | 0.324 | 0.065 | 0.108 | 5 | 5 | 3 | 0 | 0 | 0 | 0 | 20.00 | 24.40 | none |
| 56 | Censor | 0.282 | 0.047 | 0.094 | 4 | 6 | 3 | 0 | 0 | 0 | 0 | 23.67 | 27.33 | none |
| 57 | Afro | 0.269 | 0.067 | 0.090 | 0 | 4 | 3 | 0 | 0 | 0 | 0 | 22.33 | 24.50 | none |
| 58 | Assault | 0.268 | 0.027 | 0.089 | 1 | 10 | 3 | 0 | 0 | 0 | 0 | 21.00 | 28.00 | none |
| 59 | Nastie | 0.088 | 0.018 | 0.029 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 25.67 | 27.80 | none |
| 60 | Beans | 0.010 | 0.002 | 0.003 | 0 | 4 | 3 | 0 | 0 | 0 | 0 | 28.33 | 29.00 | none |

