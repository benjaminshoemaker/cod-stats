#!/usr/bin/env python3
"""Build the local BO7 team outslaying versus respawn map-win report for issue #26."""
import html
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analysis import bo7_respawn_data as respawn_data


OUT_PATH = ROOT / "analysis/bo7_team_outslay.html"
BAND_ORDER = (
    "-20 or worse", "-19 to -10", "-9 to -1", "Tied (0)",
    "+1 to +9", "+10 to +19", "+20 or better",
)
CHALLENGERS_TEAMS = frozenset({"Huntsmen", "OMiT", "Project Notorious", "ROC Esports"})


def esc(value):
    return html.escape(str(value), quote=True)


def ratio(num, den):
    return num / den if den else None


def stability_label(maps):
    if maps < 10:
        return "very small sample"
    if maps < 25:
        return "small sample"
    return "descriptive"


def mean(values):
    return statistics.fmean(values) if values else None


def median(values):
    return statistics.median(values) if values else None


def diff_band(value):
    if value <= -20:
        return "-20 or worse"
    if value <= -10:
        return "-19 to -10"
    if value < 0:
        return "-9 to -1"
    if value == 0:
        return "Tied (0)"
    if value < 10:
        return "+1 to +9"
    if value < 20:
        return "+10 to +19"
    return "+20 or better"


