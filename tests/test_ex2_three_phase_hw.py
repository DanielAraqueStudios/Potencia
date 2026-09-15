from scripts.rectifiers.ex2_three_phase_hw import solve, solve_numeric
from tests.conftest import KNOWN_CASES


def rel_err(a, b):
    return abs(a - b) / abs(b)


def test_known_case_rl_15_38():
    case = dict(Vf=260.0, f=50.0, **KNOWN_CASES["rl_15_38"])
    result = solve(**case)

    # Reference (diferent_values.txt, Ejercicio 2) used only the DC term plus
    # the single dominant 6th-harmonic (300 Hz) term, so allow a looser 3%
    # tolerance here vs. the 2% used for the fully-analytic Ejercicio 1.
    expected = dict(Vdc=304.4, Idc=20.29, PF=0.676, eta=0.676)
    for key, exp in expected.items():
        assert rel_err(result[key], exp) < 0.03, f"{key}: got {result[key]}, expected {exp}"

    # PF and eta end up numerically close in the source material; verify
    # both independently against their own definitions rather than trusting
    # that coincidence.
    assert rel_err(result["PF"], result["P"] / result["S"]) < 1e-9
    assert rel_err(result["eta"], result["P_dc"] / result["S"]) < 1e-9


def test_analytic_matches_numeric(random_rl_cases):
    Vf, f = 260.0, 50.0
    for R, L in random_rl_cases:
        analytic = solve(Vf, f, R, L)
        numeric = solve_numeric(Vf, f, R, L)
        for key in ("Vdc", "Idc"):
            assert rel_err(analytic[key], numeric[key]) < 0.02, (
                f"R={R}, L={L}, {key}: analytic={analytic[key]}, numeric={numeric[key]}"
            )
        # Vrms/Irms ripple is more sensitive to the number of harmonics kept
        # in the analytic series (solve() defaults to only the 6th-harmonic
        # term), so allow a looser 5% band on these.
        for key in ("Vrms", "Irms"):
            assert rel_err(analytic[key], numeric[key]) < 0.05, (
                f"R={R}, L={L}, {key}: analytic={analytic[key]}, numeric={numeric[key]}"
            )


def test_physical_sanity(random_rl_cases):
    Vf, f = 260.0, 50.0
    for R, L in random_rl_cases:
        r = solve(Vf, f, R, L)
        assert r["PF"] <= 1.0
        assert r["eta"] <= 1.0
        assert r["Vrms"] >= r["Vdc"]
        assert r["Irms"] >= r["Idc"]
