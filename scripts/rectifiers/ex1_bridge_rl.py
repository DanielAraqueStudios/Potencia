"""Ejercicio 1: three-phase 6-pulse full-bridge diode rectifier with R-L load.

Provides two independent solvers:
  - solve(): analytic Fourier-series solution.
  - solve_numeric(): numerical ODE integration cross-check.
"""
import numpy as np
from scipy.integrate import solve_ivp


def solve(VL, f, R, L, n_harmonics=1):
    """Analytic Fourier-series solution of the 3-phase 6-pulse bridge with R-L load.

    VL: line-to-line RMS source voltage
    f: source frequency (Hz)
    R, L: load resistance (ohm) and inductance (H)
    n_harmonics: number of AC harmonics (at 6f, 12f, ...) to include.
    """
    Vm = VL * np.sqrt(2.0)
    w = 2.0 * np.pi * f

    Vdc = (3.0 * Vm / np.pi) * (np.sin(np.pi / 6.0) - np.sin(-np.pi / 6.0))
    Idc = Vdc / R

    v_harmonics_rms_sq = 0.0
    i_harmonics_rms_sq = 0.0
    for n in range(1, n_harmonics + 1):
        m = 6 * n
        theta = np.linspace(-np.pi / 6.0, np.pi / 6.0, 20001)
        integrand = Vm * np.cos(theta) * np.cos(m * theta)
        a_m = (2.0 / (np.pi / 3.0)) * np.trapezoid(integrand, theta)

        wm = m * w
        Zm = complex(R, wm * L)
        I_m_peak = a_m / Zm
        v_m_rms = abs(a_m) / np.sqrt(2.0)
        i_m_rms = abs(I_m_peak) / np.sqrt(2.0)

        v_harmonics_rms_sq += v_m_rms ** 2
        i_harmonics_rms_sq += i_m_rms ** 2

    Vac = np.sqrt(v_harmonics_rms_sq)
    Iac = np.sqrt(i_harmonics_rms_sq)

    Vrms = np.sqrt(Vdc ** 2 + Vac ** 2)
    Irms = np.sqrt(Idc ** 2 + Iac ** 2)

    IL = Idc * np.sqrt(2.0 / 3.0)
    I_diode_dc = Idc / np.sqrt(3.0)
    I_diode_rms = Irms / np.sqrt(3.0)

    P = Irms ** 2 * R
    S = np.sqrt(3.0) * VL * IL
    PF = P / S
    P_dc = Vdc * Idc
    eta = P_dc / S

    FR_V = Vac / Vdc
    FR_I = Iac / Idc

    return dict(
        Vdc=Vdc, Vrms=Vrms, Idc=Idc, Irms=Irms, Vac=Vac, Iac=Iac,
        IL=IL, I_diode_dc=I_diode_dc, I_diode_rms=I_diode_rms,
        P=P, S=S, PF=PF, P_dc=P_dc, eta=eta, FR_V=FR_V, FR_I=FR_I,
    )


def solve_numeric(VL, f, R, L, n_periods=20):
    """Independent numeric cross-check via ODE integration of the 3-phase bridge.

    vo(t) = max(phase voltages) - min(phase voltages), i.e. the envelope of
    the six line-to-line voltages (the instantaneous DC-bus voltage of an
    ideal 6-pulse bridge). L di/dt + R i = vo(t).
    Integrates for n_periods of the fundamental, then evaluates steady-state
    quantities over the last output ripple period (T/6).
    """
    Vf = VL / np.sqrt(3.0)
    Vm_phase = Vf * np.sqrt(2.0)
    w = 2.0 * np.pi * f
    T = 1.0 / f
    tau = L / R
    settle_periods = int(np.ceil(6.0 * tau / T)) + 1
    n_periods = max(n_periods, settle_periods)
    t_end = n_periods * T

    def vo(t):
        va = Vm_phase * np.sin(w * t)
        vb = Vm_phase * np.sin(w * t - 2.0 * np.pi / 3.0)
        vc = Vm_phase * np.sin(w * t + 2.0 * np.pi / 3.0)
        return np.maximum(np.maximum(va, vb), vc) - np.minimum(np.minimum(va, vb), vc)

    def rhs(t, y):
        i = y[0]
        return [(vo(t) - R * i) / L]

    T_ripple = T / 6.0
    n_pts = 500
    t_eval = np.linspace(t_end - T_ripple, t_end, n_pts + 1)

    sol = solve_ivp(
        rhs, [0.0, t_end], [0.0], method="RK45",
        t_eval=t_eval, rtol=1e-7, atol=1e-10, max_step=T_ripple / 40.0,
    )

    i_t = sol.y[0]
    v_t = vo(t_eval)

    Idc = np.mean(i_t)
    Irms = np.sqrt(np.mean(i_t ** 2))
    Vdc = np.mean(v_t)
    Vrms = np.sqrt(np.mean(v_t ** 2))

    Vac = np.sqrt(max(Vrms ** 2 - Vdc ** 2, 0.0))
    Iac = np.sqrt(max(Irms ** 2 - Idc ** 2, 0.0))

    IL = Idc * np.sqrt(2.0 / 3.0)
    I_diode_dc = Idc / np.sqrt(3.0)
    I_diode_rms = Irms / np.sqrt(3.0)

    P = Irms ** 2 * R
    S = np.sqrt(3.0) * VL * IL
    PF = P / S
    P_dc = Vdc * Idc
    eta = P_dc / S

    FR_V = Vac / Vdc
    FR_I = Iac / Idc

    return dict(
        Vdc=Vdc, Vrms=Vrms, Idc=Idc, Irms=Irms, Vac=Vac, Iac=Iac,
        IL=IL, I_diode_dc=I_diode_dc, I_diode_rms=I_diode_rms,
        P=P, S=S, PF=PF, P_dc=P_dc, eta=eta, FR_V=FR_V, FR_I=FR_I,
    )
