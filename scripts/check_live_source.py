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
from build_data import DROP_EVENTS, DROP_GAMES, PUBLISHED, mkey

UA = "Mozilla/5.0 (compatible; cod-stats-source-check/1.0; +https://mapfive.app)"
API = "https://cod-esports.fandom.com/api.php"


PAGE = 500


def _quoted(values):
    return ",".join('"' + str(v).replace('"', '\\"') + '"' for v in sorted(values))


def source_exclusion_where():
    clauses = []
    if DROP_GAMES:
        clauses.append(f"TO.Game NOT IN({_quoted(DROP_GAMES)})")
    if DROP_EVENTS:
        clauses.append(f"TO.Name NOT IN({_quoted(DROP_EVENTS)})")
    return " AND ".join(clauses)

def live_major_wins():
    """Live {mkey(player): (wins, display_name)} for every player with >=1 major win.
    Paginates past the 500-row cap so the comparison is never silently partial.
    Returns None if the wiki can't be reached after retries."""
    base = {
        "action": "cargoquery", "format": "json", "limit": str(PAGE),
        "tables": "Tournaments=TO,TournamentResults=TR,TournamentPlayers=TP,PlayerRedirects=PR,Players=PL",
        "fields": "PL.OverviewPage=Player,COUNT(*)=Wins",
        "where": 'PL.OverviewPage IS NOT NULL AND (TP.Role IS NULL OR TP.Role="Substitute") '
                 'AND TO.Tier IN("Major","Premier") AND TR.Place_Number=1 AND '
                 + source_exclusion_where(),
        "join_on": "TO.OverviewPage=TR.OverviewPage,TR.PageAndTeam=TP.PageAndTeam,"
                   "TP.Link=PR.AllName,PR.OverviewPage=PL.OverviewPage",
        "group_by": "PR.OverviewPage", "order_by": "Wins DESC",
    }
    out, offset = {}, 0
    while True:
        params = dict(base, offset=str(offset))
        url = API + "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        rows = None
        for _ in range(6):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=30) as r:
                    data = json.load(r)
            except Exception:
                time.sleep(12); continue
            if "cargoquery" not in data:           # error / rate-limited
                time.sleep(12); continue
            rows = data["cargoquery"]; break
        if rows is None:                           # gave up on this page
            return None
        for row in rows:
            t = row["title"]
            out[mkey(t["Player"])] = (int(t["Wins"]), t["Player"])
        if len(rows) < PAGE:                       # last page
            return out
        offset += PAGE
        time.sleep(5)                              # courtesy pause between pages


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
