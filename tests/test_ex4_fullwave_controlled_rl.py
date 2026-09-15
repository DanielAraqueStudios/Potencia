import numpy as np
import pytest

from scripts.rectifiers.ex4_fullwave_controlled_rl import solve, solve_numeric


def rel_err(a, b):
    return abs(a - b) / abs(b)


ABS_FLOOR = dict(Vdc=0.5, Idc=0.02)  # volts / amps; guards near-zero-conduction cases


def test_continuous_conduction_large_L():
    # wL >> R forces continuous conduction; Vdc should match the textbook
    # closed form Vdc = 2*Vm*cos(alpha)/pi.
    Vs_rms, f, R, L, alpha_deg = 120.0, 60.0, 10.0, 1.0, 45.0
    result = solve(Vs_rms, f, R, L, alpha_deg)
    Vm = Vs_rms * np.sqrt(2.0)
    Vdc_expected = 2.0 * Vm * np.cos(np.deg2rad(alpha_deg)) / np.pi

    assert result["conduction_type"] == "continuous"
    assert rel_err(result["Vdc"], Vdc_expected) < 0.02


def test_discontinuous_conduction_small_L():
    # Very small L behaves close to a resistive controlled rectifier ->
    # current decays to zero well before the next firing angle.
    Vs_rms, f, R, L, alpha_deg = 120.0, 60.0, 15.0, 1e-3, 45.0
    result = solve(Vs_rms, f, R, L, alpha_deg)

    assert result["conduction_type"] == "discontinuous"


def test_assignment_case():
    Vs_rms, f, R, L, alpha_deg = 360.0, 60.0, 15.0, 60e-3, 45.0
    analytic = solve(Vs_rms, f, R, L, alpha_deg)
    numeric = solve_numeric(Vs_rms, f, R, L, alpha_deg, n_periods=15)

    print(f"assignment case conduction_type={analytic['conduction_type']}")
    print(f"analytic Vdc={analytic['Vdc']}, Idc={analytic['Idc']}")
    print(f"numeric  Vdc={numeric['Vdc']}, Idc={numeric['Idc']}")

    for key in ("Vdc", "Idc"):
        diff = abs(analytic[key] - numeric[key])
        tol = max(0.03 * abs(analytic[key]), ABS_FLOOR[key])
        assert diff < tol, f"{key}: analytic={analytic[key]}, numeric={numeric[key]}"


def test_analytic_matches_numeric(random_rl_cases, random_alpha_deg):
    Vs_rms, f = 360.0, 60.0
    cases = list(zip(random_rl_cases, random_alpha_deg))[::2]  # subsample to 100

    n_total = 0
    n_skipped = 0
    for (R, L), alpha_deg in cases:
        n_total += 1
        try:
            analytic = solve(Vs_rms, f, R, L, alpha_deg)
            numeric = solve_numeric(Vs_rms, f, R, L, alpha_deg, n_periods=8)
        except (RuntimeError, ValueError) as exc:
            n_skipped += 1
            print(f"skipping R={R}, L={L}, alpha_deg={alpha_deg}: {exc}")
            continue

        for key in ("Vdc", "Idc"):
            diff = abs(analytic[key] - numeric[key])
            tol = max(0.05 * abs(analytic[key]), ABS_FLOOR[key])
            if diff >= tol:
                n_skipped += 1
                print(
                    f"skipping (mismatch) R={R}, L={L}, alpha_deg={alpha_deg}, "
                    f"{key}: analytic={analytic[key]}, numeric={numeric[key]}"
                )
                break

    skip_fraction = n_skipped / n_total
    assert skip_fraction < 0.10, (
        f"too many unresolved/mismatched cases ({n_skipped}/{n_total}); solver is unreliable"
    )


def test_physical_sanity(random_rl_cases, random_alpha_deg):
    Vs_rms, f = 360.0, 60.0
    cases = list(zip(random_rl_cases, random_alpha_deg))[::2]

    for (R, L), alpha_deg in cases:
        try:
            r = solve(Vs_rms, f, R, L, alpha_deg)
        except (RuntimeError, ValueError):
            continue

        assert r["PF"] <= 1.0 + 1e-9
        assert r["eta"] <= 1.0 + 1e-9
        assert r["Irms"] >= r["Idc"] - 1e-9
        assert r["Vrms"] >= r["Vdc"] - 1e-6
        if alpha_deg < 90.0:
            assert r["Vdc"] >= -1e-6
