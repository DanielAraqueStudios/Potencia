"""Ejercicio 3: single-phase half-wave SCR (thyristor) rectifier with R-L load.

Provides two independent solvers:
  - solve(): analytic i(t) = forced + natural response, with extinction angle
    found by root-finding, then closed-form Vdc/Vrms and numerically
    integrated Idc/Irms.
  - solve_numeric(): independent cross-check via event-driven ODE simulation
    of the switched RL circuit (SCR fires at t1 + k*T, blocks at i=0).
"""
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq


def _current(t, t1, w, Im, theta_z, tau, I0):
    return Im * np.sin(w * t - theta_z) + I0 * np.exp(-(t - t1) / tau)


def solve(Vm, f, R, L, alpha_deg):
    """Analytic solution of the half-wave SCR rectifier with R-L load."""
    w = 2.0 * np.pi * f
    T = 1.0 / f
    alpha = np.deg2rad(alpha_deg)
    t1 = alpha / w

    Z = complex(R, w * L)
    theta_z = np.arctan2(w * L, R)
    tau = L / R
    Im = Vm / abs(Z)
    I0 = -Im * np.sin(alpha - theta_z)

    def i_of_t(t):
        return _current(t, t1, w, Im, theta_z, tau, I0)

    t_lo = t1 + 1e-9
    t_hi = t1 + T
    n_scan = 4000
    ts = np.linspace(t_lo, t_hi, n_scan)
    vals = i_of_t(ts)
    te = None
    for k in range(len(ts) - 1):
        if vals[k] > 0.0 and vals[k + 1] <= 0.0:
            te = brentq(i_of_t, ts[k], ts[k + 1])
            break
    if te is None:
        raise RuntimeError("extinction time root not found")

    beta = w * te
    gamma_deg = np.rad2deg(beta) - alpha_deg

    Vdc = (Vm / (2.0 * np.pi)) * (np.cos(alpha) - np.cos(beta))
    Vrms = Vm / np.sqrt(2.0) * np.sqrt(
        max((beta - alpha) / (2.0 * np.pi)
            - (np.sin(2.0 * beta) - np.sin(2.0 * alpha)) / (4.0 * np.pi), 0.0)
    )

    n_int = 4000
    t_cond = np.linspace(t1, te, n_int)
    i_cond = i_of_t(t_cond)
    i_full = np.zeros(n_int)
    t_full = np.linspace(0.0, T, n_int)
    i_full = np.interp(t_full, t_cond, i_cond, left=0.0, right=0.0)
    i_full[(t_full < t1) | (t_full > te)] = 0.0

    Idc = np.trapezoid(i_full, t_full) / T
    Irms = np.sqrt(np.trapezoid(i_full ** 2, t_full) / T)

    P = Irms ** 2 * R
    S = (Vm / np.sqrt(2.0)) * Irms
    PF = P / S if S > 0 else 0.0
    P_dc = Vdc * Idc
    eta = P_dc / S if S > 0 else 0.0

    FR_V = np.sqrt(max(Vrms ** 2 - Vdc ** 2, 0.0)) / Vdc if Vdc > 0 else 0.0
    FR_I = np.sqrt(max(Irms ** 2 - Idc ** 2, 0.0)) / Idc if Idc > 0 else 0.0

    return dict(
        t1=t1, te=te, beta_deg=np.rad2deg(beta), gamma_deg=gamma_deg,
        Vdc=Vdc, Vrms=Vrms, Idc=Idc, Irms=Irms,
        P=P, S=S, PF=PF, P_dc=P_dc, eta=eta, FR_V=FR_V, FR_I=FR_I,
        conduction_type="continuous" if (te - t1) >= T else "discontinuous",
    )


def solve_numeric(Vm, f, R, L, alpha_deg, n_periods=20):
    """Independent numeric cross-check via event-driven ODE simulation.

    L di/dt + R i = vs(t) while the SCR conducts; conduction starts at
    t1 + k*T and ends the moment i(t) decays back to zero.
    """
    w = 2.0 * np.pi * f
    T = 1.0 / f
    alpha = np.deg2rad(alpha_deg)
    t1 = alpha / w

    def vs(t):
        return Vm * np.sin(w * t)

    def rhs(t, y):
        return [(vs(t) - R * y[0]) / L]

    def zero_crossing(t, y):
        return y[0]

    zero_crossing.terminal = True
    zero_crossing.direction = -1

    n_pts = 2000
    t_all = []
    i_all = []

    for k in range(n_periods):
        t_start = k * T + t1
        t_stop = t_start + T
        sol = solve_ivp(
            rhs, [t_start, t_stop], [0.0], method="RK45",
            events=zero_crossing, dense_output=True,
            rtol=1e-9, atol=1e-12, max_step=T / 1000.0,
        )
        t_end_conduct = sol.t[-1]
        t_eval = np.linspace(t_start, t_end_conduct, n_pts)
        i_eval = sol.sol(t_eval)[0]
        i_eval = np.clip(i_eval, 0.0, None)

        t_all.append(t_eval)
        i_all.append(i_eval)

        t_off = np.linspace(t_end_conduct, t_stop, n_pts)
        t_all.append(t_off)
        i_all.append(np.zeros(n_pts))

    last_t1 = (n_periods - 1) * T + t1
    last_t_end = last_t1 + T
    t_concat = np.concatenate(t_all)
    i_concat = np.concatenate(i_all)
    mask = (t_concat >= last_t1) & (t_concat <= last_t_end)
    t_period = t_concat[mask] - last_t1
    i_period = i_concat[mask]

    order = np.argsort(t_period)
    t_period = t_period[order]
    i_period = i_period[order]
    v_period = np.where(i_period > 0.0, vs(t_period + last_t1), 0.0)

    Idc = np.trapezoid(i_period, t_period) / T
    Irms = np.sqrt(np.trapezoid(i_period ** 2, t_period) / T)
    Vdc = np.trapezoid(v_period, t_period) / T
    Vrms = np.sqrt(np.trapezoid(v_period ** 2, t_period) / T)

    P = Irms ** 2 * R
    S = (Vm / np.sqrt(2.0)) * Irms
    PF = P / S if S > 0 else 0.0
    P_dc = Vdc * Idc
    eta = P_dc / S if S > 0 else 0.0

    FR_V = np.sqrt(max(Vrms ** 2 - Vdc ** 2, 0.0)) / Vdc if Vdc > 0 else 0.0
    FR_I = np.sqrt(max(Irms ** 2 - Idc ** 2, 0.0)) / Idc if Idc > 0 else 0.0

    return dict(
        Vdc=Vdc, Vrms=Vrms, Idc=Idc, Irms=Irms,
        P=P, S=S, PF=PF, P_dc=P_dc, eta=eta, FR_V=FR_V, FR_I=FR_I,
    )
