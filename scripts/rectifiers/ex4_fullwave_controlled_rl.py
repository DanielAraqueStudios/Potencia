"""Ejercicio 4: single-phase full-wave controlled rectifier with R-L load.

Center-tapped-transformer topology (Figure 4): two SCRs, each firing once per
half-cycle at wt = alpha (SCR A) and wt = pi + alpha (SCR B). Conduction may
be continuous (current never reaches zero; each half-cycle is an identical,
periodic segment of a steady-state waveform) or discontinuous (current decays
to zero before the next SCR fires, so there is a dead interval each
half-cycle).

Provides two independent solvers:
  - solve(): analytic solution. Tries the discontinuous-mode extinction angle
    first (same math as ex3's half-wave SCR case, since each half-cycle
    starts from zero current); if the natural zero-crossing occurs before the
    next firing angle (pi + alpha), that is the correct regime. Otherwise
    conduction is continuous, and the periodic offset constant is solved in
    closed form from the boundary condition i(t1) = i(t1 + pi/w).
  - solve_numeric(): independent cross-check via event-driven ODE simulation
    of the switched circuit, letting continuous/discontinuous behavior emerge
    from the simulation itself.
"""
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq


def _current(t, t1, w, Im, theta_z, tau, I0):
    return Im * np.sin(w * t - theta_z) + I0 * np.exp(-(t - t1) / tau)


def solve(Vs_rms, f, R, L, alpha_deg):
    """Analytic solution of the full-wave controlled rectifier, R-L load."""
    Vm = Vs_rms * np.sqrt(2.0)
    w = 2.0 * np.pi * f
    T = 1.0 / f
    Thalf = T / 2.0
    alpha = np.deg2rad(alpha_deg)
    t1 = alpha / w
    t_next = t1 + Thalf

    Z = complex(R, w * L)
    theta_z = np.arctan2(w * L, R)
    tau = L / R
    Im = Vm / abs(Z)

    # --- Try discontinuous mode first: SCR turns on at t1 with i(t1)=0. ---
    I0_disc = -Im * np.sin(alpha - theta_z)

    def i_disc(t):
        return _current(t, t1, w, Im, theta_z, tau, I0_disc)

    t_lo, t_hi = t1 + 1e-12, t_next
    n_scan = 4000
    ts = np.linspace(t_lo, t_hi, n_scan)
    vals = i_disc(ts)
    te = None
    for k in range(len(ts) - 1):
        if vals[k] > 0.0 and vals[k + 1] <= 0.0:
            te = brentq(i_disc, ts[k], ts[k + 1])
            break

    if te is not None and te < t_next - 1e-9:
        conduction_type = "discontinuous"
        end_time = te

        def i_of_t(t):
            return i_disc(t)

        t_cond = np.linspace(t1, te, 4000)
        i_cond = i_of_t(t_cond)
        w_te = w * te
        beta_deg = np.rad2deg(w_te)

        Vdc = (w / np.pi) * np.trapezoid(Vm * np.sin(w * t_cond), t_cond)
        Vrms = np.sqrt((w / np.pi) * np.trapezoid((Vm * np.sin(w * t_cond)) ** 2, t_cond))
    else:
        conduction_type = "continuous"
        end_time = t_next

        decay = np.exp(-Thalf / tau)
        A = -2.0 * Im * np.sin(alpha - theta_z) / (1.0 - decay)

        def i_of_t(t):
            return _current(t, t1, w, Im, theta_z, tau, A)

        t_cond = np.linspace(t1, t_next, 4000)
        beta_deg = np.rad2deg(w * t_next)

        Vdc = 2.0 * Vm * np.cos(alpha) / np.pi
        Vrms = Vm / np.sqrt(2.0)

    i_cond = np.clip(i_of_t(t_cond), 0.0, None)

    # Current is zero outside [t1, end_time] within the half-period, so the
    # average/rms only need the conduction interval itself.
    Idc = np.trapezoid(i_cond, t_cond) / Thalf
    Irms = np.sqrt(np.trapezoid(i_cond ** 2, t_cond) / Thalf)

    P = Irms ** 2 * R
    S = Vs_rms * Irms
    PF = P / S if S > 0 else 0.0
    P_dc = Vdc * Idc
    eta = P_dc / S if S > 0 else 0.0

    FR_V = np.sqrt(max(Vrms ** 2 - Vdc ** 2, 0.0)) / Vdc if Vdc > 0 else 0.0
    FR_I = np.sqrt(max(Irms ** 2 - Idc ** 2, 0.0)) / Idc if Idc > 0 else 0.0

    return dict(
        conduction_type=conduction_type,
        t1=t1, te_or_period_end=end_time, beta_deg=beta_deg,
        Vdc=Vdc, Vrms=Vrms, Idc=Idc, Irms=Irms,
        P=P, S=S, PF=PF, P_dc=P_dc, eta=eta, FR_V=FR_V, FR_I=FR_I,
    )


