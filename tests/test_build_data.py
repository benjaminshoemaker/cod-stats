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
    # The season is in progress: 4 majors played, 6 scheduled (4 CDL Majors + Champs +
    # EWC). Shares must divide by the 6 every team will be able to play, or current
    # winners are overstated. The mis-tiered Challengers Finals is excluded (DROP_EVENTS),
    # so this is 6, not the 7 the wiki's Majors portal lists.
    g = next(g for g in data["games"] if g["game"] == "Black Ops 7")
    assert g["majors"] == 4          # played so far (event list length)
    assert g["denom"] == 6           # scheduled majors, Challengers Finals dropped
    assert g["weight"] == round(1 / 6, 4)
    bo7_players = [p for p in data["players"].values()
                   if any(s["game"] == "Black Ops 7" for s in p["seasons"])]
    assert bo7_players
    for p in bo7_players:
        s = next(s for s in p["seasons"] if s["game"] == "Black Ops 7")
        assert s["majors"] == 6 and s["held"] == 4
        assert s["share"] == round(s["wins"] / 6, 4)


def test_dropped_events_excluded_everywhere(data):
    # DROP_EVENTS (mis-tiered non-majors) must not appear as a scheduled major, an
    # event row, or anyone's win — otherwise the season denominator re-inflates.
    from build_data import DROP_EVENTS
    for g in data["games"]:
        listed = {e["event"] for e in g["events"]}
        assert not (listed & DROP_EVENTS), f"{g['game']} still lists a dropped event"
    for p in data["players"].values():
        for s in p["seasons"]:
            assert not ({e["event"] for e in s["events"]} & DROP_EVENTS)


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


def test_place_score_parses_ranges_and_open_ended_finishes():
    # Average placement uses the official finish range's midpoint rather than the
    # lower bound used for sorting on the wiki. Store it doubled so .5 stays exact.
    assert build_data.place_x2({"Place": "1", "PlaceNumber": "1"}) == 2
    assert build_data.place_x2({"Place": "5-6", "PlaceNumber": "5"}) == 11
    assert build_data.place_x2({"Place": "9-12*", "PlaceNumber": "9"}) == 21
    assert build_data.place_x2({"Place": ">12", "PlaceNumber": ""}) == 26


def test_average_placement_uses_same_rows_as_player_page(data):
    # `_participation` is what writes site/participation.json for the player page.
    # The leaderboard/player aggregate must be derived from the same normalized rows.
    for name, pl in data["players"].items():
        part = data["_participation"][name]
        assert pl["events_placed"] == len(part)
        assert pl["place_x2_sum"] == sum(m["placeX2"] for m in part)
        expected = build_data.avg_place_from_x2(pl["place_x2_sum"], pl["events_placed"])
        assert pl["avg_place"] == expected

        by_game = {}
        for m in part:
            g = by_game.setdefault(m["game"], {"events": 0, "sum": 0})
            g["events"] += 1
            g["sum"] += m["placeX2"]
        assert {r["game"]: (r["events"], r["placeX2Sum"]) for r in pl["placements"]} == {
            g: (v["events"], v["sum"]) for g, v in by_game.items()
        }


def test_participation_rows_include_roster_team_and_cached_logo(data):
    scump_rows = data["_participation"]["Scump"]
    assert scump_rows[0]["team"] == "Quantic LeveraGe"
    assert any(r["event"] == "Call of Duty League 2022 - Major 1"
               and r["team"] == "OpTic Texas" for r in scump_rows)
    assert data["players"]["Scump"]["teams"][:3] == [
        "Quantic LeveraGe",
        "apeX eSports NA",
        "OpTic Gaming",
    ]
    assert data["players"]["Scump"]["teams"][-1] == "OpTic Texas"
    assert any(e["event"] == "Call of Duty League 2022 - Major 1"
               and e["team"] == "OpTic Texas"
               for s in data["players"]["Scump"]["seasons"] for e in s["events"])

    optic = data["teamLogos"]["OpTic Texas"]
    assert optic["file"] == "File:OpTic Texaslogo std.png"
    assert optic["remoteSrc"].startswith("https://static.wikia.nocookie.net/")
    assert optic["src"].startswith("assets/team-logos/")


def test_game_events_include_full_winner_team_for_logos(data):
    bo7 = next(g for g in data["games"] if g["game"] == "Black Ops 7")
    major4 = next(e for e in bo7["events"] if e["event"] == "Call of Duty League 2026 - Major 4")
    assert major4["winner"] == "OTX"
    assert major4["winnerTeam"] == "OpTic Texas"


