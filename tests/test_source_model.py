import hashlib
import json

import pytest

import build_data
import source_model


def stat_row(**overrides):
    row = {
        "Player": "Scump",
        "Event": "Call of Duty Championship 2013",
        "EventId": "Call of Duty Championship 2013",
        "Game": "Black Ops 2",
        "Mode": "Hardpoint",
        "Date": "2013-04-07",
        "Team": "OpTic Gaming",
        "TeamVs": "Fariko Impact",
        "Map": "Yemen",
        "SeriesId": "series-1",
        "Kills": 38,
        "Deaths": 35,
    }
    row.update(overrides)
    return row


def test_repeated_map_names_receive_distinct_observation_ids():
    rows = [stat_row(Kills=38), stat_row(Kills=31)]

    observations = source_model.canonicalize_map_observations(rows)

    assert len(observations) == 2
    assert observations[0]["observationId"] != observations[1]["observationId"]
    assert sorted(row["observationOccurrence"] for row in observations) == [1, 2]


def test_derived_observation_ids_are_stable_when_source_rows_are_reordered():
    rows = [stat_row(Kills=38), stat_row(Kills=31)]

    forward = source_model.canonicalize_map_observations(rows)
    reversed_rows = source_model.canonicalize_map_observations(list(reversed(rows)))

    forward_ids = {row["Kills"]: row["observationId"] for row in forward}
    reversed_ids = {row["Kills"]: row["observationId"] for row in reversed_rows}
    assert forward_ids == reversed_ids


def test_exact_duplicate_map_observation_is_rejected():
    row = stat_row()
    with pytest.raises(source_model.SourceConflictError, match="exact duplicate map observation"):
        source_model.canonicalize_map_observations([row, dict(row)])


def test_conflicting_upstream_observation_id_is_rejected():
    rows = [stat_row(StatId="wiki-1", Kills=38), stat_row(StatId="wiki-1", Kills=31)]
    with pytest.raises(source_model.SourceConflictError, match="wiki-1"):
        source_model.canonicalize_map_observations(rows)


def test_event_registry_rejects_conflicting_ids():
    rows = [
        {"Game": "Black Ops 2", "Event": "Same Event", "EventId": "Page/A"},
        {"Game": "Black Ops 2", "Event": "Same Event", "EventId": "Page/B"},
    ]
    with pytest.raises(RuntimeError, match="conflicting event IDs"):
        build_data.build_event_registry(rows, [])


def test_cross_source_winner_conflict_is_rejected():
    events = [{"Game": "Black Ops 2", "Event": "Major", "EventId": "Major", "Winner": "Team A"}]
    tpart = [{"Game": "Black Ops 2", "Event": "Major", "EventId": "Major", "Team": "Team B", "Place": "1"}]
    registry = build_data.build_event_registry(events, [], tpart)
    with pytest.raises(RuntimeError, match="conflicts with team results"):
        build_data.validate_cross_source_consistency(events, [], [], [], tpart, registry)


def test_equal_best_participation_placements_require_reviewed_resolution():
    rows = [
        {"Player": "Lewis", "Event": "Major", "Place": "9-12", "Team": "A"},
        {"Player": "Lewis", "Event": "Major", "Place": "9-12", "Team": "B"},
    ]
    conflict_id = "participation:lewis:Major"
    with pytest.raises(RuntimeError, match="explicit reviewed resolution"):
        build_data.select_participation_row(rows, "lewis", "Major", {"participation": {}})

    resolutions = {"participation": {conflict_id: {
        "chosenTeam": "B",
        "reviewedAt": "2026-07-19",
        "rationale": "Reviewed synthetic decision",
        "evidence": ["https://example.com/evidence"],
    }}}
    assert build_data.select_participation_row(rows, "lewis", "Major", resolutions)["Team"] == "B"


def test_source_manifest_validates_hash_row_count_and_required_metadata(tmp_path):
    payload = [{"id": 1}, {"id": 2}]
    raw = json.dumps(payload).encode()
    (tmp_path / "facts.json").write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    manifest = {
        "schemaVersion": source_model.MANIFEST_SCHEMA_VERSION,
        "generatedAt": "2026-07-19T01:02:03Z",
        "latestRefreshBatchId": "test-batch",
        "sources": {
            "facts.json": {
                "status": "canonical",
                "source": "Example",
                "provenanceTimestamp": "2026-07-19T00:00:00Z",
                "timestampKind": "retrieved",
                "timestampPrecision": "second",
                "refreshBatchId": "test-batch",
                "sourceSchemaVersion": 1,
                "queryVersion": "test-query-v1",
                "queryScope": "Synthetic facts",
                "rowCount": 2,
                "sha256": digest,
            }
        },
    }
    (tmp_path / "source_manifest.json").write_text(json.dumps(manifest))

    assert source_model.validate_source_manifest(tmp_path, required={"facts.json"}) == manifest

    manifest["sources"]["facts.json"]["rowCount"] = 3
    (tmp_path / "source_manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(RuntimeError, match="row count"):
        source_model.validate_source_manifest(tmp_path, required={"facts.json"})


def test_source_policy_names_authority_and_conflict_action():
    policy = source_model.load_source_policy()
    map_policy = policy["entities"]["mapObservation"]
    assert map_policy["authority"] == "player_stats_participants.json"
    assert map_policy["conflictAction"] == "fail"
    assert "player_stats.json" in map_policy["deprecatedSources"]


def test_committed_source_manifest_and_quarantine_are_current():
    manifest = source_model.validate_source_manifest(
        source_model.ROOT, required=build_data.REQUIRED_CORE_SOURCE_FILES
    )
    assert manifest["sources"]["player_stats_participants.json"]["status"] == "canonical"
    assert manifest["sources"]["player_stats.json"]["status"] == "deprecated"
    assert manifest["schemaVersion"] == 2
    assert {entry["timestampPrecision"] for entry in manifest["sources"].values()} == {"date"}
    assert {entry["refreshBatchId"] for entry in manifest["sources"].values()} == {
        "snapshot-2026-07-19-import"
    }
    assert all(entry["queryVersion"] for entry in manifest["sources"].values())
    report = source_model.validate_conflict_quarantine(source_model.ROOT)
    assert report["unresolved"] == []


def test_committed_canonical_map_source_has_unique_observations():
    rows = json.loads((source_model.ROOT / "player_stats_participants.json").read_text())
    assert rows
    observations = source_model.canonicalize_map_observations(rows)
    assert len(observations) == len(rows)
    assert len({row["observationId"] for row in observations}) == len(rows)


def test_stat_id_backfill_checkpoint_is_complete_for_finished_event_pages():
    partial_path = source_model.ROOT / "player_stats_participants.partial.json"
    progress_path = source_model.ROOT / "player_stats_participants.progress.json"
    if not partial_path.exists() and not progress_path.exists():
        rows = json.loads(
            (source_model.ROOT / "player_stats_participants.json").read_text()
        )
        assert rows
        assert all(row.get("StatId") for row in rows)
        return

    assert partial_path.exists() and progress_path.exists()
    rows = json.loads(partial_path.read_text())
    progress = json.loads(progress_path.read_text())
    completed = set(progress.get("completed") or [])
    assert completed
    assert not progress.get("failed")
    assert {row.get("Event") for row in rows} <= completed
    usable = [
        row for row in rows
        if row.get("Kills") not in (None, "") and row.get("Deaths") not in (None, "")
    ]
    assert all(row.get("StatId") for row in usable)
