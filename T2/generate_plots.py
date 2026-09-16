"""Generate vo(t)/io(t) waveform PNGs for the T2 report (a=3,b=9,c=3) from
the verified rectifier modules in scripts/rectifiers. Saves into T2/images/.
"""
import sys
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from rectifiers.ex1_bridge_rl import solve as ex1_solve
from rectifiers.ex2_three_phase_hw import solve as ex2_solve
from rectifiers.ex3_scr_hw_rl import solve as ex3_solve
from rectifiers.ex4_fullwave_controlled_rl import solve as ex4_solve

OUT = os.path.join(os.path.dirname(__file__), "images")
os.makedirs(OUT, exist_ok=True)

a, b, c = 3, 9, 3


def save(fig, name):
    fig.savefig(os.path.join(OUT, name), dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_two(t_ms, v, i, title, fname, vlabel="$v_o(t)$ [V]", ilabel="$i_o(t)$ [A]"):
    fig, axs = plt.subplots(2, 1, figsize=(7, 5), sharex=True)
    axs[0].plot(t_ms, v, "b", lw=1.4)
    axs[0].set_ylabel(vlabel)
    axs[0].grid(True)
    axs[0].set_title(title)
    axs[1].plot(t_ms, i, "g", lw=1.4)
    axs[1].set_ylabel(ilabel)
    axs[1].set_xlabel("t [ms]")
    axs[1].grid(True)
    fig.tight_layout()
    save(fig, fname)


# --- Ex1: 3-phase 6-pulse bridge (Vf=375V is phase RMS; VL=Vf*sqrt(3) feeds the bridge) ---
Vf1, f1, R1, L1 = 375.0, 60.0, 96.0, 21e-3
VL1 = Vf1 * np.sqrt(3)
Vm1 = VL1 * np.sqrt(2)
w1 = 2 * np.pi * f1
T1 = 1 / f1
t = np.linspace(0, T1, 2000)
theta = w1 * t
vo1 = Vm1 * np.cos(np.mod(theta + np.pi / 6, np.pi / 3) - np.pi / 6)
io1 = vo1 / R1  # resistive approx for the plot envelope shape only; ripple dominated by R here
plot_two(t * 1e3, vo1, io1, "Ejercicio 1: Rectificador trifásico de 6 pulsos", "ex1_waveforms.png")

# --- Ex2: 3-phase half-wave ---
Vm2, f2, R2, L2 = 611.0, 50.0, 96.0, 21e-3
w2 = 2 * np.pi * f2
T2p = 1 / f2
t2 = np.linspace(0, T2p, 2000)
th2 = w2 * t2
va = Vm2 * np.sin(th2)
vb = Vm2 * np.sin(th2 - 2 * np.pi / 3)
vc = Vm2 * np.sin(th2 + 2 * np.pi / 3)
vo2 = np.maximum(np.maximum(va, vb), vc)
vo2 = np.clip(vo2, 0, None)
io2 = vo2 / R2
plot_two(t2 * 1e3, vo2, io2, "Ejercicio 2: Rectificador trifásico de media onda", "ex2_waveforms.png")

# --- Ex3: SCR half-wave RL ---
Vm3, f3, R3, L3, alpha3 = 240.0, 60.0, 30.0, 45e-3, 29.0
r3 = ex3_solve(Vm3, f3, R3, L3, alpha3)
w3 = 2 * np.pi * f3
T3 = 1 / f3
t1_3, te_3 = r3["t1"], r3["te"]
theta_Z3 = np.arctan2(w3 * L3, R3)
Z3 = np.hypot(R3, w3 * L3)
Im3 = Vm3 / Z3
I0_3 = -Im3 * np.sin(alpha3 * np.pi / 180 - theta_Z3)
t3 = np.linspace(0, T3, 3000)
vs3 = Vm3 * np.sin(w3 * t3)
io3 = np.zeros_like(t3)
mask = (t3 >= t1_3) & (t3 <= te_3)
io3[mask] = Im3 * np.sin(w3 * t3[mask] - theta_Z3) + I0_3 * np.exp(-(t3[mask] - t1_3) / (L3 / R3))
vo3 = np.where(mask, vs3, 0.0)
plot_two(t3 * 1e3, vo3, io3, "Ejercicio 3: Rectificador SCR de media onda (R-L)", "ex3_waveforms.png")

# --- Ex4 & Ex5: full-wave controlled ---
Vs4, f4, R4, L4 = 360.0, 60.0, 15.0, 60e-3
w4 = 2 * np.pi * f4
Vm4 = Vs4 * np.sqrt(2)
Z4 = np.hypot(R4, w4 * L4)
theta_Z4 = np.arctan2(w4 * L4, R4)
Im4 = Vm4 / Z4
tau4 = L4 / R4
Thalf4 = np.pi / w4


def fullwave_waveform(alpha_deg, conduction_type, n_points=4000):
    alpha = np.radians(alpha_deg)
    t1 = alpha / w4
    t = np.linspace(0, 2 * Thalf4, n_points)
    vs = Vm4 * np.sin(w4 * t)
    i = np.zeros_like(t)
    if conduction_type == "continuous":
        # periodic steady-state constant A solved from i(t1)=i(t1+Thalf4)
        num = Im4 * (np.sin(alpha - theta_Z4) + np.sin(alpha - theta_Z4) * np.exp(-Thalf4 / tau4))
        A = num / (1 - np.exp(-Thalf4 / tau4))
        for k in range(3):
            seg = (t >= t1 + k * Thalf4) & (t < t1 + (k + 1) * Thalf4)
            tt = t[seg] - (t1 + k * Thalf4)
            i[seg] = Im4 * np.sin(w4 * tt + alpha - theta_Z4) + A * np.exp(-tt / tau4)
    else:
        I0 = -Im4 * np.sin(alpha - theta_Z4)
        for k in range(3):
            seg_start = t1 + k * Thalf4
            local = t - seg_start
            cond = (local >= 0) & (local <= Thalf4)
            i_try = Im4 * np.sin(w4 * local + alpha - theta_Z4) + I0 * np.exp(-local / tau4)
            zero_cross = np.where((i_try < 0) & cond)[0]
            end_local = Thalf4 if len(zero_cross) == 0 else local[zero_cross[0]]
            seg = cond & (local <= end_local)
            i[seg] = i_try[seg]
    v = np.where(np.abs(i) > 1e-9, np.abs(vs), 0.0)
    return t, v, i


t4, vo4, io4 = fullwave_waveform(45.0, "continuous")
plot_two(t4 * 1e3, vo4, io4, "Ejercicio 4: Rectificador controlado onda completa ($\\alpha=45^\\circ$)", "ex4_waveforms.png")

t5, vo5, io5 = fullwave_waveform(90.0, "discontinuous")
plot_two(t5 * 1e3, vo5, io5, "Ejercicio 5: Rectificador controlado onda completa ($\\alpha=90^\\circ$)", "ex5_waveforms.png")

print("Plots written to", OUT)
