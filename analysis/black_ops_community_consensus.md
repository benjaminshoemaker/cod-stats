# Black Ops Community Consensus

Issue scope: #15, fan/community consensus rankings only.

Inventory status: exhaustive-attempt v1.

This note applies the reproducible community-consensus method to Black Ops. It
excludes official awards, media/creator/player lists, performance stats, and the
site's resume model.

The search pass used Reddit/community terms including `Black Ops`, `BO1`,
`blops`, `top 3`, `top 5`, `top 10`, `best players`, `JKap`, `Scump`,
`ProoFy`, `ACHES`, `ASSASS1N`, `John`, `MerK`, `BigTymeR`, `TeeP`, and
`StaiNViLLe`.

The non-Reddit pass used old-forum/message-board terms including `forum`,
`message board`, `GameBattles`, `Major League Gaming`, `MLG`, `GameFAQs`,
`TheTechGame`, and `Se7enSins`, plus player gamertag clusters. It did not find a
clean citable legacy-board ranked ballot in this pass. That search is logged as
reviewed-not-scored so future passes know it was attempted.

No large aggregate Black Ops community survey was found. If one is found later,
score it using `community_aggregate_survey` handling from
`analysis/community_consensus_methodology.md`.

## Method

1. Use only community sources with explicit Black Ops player rankings.
2. Treat each thread as one source cluster. Ballots inside the same thread are
   averaged first because comments in one thread are not fully independent.
3. Extract explicit ranked, tied, or clearly unordered player lists. Unordered
   lists are scored as tied ranks rather than forcing an invented order.
4. Convert each ballot to normalized Borda points:

   ```text
   points = (list_size + 1 - rank) / list_size
   ```

5. Apply the standard source weights from
   `analysis/community_consensus_methodology.md`: diminishing sample-size weight
   for thread clusters, weak Reddit-score weight when available, and 0.50x for
   single community ballots.
6. Apply the timing multiplier from
   `analysis/community_consensus_methodology.md`. Near-contemporaneous sources
   receive a modest 1.15x multiplier.
7. Sum weighted source scores across sources.

## Sources Scored

