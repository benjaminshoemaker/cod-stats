"""Canonical source contracts for the static data pipeline.

The raw JSON snapshots intentionally remain easy to inspect.  This module adds
the missing database-like guarantees around them: provenance manifests,
explicit authority policy, stable observation identities, and fail-closed
conflict validation.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MANIFEST_NAME = "source_manifest.json"
POLICY_NAME = "data_source_policy.json"
CONFLICTS_NAME = "source_conflicts.json"
MANIFEST_SCHEMA_VERSION = 2

SOURCE_METADATA = {
    "major_events.json": ("canonical", "CoD Esports Wiki Cargo", "Major/Premier tournaments and first-place team"),
    "player_event_wins.json": ("canonical", "CoD Esports Wiki Cargo", "Major/Premier first-place player and substitute rows"),
    "champs_wins.json": ("canonical", "CoD Esports Wiki Cargo", "World Championship first-place player rows"),
    "player_participation.json": ("canonical", "CoD Esports Wiki Cargo", "All player placements at Major/Premier tournaments"),
    "team_participation.json": ("canonical", "CoD Esports Wiki Cargo", "All team placements at Major/Premier tournaments"),
    "player_accolades.json": ("canonical", "CoD Esports Wiki Cargo", "Supported formal award types joined to tournaments"),
    "player_stats_participants.json": ("canonical", "CoD Esports Wiki Cargo PlayerStats", "Map observations fetched by canonical Major/Premier event page"),
    "player_stats_participants.events.json": ("canonical", "CoD Esports Wiki Cargo", "Canonical played Major/Premier event-page registry for PlayerStats"),
    "legacy_player_event_stats.json": ("supplemental", "codcompstats legacy wiki pages", "Major-only event aggregate K/D coverage"),
    "player_roles.json": ("curated", "cod_stats research", "Curated player role stints"),
    "team_logos.json": ("supplemental", "CoD Esports Wiki assets", "Team display names and cached logo paths"),
    "community_consensus_sources.json": ("curated", "Public community sources", "Reviewed community-consensus source ledger"),
    "community_consensus_ballots.json": ("curated", "Public community sources", "Atomic ballots extracted from scored community sources"),
    "player_authored_sources.json": ("curated", "Public authored sources", "Source-first authored rankings and claims"),
    "validation/benchmarks.json": ("curated", "External benchmark sources", "Dated external claims used as regression fixtures"),
    "validation/breaking-point-benchmarks.json": ("curated", "Breaking Point", "Live objective-stat benchmark definitions"),
    "source_conflict_resolutions.json": ("curated", "cod_stats source review", "Explicit reviewed decisions for otherwise ambiguous source conflicts"),
}

SOURCE_QUERY_VERSIONS = {
    "major_events.json": "cargo-major-events-v1",
    "player_event_wins.json": "cargo-player-major-wins-v1",
    "champs_wins.json": "cargo-championship-wins-v1",
    "player_participation.json": "cargo-player-participation-v1",
    "team_participation.json": "cargo-team-participation-v1",
    "player_accolades.json": "cargo-formal-accolades-v1",
    "player_stats_participants.json": "cargo-major-event-player-stats-v2",
    "player_stats_participants.events.json": "cargo-major-event-registry-v1",
}


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_refresh_batch_id(timestamp=None):
    stamp = (timestamp or utc_now()).replace("-", "").replace(":", "")
    return f"refresh-{stamp}-{uuid.uuid4().hex[:8]}"


class SourceConflictError(RuntimeError):
    """Raised when two facts claim the same stable identity."""


def _json_rows(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("cargoquery"), list):
        return payload["cargoquery"]
    for key in ("sources", "ballots", "roles", "benchmarks"):
        if isinstance(payload, dict) and isinstance(payload.get(key), list):
            return payload[key]
    return None


def file_fingerprint(path):
    path = Path(path)
    raw = path.read_bytes()
    payload = json.loads(raw)
    rows = _json_rows(payload)
    return {
        "rowCount": len(rows) if rows is not None else None,
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def build_source_manifest(
    root=ROOT,
    provenance_timestamp=None,
    previous=None,
    updated_sources=None,
    refresh_batch_id=None,
    timestamp_kind=None,
    timestamp_precision=None,
):
    root = Path(root)
    previous_entries = (previous or {}).get("sources") or {}
    entries = {}
    for name, (status, source, query_scope) in SOURCE_METADATA.items():
        path = root / name
        if not path.exists():
            continue
        prior = previous_entries.get(name) or {}
        use_new_timestamp = updated_sources is None or name in set(updated_sources)
        timestamp = provenance_timestamp if use_new_timestamp else prior.get("provenanceTimestamp")
        timestamp = timestamp or prior.get("provenanceTimestamp")
        default_kind = "retrieved" if status in {"canonical", "deprecated", "supplemental"} else "curatedReview"
        entry_timestamp_kind = (
            timestamp_kind if use_new_timestamp and timestamp_kind
            else prior.get("timestampKind") or default_kind
        )
        entry_precision = (
            timestamp_precision if use_new_timestamp and timestamp_precision
            else prior.get("timestampPrecision")
            or ("second" if timestamp and "T" in timestamp else "date")
        )
        entry_batch_id = (
            refresh_batch_id if use_new_timestamp and refresh_batch_id
            else prior.get("refreshBatchId")
            or (previous or {}).get("latestRefreshBatchId")
        )
        if not timestamp:
            raise RuntimeError(f"{name}: provenance timestamp is required")
        if not entry_batch_id:
            entry_batch_id = f"legacy-{str(timestamp)[:10]}"
        entries[name] = {
            "status": status,
            "source": source,
            "provenanceTimestamp": timestamp,
            "timestampKind": entry_timestamp_kind,
            "timestampPrecision": entry_precision,
            "refreshBatchId": entry_batch_id,
            "sourceSchemaVersion": 1,
            "queryVersion": SOURCE_QUERY_VERSIONS.get(name, "curated-contract-v1"),
            "queryScope": query_scope,
            **file_fingerprint(path),
        }
    latest_batch = refresh_batch_id or (previous or {}).get("latestRefreshBatchId")
    return {
        "schemaVersion": MANIFEST_SCHEMA_VERSION,
        "generatedAt": utc_now(),
        "latestRefreshBatchId": latest_batch or next(iter(entries.values()))["refreshBatchId"],
        "sources": entries,
    }


def write_source_manifest(
    root=ROOT,
    provenance_timestamp=None,
    updated_sources=None,
    refresh_batch_id=None,
    timestamp_kind=None,
    timestamp_precision=None,
):
    root = Path(root)
    path = root / MANIFEST_NAME
    previous = json.loads(path.read_text()) if path.exists() else None
    manifest = build_source_manifest(
        root, provenance_timestamp, previous, updated_sources,
        refresh_batch_id, timestamp_kind, timestamp_precision,
    )
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(manifest, indent=2) + "\n")
    os.replace(tmp, path)
    return manifest


def load_source_policy(root=ROOT):
    path = Path(root) / POLICY_NAME
    if not path.exists():
        raise RuntimeError(f"required source policy is missing: {path}")
    policy = json.loads(path.read_text())
    if policy.get("schemaVersion") != 1 or not policy.get("entities"):
        raise RuntimeError(f"invalid source policy: {path}")
    return policy


def load_conflict_resolutions(root=ROOT):
    path = Path(root) / "source_conflict_resolutions.json"
    if not path.exists():
        raise RuntimeError(f"required conflict resolutions are missing: {path}")
    resolutions = json.loads(path.read_text())
    if resolutions.get("schemaVersion") != 1:
        raise RuntimeError(f"invalid conflict resolution schema: {path}")
    return resolutions


def validate_source_manifest(root=ROOT, required=None):
    root = Path(root)
    path = root / MANIFEST_NAME
    if not path.exists():
        raise RuntimeError(f"required source manifest is missing: {path}")
    manifest = json.loads(path.read_text())
    if manifest.get("schemaVersion") != MANIFEST_SCHEMA_VERSION:
        raise RuntimeError(f"unsupported source manifest schema: {manifest.get('schemaVersion')!r}")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", manifest.get("generatedAt") or ""):
        raise RuntimeError("source manifest generatedAt must be a seconds-precision UTC timestamp")
    if not manifest.get("latestRefreshBatchId"):
        raise RuntimeError("source manifest latestRefreshBatchId is required")
    entries = manifest.get("sources") or {}
    missing = sorted(set(required or ()) - set(entries))
    if missing:
        raise RuntimeError(f"source manifest missing required entries: {', '.join(missing)}")
    required_metadata = {
        "status", "source", "provenanceTimestamp", "timestampKind",
        "timestampPrecision", "refreshBatchId", "sourceSchemaVersion",
        "queryVersion", "queryScope", "rowCount", "sha256",
    }
    for name, entry in entries.items():
        absent = sorted(required_metadata - set(entry))
        if absent:
            raise RuntimeError(f"{name}: source manifest missing metadata: {', '.join(absent)}")
        precision = entry["timestampPrecision"]
        timestamp = entry["provenanceTimestamp"]
        if precision == "second" and not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", timestamp):
            raise RuntimeError(f"{name}: second-precision provenance timestamp is invalid")
        if precision == "date" and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", timestamp):
            raise RuntimeError(f"{name}: date-precision provenance timestamp is invalid")
        if precision not in {"date", "second"}:
            raise RuntimeError(f"{name}: unsupported timestamp precision {precision!r}")
        if not entry["refreshBatchId"] or not entry["queryVersion"]:
            raise RuntimeError(f"{name}: refresh batch and query version are required")
        source_path = root / name
        if not source_path.exists():
            raise RuntimeError(f"manifested source is missing: {source_path}")
        actual = file_fingerprint(source_path)
        if entry["rowCount"] != actual["rowCount"]:
            raise RuntimeError(
                f"{name}: source manifest row count {entry['rowCount']} != {actual['rowCount']}"
            )
        if entry["sha256"] != actual["sha256"]:
            raise RuntimeError(f"{name}: source manifest hash does not match the snapshot")
    return manifest


def validate_conflict_quarantine(root=ROOT):
    path = Path(root) / CONFLICTS_NAME
    if not path.exists():
        raise RuntimeError(f"required conflict quarantine is missing: {path}")
    report = json.loads(path.read_text())
    if report.get("schemaVersion") != 1:
        raise RuntimeError(f"invalid conflict quarantine schema: {path}")
    unresolved = report.get("unresolved") or []
    if unresolved:
        ids = ", ".join(str(row.get("id") or "unknown") for row in unresolved[:5])
        raise SourceConflictError(f"unresolved source conflicts: {ids}")
    return report


def _player_name(row):
    return str(row.get("Player") or row.get("PlayerLink") or row.get("PlayerName") or "").strip()


def _base_observation_key(row):
    return (
        _player_name(row).casefold(),
        str(row.get("EventId") or row.get("Event") or ""),
        str(row.get("Date") or ""),
        str(row.get("SeriesId") or ""),
        str(row.get("Map") or ""),
        str(row.get("Mode") or row.get("Gamemode") or ""),
        str(row.get("Team") or ""),
        str(row.get("TeamVs") or ""),
    )


def _fact_signature(row):
    ignored = {"observationId", "observationOccurrence"}
    return json.dumps({k: row[k] for k in sorted(row) if k not in ignored}, sort_keys=True, separators=(",", ":"))


def canonicalize_map_observations(rows):
    """Validate and identify canonical player-map observations.

    A series can legitimately use the same map/mode more than once, so repeated
    base keys receive occurrence numbers rather than being collapsed.  Exact
    duplicate facts are rejected because the source provides no evidence that
    they are separate maps.  When an upstream stable ID is available it is
    authoritative and conflicting facts for that ID fail immediately.
    """
    upstream = {}
    exact_seen = set()
    # Old snapshots predate Cargo's StatId field. Assign their occurrence
    # numbers by sorted fact content so identity does not depend on file order.
    derived_signatures = defaultdict(set)
    for source_row in rows:
        if not str(source_row.get("StatId") or source_row.get("ObservationId") or "").strip():
            derived_signatures[_base_observation_key(source_row)].add(_fact_signature(source_row))
    derived_occurrences = {
        base: {signature: index for index, signature in enumerate(sorted(signatures), 1)}
        for base, signatures in derived_signatures.items()
    }
    out = []
    for index, source_row in enumerate(rows):
        row = dict(source_row)
        for field in ("Event", "Game", "Mode", "Date", "Team", "TeamVs", "Map", "SeriesId", "Kills", "Deaths"):
            if row.get(field) in (None, ""):
                raise SourceConflictError(f"map observation {index} missing required field {field}")
        if not _player_name(row):
            raise SourceConflictError(f"map observation {index} missing player identity")
        signature = _fact_signature(row)
        upstream_id = str(row.get("StatId") or row.get("ObservationId") or "").strip()
        if upstream_id:
            prior = upstream.get(upstream_id)
            if prior is not None and prior != signature:
                raise SourceConflictError(f"conflicting map facts for upstream observation {upstream_id}")
            if prior is not None:
                raise SourceConflictError(f"exact duplicate map observation {upstream_id}")
            upstream[upstream_id] = signature
            observation_id = f"wiki:{upstream_id}"
            occurrence = 1
        else:
            if signature in exact_seen:
                raise SourceConflictError("exact duplicate map observation without an upstream ID")
            exact_seen.add(signature)
            base = _base_observation_key(row)
            occurrence = derived_occurrences[base][signature]
            encoded = json.dumps([*base, occurrence], separators=(",", ":")).encode()
            observation_id = "derived:" + hashlib.sha256(encoded).hexdigest()[:24]
        row["observationId"] = observation_id
        row["observationOccurrence"] = occurrence
        out.append(row)
    return out
