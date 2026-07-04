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
