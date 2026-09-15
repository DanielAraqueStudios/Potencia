"""Ejercicio 2: three-phase half-wave (3-pulse) diode rectifier with R-L load.

Each diode conducts for one third of a period while its phase is the
instantaneous maximum of the three line-to-neutral sinusoids. The output
ripple's dominant harmonic sits at 6f (n=1 in this module's numbering),
i.e. the 6th harmonic of the source frequency (3 pulses per cycle -> the
Fourier series of vo(t) only has DC and multiples of 3*f_pulse = 6f terms
beyond the fundamental pulse rate).

Provides two independent solvers:
  - solve(): analytic Fourier-series solution.
  - solve_numeric(): numerical ODE integration cross-check.
"""
import numpy as np
from scipy.integrate import solve_ivp


def solve(Vf, f, R, L, n_harmonics=1):
    """Analytic Fourier-series solution of the 3-pulse half-wave rectifier.

    Vf: source line-to-neutral RMS voltage
    f: source frequency (Hz)
    R, L: load resistance (ohm) and inductance (H)
    n_harmonics: number of AC harmonics (at 6f, 12f, 18f, ...) to include.
    """
    Vm = Vf * np.sqrt(2.0)
    VL = np.sqrt(3.0) * Vf
    w = 2.0 * np.pi * f

    Vdc = (3.0 / (2.0 * np.pi)) * Vm * (np.sin(np.pi / 3.0) - np.sin(-np.pi / 3.0))
    Idc = Vdc / R

    harmonics_rms_sq = 0.0
    i_harmonics_rms_sq = 0.0
    for n in range(1, n_harmonics + 1):
        m = 6 * n
        theta = np.linspace(-np.pi / 3.0, np.pi / 3.0, 20001)
        integrand = Vm * np.cos(theta) * np.cos(m * theta)
        an = (2.0 / (2.0 * np.pi / 3.0)) * np.trapezoid(integrand, theta)
        v_n_rms = abs(an) / np.sqrt(2.0)
        wn = m * w
        Zn = complex(R, wn * L)
        i_n_peak = an / Zn
        i_n_rms = abs(i_n_peak) / np.sqrt(2.0)
        harmonics_rms_sq += v_n_rms ** 2
        i_harmonics_rms_sq += i_n_rms ** 2

    Vac = np.sqrt(harmonics_rms_sq)
    Iac = np.sqrt(i_harmonics_rms_sq)

    Vrms = np.sqrt(Vdc ** 2 + Vac ** 2)
    Irms = np.sqrt(Idc ** 2 + Iac ** 2)

    I_line = Idc / np.sqrt(3.0)
    I_diode = I_line

    P = Irms ** 2 * R
    S = np.sqrt(3.0) * VL * I_line
    PF = P / S
    P_dc = Vdc * Idc
    eta = P_dc / S

    FR_V = Vac / Vdc
    FR_I = Iac / Idc

    return dict(
        Vm=Vm, VL=VL, Vdc=Vdc, Vrms=Vrms, Idc=Idc, Irms=Irms,
        I_line=I_line, I_diode=I_diode,
        P=P, S=S, PF=PF, P_dc=P_dc, eta=eta, FR_V=FR_V, FR_I=FR_I,
    )


def solve_numeric(Vf, f, R, L, n_periods=20):
    """Independent numeric cross-check via ODE integration of the circuit.

    vo(t) = max(va(t), vb(t), vc(t)) with phases spaced 120 degrees apart
    (this is what a 3-pulse half-wave rectifier selecting the diode with
    the highest instantaneous anode voltage produces).
    L di/dt + R i = vo(t). Integrates for n_periods of the source, then
    evaluates steady-state quantities over the last full period.
    """
    Vm = Vf * np.sqrt(2.0)
    VL = np.sqrt(3.0) * Vf
    w = 2.0 * np.pi * f
    T = 1.0 / f

    # The L/R settling time constant can span several source periods for
    # large L / small R; make sure we integrate well past it (>= 8 tau)
    # before sampling the "steady state" last period, on top of the
    # caller-requested minimum n_periods.
    tau_periods = int(np.ceil(8.0 * (L / R) * f)) + 2
    n_periods = max(n_periods, tau_periods)
    t_end = n_periods * T

    def vo(t):
        va = Vm * np.sin(w * t)
        vb = Vm * np.sin(w * t - 2.0 * np.pi / 3.0)
        vc = Vm * np.sin(w * t + 2.0 * np.pi / 3.0)
        return np.maximum(np.maximum(va, vb), vc)

    def rhs(t, y):
        i = y[0]
        return [(vo(t) - R * i) / L]

    n_pts_per_period = 2000
    t_eval = np.linspace((n_periods - 1) * T, t_end, n_pts_per_period + 1)

    sol = solve_ivp(
        rhs, [0.0, t_end], [0.0], method="RK45",
        t_eval=t_eval, rtol=1e-9, atol=1e-12, max_step=T / 500.0,
    )

    i_t = sol.y[0]
    v_t = vo(t_eval)

    Idc = np.mean(i_t)
    Irms = np.sqrt(np.mean(i_t ** 2))
    Vdc = np.mean(v_t)
    Vrms = np.sqrt(np.mean(v_t ** 2))

    Vac = np.sqrt(max(Vrms ** 2 - Vdc ** 2, 0.0))
    Iac = np.sqrt(max(Irms ** 2 - Idc ** 2, 0.0))

    I_line = Idc / np.sqrt(3.0)
    I_diode = I_line

    P = Irms ** 2 * R
    S = np.sqrt(3.0) * VL * I_line
    PF = P / S
    P_dc = Vdc * Idc
    eta = P_dc / S

    FR_V = Vac / Vdc
    FR_I = Iac / Idc

    return dict(
        Vm=Vm, VL=VL, Vdc=Vdc, Vrms=Vrms, Idc=Idc, Irms=Irms,
        I_line=I_line, I_diode=I_diode,
        P=P, S=S, PF=PF, P_dc=P_dc, eta=eta, FR_V=FR_V, FR_I=FR_I,
    )
