import json

import pytest

import source_model
from source_refresh import SourceRefreshTransaction


def seed_root(root):
    (root / "a.json").write_text('[{"value":"old-a"}]')
    (root / "b.json").write_text('[{"value":"old-b"}]')
    manifest = source_model.build_source_manifest(
        root, provenance_timestamp="2026-07-19T00:00:00Z"
    )
    (root / source_model.MANIFEST_NAME).write_text(json.dumps(manifest, indent=2) + "\n")


@pytest.fixture
def synthetic_sources(monkeypatch, tmp_path):
    monkeypatch.setattr(source_model, "SOURCE_METADATA", {
        "a.json": ("canonical", "test", "a facts"),
        "b.json": ("canonical", "test", "b facts"),
    })
    seed_root(tmp_path)
    return tmp_path


def test_refresh_transaction_rolls_back_every_source_on_validation_failure(synthetic_sources):
    root = synthetic_sources
    original_manifest = (root / source_model.MANIFEST_NAME).read_text()
    transaction = SourceRefreshTransaction(root)
    transaction.stage_json("a.json", [{"value": "new-a"}])
    transaction.stage_json("b.json", [{"value": "new-b"}])

    with pytest.raises(RuntimeError, match="reconciliation failed"):
        transaction.commit(
            validate=lambda: (_ for _ in ()).throw(RuntimeError("reconciliation failed"))
        )

    assert json.loads((root / "a.json").read_text()) == [{"value": "old-a"}]
    assert json.loads((root / "b.json").read_text()) == [{"value": "old-b"}]
    assert (root / source_model.MANIFEST_NAME).read_text() == original_manifest


def test_refresh_transaction_promotes_all_sources_together(synthetic_sources):
    root = synthetic_sources
    transaction = SourceRefreshTransaction(root)
    transaction.stage_json("a.json", [{"value": "new-a"}])
    transaction.stage_json("b.json", [{"value": "new-b"}])
    transaction.commit(validate=lambda: None)

    assert json.loads((root / "a.json").read_text()) == [{"value": "new-a"}]
    assert json.loads((root / "b.json").read_text()) == [{"value": "new-b"}]
    manifest = source_model.validate_source_manifest(root, required={"a.json", "b.json"})
    entries = manifest["sources"]
    assert entries["a.json"]["timestampPrecision"] == "second"
    assert entries["a.json"]["refreshBatchId"] == entries["b.json"]["refreshBatchId"]
    assert entries["a.json"]["refreshBatchId"] == manifest["latestRefreshBatchId"]
