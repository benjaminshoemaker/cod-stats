"""Staleness guards for the committed generated artifacts.

site/data.js regenerates on every data change, but site/clusters.js and
site/similarity.js only regenerate when someone runs the analysis pipeline
(which needs numpy/scipy — see requirements.txt). That gap has shipped real
bugs: a clusters.js rebuild once flipped the similarity map's y-axis against
its hardcoded annotations, and both files carried win-based debut/span fields
after the rest of the site moved to participation-based careers.

These tests compare the committed artifacts against the committed dataset —
stdlib only, no scientific stack — so a stale or drifted regeneration fails CI
instead of waiting for an audit. If they fail after a data change, rerun:
    python analysis/similarity.py && python analysis/cluster_map.py
"""
import json
import math
import os

import pytest

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
def clusters():
    return _load_js(os.path.join("site", "clusters.js"), "window.CLUSTERS=")


@pytest.fixture(scope="module")
def sim():
    return _load_js(os.path.join("site", "similarity.js"), "window.SIM=")


def _corr(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return cov / (sx * sy)


def test_data_js_matches_data_json(dataset):
    # build_data.write() emits both in one act; if they ever diverge something
    # other than the build wrote one of them.
    appdata = _load_js(os.path.join("site", "data.js"), "window.APP_DATA=")
    assert appdata == dataset


def test_kor_json_is_generated_with_mode_specific_rows():
    kor = json.load(open(os.path.join(ROOT, "site", "kor.json")))
    assert set(kor["meta"]["splits"]) == {"respawn", "snd"}
    assert "overall" not in kor["meta"]["splits"]
    bo6 = kor["games"]["Black Ops 6"]["splits"]
    assert bo6["respawn"]["qualified"] > 0
    assert bo6["respawn"]["playersWithMaps"] >= bo6["respawn"]["qualified"]
    assert bo6["snd"]["qualified"] > 0
    assert bo6["respawn"]["rows"][0]["korPerMap"] > 0
    assert bo6["respawn"]["rows"][0]["role"] in {"AR", "Flex", "SMG", "Unknown"}
    assert bo6["respawn"]["rows"][0]["medianOpponentPlace"] is not None
    assert bo6["respawn"]["rows"][0]["top8OpponentPct"] is not None


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


def test_clusters_covers_every_leaderboard_player(clusters, lb):
    names = {p["name"] for p in clusters["players"]}
    assert names == set(lb), (
        f"clusters.js players != leaderboard: only-in-map={names - set(lb)}, "
        f"missing={set(lb) - names}"
    )


def test_clusters_display_stats_match_leaderboard(clusters, lb):
    # Every display field the map shows must equal the canonical dataset's
    # value — including the participation-based career fields (firstPlayed /
    # careerSpan), NOT the older first-win/win-span ones.
    for p in clusters["players"]:
        r = lb[p["name"]]
        assert p["adj"] == round(r["adjAll"], 1), p["name"]
        assert p["raw"] == r["raw"], p["name"]
        assert p["champs"] == r["champs"], p["name"]
        assert p["titles"] == r["titlesAll"], p["name"]
        assert p["debut"] == r["firstPlayed"], (
            f"{p['name']}: map debut {p['debut']} != firstPlayed "
            f"{r['firstPlayed']} (win-based field regression?)"
        )
        assert p["span"] == r["careerSpan"], (
            f"{p['name']}: map span {p['span']} != careerSpan "
            f"{r['careerSpan']} (win-based field regression?)"
        )


def test_clusters_axis_orientation_matches_page_annotations(clusters, lb):
    # map.html hardcodes "← the field / all-time greats →" and "efficient ·
    # peak-heavy ↑ / ↓ long · well-traveled". cluster_map.py pins both signs;
    # this catches a regeneration that lost the pinning (it happened once).
    P = clusters["players"]
    xs = [p["x"] for p in P]
    ys = [p["y"] for p in P]
    adj = [lb[p["name"]]["adjAll"] for p in P]
    span = [lb[p["name"]]["careerSpan"] for p in P]
    assert _corr(xs, adj) > 0.5, "x-axis no longer tracks adjusted wins rightward"
    assert _corr(ys, span) < -0.2, "y-axis flipped: long careers must point down"


def test_clusters_metadata_complete(clusters):
    cls = clusters["clusters"]
    assert [c["id"] for c in cls] == list(range(clusters["k"]))
    assert sum(c["size"] for c in cls) == len(clusters["players"])
    names = {p["name"] for p in clusters["players"]}
    by_cluster = {}
    for p in clusters["players"]:
        by_cluster.setdefault(p["cluster"], set()).add(p["name"])
    for c in cls:
        assert c.get("label"), f"cluster {c['id']} missing display label"
        assert c["archetype"] in names, f"archetype {c['archetype']} not a player"
        assert c["archetype"] in by_cluster[c["id"]], (
            f"archetype {c['archetype']} not a member of cluster {c['id']}"
        )
    stats = clusters.get("stats") or {}
    assert 0 < stats.get("rAdj", 0) <= 1, "stats.rAdj missing (map prose goes stale)"
    assert 0 < stats.get("kept", 0) <= 1, "stats.kept missing (map prose goes stale)"


def test_clusters_comps_reference_real_players(clusters):
    names = {p["name"] for p in clusters["players"]}
    for p in clusters["players"]:
        for c in p["comps"]:
            assert c["name"] in names, f"{p['name']} comp {c['name']} unknown"


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
