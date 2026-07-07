# Community Consensus Methodology

Issue scope: #15, fan/community consensus rankings only.

This method summarizes community consensus for the best players in a given Call
of Duty title. It excludes official awards, media/creator/player lists, raw
stats, and the site's resume model.

Prototype source files:

- `community_consensus_sources.json`
- `community_consensus_ballots.json`

Prototype scorer:

- `scripts/build_community_consensus.py`

## Source Types

### Community Aggregate Survey

Use this when a community source already collected many ballots and published an
aggregate ranking or score table. Examples include r/CoDCompetitive's annual
Top 30 surveys, the Ghosts Top 50 project, and the BO3 Top 30 NA project.

These sources are the strongest #15 evidence because the source has already
aggregated many community ballots.

Required fields:

```json
{
  "source_kind": "community_aggregate_survey",
  "game": "Ghosts",
  "url": "https://...",
  "title": "Official r/CoDCompetitive Top 50 Players in Ghosts",
  "published_date": "2014-07-27",
  "sample_size": 450,
  "ranking_scope": "global",
  "ranking_size": 50,
  "scoring_notes": "Published community-poll result; top five post links hub/full image.",
  "ranked_players": [
    {"player": "Crimsix", "rank": 1}
  ]
}
```

Scoring:

```text
rank_points = (ranking_size + 1 - rank) / ranking_size
sample_multiplier = min(3.0, max(1.5, sqrt(valid_ballots) / 10))
quality_multiplier =
  1.25 if the source publishes methodology, vote count, filtering, or full score details
  1.10 if the source publishes a clear ranking but limited methodology
  1.00 if the source publishes only a ranking image/list
source_contribution = rank_points * sample_multiplier * quality_multiplier
```

If valid ballot count is unknown, use:

```text
sample_multiplier = 1.75 for a named aggregate survey/project
sample_multiplier = 1.50 for an aggregate list with unclear collection details
```

Do not apply the ordinary Reddit thread upvote multiplier to aggregate surveys.
For a survey, the meaningful sample is the ballot count, not the Reddit post's
karma.

If an aggregate survey covers only part of a title, preserve that explicitly as
`season_coverage`. This is separate from timing. A mid-season poll can be
contemporaneous and high quality while still only measuring the first half of a
season.

### Community Thread Cluster

Use this when a Reddit/community thread contains several individual ranked
comments but no official aggregate result.

Scoring:

```text
ballot_points = (list_size + 1 - rank) / list_size

comment_reception_raw =
  1.00 if comment_score is missing or 0
  1 + 0.25 * log1p(score) / log1p(max_positive_score_in_thread) if score > 0
  1 - 0.25 * log1p(abs(score)) / log1p(max_abs_negative_score_in_thread) if score < 0

comment_reception_raw is clamped to [0.75, 1.25]
comment_reception_weight =
  comment_reception_raw / average(comment_reception_raw inside the thread)

thread_base_score =
  weighted_average(ballot_points inside the thread, comment_reception_weight)

sample_multiplier = min(1.5, sqrt(ballot_count) / 2)
reddit_score_multiplier =
  1.00 if unknown/0-2
  1.05 if 3-9
  1.10 if 10-24
  1.20 if 25-49
  1.30 if 50+
source_contribution = thread_base_score * sample_multiplier * reddit_score_multiplier
```

Thread comments are averaged before weighting because comments in one thread are
not fully independent of each other. More ballots help, but with diminishing
returns.

If comment-level Reddit scores are available, use them only as a bounded
within-thread reception weight. They do not add ballots and do not make the
thread itself more powerful. The normalization step keeps the average ballot
weight inside the thread at 1.0, so comment scores only redistribute the
thread's fixed base score among its own ballots. Store these as score snapshots,
not as true upvote/downvote counts, because Reddit exposes net scores and those
scores can be noisy or fuzzed.

### Single Community Ballot

Use this when one community post/comment contains a clean ranked list but is not
itself an aggregate survey.

Scoring:

```text
source_contribution = ballot_points * 0.50 * reddit_score_multiplier
```

## Source Timing

After source-type/sample/upvote weighting, apply a light timing multiplier:

```text
contemporaneous: 1.20
near_contemporaneous: 1.15
retrospective: 1.00
late_retrospective: 0.90
unknown: 1.00
```

This gives modest extra credit to polls/opinions gathered close to the title
being discussed. The multiplier is intentionally small because later community
threads can still include informed voters, and because source quality and sample
size should matter more than publication date alone.

## Season Coverage

After timing, apply a separate season-coverage multiplier:

```text
end_of_title: 1.00
late_season: 0.85
mid_season: 0.60
early_season: 0.40
partial_split_only: 0.30
unknown: 1.00
```

