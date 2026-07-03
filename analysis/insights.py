"""
Insight/outlier finder for the CoD era-adjusted major-wins project.

Goal: surface players who are UNUSUAL on some ratio or signature — the kind of
thing where "JKap wins a high share of World Championships relative to his
era-adjusted overall wins" is one example. We compute a battery of signatures
off the clean, reconciled per-player breakdown in site/data.js (d['players']),
join major_events.json for LAN/region/prizepool metadata, and report the
extremes in each category with real numbers.

Run: python3 analysis/insights.py   (writes analysis/out/insights.json + prints)
"""
from __future__ import annotations
import json, os, datetime as dt
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def load():
    txt = open(os.path.join(ROOT, "site", "data.js")).read()
    txt = txt[txt.index("=") + 1:].rstrip().rstrip(";")
    d = json.loads(txt)
    me = json.load(open(os.path.join(ROOT, "major_events.json")))
    return d, me


def parse_money(s):
    if not s:
        return None
    digits = "".join(c for c in s if c.isdigit())
    return int(digits) if digits else None


def days(a, b):
    fmt = "%Y-%m-%d"
    return (dt.datetime.strptime(b, fmt) - dt.datetime.strptime(a, fmt)).days


def build():
    d, me = load()
    meta = d["meta"]
    players = d["players"]          # dict name -> detail
    lb = {p["name"]: p for p in d["leaderboard"]}
    seasonOrder = meta["seasonOrder"]
    sidx = {g: i for i, g in enumerate(seasonOrder)}

    # event metadata index (by exact event name)
    ev = {}
    for r in me:
        ev[r["Event"]] = r

    rows = []
    for name, p in players.items():
        raw = p["raw"]
        adj = p["adj_all"]
        champs = p["champs"]
        peak = p["peak_all"]["adj"]
        titles = p["titles_all"]
        span = p["span_all"]
        first, last = p["first_year"], p["last_year"]

        # flatten every winning event with metadata + season game
        wins = []
        for s in p["seasons"]:
            for e in s["events"]:
                m = ev.get(e["event"], {})
                wins.append({
                    "event": e["event"], "date": e["date"], "game": s["game"],
                    "pre_bo2": s["pre_bo2"], "weight": e["weight"],
                    "type": m.get("EventType"), "region": m.get("Region"),
                    "prize": parse_money(m.get("Prizepool")),
                })
        wins.sort(key=lambda w: w["date"])
        nwin = len(wins)

        # --- signatures ---
        offline = sum(1 for w in wins if w["type"] and "Offline" in w["type"])
        online = sum(1 for w in wins if w["type"] == "Online")
        regions = Counter(w["region"] for w in wins if w["region"])
        intl = sum(v for k, v in regions.items() if k == "International")
        pre = sum(1 for w in wins if w["pre_bo2"])

        # career timing: mean fractional position of wins in [first_date,last_date]
        frontload = None
        career_days = None
        longest_drought = None
        if nwin >= 2:
            d0, d1 = wins[0]["date"], wins[-1]["date"]
            span_days = days(d0, d1)
            career_days = span_days
            if span_days > 0:
                frontload = sum(days(d0, w["date"]) / span_days for w in wins) / nwin
            gaps = [days(wins[i]["date"], wins[i + 1]["date"]) for i in range(nwin - 1)]
            longest_drought = max(gaps) if gaps else 0

        # best calendar year
        byyear = Counter(w["date"][:4] for w in wins)
        best_year = byyear.most_common(1)[0] if byyear else (None, 0)

        # ring timing
        ring_events = p.get("champ_events", [])
        ring_years = sorted(int(r["year"]) for r in ring_events)
        ring_span = (ring_years[-1] - ring_years[0]) if len(ring_years) >= 2 else 0

        lbp = lb.get(name, {})
        rows.append({
            "name": name,
            "raw": raw, "adj": adj, "champs": champs, "peak": peak,
            "titles": titles, "span": span, "first": first, "last": last,
            "nwin": nwin,
            "adjRank": lbp.get("adjRank"), "rawRank": lbp.get("rawRank"),
            "delta": lbp.get("delta"),
            "adjPost": p["adj_post"],
            # ratios
            "ring_rate": champs / adj if adj else 0,          # rings per adj win
            "peak_share": peak / adj if adj else 0,           # one-season concentration
            "density": (adj / span) if span >= 1 else None,   # adj wins per active yr
            "era_infl": raw / adj if adj else 0,              # raw/adj deflation
            "pre_share": pre / nwin if nwin else 0,
            "offline_share": offline / nwin if nwin else 0,
            "online_share": online / nwin if nwin else 0,
            "intl_share": intl / nwin if nwin else 0,
            "n_regions": len(regions),
            "wins_per_title": raw / titles if titles else 0,
            "frontload": frontload,
            "career_days": career_days,
            "longest_drought": longest_drought,
            "best_year": best_year[0], "best_year_n": best_year[1],
            "ring_years": ring_years, "ring_span": ring_span,
        })
    return meta, rows


