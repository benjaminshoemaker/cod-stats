# Community Consensus Methodology

Issue scope: #15, fan/community consensus rankings only.

This method summarizes community consensus for the best players in a given Call
of Duty title. It excludes official awards, media/creator/player lists, raw
stats, and the site's resume model.

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

### Community Thread Cluster

Use this when a Reddit/community thread contains several individual ranked
comments but no official aggregate result.

Scoring:

```text
ballot_points = (list_size + 1 - rank) / list_size
thread_base_score = average(ballot_points inside the thread)
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

### Single Community Ballot

Use this when one community post/comment contains a clean ranked list but is not
itself an aggregate survey.

Scoring:

```text
source_contribution = ballot_points * 0.50 * reddit_score_multiplier
```

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

## Confidence

High confidence:

- One strong aggregate survey with 100+ valid ballots, or
- Five or more scored source clusters with no single source contributing more
  than half the player's score.

Medium confidence:

- Three or more scored source clusters, or
- One aggregate source with unknown sample size but clear methodology/ranking.

Low confidence:

- One or two ordinary thread clusters, or
- Single-ballot sources only.

Flag as `close_race` when adjacent ranks are within 5% of each other.

## Inventory Rules

Every title pass should maintain three lists:

- `scored`: sources included in the calculation.
- `reviewed_not_scored`: relevant sources without clean extractable rankings.
- `excluded`: media, creator, player, official award, stat, or resume sources
  that belong to other tickets.

Inventory status labels:

- `pilot`: enough to test the method, not enough to claim broad coverage.
- `expanded`: multiple search terms and source families checked.
- `exhaustive_attempt_v1`: broad search terms, known annual survey lineage,
  aggregate posts, and relevant discussion leads checked.
