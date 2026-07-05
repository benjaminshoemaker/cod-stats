# Black Ops 2 Community Consensus

Issue scope: #15, fan/community consensus rankings only.

Inventory status: exhaustive-attempt v1.

This note tests a reproducible way to summarize community consensus for one
title. It intentionally excludes official awards, media/creator/player lists,
performance stats, and the site's resume model.

The search pass used Reddit/community terms including `BO2`, `Black Ops 2`,
`blops2`, `top 5`, `top 10`, `best players`, `Karma`, `Crimsix`, `Clayster`,
`Parasite`, and `ACHES`. Sources are scored only when they contain explicit
ranked BO2 ballots. Broader debate threads are logged as reviewed but not scored
unless they contain a clean extractable ranking.

No large aggregate BO2 survey was found in the aggregate-survey deep dive. If one
is found later, score it using `community_aggregate_survey` handling from
`analysis/community_consensus_methodology.md` rather than the ordinary thread
cluster handling below.

## Method

1. Use only community sources with explicit Black Ops 2 player rankings.
2. Treat each Reddit thread as one source cluster. Ballots inside the same
   thread are averaged first, because comments in one thread are not fully
   independent of each other.
3. Inside each thread, extract explicit ranked ballots. Joke lists, pure stats
   comments, and unranked debate comments are not scored.
4. Convert each ranked ballot to normalized Borda points:

   ```text
   points = (list_size + 1 - rank) / list_size
   ```

   Examples: #1 on a top-10 list earns 1.0, #5 earns 0.6, #10 earns 0.1.
   #1 on a top-5 list earns 1.0, #5 earns 0.2.
5. Ties receive the average rank. Example: `Parasite/Aches` listed at 4/5 gives
   each player rank 4.5.
6. Average all ballot scores inside a thread to create that thread's base score.
7. Apply a diminishing sample-size multiplier to the thread:

   ```text
   sample_multiplier = min(1.5, sqrt(ballot_count) / 2)
   ```

   This gives larger threads more weight without letting one large Reddit thread
   dominate the whole model. One ballot is worth 0.5x, four ballots are worth
   1.0x, nine ballots are worth 1.5x, and the multiplier is capped at 1.5x.
8. Apply a weak Reddit-score multiplier from the thread/post score:

   | Reddit score | Multiplier |
   |---:|---:|
   | unknown / 0-2 | 1.00 |
   | 3-9 | 1.05 |
   | 10-24 | 1.10 |
   | 25-49 | 1.20 |
   | 50+ | 1.30 |

   Upvotes are intentionally weak. They can reflect agreement, but also timing,
   visibility, humor, and thread dynamics. Comment-level scores should be used
   in a future fully automated extractor when they are available for every
   scored ballot; this manual pass uses the thread/post score consistently
   because it is available for every scored source cluster.
9. Sum weighted thread scores across sources.

## Sources Scored