def top(rows, key, n=8, reverse=True, filt=None, fmt=None):
    xs = [r for r in rows if (filt(r) if filt else True) and r.get(key) is not None]
    xs.sort(key=lambda r: r[key], reverse=reverse)
    out = []
    for r in xs[:n]:
        v = r[key]
        out.append(f"{r['name']:12s} {fmt(r) if fmt else v}")
    return out


def section(title, lines):
    print(f"\n## {title}")
    for l in lines:
        print(f"  {l}")


def main():
    meta, rows = build()
    print(f"# CoD insight finder — {len(rows)} players "
          f"(console majors={meta['consoleMajors']}, seasons={meta['consoleSeasons']})")

    # 1. Ring merchants (the JKap axis) — most World Champs per era-adjusted win
    section("Ring merchants — World Champs per era-adjusted win (min 1 ring, adj>=2)",
            top(rows, "ring_rate", filt=lambda r: r["champs"] >= 1 and r["adj"] >= 2,
                fmt=lambda r: f"{r['ring_rate']:.3f}  ({r['champs']} rings / {r['adj']:.1f} adj wins, raw {r['raw']})"))

    # 2. Ringless kings — most adjusted wins, zero World Champs
    section("Ringless kings — most era-adjusted wins with ZERO World Champs",
            top(rows, "adj", filt=lambda r: r["champs"] == 0,
                fmt=lambda r: f"{r['adj']:.1f} adj wins, {r['raw']} raw, 0 rings"))

    # 3. One-season wonders — highest share of career in single best season
    section("One-season wonders — best season as share of career (adj>=2)",
            top(rows, "peak_share", filt=lambda r: r["adj"] >= 2,
                fmt=lambda r: f"{r['peak_share']*100:.0f}%  (peak {r['peak']:.2f} of {r['adj']:.1f} adj)"))

    # 4. Iron men — lowest peak-share (most evenly spread), needs real body of work
    section("Metronomes — most evenly spread careers (lowest peak share, adj>=5)",
            top(rows, "peak_share", reverse=False, filt=lambda r: r["adj"] >= 5,
                fmt=lambda r: f"{r['peak_share']*100:.0f}%  (peak {r['peak']:.2f} of {r['adj']:.1f} adj, {r['titles']} titles)"))

    # 5. Era-adjustment winners / losers (rank delta)
    section("Boosted most by era-adjustment (raw rank -> adj rank gain)",
            top(rows, "delta", filt=lambda r: r["delta"] is not None,
                fmt=lambda r: f"+{r['delta']} (raw #{r['rawRank']} -> adj #{r['adjRank']})"))
    section("Penalized most by era-adjustment",
            top(rows, "delta", reverse=False, filt=lambda r: r["delta"] is not None,
                fmt=lambda r: f"{r['delta']} (raw #{r['rawRank']} -> adj #{r['adjRank']})"))

    # 6. Era inflation — raw count deflates most under adjustment (early-era volume)
    section("Volume of the old era — raw/adj ratio highest (raw>=5)",
            top(rows, "era_infl", filt=lambda r: r["raw"] >= 5,
                fmt=lambda r: f"{r['era_infl']:.2f}x  ({r['raw']} raw -> {r['adj']:.1f} adj)"))

    # 7. Pre-BO2 dependence
    section("Ancient regime — highest share of wins that are pre-Black Ops 2 (nwin>=3)",
            top(rows, "pre_share", filt=lambda r: r["nwin"] >= 3,
                fmt=lambda r: f"{r['pre_share']*100:.0f}%  ({r['nwin']} wins, debut {r['first']})"))

    # 8. Density — adj wins per active year
    section("Compressed dominance — era-adj wins per active year (adj>=4, span>=2)",
            top(rows, "density", filt=lambda r: r["adj"] >= 4 and r["span"] >= 2,
                fmt=lambda r: f"{r['density']:.2f}/yr  ({r['adj']:.1f} adj / {r['span']}y)"))

    # 9. Versatility across titles
    section("Journeymen — won across the most distinct CoD titles",
            top(rows, "titles",
                fmt=lambda r: f"{r['titles']} titles ({r['raw']} raw wins, {r['first']}-{r['last']})"))
    section("Specialists — most raw wins concentrated in fewest titles (raw>=6)",
            top(rows, "wins_per_title", filt=lambda r: r["raw"] >= 6,
                fmt=lambda r: f"{r['wins_per_title']:.1f} wins/title  ({r['raw']} raw in {r['titles']} titles)"))

    # 10. LAN vs online
    section("LAN monsters — highest offline share (nwin>=4)",
            top(rows, "offline_share", filt=lambda r: r["nwin"] >= 4,
                fmt=lambda r: f"{r['offline_share']*100:.0f}% offline  ({r['nwin']} wins)"))
    section("Online-heavy resumes — most online wins (nwin>=3)",
            top(rows, "online_share", filt=lambda r: r["nwin"] >= 3,
                fmt=lambda r: f"{r['online_share']*100:.0f}% online  ({r['nwin']} wins)"))

    # 11. Internationalism
    section("Globe-trotters — won across the most distinct regions",
            top(rows, "n_regions", filt=lambda r: r["nwin"] >= 4,
                fmt=lambda r: f"{r['n_regions']} regions, {r['intl_share']*100:.0f}% international ({r['nwin']} wins)"))

    # 12. Career timing
    section("Late bloomers — most back-loaded win timing (nwin>=4, span present)",
            top(rows, "frontload", filt=lambda r: r["nwin"] >= 4 and r["frontload"] is not None,
                fmt=lambda r: f"{r['frontload']*100:.0f}% (1=all-late)  {r['nwin']} wins {r['first']}-{r['last']}"))
    section("Prodigies — most front-loaded win timing (nwin>=4)",
            top(rows, "frontload", reverse=False, filt=lambda r: r["nwin"] >= 4 and r["frontload"] is not None,
                fmt=lambda r: f"{r['frontload']*100:.0f}% (0=all-early)  {r['nwin']} wins {r['first']}-{r['last']}"))

    # 13. Droughts & comebacks
    section("Longest major droughts between wins (days), nwin>=4",
            top(rows, "longest_drought", filt=lambda r: r["nwin"] >= 4,
                fmt=lambda r: f"{r['longest_drought']} days ({r['longest_drought']/365:.1f}y)  {r['nwin']} wins"))

    # 14. Best single year
    section("Biggest single-year hauls (most majors in one calendar year)",
            top(rows, "best_year_n",
                fmt=lambda r: f"{r['best_year_n']} majors in {r['best_year']}  (career {r['raw']} raw)"))

    # 15. Longevity bridges
    section("Longevity — longest span first->last major (days), any nwin",
            top(rows, "career_days", filt=lambda r: r["career_days"] is not None,
                fmt=lambda r: f"{r['career_days']/365:.1f}y  {r['first']}-{r['last']} ({r['raw']} raw)"))

    # 16. Ring longevity
    section("Ring longevity — most years between first & last World Champ",
            top(rows, "ring_span", filt=lambda r: r["champs"] >= 2,
                fmt=lambda r: f"{r['ring_span']}y  rings in {r['ring_years']}"))

    # 17. Most dominant single season ever (absolute peak)
    section("Most dominant single seasons ever (absolute era-adj peak)",
            top(rows, "peak",
                fmt=lambda r: f"{r['peak']:.2f}  ({r['name']})"))

    out = os.path.join(HERE, "out", "insights.json")
    json.dump({"meta": meta, "rows": rows}, open(out, "w"), indent=2)
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
