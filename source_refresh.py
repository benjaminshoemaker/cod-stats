"""All-or-rollback source snapshot promotion for multi-source refreshes."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
from pathlib import Path

import source_model


class SourceRefreshTransaction:
    """Stage source writes and promote them as one validated unit.

    Files are replaced individually because the repository keeps human-readable
    JSON at stable paths. A complete backup is retained until validation passes,
    so any write or validation failure restores the pre-refresh snapshot.
    """

    def __init__(self, root):
        self.root = Path(root)
        self.stage_root = Path(tempfile.mkdtemp(prefix="source-refresh-stage-", dir=self.root))
        self.backup_root = None
        self.updated_sources = set()

        for name in source_model.SOURCE_METADATA:
            source = self.root / name
            if source.exists():
                target = self.stage_root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)

    def stage_json(self, name, payload):
        target = self.stage_root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps(payload))
        os.replace(tmp, target)
        self.updated_sources.add(name)

    def commit(self, validate=None, rollback_side_effects=()):
        if not self.updated_sources:
            self.close()
            return
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        previous = json.loads((self.root / source_model.MANIFEST_NAME).read_text())
        manifest = source_model.build_source_manifest(
            self.stage_root,
            provenance_timestamp=timestamp,
            previous=previous,
            updated_sources=self.updated_sources,
        )
        (self.stage_root / source_model.MANIFEST_NAME).write_text(
            json.dumps(manifest, indent=2) + "\n"
        )
        source_model.validate_source_manifest(self.stage_root)

        targets = sorted(self.updated_sources) + [source_model.MANIFEST_NAME]
        side_effects = list(rollback_side_effects)
        self.backup_root = Path(tempfile.mkdtemp(prefix="source-refresh-backup-", dir=self.root))
        existed = set()
        for name in [*targets, *side_effects]:
            source = self.root / name
            if source.exists():
                existed.add(name)
                backup = self.backup_root / name
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, backup)

        try:
            for name in targets:
                source = self.stage_root / name
                target = self.root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                tmp = target.with_name(target.name + f".{os.getpid()}.promote")
                shutil.copy2(source, tmp)
                os.replace(tmp, target)
            if validate:
                validate()
        except BaseException:
            for name in [*targets, *side_effects]:
                target = self.root / name
                backup = self.backup_root / name
                if name in existed:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(backup, target)
                elif target.exists():
                    target.unlink()
            raise
        finally:
            self.close()

    def close(self):
        if self.stage_root and self.stage_root.exists():
            shutil.rmtree(self.stage_root)
        if self.backup_root and self.backup_root.exists():
            shutil.rmtree(self.backup_root)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is not None:
            self.close()
        return False
