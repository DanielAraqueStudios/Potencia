"""Dump numeric results for all T2.pdf exercises (a=3, b=9, c=3) from the
verified rectifier modules, for use in writing the LaTeX report."""
import json
import sys

sys.path.insert(0, "scripts")
from rectifiers.ex1_bridge_rl import solve as ex1_solve
from rectifiers.ex2_three_phase_hw import solve as ex2_solve
from rectifiers.ex3_scr_hw_rl import solve as ex3_solve
from rectifiers.ex4_fullwave_controlled_rl import solve as ex4_solve

a, b, c = 3, 9, 3

results = {}

# Ex1: 3-phase 6-pulse bridge. Vf=25(a+b+c) is the PHASE (line-to-neutral) RMS
# voltage; the bridge is fed by the line-to-line voltage VL = Vf*sqrt(3).
Vf1 = 25 * (a + b + c)
VL1 = Vf1 * 3 ** 0.5
R1 = 8 * (a + b)
L1 = (2 * b + c) * 1e-3
results["ex1"] = dict(Vf=Vf1, VL=VL1, f=60.0, R=R1, L_mH=(2 * b + c),
                       out=ex1_solve(VL1, 60.0, R1, L1))

# Ex2: 3-phase half-wave, Vm=611V (peak phase), f=50Hz, reuse R,L from Ex1
Vm2 = 611.0
Vf2 = Vm2 / (2 ** 0.5)
results["ex2"] = dict(Vf=Vf2, Vm=Vm2, f=50.0, R=R1, L_mH=(2 * b + c),
                       out=ex2_solve(Vf2, 50.0, R1, L1))

# Ex3: SCR half-wave, Vm=20(a+b), f=60, R=2(a+b+c), L=45mH, alpha=(4a+3c+8)deg
Vm3 = 20 * (a + b)
R3 = 2 * (a + b + c)
L3 = 45e-3
alpha3 = 4 * a + 3 * c + 8
results["ex3"] = dict(Vm=Vm3, f=60.0, R=R3, L_mH=45, alpha_deg=alpha3,
                       out=ex3_solve(Vm3, 60.0, R3, L3, alpha3))

# Ex4: full-wave controlled, Vs=30(b+c) RMS, f=60, R=(a+b+c), L=60mH, alpha=45
Vs4 = 30 * (b + c)
R4 = a + b + c
L4 = 60e-3
alpha4 = 45.0
out4 = ex4_solve(Vs4, 60.0, R4, L4, alpha4)
results["ex4"] = dict(Vs=Vs4, f=60.0, R=R4, L_mH=60, alpha_deg=alpha4, out=out4)

# Ex5: same circuit as Ex4, alpha picked based on Ex4's conduction type
alpha5 = 25.0 if out4["conduction_type"] == "discontinuous" else 90.0
results["ex5"] = dict(Vs=Vs4, f=60.0, R=R4, L_mH=60, alpha_deg=alpha5,
                       ex4_conduction=out4["conduction_type"],
                       out=ex4_solve(Vs4, 60.0, R4, L4, alpha5))


def _clean(o):
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (int, float, str, bool)) or o is None:
        return o
    return float(o)


print(json.dumps(_clean(results), indent=2))
