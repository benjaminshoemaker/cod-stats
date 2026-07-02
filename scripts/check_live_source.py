#!/usr/bin/env python3
"""Daily drift check against the live source of truth.

Re-runs the exact Cargo query that generates the wiki's "Major Wins" leaderboard
(https://cod-esports.fandom.com/wiki/List_of_Most_Major_Tournament_Wins_by_Player)
and compares the live per-player Raw Wins to our hardcoded PUBLISHED list (and,
transitively, the data the site is built from — the build guard keeps data.js == PUBLISHED).

Behavior:
  * exit 0 + "match"   — every player on our PUBLISHED list still matches the live wiki
  * exit 0 + "SKIP"    — wiki unreachable/rate-limited (no false alarm on outages)
  * exit 1 + diff      — a real numeric mismatch (your signal to re-pull + update PUBLISHED)

Run manually:  python3 scripts/check_live_source.py
"""
import json, sys, os, time, urllib.parse, urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from build_data import PUBLISHED, mkey

UA = "Mozilla/5.0 (compatible; cod-stats-source-check/1.0; +https://cod-stats-one.vercel.app)"
API = "https://cod-esports.fandom.com/api.php"


def live_major_wins():
    """Live {mkey(player): (wins, display_name)} for every player with >=1 major win.
    Returns None if the wiki can't be reached after retries."""
    params = {
        "action": "cargoquery", "format": "json", "limit": "500",
        "tables": "Tournaments=TO,TournamentResults=TR,TournamentPlayers=TP,PlayerRedirects=PR,Players=PL",
        "fields": "PL.OverviewPage=Player,COUNT(*)=Wins",
        "where": 'PL.OverviewPage IS NOT NULL AND (TP.Role IS NULL OR TP.Role="Substitute") '
                 'AND TO.Tier IN("Major","Premier") AND TR.Place_Number=1',
        "join_on": "TO.OverviewPage=TR.OverviewPage,TR.PageAndTeam=TP.PageAndTeam,"
                   "TP.Link=PR.AllName,PR.OverviewPage=PL.OverviewPage",
        "group_by": "PR.OverviewPage", "order_by": "Wins DESC",
    }
    url = API + "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    for _ in range(6):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.load(r)
        except Exception:
            time.sleep(12); continue
        if "cargoquery" not in data:           # error / rate-limited
            time.sleep(12); continue
        out = {}
        for row in data["cargoquery"]:
            t = row["title"]
            out[mkey(t["Player"])] = (int(t["Wins"]), t["Player"])
        if len(data["cargoquery"]) >= 500:
            # our 50 all have 4+ wins so they sort well inside the top 500, but a
            # truncated result should never silently pass as a full comparison
            print("WARNING: cargo query returned the 500-row cap; comparison may be partial")
        return out
    return None


def main():
    live = live_major_wins()
    if live is None:
        print("SKIP: live CoD Esports Wiki unreachable/rate-limited — no drift conclusion.")
        return 0

    mism = []
    for name, pub in PUBLISHED:
        got = live.get(mkey(name))
        got_wins = got[0] if got else None
        if got_wins != pub:
            mism.append((name, pub, got_wins))

    # the list covers everyone at/above the cutoff (min wins on PUBLISHED), so any
    # non-listed player reaching it belongs on the board
    floor = min(p for _, p in PUBLISHED)
    ours = {mkey(n) for n, _ in PUBLISHED}
    newcomers = sorted(((w, nm) for k, (w, nm) in live.items() if w >= floor and k not in ours), reverse=True)[:10]

    lines = []
    if mism:
        lines += ["## ❌ Raw Wins drift vs the live wiki", "",
                  "| Player | Our Raw Wins | Live wiki |", "|---|---:|---:|"]
        lines += [f"| {n} | {pub} | {got if got is not None else '— (not found)'} |" for n, pub, got in mism]
    if newcomers:
        lines += ["", f"## ⚠️ Players with ≥{floor} wins missing from our {len(PUBLISHED)}-player list"]
        lines += [f"- {nm}: {w} major wins" for w, nm in newcomers]
    report = "\n".join(lines) if lines else f"## ✅ Raw Wins match the live wiki for all {len(PUBLISHED)} players"

    print(report)
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a") as f:
            f.write(report + "\n")
    return 1 if mism else 0


if __name__ == "__main__":
    sys.exit(main())
