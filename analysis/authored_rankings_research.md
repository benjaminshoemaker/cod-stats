# Authored Ranking Sources Research

Issue scope: #16, media/player/creator/caster/coach-authored rankings and
explicit subjective player claims.

This is separate from:

- #15 fan/community consensus polls and threads;
- #13 objective stat sources and derived skill metrics;
- #11 formal awards, MVPs, and official or panel-voted honors.

## Verdict

Authored lists are useful as a labeled subjective evidence lane, but they should
not ship as a scored formula yet.

There are enough sourceable lists and claims to support an inventory and
evidence cards. There is not enough methodological consistency to treat these as
one clean ranking model. Sources mix greatness, skill, championships, peak,
longevity, role, popularity, and author familiarity in different proportions.
The first version should preserve each source as authored evidence rather than
aggregate it into a single "media score."

Recommended v1:

- build a normalized source file for authored rankings and claims;
- expose cited cards or rows on future player/debate pages;
- include source family, author type, date, scope, ranked players, claim tags,
  and caveats;
- do not blend authored sources into adjusted wins, Skill/KOR, formal honors, or
  community consensus.

Do not ship yet:

- a site-wide authored-list leaderboard;
- a combined creator/media/player score;
- uncited video-only claims without transcript, timestamp, or stable clip;
- role claims as facts without preserving the source identity and wording.

## Prototype Files

- `player_authored_sources.json` stores source metadata, extracted ranking
  entries, direct claims, and verification leads.
- `scripts/build_authored_sources.py` validates the source file and emits
  `player_authored_summary.json`.
- `player_authored_summary.json` is a generated research artifact with
  per-player authored evidence counts, best/median all-time ranks, claim tags,
  and verification leads.
- `tests/test_authored_sources.py` locks the v1 contract: source identity is
  preserved, verification leads are not ranked, and the builder does not create
  a consensus score.

## Source Inventory

### High Confidence

These sources have stable URLs, visible author/source identity, dates, and either
ranked lists or clear reported claims.

| Source | Date | Author/source type | Scope | Useful fields | Notes |
|---|---:|---|---|---|---|
| Nerd Street, "Top 10 greatest Call of Duty players of all time" | 2022-08-12 | media article, Brian Bencomo | all-time top 10 | rank, player, rationale, stated methodology | Strong first seed because it explains factors: tournament wins, Champs weight, Champs top-three finishes, and individual accolades. This is a greatness/resume-heavy list, not pure skill. URL: https://nerdstreet.com/news/2022/8/top-10-greatest-call-of-duty-players-all-time |
| Dexerto, "Top 10 best Call of Duty players of all time" | 2022 | media article | all-time top 10 | rank, player, role claims, rationale | Useful for all-time subjective placement and role/skill language such as "greatest AR" or "best entry SMG." Need capture exact publication date from page metadata if ingested. URL: https://www.dexerto.com/call-of-duty/top-10-best-call-of-duty-players-of-all-time-1900543/ |
| Dexerto, Nadeshot on Scump GOAT | 2023-01-18 | media report of player/owner claim | explicit GOAT/skill claim | quoted claim, claimant, reporter, player, claim tags | Strong claim source because it attributes Nadeshot's reasoning and separates talent/impact from resume. URL: https://www.dexerto.com/call-of-duty/nadeshot-gives-his-take-on-whether-scump-is-the-cod-goat-2036855/ |
| CoD Esports Wiki article, "Top 10 BEST Players of All Time" | 2018-06 | authored wiki article | all-time top 10 through 2018 | rank, player, methodology notes | Useful historical snapshot. Treat as authored article, not official wiki fact. URL: https://cod-esports.fandom.com/wiki/Article%3ATop_10_Players_of_All_Time |
| Breaking Point annual Top 20 article series | 2024-2025 examples | media/stat outlet, EasyMac | title-season top 20 | rank, title, player, role/stat rationale | Strong for modern title-specific authored lists. Each rank is often a separate article with rationale and stats. Example MW3 #1 Simp: https://breakingpoint.gg/posts/top-20-players-of-mw3-1-simp. Example BO6 #1 Scrap: https://breakingpoint.gg/posts/1-scrap-top-20-players-of-black-ops-6 |

### Medium Confidence

These are probably useful, but need timestamp/transcript work before ingestion.

| Source family | Why useful | Ingestion caveat |
|---|---|---|
| TacticalRab videos covering GOAT/player debates | Good coverage of creator/media discourse, player/caster comments, and current debate framing. | Use only with stable YouTube URL, timestamp, and either transcript or hand-verified quote. Do not ingest from video title alone. |
| The Flank / Reverse Sweep / player podcasts | Useful for player/caster/coach claims and role-specific rationale. | Needs timestamped clips or transcripts. Host banter should be marked as discussion, not a formal ranking. |
| Player/creator top-N videos, e.g. Attach and Temp top-30 most talented list | Useful for talent-specific scope distinct from GOAT/resume. | Must preserve that "most talented" is not "greatest." Need full ranked list and timestamp evidence. |
| Social clips from X/Instagram/TikTok | Often capture explicit claims from players or creators. | Fragile URLs, poor metadata, and low context. Use as supporting evidence only unless backed by original video/podcast. |