def aggregate_team_maps(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[respawn_data.map_key(row)].append(row)
    team_maps = []
    invalid_maps = []
    for key, group in sorted(grouped.items()):
        reasons = []
        teams = sorted({row.get("Team") or "" for row in group})
        if len(group) != 8:
            reasons.append(f"expected 8 player rows, found {len(group)}")
        if len(teams) != 2 or "" in teams:
            reasons.append(f"expected 2 named teams, found {len(set(teams) - {''})}")
        if len({row["player"] for row in group}) != len(group):
            reasons.append("duplicate player rows")
        if len(teams) == 2 and "" not in teams:
            for team in teams:
                team_rows = [row for row in group if row.get("Team") == team]
                opponent = teams[1] if team == teams[0] else teams[0]
                if len(team_rows) != 4:
                    reasons.append(f"expected 4 rows for {team}, found {len(team_rows)}")
                if {row.get("TeamVs") for row in team_rows} != {opponent}:
                    reasons.append("opponent fields do not resolve to the other team")
                if len({row["win"] for row in team_rows}) != 1:
                    reasons.append(f"inconsistent team result for {team}")
        if reasons:
            invalid_maps.append({"key": list(key), "reasons": sorted(set(reasons))})
            continue
        totals = {
            team: sum(row["kills"] for row in group if row.get("Team") == team)
            for team in teams
        }
        for team in teams:
            opponent = teams[1] if team == teams[0] else teams[0]
            team_rows = [row for row in group if row.get("Team") == team]
            kills = totals[team]
            opponent_kills = totals[opponent]
            differential = kills - opponent_kills
            team_maps.append({
                "team": team,
                "opponent": opponent,
                "event": respawn_data.event_key(team_rows[0]),
                "date": team_rows[0].get("Date"),
                "series": team_rows[0].get("SeriesId"),
                "mode": team_rows[0].get("Mode"),
                "map": team_rows[0].get("Map"),
                "kills": kills,
                "opponentKills": opponent_kills,
                "killDiff": differential,
                "slayBucket": "outslay" if differential > 0 else "outslayed" if differential < 0 else "tied",
                "win": team_rows[0]["win"],
                "result": "Win" if team_rows[0]["win"] else "Loss",
                "playerRows": len(team_rows),
            })
    return team_maps, {
        "maps": len(grouped),
        "validMaps": len(grouped) - len(invalid_maps),
        "teamMaps": len(team_maps),
        "invalidMaps": invalid_maps,
    }


def team_map_key(row):
    return (row["event"], row["date"], row["series"], row["mode"], row["map"])


def exclude_challengers_teams(team_maps):
    excluded_keys = {
        team_map_key(row) for row in team_maps
        if row["team"] in CHALLENGERS_TEAMS or row["opponent"] in CHALLENGERS_TEAMS
    }
    return [row for row in team_maps if team_map_key(row) not in excluded_keys], len(excluded_keys)


def aggregate_teams(team_maps, mode=None):
    if mode and mode != "All respawn":
        team_maps = [row for row in team_maps if row["mode"] == mode]
    grouped = defaultdict(list)
    for row in team_maps:
        grouped[row["team"]].append(row)
    output = []
    for team, group in grouped.items():
        maps = len(group)
        wins = sum(row["win"] for row in group)
        losses = maps - wins
        bucket_counts = Counter(row["slayBucket"] for row in group)
        bucket_wins = Counter(row["slayBucket"] for row in group if row["win"])
        outslay_maps = bucket_counts["outslay"]
        outslay_wins = bucket_wins["outslay"]
        tied_maps = bucket_counts["tied"]
        tied_wins = bucket_wins["tied"]
        outslayed_maps = bucket_counts["outslayed"]
        negative_slay_wins = bucket_wins["outslayed"]
        non_outslay_maps = tied_maps + outslayed_maps
        non_outslay_wins = tied_wins + negative_slay_wins
        win_given_outslay = ratio(outslay_wins, outslay_maps)
        win_given_non_outslay = ratio(non_outslay_wins, non_outslay_maps)
        output.append({
            "team": team,
            "maps": maps,
            "wins": wins,
            "losses": losses,
            "winRate": ratio(wins, maps),
            "outslayMaps": outslay_maps,
            "outslayWins": outslay_wins,
            "outslayFailures": outslay_maps - outslay_wins,
            "winGivenOutslay": win_given_outslay,
            "outslayFailureRate": ratio(outslay_maps - outslay_wins, outslay_maps),
            "tiedMaps": tied_maps,
            "tiedWins": tied_wins,
            "winGivenTied": ratio(tied_wins, tied_maps),
            "outslayedMaps": outslayed_maps,
            "negativeSlayWins": negative_slay_wins,
            "winGivenOutslayed": ratio(negative_slay_wins, outslayed_maps),
            "winGivenNonOutslay": win_given_non_outslay,
            "outslayGivenWin": ratio(outslay_wins, wins),
            "outslayGivenLoss": ratio(outslay_maps - outslay_wins, losses),
            "outslayWinUplift": (
                win_given_outslay - win_given_non_outslay
                if win_given_outslay is not None and win_given_non_outslay is not None else None
            ),
            "avgKillDiff": mean([row["killDiff"] for row in group]),
            "medianKillDiff": median([row["killDiff"] for row in group]),
            "avgWinKillDiff": mean([row["killDiff"] for row in group if row["win"]]),
            "medianWinKillDiff": median([row["killDiff"] for row in group if row["win"]]),
            "avgLossKillDiff": mean([row["killDiff"] for row in group if not row["win"]]),
            "medianLossKillDiff": median([row["killDiff"] for row in group if not row["win"]]),
            "stability": stability_label(maps),
        })
    return sorted(output, key=lambda row: (-row["maps"], row["team"].lower()))


def aggregate_diff_bands(team_maps, mode=None):
    if mode and mode != "All respawn":
        team_maps = [row for row in team_maps if row["mode"] == mode]
    grouped = defaultdict(list)
    for row in team_maps:
        grouped[(row["team"], diff_band(row["killDiff"]))].append(row)
    output = []
    for (team, band), group in grouped.items():
        wins = sum(row["win"] for row in group)
        output.append({
            "team": team, "band": band, "bandOrder": BAND_ORDER.index(band),
            "maps": len(group), "wins": wins, "losses": len(group) - wins,
            "winRate": ratio(wins, len(group)),
        })
    return sorted(output, key=lambda row: (row["team"].lower(), row["bandOrder"]))


def overall(team_maps):
    counts = Counter(row["slayBucket"] for row in team_maps)
    wins = Counter(row["slayBucket"] for row in team_maps if row["win"])
    return {
        "teamMaps": len(team_maps),
        "maps": len(team_maps) // 2,
        "teams": len({row["team"] for row in team_maps}),
        "events": len({row["event"] for row in team_maps}),
        "outslayMaps": counts["outslay"],
        "tiedMaps": counts["tied"],
        "outslayedMaps": counts["outslayed"],
        "winGivenOutslay": ratio(wins["outslay"], counts["outslay"]),
        "winGivenTied": ratio(wins["tied"], counts["tied"]),
        "winGivenOutslayed": ratio(wins["outslayed"], counts["outslayed"]),
    }


def report_html(team_maps, audit, rejected, progress):
    scopes = ["All respawn", *sorted({row["mode"] for row in team_maps})]
    scoped_rows = {scope: team_maps if scope == "All respawn" else [row for row in team_maps if row["mode"] == scope] for scope in scopes}
    summaries = {scope: aggregate_teams(rows) for scope, rows in scoped_rows.items()}
    overalls = {scope: overall(rows) for scope, rows in scoped_rows.items()}
    drilldowns = {scope: rows for scope, rows in scoped_rows.items()}
    initial_scope = "Hardpoint" if "Hardpoint" in scopes else "All respawn"
    initial = overalls[initial_scope]
    hardpoint_summaries = summaries.get("Hardpoint", [])
    larger_hardpoint_samples = [row for row in hardpoint_summaries if row["maps"] >= 25 and row["outslayGivenWin"] is not None]
    most_reliant = max(larger_hardpoint_samples, key=lambda row: (row["outslayGivenWin"], row["wins"])) if larger_hardpoint_samples else None
    least_reliant = min(larger_hardpoint_samples, key=lambda row: (row["outslayGivenWin"], -row["wins"])) if larger_hardpoint_samples else None
    hardpoint_overall = overalls.get("Hardpoint", initial)
    if most_reliant and least_reliant:
        finding = (
            f"Across {hardpoint_overall['maps']} Hardpoints, the team with more kills won "
            f"{100 * hardpoint_overall['winGivenOutslay']:.1f}% of the time. Among teams with 25+ "
            f"Hardpoints, {most_reliant['team']} was most reliant: it outslayed in "
            f"{most_reliant['outslayWins']} of {most_reliant['wins']} wins "
            f"({100 * most_reliant['outslayGivenWin']:.1f}%). {least_reliant['team']} was least "
            f"reliant: {least_reliant['outslayWins']} of {least_reliant['wins']} wins "
            f"({100 * least_reliant['outslayGivenWin']:.1f}%), with "
            f"{least_reliant['negativeSlayWins']} wins while being outslayed. The 25-map threshold "
            "is only for this headline comparison; every team remains in the table below."
        )
    else:
        finding = "The full sortable table below retains every team and labels small samples."
    failed = progress.get("failed") or {}
    js = lambda value: json.dumps(value).replace("</", "<\\/")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Black Ops 7: team outslaying and respawn map wins</title>
<link rel="stylesheet" href="../site/vendor/tabulator.min.css"><link rel="stylesheet" href="../site/assets/style.css">
<style>body{{background:var(--bg,#0b0e13)}} main{{max-width:1500px;margin:0 auto;padding:28px 20px 60px}} .cards{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:18px 0}} .card{{border:1px solid var(--line);background:var(--panel);border-radius:10px;padding:14px}} .k{{font-size:12px;color:var(--muted);text-transform:uppercase}} .v{{font-size:25px;font-weight:800;margin-top:4px}} .sub{{font-size:12px;color:var(--muted);margin-top:4px}} .controls{{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:18px 0}} select{{background:var(--panel);color:var(--text);border:1px solid var(--line);padding:8px;border-radius:6px}} .callout{{border-left:3px solid var(--gold);padding:10px 14px;background:var(--panel);margin:16px 0}} .table-block{{margin-bottom:34px}} .section-note{{max-width:950px}} details{{border:1px solid var(--line);border-radius:8px;background:var(--panel);padding:12px 14px;margin:18px 0}} summary{{cursor:pointer;font-weight:700}} details .controls{{margin-top:14px}} details ul{{margin-bottom:0}} @media(max-width:850px){{.cards{{grid-template-columns:1fr 1fr}}}} @media(max-width:520px){{.cards{{grid-template-columns:1fr}}}}</style>
</head><body><main><p class="eyebrow">Local analysis · GitHub #26</p><h1>Black Ops 7: team outslaying and respawn map wins</h1>
<p class="lede">Which CDL teams were most—and least—reliant on slaying to win Hardpoints? Every included BO7 Major/Premier respawn map through {esc(respawn_data.ASOF)} is validated from eight player rows. Challengers-qualified teams—and entire maps involving them—are excluded. Hardpoint is the default; Overload and all-respawn views remain available. Same-map association is descriptive, not causal.</p>
<div class="cards"><div class="card"><div class="k">Major events</div><div class="v" id="events-card">{initial['events']}</div><div class="sub">Challengers teams excluded</div></div><div class="card"><div class="k">Maps</div><div class="v" id="maps-card">{initial['maps']}</div><div class="sub" id="maps-note">{esc(initial_scope)}</div></div><div class="card"><div class="k">CDL teams</div><div class="v" id="teams-card">{initial['teams']}</div><div class="sub">Every league team included</div></div><div class="card"><div class="k">Team-map rows</div><div class="v" id="rows-card">{initial['teamMaps']}</div><div class="sub">Two validated sides per map</div></div></div>
<div class="callout" id="hardpoint-finding"><strong>Hardpoint read:</strong> {esc(finding)}</div>
<div class="controls"><label for="mode">Mode</label><select id="mode">{''.join(f'<option{(" selected" if scope == initial_scope else "")}>{esc(scope)}</option>' for scope in scopes)}</select></div>
<section class="table-block"><h2>Slaying reliance: most to least</h2><p class="section-note"><strong>Wins with outslay</strong> is the reliance measure: P(team outslayed | team won). The next two columns separate converting a kill edge from winning without one. Fractions keep every denominator visible; teams with no wins show n/a. No minimum-map cutoff is applied.</p><div id="summary-table"></div></section>
<details id="drilldown"><summary>Open team map drilldown</summary><div class="controls"><label for="team">Team</label><select id="team"></select></div><div id="drilldown-table"></div></details>
<details><summary>Coverage and exclusions</summary><ul><li>Source maps validated: {audit['validMaps']} / {audit['maps']}</li><li>Maps excluded for a Challengers-qualified team: {audit['excludedChallengersMaps']}</li><li>Included team-map rows: {audit['includedTeamMaps']}</li><li>Invalid maps: {len(audit['invalidMaps'])}</li><li>Fetch failures: {len(failed)}</li></ul><p class="small muted">Excluded teams: {esc(', '.join(sorted(CHALLENGERS_TEAMS)))}. Rejected player rows: {esc(json.dumps(rejected, sort_keys=True))}.</p></details>
<p class="small muted">Related individual-player K/D analysis: <a href="https://github.com/benjaminshoemaker/cod-stats/issues/27">GitHub #27</a>.</p>
<script src="../site/vendor/tabulator.min.js"></script><script src="../site/assets/app.js"></script><script>
const summaries={js(summaries)}; const overalls={js(overalls)}; const drilldowns={js(drilldowns)};
const pct=v=>v==null?'n/a':(100*v).toFixed(1)+'%'; const num=v=>v==null?'n/a':(v>=0?'+':'')+v.toFixed(1);
const fraction=(num,den,rate)=>pct(rate)+' · '+num+'/'+den;
const percentageSorter=(a,b)=>{{if(a==null&&b==null)return 0;if(a==null)return -1;if(b==null)return 1;return a-b;}};
const columns=[{{title:'Team',field:'team',frozen:true}},{{title:'HPs',field:'maps',sorter:'number',headerTooltip:'Included maps in the selected mode'}},{{title:'W–L',field:'wins',formatter:c=>c.getRow().getData().wins+'–'+c.getRow().getData().losses}},{{title:'Wins with outslay',field:'outslayGivenWin',formatter:c=>{{const d=c.getRow().getData();return fraction(d.outslayWins,d.wins,d.outslayGivenWin)}},sorter:percentageSorter,headerTooltip:'Sorted by percentage: outslay wins / all wins'}},{{title:'Win when outslaying',field:'winGivenOutslay',formatter:c=>{{const d=c.getRow().getData();return fraction(d.outslayWins,d.outslayMaps,d.winGivenOutslay)}},sorter:percentageSorter,headerTooltip:'Sorted by percentage: outslay wins / maps with a positive kill differential'}},{{title:'Win when outslayed',field:'winGivenOutslayed',formatter:c=>{{const d=c.getRow().getData();return fraction(d.negativeSlayWins,d.outslayedMaps,d.winGivenOutslayed)}},sorter:percentageSorter,headerTooltip:'Sorted by percentage: wins / maps with a negative kill differential'}}];
const drillCols=[{{title:'Date',field:'date'}},{{title:'Event',field:'event'}},{{title:'Mode',field:'mode'}},{{title:'Map',field:'map'}},{{title:'Opponent',field:'opponent'}},{{title:'Team kills',field:'kills',sorter:'number'}},{{title:'Opponent kills',field:'opponentKills',sorter:'number'}},{{title:'Kill diff',field:'killDiff',formatter:c=>num(c.getValue()),sorter:'number'}},{{title:'Slay result',field:'slayBucket'}},{{title:'Map result',field:'result'}}];
const opts=(label,data,columns,sort)=>({{label,data,layout:'fitDataStretch',responsiveLayout:false,columns:columns.map(column=>({{headerTooltip:column.title,...column}})),initialSort:sort}});
const initial={json.dumps(initial_scope)};
const summaryTable=TableSurface.mountTabulator('#summary-table',opts('Team slaying reliance',summaries[initial],columns,[{{column:'outslayGivenWin',dir:'desc'}},{{column:'maps',dir:'desc'}}]));
const drillTable=TableSurface.mountTabulator('#drilldown-table',opts('Underlying team-map results',[],drillCols,[{{column:'date',dir:'desc'}}]));
function populateTeams(scope){{const select=document.getElementById('team');const prior=select.value;const names=[...new Set(drilldowns[scope].map(row=>row.team))].sort((a,b)=>a.localeCompare(b));select.innerHTML=names.map(name=>`<option>${{name}}</option>`).join('');if(names.includes(prior))select.value=prior;}}
function applyTeam(){{const scope=document.getElementById('mode').value;const team=document.getElementById('team').value;drillTable.replaceData(drilldowns[scope].filter(row=>row.team===team));}}
function applyScope(){{const scope=document.getElementById('mode').value;const data=overalls[scope];document.getElementById('events-card').textContent=data.events;document.getElementById('maps-card').textContent=data.maps;document.getElementById('maps-note').textContent=scope;document.getElementById('teams-card').textContent=data.teams;document.getElementById('rows-card').textContent=data.teamMaps;summaryTable.replaceData(summaries[scope]);populateTeams(scope);applyTeam();}}
document.getElementById('mode').addEventListener('change',applyScope);document.getElementById('team').addEventListener('change',applyTeam);populateTeams(initial);applyTeam();
document.getElementById('drilldown').addEventListener('toggle',event=>{{if(event.target.open)drillTable.redraw(true);}});
</script></main></body></html>"""


def build_report(raw_rows, progress=None):
    player_rows, rejected = respawn_data.normalize_rows(raw_rows)
    player_audit = respawn_data.validate_maps(player_rows)
    if player_audit["invalidMaps"]:
        raise RuntimeError(f"Player-map validation failed for {len(player_audit['invalidMaps'])} maps")
    team_maps, audit = aggregate_team_maps(player_audit["rows"])
    if audit["invalidMaps"]:
        raise RuntimeError(f"Team-map validation failed for {len(audit['invalidMaps'])} maps")
    if not team_maps:
        raise RuntimeError("No valid BO7 respawn team maps")
    team_maps, excluded_maps = exclude_challengers_teams(team_maps)
    audit["excludedChallengersMaps"] = excluded_maps
    audit["includedTeamMaps"] = len(team_maps)
    OUT_PATH.write_text(report_html(team_maps, audit, rejected, progress or {"failed": {}}))
    return team_maps, audit


def main():
    raw_rows, progress = respawn_data.load_or_fetch_rows()
    if progress.get("failed"):
        raise RuntimeError(f"PlayerStats fetch failures: {progress['failed']}")
    team_maps, audit = build_report(raw_rows, progress)
    print(f"wrote {OUT_PATH.relative_to(ROOT)}")
    print(f"validated {audit['validMaps']} maps, {len(team_maps)} team-map rows, {len({row['team'] for row in team_maps})} teams")
    print(dict(sorted(Counter(row["mode"] for row in team_maps).items())))


if __name__ == "__main__":
    main()
