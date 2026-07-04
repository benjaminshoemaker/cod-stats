#!/usr/bin/env python3
"""Validate external stat claims against the committed source snapshots.

Benchmarks live in validation/benchmarks.json. They are intentionally separate
from build_data.py's reconstruction guard: these checks answer "does our current
source reproduce an outside stat claim as of the claim date?"
"""
import argparse
import html
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import build_data


HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_FIXTURES = os.path.join(HERE, "validation", "benchmarks.json")
_BP_CACHE = {}


def _load_json(name):
    with open(os.path.join(HERE, name)) as f:
        return json.load(f)


def _row_date(row):
    return row.get("Date") or "0000-00-00"


def _as_of(bench):
    return bench.get("asOf") or bench.get("sourceDate") or build_data.ASOF


def _same_player(row, player):
    return build_data.mkey(row.get("Player") or "") == build_data.mkey(player)


def _counted_major_row(row, as_of):
    return (
        row.get("Game") not in build_data.DROP_GAMES
        and row.get("Event") not in build_data.DROP_EVENTS
        and _row_date(row) <= as_of
    )


def _matches_filters(row, filters):
    for key, expected in (filters or {}).items():
        if key == "games":
            if row.get("Game") not in expected:
                return False
        elif key == "events":
            if row.get("Event") not in expected:
                return False
        elif key == "modes":
            if row.get("Mode") not in expected:
                return False
        elif row.get(key) != expected:
            return False
    return True


def raw_major_wins(bench):
    as_of = _as_of(bench)
    rows = _load_json("player_event_wins.json")
    return sum(
        1
        for row in rows
        if _same_player(row, bench["player"])
        and _counted_major_row(row, as_of)
        and _matches_filters(row, bench.get("filters"))
    )


def finals_record(bench):
    as_of = _as_of(bench)
    rows = _load_json("player_participation.json")
    wins = losses = 0
    for row in rows:
        if not _same_player(row, bench["player"]):
            continue
        if not _counted_major_row(row, as_of) or not _matches_filters(row, bench.get("filters")):
            continue
        place = str(row.get("PlaceNumber") or "").strip()
        if place == "1":
            wins += 1
        elif place == "2":
            losses += 1
    return {"wins": wins, "losses": losses}


def championship_wins(bench):
    as_of = _as_of(bench)
    rows = _load_json("champs_wins.json")["cargoquery"]
    return sum(
        1
        for row in rows
        if _same_player(row["title"], bench["player"])
        and (row["title"].get("Date") or "0000-00-00") <= as_of
    )


def overall_kd(bench):
    as_of = _as_of(bench)
    kills = deaths = maps = 0
    for row in _load_json("player_stats.json"):
        if not _same_player(row, bench["player"]):
            continue
        if _row_date(row) > as_of or not _matches_filters(row, bench.get("filters")):
            continue
        kills += int(row.get("Kills") or 0)
        deaths += int(row.get("Deaths") or 0)
        maps += 1
    kd = round(kills / deaths, 3) if deaths else None
    return {"kills": kills, "deaths": deaths, "maps": maps, "kd": kd}


def _fetch_breaking_point_page(url):
    if url in _BP_CACHE:
        return _BP_CACHE[url]
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (cod-stats validation)"})
    text = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', text)
    if not match:
        raise RuntimeError(f"Breaking Point page has no __NEXT_DATA__: {url}")
    data = json.loads(html.unescape(match.group(1)))
    _BP_CACHE[url] = data
    return data


def _bp_player_stats(url):
    data = _fetch_breaking_point_page(url)
    return data["props"]["pageProps"]["player"]["stats"]


def _matches_bp_filters(row, filters):
    for key, expected in (filters or {}).items():
        if key == "seasonId":
            if row.get("season_id") != expected:
                return False
        elif key == "eventIds":
            if row.get("event_id") not in expected:
                return False
        elif key == "eventTypes":
            if row.get("event_type") not in expected:
                return False
        elif key == "modeIds":
            if row.get("mode_id") not in expected:
                return False
        elif row.get(key) != expected:
            return False
    return True


def _finish_kd(kills, deaths, maps):
    return {"kills": kills, "deaths": deaths, "maps": maps,
            "kd": round(kills / deaths, 3) if deaths else None}


def _breaking_point_kd(bench):
    kills = deaths = maps = 0
    for row in _bp_player_stats(bench["sourceUrl"]):
        if not _matches_bp_filters(row, bench.get("externalFilters")):
            continue
        kills += int(row.get("kills") or 0)
        deaths += int(row.get("deaths") or 0)
        maps += 1
    return _finish_kd(kills, deaths, maps)


def breaking_point_season_kd(bench):
    """Compare our local PlayerStats aggregate with a live Breaking Point page.

    The returned deltas are local minus Breaking Point, so a clean match is zero.
    Live benchmarks are skipped by default and run with --include-live.
    """
    local_bench = dict(bench)
    local_bench["filters"] = bench.get("localFilters", {})
    local = overall_kd(local_bench)
    bp = _breaking_point_kd(bench)
    kd_delta = None if local["kd"] is None or bp["kd"] is None else round(local["kd"] - bp["kd"], 3)
    return {
        "local": local,
        "breakingPoint": bp,
        "mapsDelta": local["maps"] - bp["maps"],
        "kdDelta": kd_delta,
    }


METRICS = {
    "raw_major_wins": raw_major_wins,
    "finals_record": finals_record,
    "championship_wins": championship_wins,
    "overall_kd": overall_kd,
    "breaking_point_season_kd": breaking_point_season_kd,
}


def _close(actual, expected, tolerance):
    if isinstance(expected, float) or isinstance(actual, float):
        return abs(actual - expected) <= tolerance
    return actual == expected


def compare(actual, expected, tolerance=0):
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return False
        return all(compare(actual.get(k), v, tolerance) for k, v in expected.items())
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        return _close(actual, expected, tolerance)
    return actual == expected


def evaluate(bench):
    metric = bench["metric"]
    if metric not in METRICS:
        raise ValueError(f"{bench['id']}: unknown metric {metric!r}")
    actual = METRICS[metric](bench)
    ok = compare(actual, bench["expected"], bench.get("tolerance", 0))
    return {"id": bench["id"], "ok": ok, "actual": actual, "expected": bench["expected"]}


def load_benchmarks(path):
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, dict):
        return data.get("benchmarks", [])
    return data


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--fixtures", default=DEFAULT_FIXTURES)
    p.add_argument("--include-pending", action="store_true")
    p.add_argument("--include-live", action="store_true",
                   help="run live external-source checks such as Breaking Point")
    args = p.parse_args(argv)

    benches = load_benchmarks(args.fixtures)
    active = []
    for bench in benches:
        status = bench.get("status", "active")
        if status == "active" or (status == "pending" and args.include_pending) or (status == "live" and args.include_live):
            active.append(bench)
    results = [evaluate(b) for b in active]
    failures = [r for r in results if not r["ok"]]

    for result in results:
        marker = "PASS" if result["ok"] else "FAIL"
        print(f"{marker} {result['id']}: expected {result['expected']!r}, got {result['actual']!r}")
    skipped = len(benches) - len(active)
    if skipped:
        print(f"SKIP {skipped} pending/manual benchmark(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