def solve_numeric(Vs_rms, f, R, L, alpha_deg, n_periods=20):
    """Independent numeric cross-check via event-driven ODE simulation.

    Each SCR is assumed to fire at t1 + k*Thalf and hands current to the next
    SCR either at natural zero-crossing (discontinuous) or at the next firing
    instant (continuous handoff, since the incoming SCR is forward biased and
    the outgoing one commutates off). Either behavior emerges naturally from
    simulating L di/dt + R i = vs(t) with a hard current floor at zero.
    """
    Vm = Vs_rms * np.sqrt(2.0)
    w = 2.0 * np.pi * f
    T = 1.0 / f
    Thalf = T / 2.0
    alpha = np.deg2rad(alpha_deg)
    t1 = alpha / w

    def vs(t):
        return Vm * np.sin(w * t)

    def zero_crossing(t, y):
        return y[0]

    zero_crossing.terminal = True
    zero_crossing.direction = -1

    n_pts = 1000
    t_all = []
    i_all = []

    i_start = 0.0
    for k in range(2 * n_periods):
        t_start = k * Thalf + t1
        t_stop = t_start + Thalf
        # SCR A (even k) is driven by v1(t) = vs(t); SCR B (odd k) is driven
        # by the other transformer half, v2(t) = -v1(t) = -vs(t).
        sign = 1.0 if k % 2 == 0 else -1.0

        def rhs(t, y, sign=sign):
            return [(sign * vs(t) - R * y[0]) / L]

        sol = solve_ivp(
            rhs, [t_start, t_stop], [i_start], method="RK45",
            events=zero_crossing, dense_output=True,
            rtol=1e-9, atol=1e-12, max_step=Thalf / 1000.0,
        )

        if sol.t_events[0].size > 0:
            t_end_conduct = sol.t[-1]
            t_eval = np.linspace(t_start, t_end_conduct, n_pts)
            i_eval = np.clip(sol.sol(t_eval)[0], 0.0, None)
            t_all.append(t_eval)
            i_all.append(i_eval)

            t_off = np.linspace(t_end_conduct, t_stop, n_pts)
            t_all.append(t_off)
            i_all.append(np.zeros(n_pts))
            i_start = 0.0
        else:
            t_eval = np.linspace(t_start, t_stop, n_pts)
            i_eval = np.clip(sol.sol(t_eval)[0], 0.0, None)
            t_all.append(t_eval)
            i_all.append(i_eval)
            i_start = i_eval[-1]

    last_k = 2 * n_periods - 2
    last_t1 = last_k * Thalf + t1
    last_t_end = last_t1 + Thalf
    t_concat = np.concatenate(t_all)
    i_concat = np.concatenate(i_all)
    mask = (t_concat >= last_t1) & (t_concat <= last_t_end)
    t_period = t_concat[mask] - last_t1
    i_period = i_concat[mask]

    order = np.argsort(t_period)
    t_period = t_period[order]
    i_period = i_period[order]
    v_period = np.where(i_period > 0.0, vs(t_period + last_t1), 0.0)

    Idc = np.trapezoid(i_period, t_period) / Thalf
    Irms = np.sqrt(np.trapezoid(i_period ** 2, t_period) / Thalf)
    Vdc = np.trapezoid(v_period, t_period) / Thalf
    Vrms = np.sqrt(np.trapezoid(v_period ** 2, t_period) / Thalf)

    P = Irms ** 2 * R
    S = Vs_rms * Irms
    PF = P / S if S > 0 else 0.0
    P_dc = Vdc * Idc
    eta = P_dc / S if S > 0 else 0.0

    FR_V = np.sqrt(max(Vrms ** 2 - Vdc ** 2, 0.0)) / Vdc if Vdc > 0 else 0.0
    FR_I = np.sqrt(max(Irms ** 2 - Idc ** 2, 0.0)) / Idc if Idc > 0 else 0.0

    return dict(
        Vdc=Vdc, Vrms=Vrms, Idc=Idc, Irms=Irms,
        P=P, S=S, PF=PF, P_dc=P_dc, eta=eta, FR_V=FR_V, FR_I=FR_I,
    )
