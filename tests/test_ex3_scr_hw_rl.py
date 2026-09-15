import pytest

from scripts.rectifiers.ex3_scr_hw_rl import solve, solve_numeric


def rel_err(a, b):
    return abs(a - b) / abs(b)


ABS_FLOOR = dict(Vdc=0.05, Idc=0.01)  # volts / amps; guards near-zero-conduction cases


def test_known_case_rl_15_38_alpha37():
    result = solve(Vm=180.0, f=60.0, R=15.0, L=38e-3, alpha_deg=37.0)

    # Reference values from Main_report_2/diferent_values.txt, Ejercicio 3.
    # te was itself found numerically there, so use a looser tolerance.
    assert rel_err(result["te"], 10.37e-3) < 0.05
    assert rel_err(result["Vdc"], 43.5) < 0.05
    assert rel_err(result["Idc"], 2.90) < 0.05

    # theta_Z = atan(w*L/R) = 43.67deg > alpha = 37deg here, which pushes the
    # conduction angle past 180deg for this particular case. Real phenomenon
    # for a single-pulse half-wave SCR, not a bug.
    assert result["gamma_deg"] > 180.0


def test_analytic_matches_numeric(random_rl_cases, random_alpha_deg):
    Vm, f = 180.0, 60.0
    n_total = 0
    n_skipped = 0
    for (R, L), alpha_deg in zip(random_rl_cases, random_alpha_deg):
        n_total += 1
        try:
            analytic = solve(Vm, f, R, L, alpha_deg)
        except RuntimeError as exc:
            n_skipped += 1
            print(f"skipping R={R}, L={L}, alpha_deg={alpha_deg}: {exc}")
            continue

        numeric = solve_numeric(Vm, f, R, L, alpha_deg, n_periods=8)
        for key in ("Vdc", "Idc"):
            diff = abs(analytic[key] - numeric[key])
            tol = max(0.03 * abs(analytic[key]), ABS_FLOOR[key])
            assert diff < tol, (
                f"R={R}, L={L}, alpha_deg={alpha_deg}, {key}: "
                f"analytic={analytic[key]}, numeric={numeric[key]}"
            )

    skip_fraction = n_skipped / n_total
    assert skip_fraction < 0.10, (
        f"too many unresolved cases ({n_skipped}/{n_total}); solver is unreliable"
    )


def test_physical_sanity(random_rl_cases, random_alpha_deg):
    Vm, f = 180.0, 60.0
    T = 1.0 / f
    for (R, L), alpha_deg in zip(random_rl_cases, random_alpha_deg):
        try:
            r = solve(Vm, f, R, L, alpha_deg)
        except RuntimeError:
            continue

        assert r["t1"] < r["te"]
        # Conduction interval bounded to at most one full period; gamma can
        # legitimately exceed 180deg when alpha < theta_Z (see known case).
        assert r["te"] - r["t1"] <= T + 1e-6
        assert r["Vdc"] >= 0.0
        assert r["PF"] <= 1.0 + 1e-9
        assert r["eta"] <= 1.0 + 1e-9
