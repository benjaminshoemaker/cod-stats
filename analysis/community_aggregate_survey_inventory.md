# Community Aggregate Survey Inventory

Issue scope: #15, fan/community aggregate rankings only.

This is a deep-dive inventory of large-sample or already-aggregated community
ranking sources. These should be scored as `community_aggregate_survey`, not as
ordinary Reddit discussion threads.

## Found Aggregate Sources

| Game | Source | Status | Sample / methodology notes | Coverage |
|---|---|---|---|---|
| Ghosts | [The Results - r/CoDCompetitive's list of the best players in Ghosts so far - Version 2](https://www.reddit.com/r/CoDCompetitive/comments/23hs5q/the_results_rcodcompetitives_list_of_the_best/) | usable aggregate | Says it used over 450 votes; first place got 10 points, second 9, etc.; notes duplicate vote filtering. | Top 30, mid-season/version 2. |
| Ghosts | [Official r/CoDCompetitive Top 50 Players in Ghosts - #5-1](https://www.reddit.com/r/CoDCompetitive/comments/2bwkow/official_rcodcompetitive_top_50_players_in_ghosts/) | usable aggregate, needs full-series reconstruction | Says rankings are based on a community poll; top two received 87% of first-place votes; links hub/full ranking image. | Top 50, end-of-title project. |
| Black Ops 3 | [r/CoDCompetitive's Top 30 North American Players in Black Ops 3 - Top 5](https://www.reddit.com/r/CoDCompetitive/comments/60prmj/rcodcompetitives_top_30_north_american_players_in/) | usable aggregate | Says the subreddit got hundreds of responses and a definitive ranking; links all list segments and full score image. | Top 30 NA only. |
| Infinite Warfare | [According to you the 10 best players in Infinite Warfare...](https://www.reddit.com/r/CoDCompetitive/comments/6itwrn/according_to_you_the_10_best_players_in_infinite/) | usable aggregate with caveat | Later annual posts label this as first half of season only. | Top 10, partial-season. |
| World War II | [Top 10 players in WWII in the opinion of r/CoDCompetitive - A Survey](https://www.reddit.com/r/CoDCompetitive/comments/a2dgog/top_10_players_in_wwii_in_the_opinion_of/) | survey lead | Survey collection post. | Input form, not final result. |
| World War II | [The top 10 players in WWII according to r/CoDCompetitive...](https://www.reddit.com/r/CoDCompetitive/comments/a2j9sq/the_top_10_players_in_wwii_according_to/) | usable aggregate | Result post; comment links full Google Sheets results and notes players outside image had less than 1% top-10 selection. | Top 10. |
| Black Ops 4 | [The top 10 players in Black Ops 4 according to r/CoDCompetitive...](https://www.reddit.com/r/CoDCompetitive/comments/cv8yev/the_top_10_players_in_black_ops_4_according_to/) | usable aggregate | Result post; later annual posts link the result image as BO4 Top 10. | Top 10. |
| Modern Warfare | [The top 30 players in Modern Warfare according to r/CoDCompetitive...](https://www.reddit.com/r/CoDCompetitive/comments/im3gkx/the_top_30_players_in_modern_warfare_according_to/) | usable aggregate | Result post includes methodology comment: 545 responses, 345 counted, 293 correctly filled, 52 marginally incorrect with extra players randomly removed; links previous years. | Top 30. |
| Black Ops Cold War | [Top 30 Players in Black Ops Cold War according to Reddit - 6th annual survey](https://www.reddit.com/r/CoDCompetitive/comments/pmun9u/top_30_players_in_black_ops_cold_war_according_to/) | survey lead | Collection post; says prior forms were successful. | Input form. |
| Black Ops Cold War | [Reddit's Top 30 Black Ops Cold War Players](https://www.reddit.com/r/CoDCompetitive/comments/po7hvz/reddits_top_30_black_ops_cold_war_players/) | usable aggregate | Result post linked by the 10th annual survey as CW result. | Top 30. |
| Vanguard | [7th annual r/CoDCompetitive Top 30 Players Survey - Vanguard Season](https://www.reddit.com/r/CoDCompetitive/comments/wl5lea/7th_annual_rcodcompetitive_top_30_players_survey/) | survey lead | Collection post for the annual survey. | Input form. |
| Vanguard | [Reddit's Top 30 Call of Duty Vanguard Players](https://www.reddit.com/r/CoDCompetitive/comments/woivlt/reddits_top_30_call_of_duty_vanguard_players/) | usable aggregate | Result post linked by the 10th annual survey as Vanguard result. | Top 30. |
| Modern Warfare II | [Reddit's Top 30 Modern Warfare II Players](https://www.reddit.com/r/CoDCompetitive/comments/151cutn/reddits_top_30_modern_warfare_ii_players/) | usable aggregate | Result post says it received just over 250 votes for overall season rankings. | Top 30. |
| Modern Warfare III | [Reddit's Top 30 Modern Warfare III Players](https://www.reddit.com/r/CoDCompetitive/comments/1f6ler9/reddits_top_30_modern_warfare_iii_players/) | usable aggregate | Result post linked by the 10th annual survey as MWIII result. | Top 30. |
| Black Ops 6 | [10th Annual r/CoDCompetitive Top 30 Players Survey](https://www.reddit.com/r/CoDCompetitive/comments/1mryi1d/10th_annual_rcodcompetitive_top_30_players_survey/) | survey lead | Collection post; gives scoring format: 20-11 = 1 point, 10-6 = 2, 5-2 = 3, first = 5; links previous games. | Input form. |
| Black Ops 6 | [r/CoDCompetitive's Top 30 Black Ops 6 Players](https://www.reddit.com/r/CoDCompetitive/comments/1n1ujv2/rcodcompetitives_top_30_black_ops_6_players/) | usable aggregate | Result post says just under 260 votes with about 48 troll votes. | Top 30. |

## Gaps / Not Found

| Game | Status | Notes |
|---|---|---|
| Black Ops 2 | no large aggregate survey found | Several ranked community threads exist, but no large-sample survey result was found in this pass. The "Pro Vote for Best Players in Black Ops II?" thread appears to be a request/lead, not a released result. |
| Advanced Warfare | no large aggregate survey found | Found normal top-10 discussion threads and retrospective debate, but no r/CoDCompetitive aggregate survey/result post comparable to Ghosts/BO3/WWII+. |

## Implementation Notes

- Aggregate surveys should get priority over ordinary thread clusters for the
  same title.
- If multiple aggregate surveys exist for a title, keep all of them but preserve
  timing/context. Example: Ghosts has a mid-season 450-vote result and a later
  Top 50 project.
- Partial-season aggregates should be marked with `coverage: partial_season`
  and should not be treated as equivalent to end-of-title surveys.
- Region-limited aggregates should be marked with `ranking_scope`. BO3's Top 30
  is explicitly North America only.
- Survey leads/input-form posts are useful provenance but should not be scored
  unless the corresponding result is missing and the form itself exposes enough
  data, which is unlikely.
