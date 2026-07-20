#!/usr/bin/env python3
"""Reconcile overlapping source facts and write the conflict quarantine."""
import json
import os
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import build_data
from source_model import SourceConflictError, canonicalize_map_observations, load_conflict_resolutions


def main():
    raw_events = json.load(open(os.path.join(ROOT, "major_events.json")))
    sources = build_data.load_source_bundle()
    events_all, events = sources.events_all, sources.events
    pwins, champs = sources.player_wins, sources.champs_wins
    ppart, tpart, accolades = (
        sources.player_participation, sources.team_participation, sources.accolades
    )
    stats, event_pages = sources.canonical_map_stats, sources.event_pages
    unresolved = []
    resolved = []
    resolutions = load_conflict_resolutions(ROOT)

    name_ids = defaultdict(set)
    for row in [*raw_events, *event_pages]:
        game = row.get("Game") or row.get("game")
        event = row.get("Event") or row.get("event")
        event_id = row.get("EventId") or row.get("OverviewPage") or row.get("page")
        if game and event and event_id:
            name_ids[(game, event)].add(event_id)
    for (game, event), ids in sorted(name_ids.items()):
        if len(ids) < 2:
            continue
        item = {
            "id": f"event-identity:{game}:{event}",
            "entity": "majorEvent",
            "facts": sorted(ids),
        }
        if game in build_data.DROP_GAMES or event in build_data.DROP_EVENTS:
            resolved.append({**item, "resolution": "Excluded before canonical identity is built", "policy": "DROP_GAMES/DROP_EVENTS"})
        else:
            unresolved.append(item)

    registry = build_data.build_event_registry(events_all, event_pages, pwins, ppart, tpart, stats, accolades)
    grouped = defaultdict(list)
    for row in ppart:
        if not build_data._keep(row) or not build_data._played(row.get("Date")):
            continue
        grouped[(build_data.mkey(row.get("Player")), build_data.event_id_for(row, registry))].append(row)
    for (player, event_id), rows in sorted(grouped.items()):
        if len(rows) < 2:
            continue
        try:
            chosen = build_data.select_participation_row(rows, player, event_id, resolutions)
        except RuntimeError as exc:
            unresolved.append({
                "id": f"participation:{player}:{event_id}", "entity": "participation",
                "facts": rows, "reason": str(exc),
            })
            continue
        best_place = build_data.place_x2(chosen)
        tied_best = [row for row in rows if build_data.place_x2(row) == best_place]
        decision = (resolutions.get("participation") or {}).get(
            f"participation:{player}:{event_id}"
        )
        resolved.append({
            "id": f"participation:{player}:{event_id}",
            "entity": "participation",
            "facts": rows,
            "resolution": {
                "rule": "explicitReviewedDecision" if len(tied_best) > 1 else "bestPlacement",
                "chosen": chosen,
                **({"review": decision} if len(tied_best) > 1 else {}),
            },
            "policy": "data_source_policy.json#participation",
        })

    try:
        canonicalize_map_observations(stats)
    except SourceConflictError as exc:
        unresolved.append({"id": "map-observation-validation", "entity": "mapObservation", "reason": str(exc)})
    try:
        build_data.validate_cross_source_consistency(events, pwins, champs, ppart, tpart, registry)
    except RuntimeError as exc:
        unresolved.append({"id": "cross-source-reconciliation", "entity": "crossSource", "reason": str(exc)})

    report = {
        "schemaVersion": 1,
        "asOf": build_data.ASOF,
        "unresolved": unresolved,
        "resolved": resolved,
    }
    path = os.path.join(ROOT, "source_conflicts.json")
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    os.replace(tmp, path)
    print(f"wrote source_conflicts.json ({len(resolved)} resolved, {len(unresolved)} unresolved)")
    if unresolved:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
