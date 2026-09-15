from scripts.rectifiers.ex1_bridge_rl import solve, solve_numeric
from tests.conftest import KNOWN_CASES


def rel_err(a, b):
    return abs(a - b) / abs(b)


def test_known_case_rl_15_38():
    case = KNOWN_CASES["rl_15_38"]
    result = solve(VL=380.0, f=50.0, R=case["R"], L=case["L"])

    expected = dict(Vdc=513.0, Idc=34.2, PF=0.955)
    for key, exp in expected.items():
        assert rel_err(result[key], exp) < 0.03, f"{key}: got {result[key]}, expected {exp}"


def test_analytic_matches_numeric(random_rl_cases):
    VL, f = 380.0, 50.0
    for R, L in random_rl_cases[:20]:
        analytic = solve(VL, f, R, L)
        numeric = solve_numeric(VL, f, R, L)
        for key in ("Vdc", "Vrms", "Idc", "Irms"):
            assert rel_err(analytic[key], numeric[key]) < 0.02, (
                f"R={R}, L={L}, {key}: analytic={analytic[key]}, numeric={numeric[key]}"
            )


def test_internal_consistency(random_rl_cases):
    VL, f = 380.0, 50.0
    for R, L in random_rl_cases:
        r = solve(VL, f, R, L)
        assert r["PF"] <= 1.0
        assert r["eta"] <= 1.0
        assert r["Vrms"] >= r["Vdc"]
        assert r["Irms"] >= r["Idc"]
        assert rel_err(r["P"], r["Irms"] ** 2 * R) < 0.01
