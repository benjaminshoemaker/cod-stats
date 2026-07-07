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


def test_kor_detail_json_is_generated_and_reconciles():
    # write() splits the event-by-event traces into kor-detail.json; kor.json's
    # shape (the page's fetch contract) must stay unchanged, and the traces must
    # cover exactly the qualified rows.
    kor = json.load(open(os.path.join(ROOT, "site", "kor.json")))
    assert "_detail" not in kor
    players = json.load(open(os.path.join(ROOT, "site", "kor-detail.json")))["players"]
    row_keys = {(r["player"], g, s) for g, gd in kor["games"].items()
                for s, sc in gd["splits"].items() for r in sc["rows"]}
    detail_keys = {(p, g, s) for p, games in players.items()
                   for g, splits in games.items() for s in splits}
    assert detail_keys == row_keys
    scump = players["Scump"]["Black Ops 2"]["respawn"]
    row = next(r for r in kor["games"]["Black Ops 2"]["splits"]["respawn"]["rows"]
               if r["player"] == "Scump")
    assert sum(e["maps"] for e in scump) == row["maps"]
    assert len(scump) == row["events"]

    # per-title map shards exist where kor-detail points and reconcile to traces
    detail = json.load(open(os.path.join(ROOT, "site", "kor-detail.json")))
    shard_path = detail["meta"]["mapFiles"]["Black Ops 2"]
    shard = json.load(open(os.path.join(ROOT, "site", shard_path)))
    assert shard["game"] == "Black Ops 2"
    for e in scump:
        rows = [m for m in shard["players"]["Scump"][e["id"]] if not m["snd"]]
        assert len(rows) == e["maps"]
        assert sum(m["k"] for m in rows) == e["kills"]
        assert sum(m["d"] for m in rows) == e["deaths"]


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