def test_curated_primary_roles_emit_by_active_game(data):
    scump_roles = data["players"]["Scump"]["role_by_game"]
    assert scump_roles
    assert {r["role"] for r in scump_roles} == {"SMG"}
    assert scump_roles[0] == {"game": "Black Ops", "year": 2011, "role": "SMG"}

    formal_roles = data["players"]["FormaL"]["role_by_game"]
    assert {r["role"] for r in formal_roles} == {"AR"}
    assert formal_roles[0]["game"] == "Ghosts"

    kenny_roles = data["players"]["Kenny"]["role_by_game"]
    assert {r["role"] for r in kenny_roles} == {"Flex"}
    assert [r["game"] for r in kenny_roles] == sorted(
        {m["game"] for m in data["_participation"]["Kenny"]},
        key=data["meta"]["seasonOrder"].index,
    )


def test_unlisted_primary_roles_default_to_unknown(data):
    assert data["players"]["Crimsix"]["primary_role"] == "Unknown"
    assert data["players"]["Bobby"]["primary_role"] == "Unknown"
    assert {r["role"] for r in data["players"]["Bobby"]["role_by_game"]} == {"Unknown"}


def test_role_stints_support_game_bounded_switches(monkeypatch):
    roles = [
        {"player": "Scump", "role": "SMG", "start_game": "Black Ops", "end_game": "Black Ops 4"},
        {"player": "Scump", "role": "AR", "start_game": "Modern Warfare"},
    ]
    monkeypatch.setattr(build_data, "load_role_stints", lambda: roles)

    events_all, events, *_ = build_data.load_sources()
    S = build_data.season_context(events, events_all)
    stints = build_data.index_role_stints(
        build_data.load_role_stints(),
        {build_data.mkey(n): n for n, _ in build_data.PUBLISHED},
        S,
    )

    active = ["Black Ops", "Black Ops 4", "Modern Warfare", "Modern Warfare II"]
    rows = build_data.role_by_game("Scump", active, S, stints)
    assert [r["role"] for r in rows] == ["SMG", "SMG", "AR", "AR"]


def test_role_stints_reject_overlapping_bounds(monkeypatch):
    roles = [
        {"player": "Scump", "role": "SMG", "start_game": "Black Ops 2", "end_game": "Black Ops 4"},
        {"player": "Scump", "role": "AR", "start_game": "Ghosts"},
    ]
    monkeypatch.setattr(build_data, "load_role_stints", lambda: roles)

    events_all, events, *_ = build_data.load_sources()
    S = build_data.season_context(events, events_all)
    with pytest.raises(RuntimeError, match="overlapping role stints"):
        build_data.index_role_stints(
            build_data.load_role_stints(),
            {build_data.mkey(n): n for n, _ in build_data.PUBLISHED},
            S,
        )


def test_curated_primary_roles_can_switch_across_real_careers(data):
    crimsix = {r["game"]: r["role"] for r in data["players"]["Crimsix"]["role_by_game"]}
    assert crimsix["Call of Duty 4"] == "AR"
    assert crimsix["Black Ops 2"] == "SMG"
    assert crimsix["Ghosts"] == "Flex"
    assert crimsix["Infinite Warfare"] == "Flex"
    assert crimsix["World War II"] == "AR"
    assert crimsix["Vanguard"] == "AR"
    assert data["players"]["Crimsix"]["primary_role"] == "Unknown"

    attach = {r["game"]: r["role"] for r in data["players"]["Attach"]["role_by_game"]}
    assert attach["Black Ops 2"] == "SMG"
    assert attach["Vanguard"] == "SMG"
    assert attach["Modern Warfare II"] == "AR"
    assert data["players"]["Attach"]["primary_role"] == "Unknown"

    joshh = {r["game"]: r["role"] for r in data["players"]["Joshh"]["role_by_game"]}
    assert joshh["Modern Warfare 3"] == "SMG"
    assert joshh["Ghosts"] == "SMG"
    assert joshh["Advanced Warfare"] == "AR"
    assert joshh["Black Ops 4"] == "AR"
    assert data["players"]["Joshh"]["primary_role"] == "Unknown"


def test_recent_curated_unknowns_now_have_roles(data):
    expected = {
        "MadCat": "AR",
        "Censor": "SMG",
        "Dedo": "AR",
        "Frosty": "AR",
        "Mack": "Flex",
    }
    for name, role in expected.items():
        assert data["players"][name]["primary_role"] == role
        assert {r["role"] for r in data["players"][name]["role_by_game"]} == {role}