This prevents a mid-season or split-only result from counting like a full-title
verdict. Partial-season sources are still useful: they capture who was already
considered elite at the time, and they help identify whether a later ranking is
driven by late-season recency. They should not carry the same weight as an
end-of-title survey for final title consensus.

## Combining Sources

For each player-title pair:

```text
community_consensus_score = sum(source_contribution)
```

Rank players by `community_consensus_score`.

Output should include:

```json
{
  "game": "Black Ops 2",
  "player": "Karma",
  "consensus_rank": 1,
  "consensus_score": 5.267,
  "tier": "top_1",
  "source_count": 5,
  "aggregate_survey_count": 0,
  "thread_cluster_count": 4,
  "single_ballot_count": 1,
  "confidence": "medium",
  "notes": "No large aggregate BO2 survey found in exhaustive-attempt v1."
}
```

## Cross-Title Rollups

Each title has the same maximum career-rollup value. The rollup does not give
modern titles more weight because their source coverage is stronger; source
quality only affects the rank within a title and the confidence notes.

Convert each title rank to top-heavy normalized points:

```text
title_points = max(0, (31 - consensus_rank) / 30) ** 2.5
```

This keeps the score continuous while making elite title ranks matter far more
than lower top-30 placements. Played-but-unranked titles add zero points.

Analysis-report career rollups should show:

- total score;
- score per played title;
- score per ranked title;
- event wins;
- played titles;
- ranked titles;
- top-1, top-3, top-5, and top-10 title counts.

The site's overall table intentionally shows a narrower set: rank, player,
total score, average rank (played-but-unranked titles counted as rank 31),
title count (played titles), event wins (context only), top-1/3/5/10 counts,
and a trace link. Score-per-played-title and score-per-ranked-title remain
analysis-only views; they were removed from the page to keep one headline
score per player.

## Confidence

Confidence is a source-depth tag, implemented in
`scripts/build_community_consensus.py`:

High confidence:

- The player-title row is backed by at least one aggregate survey source, or
- Five or more scored sources.

Medium confidence:

- Three or four scored sources.

Low confidence:

- One or two scored sources; treat the resulting order as provisional.

(An earlier draft gated "high" on 100+ valid ballots and on no single source
contributing more than half the score. The shipped rule is intentionally the
simpler source-count/aggregate-presence version above; ballot counts and
per-source dominance stay visible in the trace so readers can judge depth
themselves.)

Flag as `close_race` when adjacent ranks are within 5% of each other. The site
surfaces this as a "close race" sub-label with the 5% definition in the tooltip
and in the methodology page's community-confidence section.

## Title Report Output

Every serial title report should show event wins in the headline consensus table
by default. The minimum table columns on the site's per-title view are:

- consensus rank;
- player;
- consensus score (displayed to 2 decimals; traces keep exact values);
- confidence;
- scored source count;
- title event wins (context only, never a scoring input — the winning events
  themselves are surfaced via the event-wins cell tooltip rather than a
  dedicated column, to keep the table scannable).

A separate "title events played" column is intentionally not shown: played-title
context lives in the overall rollup's Title count column, and per-title
participation detail belongs to the player pages. Analysis reports in this
directory may keep the fuller resume sanity-check tables (top-two/three/four
placements, average placement, events played); the site view deliberately stays
narrower. Do not make the user cross-reference a second table just to see
whether the consensus order passes the wins sanity check.

## Inventory Rules

Every title pass should maintain three lists:

- `scored`: sources included in the calculation.
- `reviewed_not_scored`: relevant sources without clean extractable rankings.
- `excluded`: media, creator, player, official award, stat, or resume sources
  that belong to other tickets.

Every title pass should also record the source families searched. Reddit is a
high-yield source, but it is not enough by itself, especially for older titles.
The discovery pass should include:

- Reddit/r/CoDCompetitive title-rank threads and player-specific debate threads.
- Known aggregate-survey lineage: Top 30/Top 50/community poll posts, image hubs,
  and follow-up threads.
- General web searches for old forums and message boards using title aliases,
  ranking terms, and player gamertag clusters.
- Targeted site searches for likely legacy homes such as MLG forums,
  GameBattles-adjacent discussions, GameFAQs, TheTechGame, Se7enSins, and other
  surviving community archives.
- Player-gamertag searches, especially for older titles where ranking discussion
  may appear in threads not titled as rankings.

Log old-board searches even when they find no clean ranked ballot. A
`reviewed_not_scored` source record is still useful because it prevents later
passes from mistaking "not found yet" for "not searched."

Inventory status labels:

- `pilot`: enough to test the method, not enough to claim broad coverage.
- `expanded`: multiple search terms and source families checked.
- `exhaustive_attempt_v1`: broad search terms, known annual survey lineage,
  aggregate posts, and relevant discussion leads checked.
