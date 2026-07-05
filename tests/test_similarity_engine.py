import math
import json

import numpy as np
import pytest

from analysis import similarity


def test_shared_percentiles_give_ties_the_same_rank():
    pct = similarity.shared_percentiles(np.array([0.0, 0.0, 1.0, 2.0]))

    assert pct[0] == pct[1]
    assert pct[0] == pytest.approx(16.6666666667)
    assert pct[-1] == 100


def test_load_players_flattens_skill_rates_and_masks_low_samples(tmp_path):
    data = {
        "leaderboard": [
            {"name": "Enough", "primaryRole": "SMG"},
            {"name": "Sparse", "primaryRole": "AR"},
        ],
        "players": {
            "Enough": {
                "role_by_game": [],
                "skillStats": {
                    "overall": {"kd": 1.123, "interactions": 3550, "maps": 100},
                    "splits": {
                        "respawn": {"kd": 1.234, "maps": 40},
                        "snd": {"kd": 0.987, "maps": 25},
                    },
                },
            },
            "Sparse": {
                "role_by_game": [],
                "skillStats": {
                    "overall": {"kd": 1.8, "interactions": 960, "maps": 24},
                    "splits": {
                        "respawn": {"kd": 1.7, "maps": 12},
                        "snd": {"kd": 1.9, "maps": 4},
                    },
                },
            },
        },
    }
    path = tmp_path / "data.json"
    path.write_text(json.dumps(data))

    players = similarity.load_players(str(path))

    enough = players[0]
    assert enough["skill_kd"] == 1.123
    assert enough["skill_respawn_kd"] == 1.234
    assert enough["skill_snd_kd"] == 0.987
    assert enough["skill_interactions_per_map"] == 35.5
    assert "skill_kd" not in players[1]
    assert "skill_respawn_kd" not in players[1]
    assert "skill_snd_kd" not in players[1]
    assert "skill_interactions_per_map" not in players[1]


def test_contributions_ignore_missing_features_instead_of_nan_poisoning():
    players = [
        {"name": "A", "x": 1, "y": 1},
        {"name": "B", "x": 3},
        {"name": "C", "x": 4, "y": 4},
    ]
    registry = {
        "cap": 4.0,
        "groups": {
            "g": {
                "weight": 1.0,
                "features": {
                    "x": {"label": "X"},
                    "y": {"label": "Y"},
                },
            }
        },
    }
    fs = similarity.FeatureSpace(players, registry)

    contrib = fs.contributions(0, 1)

    assert contrib == [("X", 1.0)]
    assert all(math.isfinite(v) for _, v in contrib)


def test_role_distance_uses_overlapping_known_seasons_only():
    players = [
        {"name": "AR", "x": 1, "role_by_game": [
            {"game": "Ghosts", "role": "AR"},
            {"game": "Advanced Warfare", "role": "Unknown"},
        ]},
        {"name": "Flex", "x": 1, "role_by_game": [
            {"game": "Ghosts", "role": "Flex"},
            {"game": "Advanced Warfare", "role": "SMG"},
        ]},
        {"name": "SMG", "x": 1, "role_by_game": [
            {"game": "Ghosts", "role": "SMG"},
        ]},
        {"name": "NoOverlap", "x": 1, "role_by_game": [
            {"game": "Black Ops 6", "role": "SMG"},
        ]},
    ]
    registry = {
        "cap": 4.0,
        "role_weight": 0.07,
        "groups": {
            "g": {
                "weight": 1.0,
                "features": {"x": {"label": "X"}},
            }
        },
    }
    fs = similarity.FeatureSpace(players, registry)

    assert fs.role_distance(0, 0) == 0
    assert fs.role_distance(0, 1) == 0.5
    assert fs.role_distance(0, 2) == 1.0
    assert fs.role_distance(0, 3) is None
    assert fs.pair_distance(0, 1) == pytest.approx(0.035)
    assert fs.pair_distance(0, 2) == pytest.approx(0.07)
    assert fs.pair_distance(0, 3) == pytest.approx(0.0)
