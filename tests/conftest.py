"""Shared pytest fixtures for randomized rectifier parameter testing.

Provides seeded random-parameter generators so every exercise's test suite
draws from the same reproducible distributions of R, L, Vs, f, alpha.
"""
import random

import pytest

N_RANDOM_CASES = 200
SEED = 12345


def _rng():
    r = random.Random(SEED)
    return r


@pytest.fixture(scope="session")
def random_rl_cases():
    """List of (R_ohm, L_H) tuples, R in [1, 100] Ohm, L in [1, 200] mH."""
    r = _rng()
    return [
        (r.uniform(1.0, 100.0), r.uniform(1.0, 200.0) * 1e-3)
        for _ in range(N_RANDOM_CASES)
    ]


@pytest.fixture(scope="session")
def random_alpha_deg():
    """List of firing angles in degrees, spread across (0, 180)."""
    r = _rng()
    return [r.uniform(1.0, 179.0) for _ in range(N_RANDOM_CASES)]


# Fixed, hand-verified regression cases pulled from the project's own worked
# solutions, used with a tighter tolerance than the randomized property tests.
KNOWN_CASES = {
    "bridge_30_24": dict(Vs=208.0, f=60.0, R=30.0, L=24e-3),   # Main_report_2/main.tex
    "rl_15_38": dict(R=15.0, L=38e-3),                          # diferent_values.txt
}
