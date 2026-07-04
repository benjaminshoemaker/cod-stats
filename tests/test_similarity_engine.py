import math

import numpy as np
import pytest

from analysis import similarity


def test_shared_percentiles_give_ties_the_same_rank():
    pct = similarity.shared_percentiles(np.array([0.0, 0.0, 1.0, 2.0]))

    assert pct[0] == pct[1]
    assert pct[0] == pytest.approx(16.6666666667)
    assert pct[-1] == 100


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