| Source id | Source | Context | Ballots scored | Reddit score | Sample mult. | Upvote mult. | Final source mult. | Notes |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `2016_top10_thread` | [Top 10 Players in BO2](https://www.reddit.com/r/CoDCompetitive/comments/4wv0pk/top_10_players_in_bo2/) | retrospective community thread | 8 | 7 | 1.414 | 1.05 | 1.485 | Main top-10 discussion with multiple explicit ranked lists. |
| `2020_top5_thread` | [Who are Top 5 Pros players from each CoD since 2013](https://www.reddit.com/r/CoDCompetitive/comments/ix1uff/who_are_top_5_pros_players_from_each_cod_since/) | retrospective community thread | 3 | 15 | 0.866 | 1.10 | 0.953 | Multi-title top-5 thread; only BO2 entries used. |
| `2022_top10_thread` | [Curious for those who watched back then, who were the top 10 players in BO2?](https://www.reddit.com/r/CoDCompetitive/comments/y6esqm/curious_for_those_who_watched_back_then_who_were/) | retrospective community thread | 6 | 28 | 1.225 | 1.20 | 1.470 | Includes ranked and one tiered/ordered approximation from the post body. |
| `2014_pro_vote_thread` | [Pro Vote for Best Players in Black Ops II?](https://www.reddit.com/r/CoDCompetitive/comments/299gyj/pro_vote_for_best_players_in_black_ops_ii/) | near-contemporaneous community thread | 6 | 5 | 1.225 | 1.05 | 1.286 | The requested pro vote was not found; explicit fan top-5 comments were scored. |
| `2020_detailed_top10_post` | [Detailed Top Bo2 Players](https://www.reddit.com/r/CoDCompetitive/comments/hswjc1/detailed_top_bo2_players_with_the_addition_of/) | retrospective community post | 1 | 11 | 0.500 | 1.10 | 0.550 | Single detailed top-10 post with explicit ranking. |

## Sources Reviewed But Not Scored

| Source | Status | Reason |
|---|---|---|
| [Who was better at BO2: Crimsix or Karma?](https://www.reddit.com/r/CoDCompetitive/comments/ao35zf/who_was_better_at_bo2_crimsix_or_karma/) | reviewed, not scored | Useful head-to-head debate, but not a full ranked BO2 ballot source. |
| [How good was Clayster?](https://www.reddit.com/r/CoDCompetitive/comments/2bza8x/how_good_was_clayster/) | reviewed, not scored | Corroborates Clay/Karma/Crim top-three consensus, but not a complete ranked ballot. |
| [How good was Karma on BO2, AW and Ghosts?](https://www.reddit.com/r/CoDCompetitive/comments/8f8kdd/how_good_was_karma_on_bo2_aw_and_ghosts/) | reviewed, not scored | Useful player-specific consensus, not a ranked BO2 list. |
| [Best Player from each COD?](https://www.reddit.com/r/CoDCompetitive/comments/26lqwg/best_player_from_each_cod/) | reviewed, not scored | Extractable top-one/top-three comments exist, but no consistent top-five/top-ten ballot set was extracted in this pass. |
| [Top 3 players in each game since cod 4?](https://www.reddit.com/r/CoDCompetitive/comments/1tonlo/top_3_players_in_each_game_since_cod_4/) | reviewed, not scored | Contains useful ordered BO2 comments, but the complete ranked-ballot extraction was not clean enough for this manual pass. |
| [Top 5 Players from each CoD](https://www.reddit.com/r/CoDCompetitive/comments/6emozs/top_5_players_from_each_cod_cod_4iw/) | reviewed, not scored | Contains BO2 top-five comments, but needs full comment extraction before scoring. |
| [Top 5 in each individual game BO1 through IW](https://www.reddit.com/r/CoDCompetitive/comments/qbcepx/top_5_in_each_individual_game_bo1_through_iw/) | reviewed, not scored | Contains BO2 top-five/HM comments, but needs full comment extraction before scoring. |

## Weighted Source Contributions

| Player | 2016 thread | 2020 thread | 2022 thread | 2014 thread | Detailed post | Total |
|---|---:|---:|---:|---:|---:|---:|
| Karma | 1.374 | 0.953 | 1.298 | 1.093 | 0.550 | 5.267 |
| Crimsix | 1.383 | 0.762 | 1.326 | 1.136 | 0.495 | 5.101 |
| Clayster | 1.123 | 0.317 | 1.011 | 0.772 | 0.385 | 3.608 |
| ACHES | 1.011 | 0.381 | 1.064 | 0.129 | 0.330 | 2.915 |
| Parasite | 0.788 | 0.381 | 0.763 | 0.472 | 0.440 | 2.844 |
| MiRx | 0.428 | 0.064 | 0.426 | 0.043 | 0.220 | 1.180 |
| TeeP | 0.576 | 0.000 | 0.301 | 0.171 | 0.000 | 1.048 |
| Scump | 0.241 | 0.000 | 0.619 | 0.043 | 0.055 | 0.957 |
| KiLLa | 0.260 | 0.000 | 0.147 | 0.000 | 0.275 | 0.682 |
| JKap | 0.242 | 0.000 | 0.073 | 0.000 | 0.165 | 0.481 |
| ProoFy | 0.186 | 0.000 | 0.098 | 0.000 | 0.110 | 0.394 |

## Result

| Rank | Player | Score | Interpretation |
|---:|---|---:|---|
| 1 | Karma | 5.267 | Most first-place support and the highest aggregate weighted score. |
| 2 | Crimsix | 5.101 | Very close to Karma; best or second-best in nearly every scored source. |
| 3 | Clayster | 3.608 | Clear third; consistently included near the top. |
| 4 | ACHES | 2.915 | Very close with Parasite; stronger in the larger top-10 threads. |
| 5 | Parasite | 2.844 | Very close with ACHES; stronger in several top-5-only lists. |
| 6 | MiRx | 1.180 | Frequent back-half top-10 support. |
| 7 | TeeP | 1.048 | Regularly present in the next tier after the consensus top five. |
| 8 | Scump | 0.957 | Clear top-10 community support, but divisive and outside the top-five consensus. |
| 9 | KiLLa | 0.682 | Back-end top-10 support. |
| 10 | JKap | 0.481 | Narrowly ahead of ProoFy for the last slot. |

## Takeaways

- The high-confidence top five is Karma, Crimsix, Clayster, ACHES, and Parasite.
- Karma vs. Crimsix should be displayed as a close race, not a decisive #1.
- ACHES vs. Parasite should also be displayed as close.
- Spots 6-10 are much lower confidence. MiRx, TeeP, Scump, KiLLa, JKap, and
  ProoFy form the next tier, with JKap/ProoFy especially close.
- Missing from this calculation: media/creator/player sources, official awards,
  stats, and resume results. Those belong to other tickets or supporting views,
  not issue #15.
