# Modern Warfare 3 Community Consensus

Issue scope: #15, fan/community consensus rankings only.

Inventory status: exhaustive-attempt v1.

This note applies the reproducible community-consensus method to Modern Warfare
3. It excludes official awards, media/creator/player lists, performance stats,
and the site's resume model.

The search pass used Reddit/community terms including `MW3`, `Modern Warfare
3`, `top 3`, `top 5`, `top 10`, `best players`, `Scump`, `MerK`, `BigTymeR`,
`BigT`, `Rambo`, `ProoFy`, `TeePee`, `MadCat`, `Joshh`, `Tommey`, `Swanny`,
`Parasite`, and `NAMELESS`.

The non-Reddit pass used old-forum/message-board terms including `forum`,
`message board`, `GameBattles`, `Major League Gaming`, `MLG`, `360 Icons`,
`GameFAQs`, `TheTechGame`, and `Se7enSins`, plus player gamertag clusters. A
promising 2012 360 Icons thread titled `Top 10 Players of MW3` was found through
a Reddit reference, but the original forum URL timed out and the source is
described as Nadeshot's list, so it is excluded from #15 as a player/creator
list rather than fan/community consensus.

No large aggregate MW3 community survey was found. If one is found later, score
it using `community_aggregate_survey` handling from
`analysis/community_consensus_methodology.md`.

## Method

1. Use only community sources with explicit MW3 player rankings.
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
   for thread clusters, weak Reddit-score weight when available, 0.50x for
   single community ballots, and the timing multiplier.
6. Sum weighted source scores across sources.

## Sources Scored