| Source id | Source | Context | Ballots scored | Notes |
|---|---|---:|---:|---|
| `black_ops_reddit_2015_top5_mw2_bo1_thread` | [Who were the top 5 players in MW2 and BO1?](https://www.reddit.com/r/CoDCompetitive/comments/3g521r/who_were_the_top_5_players_in_mw2_and_bo1/) | retrospective community thread | 6 | Strongest mixed top-five/tiered source; includes repeated JKap/Scump/ProoFy support. |
| `black_ops_reddit_2020_t10_bo1_mw3_thread` | [Who Were The T10 Players In Black Ops 1 & MW3](https://www.reddit.com/r/CoDCompetitive/comments/hcc8ir/who_were_the_t10_players_in_black_ops_1_mw3/) | retrospective community thread | 4 | Mostly unordered top-ten-style comments, scored as tied groups. |
| `black_ops_reddit_2013_top3_each_game_thread` | [Top 3 players in each game since cod 4?](https://www.reddit.com/r/CoDCompetitive/comments/1tonlo/top_3_players_in_each_game_since_cod_4/) | near-contemporaneous community thread | 6 | Consistent JKap/Scump/ProoFy top-three support. |
| `black_ops_reddit_2017_top5_each_cod_thread` | [Top 5 Players from each CoD](https://www.reddit.com/r/CoDCompetitive/comments/6emozs/top_5_players_from_each_cod_cod_4iw/) | retrospective community thread | 2 | Adds ASSASS1N, John, Rambo, and BigTymeR support around the top-five fringe. |
| `black_ops_reddit_2014_best_player_each_cod_thread` | [Best Player from each COD?](https://www.reddit.com/r/CoDCompetitive/comments/26lqwg/best_player_from_each_cod/) | near-contemporaneous community thread | 8 | Best-player thread; heavily supports JKap, with one JKap/Scump tie and one longer list. |
| `black_ops_reddit_2015_best_players_each_title_thread` | [Who were the best players in each title?](https://www.reddit.com/r/CoDCompetitive/comments/3q5nka/who_were_the_best_players_in_each_title/) | retrospective community post | 1 | Single clean JKap-over-Scump ballot. |
| `black_ops_reddit_2020_top_cod_players_post` | [Top CoD Players](https://www.reddit.com/r/CoDCompetitive/comments/hs0uqu/top_cod_players/) | retrospective community post | 1 | Single JKap/Scump/ACHES top-three ballot. |
| `black_ops_reddit_2016_pre_bo2_history_thread` | [History of Competitive CoD, pre-Black Ops 2](https://www.reddit.com/r/CoDCompetitive/comments/50e2oz/history_of_competitive_cod_preblack_ops_2/) | retrospective community-history thread | 1 | Secondary claim that JKap was voted best player, Scump second, ProoFy third; original vote was not found. |
| `black_ops_reddit_2022_best_player_each_title_thread` | [Best player on each title](https://www.reddit.com/r/CoDCompetitive/comments/ww7lg7/best_player_on_each_title/) | retrospective community thread | 7 | Best-player thread; overwhelmingly JKap, with one JKap-over-Scump ballot. |

## Sources Reviewed But Not Scored

| Source | Status | Reason |
|---|---|---|
| Legacy forum/message-board web search | reviewed, not scored | Searched title terms, ranking terms, and player-gamertag clusters across general web results and likely older community domains. No clean ranked legacy-board ballot was found. |
| [Top Players of 2011 for Call of Duty: Black Ops](https://www.esportsearnings.com/history/2011/games/243-call-of-duty-black-ops) | excluded | Useful results/earnings context, but not fan/community consensus. |

## Weighted Source Contributions

| Player | 2015 top-five | 2020 top-ten | 2013 top-three | 2017 top-five | 2014 best-player | 2015 single | 2020 single | 2016 history | 2022 best-player | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| JKap | 0.959 | 0.572 | 1.408 | 0.707 | 1.576 | 0.500 | 0.500 | 0.500 | 1.323 | 8.045 |
| Scump | 0.805 | 0.572 | 0.704 | 0.495 | 0.288 | 0.250 | 0.333 | 0.333 | 0.094 | 3.875 |
| ProoFy | 0.589 | 0.434 | 0.548 | 0.000 | 0.102 | 0.000 | 0.000 | 0.167 | 0.000 | 1.839 |
| ACHES | 0.385 | 0.572 | 0.156 | 0.283 | 0.000 | 0.000 | 0.167 | 0.000 | 0.000 | 1.563 |
| ASSASS1N | 0.128 | 0.572 | 0.000 | 0.283 | 0.051 | 0.000 | 0.000 | 0.000 | 0.000 | 1.034 |
| John | 0.370 | 0.434 | 0.000 | 0.071 | 0.051 | 0.000 | 0.000 | 0.000 | 0.000 | 0.926 |
| MerK | 0.128 | 0.447 | 0.000 | 0.000 | 0.169 | 0.000 | 0.000 | 0.000 | 0.000 | 0.744 |
| TeeP | 0.000 | 0.572 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.572 |
| BigTymeR | 0.128 | 0.309 | 0.000 | 0.071 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.508 |
| StaiNViLLe | 0.180 | 0.297 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.476 |

## Result

| Rank | Player | Score | Confidence | Interpretation |
|---:|---|---:|---|---|
| 1 | JKap | 8.045 | high | Clear community-consensus #1 in this pass. Multiple best-player threads converge on him. |
| 2 | Scump | 3.875 | high | Clear #2 by scored consensus; appears across every scored source. |
| 3 | ProoFy | 1.839 | high | Strong top-three support, especially in older top-three/top-five threads. |
| 4 | ACHES | 1.563 | high | Consistent top-five support; close enough to ProoFy that this should be sanity-checked. |
| 5 | ASSASS1N | 1.034 | medium | Stronger in unordered/tiered sources; top-five placement is less certain than top four. |
| 6 | John | 0.926 | medium | Frequent support around the top-five edge. |
| 7 | MerK | 0.744 | medium | Appears in fewer consensus ballots than expected from resume strength. |
| 8 | TeeP | 0.572 | low | Appears mainly through the 2020 top-ten thread in this extraction, despite strong resume results. |
| 9 | BigTymeR | 0.508 | medium | Lower than resume context would suggest; supported mostly by unordered/tiered lists. |
| 10 | StaiNViLLe | 0.476 | low | Back-end top-ten support. |

Ranked outside the top ten: Dedo, Rambo, Bobby, Censor, TwiZz, Vengeance,
Saints, Moho, and Virus.

## Takeaways

- JKap as Black Ops #1 is the strongest signal found so far.
- Scump is also strongly separated from the rest of the field as #2.
- ProoFy and ACHES form the next tier; their order is plausible but should be
  sanity-checked.
- Ranks 5-10 are much less stable. ASSASS1N, John, MerK, TeeP, BigTymeR,
  StaiNViLLe, Dedo, and Rambo should be treated as a broader second/third tier,
  not a precise ordering.
- TeeP, MerK, and BigTymeR are likely underrepresented by this consensus-only
  method compared with results/resume data. That is not a scoring bug; it is a
  signal that the community-consensus layer and resume layer answer different
  questions.
