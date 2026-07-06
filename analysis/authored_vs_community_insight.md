# The Authored-List Check Mostly Confirms The Community List

Issue scope: #16 checked whether player, creator, and media rankings add a
separate signal from the #15 community-consensus title lists.

Short answer: mostly no.

The authored lists are useful, but not as a new ranking lane. They work better
as a validation check. When independent player/media lists and community lists
keep arriving at the same names, the community list gets more credible. It does
not need a second, parallel version saying almost the same thing.

## What We Checked

Two authored source families were clean enough to compare against the community
title rankings:

- Enable's player-authored Top 5 videos for BO2, Ghosts, AW, BO3, WWII, and
  BO4.
- Breaking Point's Top 20 player lists for MW2019, Cold War, Vanguard, MWII,
  MWIII, and BO6.

Those were compared against the existing `community_consensus.json` Top 5 or
Top 10 for the same title.

## Result

| Title | Authored source | Compared range | Match |
|---|---|---:|---|
| Black Ops 2 | Enable Top 5 | Top 5 | 5/5, exact order |
| Ghosts | Enable Top 5 | Top 5 | 4/5 |
| Advanced Warfare | Enable Top 5 | Top 5 | 5/5, exact order |
| Black Ops 3 | Enable Top 5 | Top 5 | 5/5, exact order |
| World War II | Enable Top 5 | Top 5 | 4/5 |
| Black Ops 4 | Enable Top 5 | Top 5 | 4/5 |
| Modern Warfare 2019 | Breaking Point Top 20 | Top 10 | 8/10 |
| Black Ops Cold War | Breaking Point Top 20 | Top 10 | 10/10, exact order |
| Vanguard | Breaking Point Top 20 | Top 10 | 10/10, exact order |
| Modern Warfare II | Breaking Point Top 20 | Top 10 | 10/10, exact order |
| Modern Warfare III | Breaking Point Top 20 | Top 10 | 10/10, exact order |
| Black Ops 6 | Breaking Point Top 20 | Top 10 | 10/10, exact order |

That is the finding.

The places that differ are not philosophical splits. They are normal boundary
and ordering disputes:

- Ghosts: Enable has FormaL in the Top 5; community has TeeP.
- WWII: Enable has TJHaLy in the Top 5; community has ZooMaa. SlasheR and
  Accuracy are swapped.
- BO4: Enable has Envoy in the Top 5; community has Dylan. Dashy, Simp, and
  Octane are the same top-three group in a different order.
- MW2019: Breaking Point has Mack and GodRx in the Top 10; community has Huke
  and Scump.

Those disagreements are worth noting. They are not enough to justify a separate
authored-ranking product.

## Recommendation

Keep the community list as the ranking.

Do not add an authored-list leaderboard right now. It would create a second
concept with almost the same output, weaker sample logic, and more caveats.

Do not quietly roll authored lists into the community score either. A player
video, a media Top 20, and a community survey are different kinds of evidence.
Blending them would require arbitrary weights, and the result would barely
change.

Use authored lists as corroboration:

- mention them in methodology as an external check;
- keep the source inventory for auditability;
- surface exceptions only when the authored source clearly disagrees with the
  community list.

Product label: `Community Consensus` is still the cleanest name. If this ever
becomes public copy, a subtitle is enough: "Community rankings, checked against
player and media lists."

## References

Primary authored-source inventory:

- `player_authored_sources.json`
- `player_authored_summary.json`
- `analysis/authored_rankings_recent_titles.md`
- `analysis/authored_rankings_legacy_titles.md`

Community-source inventory and method:

- `community_consensus.json`
- `community_consensus_sources.json`
- `analysis/community_consensus_methodology.md`
- `analysis/community_consensus_cross_title_rollup.md`

Authored sources used in the comparison:

- Enable, "Ranking The Top 5 COD Pros: Black Ops 2" - https://www.youtube.com/watch?v=XsHwB9IWIN0
- Enable, "Ranking The Top 5 COD Pros: GHOSTS" - https://www.youtube.com/watch?v=vL_MvgR-EY0
- Enable, "Ranking The Top 5 COD Pros: ADVANCED WARFARE" - https://www.youtube.com/watch?v=8yOFcbN8wos
- Enable, "Ranking The Top 5 COD Pros: Black Ops 3" - https://www.youtube.com/watch?v=Q1C4i3Vtt4A
- Reddit extraction summary for Enable's BO3 list - https://www.reddit.com/r/CoDCompetitive/comments/lgrlkk/enables_top_5_black_ops_3_players/
- Enable, "RANKING THE TOP 5 COD PROS: WW2" - https://www.youtube.com/watch?v=nUytyxjFt7Y
- Enable, "RANKING THE TOP 5 COD PROS: BLACK OPS 4" - https://www.youtube.com/watch?v=6DfAHGPqQGQ
- 2020 Breaking Point Awards - https://cod-esports.fandom.com/wiki/2020_Breaking_Point_Awards
- 2021 Breaking Point Awards - https://cod-esports.fandom.com/wiki/2021_Breaking_Point_Awards
- 2022 Breaking Point Awards - https://cod-esports.fandom.com/wiki/2022_Breaking_Point_Awards
- 2023 Breaking Point Awards - https://cod-esports.fandom.com/wiki/2023_Breaking_Point_Awards
- 2024 Breaking Point Awards - https://cod-esports.fandom.com/wiki/2024_Breaking_Point_Awards
- 2025 Breaking Point Awards - https://cod-esports.fandom.com/wiki/2025_Breaking_Point_Awards

Community title notes behind the comparison:

- `analysis/bo2_community_consensus.md`
- `analysis/ghosts_community_consensus.md`
- `analysis/advanced_warfare_community_consensus.md`
- `analysis/black_ops_3_community_consensus.md`
- `analysis/world_war_ii_community_consensus.md`
- `analysis/black_ops_4_community_consensus.md`
- `analysis/modern_warfare_2019_community_consensus.md`
- `analysis/black_ops_cold_war_community_consensus.md`
- `analysis/vanguard_community_consensus.md`
- `analysis/modern_warfare_ii_community_consensus.md`
- `analysis/modern_warfare_iii_community_consensus.md`
- `analysis/black_ops_6_community_consensus.md`
