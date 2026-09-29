"""Staleness guards for committed generated data and player comparisons.

The player-page similarity artifact needs the analysis pipeline (numpy/scipy).
After a data change, regenerate it with: python analysis/similarity.py.
These tests compare it against the canonical dataset using the stdlib.
"""
import json
import os

import pytest

import build_data

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_js(path, prefix):
    txt = open(os.path.join(ROOT, path)).read().strip()
    assert txt.startswith(prefix), f"{path} must start with {prefix!r}"
    return json.loads(txt[len(prefix):].rstrip(";"))


@pytest.fixture(scope="module")
def dataset():
    return json.load(open(os.path.join(ROOT, "site", "data.json")))


@pytest.fixture(scope="module")
def lb(dataset):
    return {r["name"]: r for r in dataset["leaderboard"]}


@pytest.fixture(scope="module")
def sim():
    return _load_js(os.path.join("site", "similarity.js"), "window.SIM=")


def test_data_js_matches_data_json(dataset):
    # build_data.write() emits both in one act; if they ever diverge something
    # other than the build wrote one of them.
    appdata = _load_js(os.path.join("site", "data.js"), "window.APP_DATA=")
    assert appdata == dataset


def test_community_consensus_json_is_generated_for_static_site():
    payload = json.load(open(os.path.join(ROOT, "site", "community-consensus.json")))
    assert payload["schema_version"] == 1
    assert "Black Ops 2" in payload["consensus"]["games"]
    assert payload["consensus"]["games"]["Black Ops 2"][0]["player"] == "Karma"
    assert len(payload["sources"]) >= 40
    assert any(s["source_id"] == "bo2_reddit_2016_top10_thread" for s in payload["sources"])
    assert any(b["ballot_id"] == "bo2_2016_top10_002" and "/comment/d6a5d59/" in b["url"]
               for b in payload["ballots"])
    assert payload["resumeWins"]["Black Ops 4"]["Dashy"] == 1

    canonical = {build_data.mkey(name): name for name, _ in build_data.PUBLISHED}
    seen = []
    for rows in payload["consensus"]["games"].values():
        seen.extend(row["player"] for row in rows)
    for contribution in payload["consensus"]["source_contributions"].values():
        seen.extend((contribution.get("scores") or {}).keys())
    for source in payload["sources"]:
        seen.extend(row["player"] for row in source.get("ranked_players") or [])
    for ballot in payload["ballots"]:
        seen.extend(row["player"] for row in ballot.get("entries") or [])
    mismatches = {
        player: canonical[build_data.mkey(player)]
        for player in seen
        if build_data.mkey(player) in canonical and player != canonical[build_data.mkey(player)]
    }
    assert mismatches == {}


def test_community_consensus_artifact_is_fresh():
    # community_consensus.json is only rewritten by a manual
    # `scripts/build_community_consensus.py --output` run, but build_data.py
    # consumes it as if it were source data. If the sources/ballots files are
    # edited without a rerun, the site silently ships stale consensus ranks.
    # If this fails, rerun:
    #     python3 scripts/build_community_consensus.py --output community_consensus.json
    from scripts.build_community_consensus import build
    stored = json.load(open(os.path.join(ROOT, "community_consensus.json")))
    assert build() == stored


def test_similarity_covers_every_leaderboard_player(sim, lb):
    assert set(sim["players"]) == set(lb)


def test_similarity_stats_match_leaderboard(sim, lb, dataset):
    # The player-page comparison table displays these; each must equal the
    # canonical dataset. debut is the participation-based first major entered.
    groups = dict(sim["config"]["groups"])
    assert "Skill" in groups
    assert [r[0] for r in groups["Skill"]] == [
        "skill_kd", "skill_respawn_kd", "skill_snd_kd", "skill_interactions_per_map"
    ]
    for name, p in sim["players"].items():
        r = lb[name]
        assert p["debut"] == r["firstPlayed"], (
            f"{name}: sim debut {p['debut']} != firstPlayed {r['firstPlayed']}"
        )
        m = p["metrics"]
        for key, want in (("adjAll", round(r["adjAll"], 2)), ("champs", r["champs"]),
                          ("peakAll", r["peakAll"]), ("titlesAll", r["titlesAll"]),
                          ("careerSpan", r["careerSpan"])):
            got = m[key]["v"]
            assert got == pytest.approx(want), f"{name}.{key}: {got} != {want}"
        stats = dataset["players"][name].get("skillStats") or {}
        for key, bucket in (
            ("skill_kd", stats.get("overall") or {}),
            ("skill_respawn_kd", (stats.get("splits") or {}).get("respawn") or {}),
            ("skill_snd_kd", (stats.get("splits") or {}).get("snd") or {}),
        ):
            got = m[key]["v"]
            if bucket.get("maps", 0) >= 25 and bucket.get("kd") is not None:
                assert got == pytest.approx(bucket["kd"]), f"{name}.{key}: {got} != {bucket['kd']}"
            else:
                assert got is None, f"{name}.{key}: low-sample stat should be masked"
        overall = stats.get("overall") or {}
        got = m["skill_interactions_per_map"]["v"]
        if overall.get("maps", 0) >= 25 and overall.get("interactions") is not None:
            want = round(overall["interactions"] / overall["maps"], 3)
            assert got == pytest.approx(want), (
                f"{name}.skill_interactions_per_map: {got} != {want}"
            )
        else:
            assert got is None, f"{name}.skill_interactions_per_map: low-sample stat should be masked"