### Reject Or Hold

- Reddit threads about these authored lists belong in #15 unless the thread links
  back to a sourceable authored list.
- Breaking Point Awards and other formal/panel awards belong in #11, even if the
  same page also contains Top 20 player lists.
- Article snippets without stable URL, date, and author identity should stay as
  leads.
- Pure "best player" claims without context should not be normalized until the
  surrounding conversation is reviewed.

## Source Families

Use source family to prevent accidental aggregation across unlike evidence.

```text
authored_all_time_ranking
authored_title_ranking
authored_role_ranking
authored_talent_ranking
reported_player_claim
reported_caster_claim
reported_coach_claim
creator_video_ranking
creator_video_claim
```

## Claim Tags

Start with a controlled tag list and allow multiple tags per source row.

```text
goat
greatest
best_player
best_smg
best_ar
best_flex
best_entry
highest_peak
most_talented
hardest_to_kill
map_impact
carry
leadership
longevity
resume_weighted
skill_weighted
title_specific
role_specific
better_player_not_greater_career
future_goat_candidate
```

## Proposed Schema

Store sources separately from extracted ranking rows. This keeps one source with
many ranked players from duplicating source metadata.

```json
{
  "sources": [
    {
      "source_id": "nerd-street-2022-top-10-all-time",
      "family": "authored_all_time_ranking",
      "title": "Top 10 greatest Call of Duty players of all time",
      "url": "https://nerdstreet.com/news/2022/8/top-10-greatest-call-of-duty-players-all-time",
      "published_date": "2022-08-12",
      "retrieved_date": "2026-07-06",
      "outlet": "Nerd Street",
      "author": "Brian Bencomo",
      "author_type": "media",
      "scope": {
        "kind": "all_time",
        "games": [],
        "season": null,
        "ranking_size": 10
      },
      "methodology_summary": "Greatness list weighted by tournament wins, Champs titles, Champs top-three finishes, and individual accolades.",
      "methodology_tags": ["greatest", "resume_weighted"],
      "source_quality": "high",
      "caveats": [
        "Retrospective as of 2022 Champs.",
        "Accolades and trophies are mixed with subjective greatness."
      ]
    }
  ],
  "rankings": [
    {
      "source_id": "nerd-street-2022-top-10-all-time",
      "rank": 1,
      "player": "Crimsix",
      "normalized_player": "crimsix",
      "claim_tags": ["goat", "greatest", "resume_weighted"],
      "rationale_summary": "Ranks first on LAN titles, Champs titles, Champs top-three finishes, Champs MVP, and longevity at Champs.",
      "quote": null,
      "quote_location": null
    }
  ],
  "claims": [
    {
      "source_id": "dexerto-2023-nadeshot-scump-goat",
      "claimant": "Nadeshot",
      "claimant_type": "player_owner",
      "player": "Scump",
      "normalized_player": "scump",
      "claim_tags": ["goat", "most_talented", "map_impact", "hardest_to_kill"],
      "rationale_summary": "Nadeshot frames Scump's case around talent, map impact, difficulty to kill, and roster/context disadvantages.",
      "quote": "short verified excerpt only",
      "quote_location": "article body or video timestamp"
    }
  ]
}
```

## Scoring Guidance

Do not score authored evidence in v1.

If a future score is needed, compute it only inside a source family:

- all-time authored rankings can be summarized as "appears on N lists" and
  "median rank among comparable all-time lists";
- title-specific annual lists can be shown per title, not mixed with all-time
  lists;
- talent/skill lists should not be averaged with greatness/resume lists;
- individual claims should be countable as cited endorsements, not ballot
  equivalents.

Any rollup should output evidence counts and caveats before a rank:

```json
{
  "player": "Scump",
  "authored_evidence": {
    "all_time_list_count": 3,
    "median_all_time_rank": 3.0,
    "explicit_goat_claims": 2,
    "skill_claims": ["most_talented", "hardest_to_kill"],
    "source_count": 5,
    "caveat": "Sources mix greatness, talent, and popularity."
  }
}
```

## Display Plan

Preferred first display is an evidence lane, not a ranking page.

- Player page: "Authored discussion" section with source cards grouped by
  all-time rankings, title rankings, role/skill claims, and direct quotes.
- Debate/title pages: authored-list lane beside resume, skill/KOR, formal
  honors, and community consensus.
- Compare page: optional rows such as "Authored all-time list appearances" and
  "Best authored all-time rank," with source drilldown links.
- Methodology page: state that authored evidence captures identifiable opinions,
  not objective truth.

## Next Steps

1. Create `player_authored_sources.json` using the schema above.
2. Seed it with the high-confidence sources only.
3. Add a small validation test for required fields, source IDs, author identity,
   dates, URLs, and ranking rank uniqueness per source.
4. Keep video/podcast sources in a separate `verification_leads` list until each
   has a transcript or timestamped quote.