def test_duplicate_player_event_keeps_best_placement(monkeypatch, tmp_path):
    import shutil
    for f in ("major_events.json", "player_event_wins.json", "champs_wins.json", "player_participation.json", "team_participation.json"):
        shutil.copy(build_data._p(f), tmp_path / f)
    rows = json.load(open(tmp_path / "player_participation.json"))
    rows += [
        {"Player": "Scump", "Event": "Synthetic Dup", "Game": "Black Ops 2",
         "Date": "2013-01-01", "Team": "Bad", "Place": "13-16", "PlaceNumber": "13"},
        {"Player": "Scump", "Event": "Synthetic Dup", "Game": "Black Ops 2",
         "Date": "2013-01-01", "Team": "Good", "Place": "3-4", "PlaceNumber": "3"},
    ]
    json.dump(rows, open(tmp_path / "player_participation.json", "w"))
    monkeypatch.setattr(build_data, "HERE", str(tmp_path))
    events_all, events, pwins, champs_rows, ppart, _ = build_data.load_sources()
    top = {build_data.mkey(n) for n, _ in build_data.PUBLISHED}
    _, part_rows = build_data.index_participation(ppart, top)
    assert part_rows[build_data.mkey("Scump")]["Synthetic Dup"]["place"] == "3-4"
    assert part_rows[build_data.mkey("Scump")]["Synthetic Dup"]["placeX2"] == 7


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


def test_path_features_filter_to_played_console_major_universe(tmp_path):
    from analysis import path_features

    dropped = next(iter(build_data.DROP_EVENTS))
    events = [
        {"Event": "Counted Major 1", "Game": "Black Ops 2", "Date": "2020-01-01"},
        {"Event": "Counted Major 2", "Game": "Black Ops 2", "Date": "2020-02-01"},
        {"Event": "DNS Major", "Game": "Black Ops 2", "Date": "2020-03-01"},
        {"Event": "Warzone Major", "Game": "Warzone", "Date": "2020-04-01"},
        {"Event": dropped, "Game": "Black Ops 7", "Date": "2026-06-01"},
        {"Event": "Future Major", "Game": "Black Ops 7", "Date": "2999-01-01"},
    ]
    rows = [
        {"Player": "Testy", "Event": "Counted Major 1", "Game": "Black Ops 2", "Date": "2020-01-01", "Team": "A", "Place": "1", "PlaceNumber": "1"},
        {"Player": "Testy", "Event": "Counted Major 2", "Game": "Black Ops 2", "Date": "2020-02-01", "Team": "B", "Place": "3", "PlaceNumber": "3"},
        {"Player": "Testy", "Event": "DNS Major", "Game": "Black Ops 2", "Date": "2020-03-01", "Team": "C", "Place": "DNS", "PlaceNumber": ""},
        {"Player": "Testy", "Event": "Warzone Major", "Game": "Warzone", "Date": "2020-04-01", "Team": "D", "Place": "1", "PlaceNumber": "1"},
        {"Player": "Testy", "Event": dropped, "Game": "Black Ops 7", "Date": "2026-06-01", "Team": "E", "Place": "1", "PlaceNumber": "1"},
        {"Player": "Testy", "Event": "Future Major", "Game": "Black Ops 7", "Date": "2999-01-01", "Team": "F", "Place": "1", "PlaceNumber": "1"},
    ]
    events_path = tmp_path / "major_events.json"
    part_path = tmp_path / "player_participation.json"
    json.dump(events, open(events_path, "w"))
    json.dump(rows, open(part_path, "w"))

    f = path_features.derive(str(part_path), events_json=str(events_path))["testy"]
    assert f["attendances"] == 2
    assert f["distinct_teams"] == 2
    assert f["avg_tenure"] == 1.0
    assert f["finals_rate"] == 0.5
    assert f["deep_run_rate"] == 1.0
    assert f["win_conversion"] == 0.5
    assert f["best_place"] == 1


def test_guard_raises_on_wrong_total(monkeypatch):
    monkeypatch.setattr(build_data, "PUBLISHED", build_data.PUBLISHED + [("NotARealPlayer", 5)])
    with pytest.raises(RuntimeError):
        build_data.build()


def _build_with_champs(monkeypatch, tmp_path, mutate):
    """Copy the source JSON to a tmp dir, mutate the champs rows, and build from there."""
    import shutil
    for f in ("major_events.json", "player_event_wins.json", "champs_wins.json", "player_participation.json", "team_participation.json"):
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
