"""Data-integrity tests for build_data.build().

These are the cheap, high-value tests: build_data is a pure function with a known
oracle (the wiki's published totals), so a few assertions catch silent data
corruption — including the exact aBeZy/iLLeY casing-join regression.
"""
import json
import pytest
import build_data


@pytest.fixture(scope="module")
def data():
    # build() raises if any player's reconstruction != published total, so this
    # fixture itself exercises the core invariant.
    return build_data.build()


def test_every_player_reconstructs_to_published_total(data):
    by_name = data["players"]
    for name, pub in build_data.PUBLISHED:
        recon = sum(s["wins"] for s in by_name[name]["seasons"])
        assert recon == pub, f"{name}: reconstructed {recon} != published {pub}"


def test_leaderboard_has_50_unique_ranks(data):
    lb = data["leaderboard"]
    assert len(lb) == 50
    assert sorted(r["adjRank"] for r in lb) == list(range(1, 51))
    assert sorted(r["postRank"] for r in lb) == list(range(1, 51))


def test_warzone_and_mobile_excluded(data):
    for g in ("Warzone", "Mobile"):
        assert g not in data["majors"]
        assert g not in data["meta"]["seasonOrder"]


def test_black_ops_7_excludes_future_majors(data):
    # 4 played majors as of ASOF, not the 3 future scheduled ones
    assert data["majors"]["Black Ops 7"] == 4


def test_denominator_matches_event_count_per_season(data):
    # each season's major count == the number of events listed for it
    games = {g["game"]: g for g in data["games"]}
    for game, n in data["majors"].items():
        assert len(games[game]["events"]) == n, f"{game}: {len(games[game]['events'])} events vs majors={n}"


def test_championships_known_values_and_all_modern(data):
    p = data["players"]
    expected = {"Crimsix": 3, "Karma": 3, "Clayster": 3, "Shotzzy": 3,
                "aBeZy": 2, "Simp": 2, "BigTymeR": 0}
    for name, champs in expected.items():
        assert p[name]["champs"] == champs, f"{name} champs {p[name]['champs']} != {champs}"
    # championships only exist from 2013 onward
    for name in p:
        for ev in p[name]["champ_events"]:
            assert ev["year"] >= "2013"


def test_abezy_and_illey_not_zeroed(data):
    # regression guard for the case-insensitive join bug (ABeZy vs aBeZy)
    for name in ("aBeZy", "iLLeY"):
        pl = data["players"][name]
        assert pl["adj_all"] > 0, f"{name} adjusted is 0 — casing join regression"
        assert len(pl["seasons"]) > 0
    assert data["players"]["aBeZy"]["champs"] == 2


def test_adjusted_equals_share_times_mbar(data):
    mbar = data["meta"]["mbarAll"]
    for name in ("Crimsix", "Simp", "HyDra"):
        pl = data["players"][name]
        assert abs(pl["adj_all"] - round(pl["share_all"] * mbar, 2)) <= 0.05


def test_peak_and_longevity(data):
    p = data["players"]
    mbar = data["meta"]["mbarAll"]
    # peak = best single season's share, rescaled by mbar
    for name, pl in p.items():
        if pl["seasons"]:
            expected = round(max(s["share"] for s in pl["seasons"]) * mbar, 2)
            assert abs(pl["peak_all"]["adj"] - expected) <= 0.05, name
    # known peak detail + longevity counts
    assert p["aBeZy"]["peak_all"]["season"] == "Black Ops Cold War"
    assert (p["aBeZy"]["peak_all"]["wins"], p["aBeZy"]["peak_all"]["majors"]) == (4, 6)
    assert p["Scump"]["titles_all"] == 10
    assert p["Crimsix"]["titles_all"] == 8
    # titles == distinct seasons with a major
    for name, pl in p.items():
        assert pl["titles_all"] == len(pl["seasons"]), name


def test_modern_warfare_structural_denominator(data):
    # MW 2019 ran a split Home Series format: 13 majors held, but each team played 9.
    # Shares must divide by 9, while the Seasons page still reports 13 held.
    mw_players = [pl for pl in data["players"].values()
                  if any(s["game"] == "Modern Warfare" for s in pl["seasons"])]
    assert mw_players
    for pl in mw_players:
        s = next(s for s in pl["seasons"] if s["game"] == "Modern Warfare")
        assert s["held"] == 13 and s["majors"] == 9
        assert s["share"] == round(s["wins"] / 9, 4)
    g = next(g for g in data["games"] if g["game"] == "Modern Warfare")
    assert g["majors"] == 13 and g["denom"] == 9


def test_structural_override_matches_participation():
    # The override (9) must equal MW's real max team-attendance, and no MODERN
    # season (Cold War onward) may silently become structural without review.
    from collections import defaultdict
    part = json.load(open(build_data._p("team_participation.json")))
    ev = json.load(open(build_data._p("major_events.json")))
    counted = defaultdict(set)
    for e in ev:
        if e["Game"] in build_data.DROP_GAMES or (e.get("Date") or "0") > build_data.ASOF:
            continue
        counted[e["Game"]].add(e["Event"])
    att = defaultdict(lambda: defaultdict(set))
    for r in part:
        g, evn, team = r["Game"], r["Event"], (r["Team"] or "").strip()
        if team and g in counted and evn in counted[g]:
            att[g][team].add(evn)
    maxatt = lambda g: max((len(s) for s in att[g].values()), default=0)
    assert maxatt("Modern Warfare") == build_data.STRUCTURAL_DENOM["Modern Warfare"] == 9
    for g in ["Black Ops Cold War", "Vanguard", "Modern Warfare II", "Modern Warfare III", "Black Ops 6"]:
        assert maxatt(g) == len(counted[g]), f"{g} unexpectedly structural (max {maxatt(g)} < {len(counted[g])})"


def test_guard_raises_on_wrong_total(monkeypatch):
    monkeypatch.setattr(build_data, "PUBLISHED", build_data.PUBLISHED + [("NotARealPlayer", 5)])
    with pytest.raises(RuntimeError):
        build_data.build()


def test_write_emits_valid_appdata(tmp_path, data):
    out = tmp_path / "data.js"
    build_data.write(data, str(out))
    text = out.read_text()
    assert text.startswith("window.APP_DATA=") and text.rstrip().endswith(";")
    parsed = json.loads(text[len("window.APP_DATA="):].rstrip().rstrip(";"))
    assert parsed["leaderboard"][0]["name"] in {p[0] for p in build_data.PUBLISHED}
