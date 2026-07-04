import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_script(name):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.removesuffix(".py"), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_live_source_query_excludes_non_console_ecosystems_and_dropped_events():
    check_live_source = _load_script("check_live_source.py")
    where = check_live_source.source_exclusion_where()
    assert "TO.Game NOT IN" in where
    assert '"Mobile"' in where
    assert '"Warzone"' in where
    assert "TO.Name NOT IN" in where
    assert "Call of Duty Challengers Finals 2026" in where


def test_brianstats1_hydra_benchmarks_pass_against_committed_sources():
    validate_benchmarks = _load_script("validate_benchmarks.py")
    fixtures = ROOT / "validation" / "benchmarks.json"
    benches = validate_benchmarks.load_benchmarks(fixtures)
    hydra = [b for b in benches if b["id"].startswith("brianstats1-hydra-")]
    assert len(hydra) == 2
    assert all(validate_benchmarks.evaluate(b)["ok"] for b in hydra)


def test_benchmark_runner_reports_failures(tmp_path):
    validate_benchmarks = _load_script("validate_benchmarks.py")
    fixtures = tmp_path / "benchmarks.json"
    fixtures.write_text(json.dumps({
        "benchmarks": [{
            "id": "intentional-failure",
            "status": "active",
            "source": "test",
            "sourceDate": "2025-05-26",
            "asOf": "2025-05-26",
            "player": "HyDra",
            "metric": "raw_major_wins",
            "expected": 999
        }]
    }))
    assert validate_benchmarks.main(["--fixtures", str(fixtures)]) == 1


def test_breaking_point_live_benchmarks_are_skipped_by_default(tmp_path):
    validate_benchmarks = _load_script("validate_benchmarks.py")
    fixtures = tmp_path / "benchmarks.json"
    fixtures.write_text(json.dumps({
        "benchmarks": [{
            "id": "skipped-live",
            "status": "live",
            "source": "Breaking Point",
            "sourceUrl": "https://breakingpoint.gg/players/18/kenny",
            "player": "Kenny",
            "metric": "not_a_real_metric",
            "expected": {}
        }]
    }))
    assert validate_benchmarks.main(["--fixtures", str(fixtures)]) == 0


def test_breaking_point_season_kd_compares_live_source_to_local_rows(monkeypatch):
    validate_benchmarks = _load_script("validate_benchmarks.py")

    def fake_bp_rows(_url):
        return (
            [{"season_id": 2024, "kills": 3891, "deaths": 3908}]
            + [{"season_id": 2024, "kills": 0, "deaths": 0} for _ in range(221)]
            + [{"season_id": 2023, "kills": 1, "deaths": 1}]
        )

    monkeypatch.setattr(validate_benchmarks, "_bp_player_stats", fake_bp_rows)
    result = validate_benchmarks.evaluate({
        "id": "bp-kenny-mwiii-test",
        "status": "live",
        "source": "Breaking Point",
        "sourceUrl": "https://breakingpoint.gg/players/18/kenny",
        "player": "Kenny",
        "metric": "breaking_point_season_kd",
        "asOf": "2026-06-29",
        "localFilters": {"games": ["Modern Warfare III"]},
        "externalFilters": {"seasonId": 2024},
        "expected": {"mapsDelta": 0, "kdDelta": 0},
        "tolerance": 0.005,
    })
    assert result["ok"]
    assert result["actual"]["local"]["maps"] == 222
    assert result["actual"]["breakingPoint"] == {"kills": 3891, "deaths": 3908, "maps": 222, "kd": 0.996}
