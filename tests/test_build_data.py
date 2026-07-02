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


def test_leaderboard_competition_ranks(data):
    # Ranks are competition-style: rank = 1 + (number of strictly better players),
    # so exact ties share the minimum rank instead of getting arbitrary order.
    # Adjusted ranks are validated against exact shares in
    # test_adjusted_rank_uses_exact_shares (rounded display values can tie where
    # the exact values differ); raw wins are integers so they're checked here.
    lb = data["leaderboard"]
    assert len(lb) == len(build_data.PUBLISHED)
    raw = {r["name"]: r["raw"] for r in lb}
    for r in lb:
        expected = 1 + sum(1 for v in raw.values() if v > raw[r["name"]])
        assert r["rawRank"] == expected, f"{r['name']} rawRank: {r['rawRank']} != {expected}"
    for key in ("adjRank", "postRank"):
        ranks = sorted(r[key] for r in lb)
        assert ranks[0] == 1 and len(ranks) == len(build_data.PUBLISHED)
        # competition ranking: after k players (with ties), the next distinct rank is k+1
        for i, rk in enumerate(ranks):
            assert rk <= i + 1, f"{key} has a gap inconsistent with competition ranking"


def test_raw_rank_ties_share_min_rank(data):
    # Clayster and TeeP both have 18 raw wins → both rank 6; next player is rank 8.
    lb = {r["name"]: r for r in data["leaderboard"]}
    assert lb["Clayster"]["rawRank"] == lb["TeeP"]["rawRank"] == 6
    assert lb["aBeZy"]["rawRank"] == 8


def test_adjusted_rank_uses_exact_shares(data):
    # Ranking must follow the exact (unrounded) season-share sums. Recompute each
    # player's share as an exact Fraction from their seasons and check the ordering.
    from fractions import Fraction
    shares = {}
    for name, p in data["players"].items():
        shares[name] = sum((Fraction(s["wins"], s["majors"]) for s in p["seasons"]), Fraction(0))
    lb = {r["name"]: r for r in data["leaderboard"]}
    for name, sh in shares.items():
        expected = 1 + sum(1 for v in shares.values() if v > sh)
        assert lb[name]["adjRank"] == expected, f"{name}: rank {lb[name]['adjRank']} != {expected}"
    # post-mode ranks likewise follow exact post-BO2 shares
    post = {}
    for name, p in data["players"].items():
        post[name] = sum((Fraction(s["wins"], s["majors"]) for s in p["seasons"] if not s["pre_bo2"]), Fraction(0))
    for name, sh in post.items():
        expected = 1 + sum(1 for v in post.values() if v > sh)
        assert lb[name]["postRank"] == expected, f"{name}: postRank {lb[name]['postRank']} != {expected}"


def test_warzone_and_mobile_excluded(data):
    for g in ("Warzone", "Mobile"):
        assert g not in data["majors"]
        assert g not in data["meta"]["seasonOrder"]


def test_black_ops_7_excludes_future_majors(data):
    # 4 played majors as of ASOF, not the 3 future scheduled ones
    assert data["majors"]["Black Ops 7"] == 4


def test_black_ops_7_in_progress_uses_scheduled_denominator(data):
    # The season is in progress: 4 majors played, 7 scheduled. Shares must divide
    # by the 7 every team will be able to play, or current winners are overstated.
    g = next(g for g in data["games"] if g["game"] == "Black Ops 7")
    assert g["majors"] == 4          # played so far (event list length)
    assert g["denom"] == 7           # scheduled majors (from major_events.json incl. future dates)
    assert g["weight"] == round(1 / 7, 4)
    bo7_players = [p for p in data["players"].values()
                   if any(s["game"] == "Black Ops 7" for s in p["seasons"])]
    assert bo7_players
    for p in bo7_players:
        s = next(s for s in p["seasons"] if s["game"] == "Black Ops 7")
        assert s["majors"] == 7 and s["held"] == 4
        assert s["share"] == round(s["wins"] / 7, 4)


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


def _build_with_champs(monkeypatch, tmp_path, mutate):
    """Copy the source JSON to a tmp dir, mutate the champs rows, and build from there."""
    import shutil
    for f in ("major_events.json", "player_event_wins.json", "champs_wins.json"):
        shutil.copy(build_data._p(f), tmp_path / f)
    champs = json.load(open(tmp_path / "champs_wins.json"))
    mutate(champs["cargoquery"])
    json.dump(champs, open(tmp_path / "champs_wins.json", "w"))
    monkeypatch.setattr(build_data, "HERE", str(tmp_path))
    return build_data.build()


def test_champs_guard_rejects_ambiguous_name(monkeypatch, tmp_path):
    # A disambiguated champs name ("Scump (someone else)") would silently merge into
    # the top-50 "Scump" via the case/parenthetical-stripping join — must raise.
    def add_ambiguous(rows):
        rows.append({"title": {"Player": "Scump (someone else)",
                               "Event": "Call of Duty Championship 2013", "Date": "2013-04-07"}})
    with pytest.raises(RuntimeError, match="ambiguous"):
        _build_with_champs(monkeypatch, tmp_path, add_ambiguous)


def test_champs_guard_rejects_event_not_in_wins(monkeypatch, tmp_path):
    # Every championship is itself a major, so a top-50 player's champs events must
    # be a subset of their reconstructed major wins — anything else is bad data.
    def add_bogus(rows):
        rows.append({"title": {"Player": "Scump", "Event": "Not A Real Event", "Date": "2015-01-01"}})
    with pytest.raises(RuntimeError, match="champ"):
        _build_with_champs(monkeypatch, tmp_path, add_bogus)


def test_write_emits_valid_appdata(tmp_path, data):
    out = tmp_path / "data.js"
    build_data.write(data, str(out))
    text = out.read_text()
    assert text.startswith("window.APP_DATA=") and text.rstrip().endswith(";")
    parsed = json.loads(text[len("window.APP_DATA="):].rstrip().rstrip(";"))
    assert parsed["leaderboard"][0]["name"] in {p[0] for p in build_data.PUBLISHED}