| Source id | Source | Context | Ballots scored | Notes |
|---|---|---:|---:|---|
| `mw3_reddit_2013_top3_each_game_thread` | [Top 3 players in each game since cod 4?](https://www.reddit.com/r/CoDCompetitive/comments/1tonlo/top_3_players_in_each_game_since_cod_4/) | near-contemporaneous community thread | 6 | Multiple top-three comments; includes Scump/ProoFy/MerK, Scump/ProoFy/TeeP, and one Rambo/MerK/BigTymeR ballot. |
| `mw3_reddit_2017_top5_each_cod_thread` | [Top 5 Players from each CoD](https://www.reddit.com/r/CoDCompetitive/comments/6emozs/top_5_players_from_each_cod_cod_4iw/) | retrospective community thread | 4 | Top-five comments commonly include Scump, MerK, BigTymeR, Rambo, JKap, ACHES, and PHiZZURP. |
| `mw3_reddit_2014_best_player_each_cod_thread` | [Best Player from each COD?](https://www.reddit.com/r/CoDCompetitive/comments/26lqwg/best_player_from_each_cod/) | near-contemporaneous community thread | 15 | Best-player-by-title thread. Most extractable MW3 entries name Scump as #1; one longer top-three and one Scump/ProoFy tie are preserved. |
| `mw3_reddit_2025_top3_each_era_thread` | [The Top 3 Players of Each Era](https://www.reddit.com/r/CoDCompetitive/comments/1mztxvl/the_top_3_players_of_each_era/) | late retrospective community ballot | 1 | Clean Scump/BigTymeR/MerK ballot, discounted by the late-retrospective timing multiplier. |

## Sources Reviewed But Not Scored

| Source | Status | Reason |
|---|---|---|
| [Who Were The T10 Players In Black Ops 1 & MW3](https://www.reddit.com/r/CoDCompetitive/comments/hcc8ir/who_were_the_t10_players_in_black_ops_1_mw3/) | reviewed, not scored | The MW3 comments found were too vague for scoring: Scump plus broad team references rather than a clean list. |
| 360 Icons `Top 10 Players of MW3` | excluded | Promising contemporaneous old-forum source, but the original URL timed out and the source is Nadeshot's player/creator list, not fan/community consensus. |
| Legacy forum/message-board web search | reviewed, not scored | Searched title terms, ranking terms, 360 Icons, MLG/GameBattles terms, and player-gamertag clusters. No scoreable old-board community ballot was found. |
| [History of Call of Duty Esports](https://cod-esports.fandom.com/wiki/History_of_Call_of_Duty_Esports) | excluded | Useful history/results context for MW3's unusual event ecosystem, but not fan/community consensus. |
| [Call of Duty: Modern Warfare 3 Top Players](https://www.esportsearnings.com/games/258-call-of-duty-modern-warfare-3/top-players-online) | excluded | Prize/results context, not fan/community consensus. |

## Weighted Source Contributions

| Player | 2013 top-three | 2017 top-five | 2014 best-player | 2025 top-three | Total |
|---|---:|---:|---:|---:|---:|
| Scump | 1.095 | 1.000 | 1.696 | 0.450 | 4.242 |
| ProoFy | 0.665 | 0.000 | 0.163 | 0.000 | 0.828 |
| MerK | 0.313 | 0.350 | 0.000 | 0.150 | 0.813 |
| BigTymeR | 0.078 | 0.300 | 0.038 | 0.300 | 0.717 |
| Rambo | 0.235 | 0.350 | 0.000 | 0.000 | 0.585 |
| JKap | 0.000 | 0.300 | 0.000 | 0.000 | 0.300 |
| Parasite | 0.156 | 0.000 | 0.000 | 0.000 | 0.156 |
| TeeP | 0.156 | 0.000 | 0.000 | 0.000 | 0.156 |
| ACHES | 0.000 | 0.150 | 0.000 | 0.000 | 0.150 |
| PHiZZURP | 0.000 | 0.050 | 0.000 | 0.000 | 0.050 |

## Result

| Rank | Player | Score | Confidence | Interpretation |
|---:|---|---:|---|---|
| 1 | Scump | 4.242 | medium | Clear community-consensus #1 by a large margin. |
| 2 | ProoFy | 0.828 | low | Benefits from early top-three discussion and one Scump/ProoFy tie. |
| 3 | MerK | 0.813 | medium | Close to ProoFy; stronger in top-five/resume-adjacent discussion. |
| 4 | BigTymeR | 0.717 | medium | Close to MerK/Rambo and strongly supported by resume context. |
| 5 | Rambo | 0.585 | low | Appears in several top-three/top-five lists, but fewer sources overall. |
| 6 | JKap | 0.300 | low | Appears in retrospective top-five lists despite limited MW3 participation. |
| 7 | Parasite | 0.156 | low | One unordered/top-three signal. |
| 7 | TeeP | 0.156 | low | One top-three signal; low source depth. |
| 9 | ACHES | 0.150 | low | One top-five signal. |
| 10 | PHiZZURP | 0.050 | low | One back-end top-five signal. |

## Resume Sanity Check

| Consensus | Player | Wins | Events played | Top 2 | Top 3 | Top 4 | Avg place |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | Scump | 2 | 3 | 3 | 3 | 3 | 1.33 |
| 2 | ProoFy | 0 | 3 | 1 | 2 | 2 | 7.33 |
| 3 | MerK | 4 | 5 | 5 | 5 | 5 | 1.20 |
| 4 | BigTymeR | 4 | 5 | 5 | 5 | 5 | 1.20 |
| 5 | Rambo | 3 | 4 | 4 | 4 | 4 | 1.25 |
| 6 | JKap | 0 | 1 | 1 | 1 | 1 | 2.00 |
| 7 | Parasite | 1 | 2 | 1 | 2 | 2 | 2.00 |
| 8 | TeeP | 0 | 2 | 0 | 0 | 0 | 12.00 |
| 9 | ACHES | 0 | 1 | 0 | 0 | 0 | 7.00 |
| 10 | PHiZZURP | 0 | 4 | 1 | 1 | 2 | 4.50 |

## Takeaways

- Scump as MW3 #1 is the strongest signal found so far.
- The second tier is not stable. ProoFy, MerK, BigTymeR, and Rambo are tightly
  grouped and should not be overinterpreted as a precise 2-5 order.
- The resume sanity check pushes strongly toward MerK, BigTymeR, and Rambo as
  underweighted by consensus-list evidence. All three were on the dominant
  OpTic/apX core and have much stronger win/top-finish profiles than ProoFy.
- MW3 is an especially difficult title because the event ecosystem was odd:
  fewer MLG-style LANs, heavy online/scrim reputation, US teams traveling to EU
  events, and a mix of local/pick-up rosters.
- This title should display confidence/caveats prominently if surfaced in the
  app. The consensus layer answers "who did community lists name?" not "who had
  the best title resume?"
