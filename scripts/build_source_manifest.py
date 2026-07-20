#!/usr/bin/env python3
"""Regenerate source_manifest.json fingerprints after a reviewed source update."""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from source_model import write_source_manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--timestamp",
        required=True,
        help="ISO-8601 provenance timestamp for this reviewed snapshot",
    )
    parser.add_argument("--batch-id", required=True, help="Shared source refresh batch ID")
    parser.add_argument(
        "--timestamp-kind",
        choices=("retrieved", "curatedReview", "snapshotDate"),
        default="retrieved",
    )
    args = parser.parse_args()
    precision = "second" if "T" in args.timestamp else "date"
    manifest = write_source_manifest(
        ROOT,
        args.timestamp,
        refresh_batch_id=args.batch_id,
        timestamp_kind=args.timestamp_kind,
        timestamp_precision=precision,
    )
    print(f"wrote source_manifest.json ({len(manifest['sources'])} sources)")


if __name__ == "__main__":
    main()
