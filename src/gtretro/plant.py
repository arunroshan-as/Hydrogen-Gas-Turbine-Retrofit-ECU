"""Reduced-order dynamic gas-turbine + gas-fuel-system model with the ECU in the loop.

Plant core: Rowen-type normalised turbine model (W. I. Rowen, 1983) for torque / exhaust temperature,
extended with (i) a physical gas-manifold model (valve -> manifold -> staged injectors) so fuel properties
(R, gamma, LHV, Wobbe index) enter the dynamics, (ii) pilot/main staging, (iii) a two-shaft (gas generator +
free power turbine) variant and a 3-spool lag chain. Parameters are ASSUMED for generic reference platforms.
Not validated against any machine.
"""
from dataclasses import dataclass, field
from collections import deque
import numpy as np
import pandas as pd
from . import fuel_system as FS
from . import control as CT
from .props import props

T_F = 300.0           # fuel gas temperature [K]
Q_REF = 16.5e6        # reference rated heat input [W]  (pu base for energy flow)
M_AIR_R = 20.0        # rated air flow [kg/s]
P3_R = 1.1556e6       # rated combustor pressure [Pa]
V_M = 0.01            # main manifold volume [m3]  (assumed)
P_UP = 30e5           # regulated fuel supply pressure [Pa]  (assumed)
TX_R = 790.0          # rated exhaust temperature [K]
H2_DESIGN = 1.0       # retrofit hardware is sized for 100 % H2


def size_hardware(h2=H2_DESIGN, dp_inj_frac=0.06, valve_margin=1.30):
    """Size injector total area and metering-valve A_max for rated H2 operation (assumed design basis)."""
    p = props(h2)
    m_rated = 0.96 * Q_REF / p["LHV"]
    P_m = P3_R * (1 + dp_inj_frac)
    A_inj = FS.area_for_flow(m_rated, P_m, P3_R, T_F, p["R"], p["gamma"])
    A_v = FS.area_for_flow(m_rated, P_UP, P_m, T_F, p["R"], p["gamma"]) * valve_margin
    return dict(A_inj_total=A_inj, A_v_max=A_v)


@dataclass
class Config:
    arch: str = "single"                 # "single" | "two" | "three"
    t_end: float = 80.0
    Ts: float = 0.02                      # ECU scan time [s]
    h2: callable = lambda t: 1.0         # actual fuel H2 fraction vs time
    Pe: callable = lambda t: 0.7         # generator electrical load [pu] (single) / ignored (two/three)
    N_ref: callable = lambda t: 1.0      # speed reference (single: generator; two/three: power turbine)
    compensate: bool = True              # Wobbe/composition compensation in ECU
    analyzer_delay: float = 6.0
    analyzer_lag: float = 3.0
    h2_cal: float = 0.0                  # composition assumed by an uncompensated ECU (NG calibration)
    gains: CT.Gains = field(default_factory=CT.Gains)
    tau_R: float = 8.0                   # rotor time constant [s]
    tau_g: float = 1.5                   # gas-generator lag [s] (two/three)
    tau_lp: float = 1.0                  # extra LP-spool lag [s] (three)
    tau_pt: float = 2.5                  # power-turbine + driven-machine time constant [s]
    tau_valve: float = 0.08              # metering-valve actuator time constant [s]
    trip_enabled: bool = True
    flame_out_at: float = None           # inject flame loss at time [s]
    valve_fail_close_at: float = None
    Tx_bias: float = 0.0                 # sensor bias on exhaust temperature [K]
    h2_est_bias: float = 0.0             # composition-estimate bias (fraction)


def _Ngss(w):
    return 0.62 + 0.38 * np.sqrt(max(w, 0.0))


def simulate(cfg: Config):
    hw = size_hardware()
    A_inj, A_vmax = hw["A_inj_total"], hw["A_v_max"]
    g = cfg.gains
    Ts = cfg.Ts
    dt = min(Ts, 0.005)
    nsub = max(1, int(round(Ts / dt)))
    dt = Ts / nsub
    arch = cfg.arch

    h2_0 = cfg.h2(0.0)
    p0 = props(h2_0)
    # --- initial steady state (approximate) ---
    from scipy.optimize import brentq
    eta0 = 1.0 + 0.02 * h2_0
    if arch == "single":
        w0 = 0.23 + cfg.Pe(0.0) / (1.3 * eta0)
    else:
        Pl = cfg.N_ref(0.0) ** 3
        w0 = brentq(lambda w: eta0 * 1.3 * (w - 0.23 * _Ngss(w) ** 3) - Pl, 0.05, 1.2)
    w0 = float(np.clip(w0, 0.25, 1.05))
    N = 1.0 if arch == "single" else 1.0
    Np = cfg.N_ref(0.0)
    Ng = _Ngss(w0)
    Nlp = Ng

    # states
    wp, wm, nst, phi = CT.staging(w0, h2_0)
    n_cur = max(nst, 1)
    n_dwell = 0.0
    P_m = P3_R * 1.03
    # initial valve position consistent with initial main flow
    mapper = CT.FuelMapper(A_vmax, P_UP, T_F, Q_REF, compensate=cfg.compensate, h2_cal=cfg.h2_cal)
    x_v = mapper.position(wm, h2_0, P_m) if wm > 0 else 0.0
    # settle manifold at initial flow
    for _ in range(4000):
        A = FS.valve_area(x_v, A_vmax)
        mv = FS.mass_flow(0.85 * A, P_UP, P_m, T_F, p0["R"], p0["gamma"])
        Ai = A_inj * CT.CUM[n_cur - 1] * 0.85
        mi = FS.mass_flow(Ai, P_m, P3_R, T_F, p0["R"], p0["gamma"])
        P_m += (p0["gamma"] * p0["R"] * T_F / V_M) * (mv - mi) * 0.002
    w_pilot = wp
    sa = CT.CUM[n_cur - 1] if n_cur > 0 else 0.0   # filtered active-stage area fraction (stage valves ramp, not step)
    w_c = wp + (mi * p0["LHV"] / Q_REF if wm > 0 else 0.0)
    Tx_true = TX_R - 389 * (1 - w_c) + 306 * (1 - (N if arch == "single" else Ng))
    Tx_meas = Tx_true
    pgp = 1.3 * (w_c - 0.23 * _Ngss(w_c) ** 3)   # PT power lag state(s)
    pgp2 = pgp
    # controllers
    gov = CT.PI(g.Kp, g.Ti, w_c)
    ggl = CT.PI(4.0, 6.0, 1.0)
    tl = CT.PI(g.Kt * 1000 * 0 + g.Kt, g.Tit, w_c)
    w_dem_prev = w_c
    h2_est_hist = deque([h2_0] * int(cfg.analyzer_delay / Ts + 2))
    h2_f = h2_0
    prot = CT.Protection()
    tripped = False
    flame = True
    rows = []
    t = 0.0
    nsteps = int(cfg.t_end / Ts)
    x_cmd = x_v
    valve_closed_cmd = False
    for k in range(nsteps):
        h2 = cfg.h2(t)
        pr = props(h2)
        # ---- analyzer (transport delay + first-order lag) ----
        h2_est_hist.append(h2)
        h2_del = h2_est_hist.popleft()
        h2_f += (h2_del - h2_f) * Ts / max(cfg.analyzer_lag, Ts)
        h2_est = float(np.clip(h2_f + cfg.h2_est_bias, 0, 1))
        # ---- ECU ----
        Pe = 0.0 if tripped else cfg.Pe(t)      # generator breaker opens on trip
        N_ctrl = N if arch == "single" else Np
        e_s = cfg.N_ref(t) - N_ctrl
        Tx_m = Tx_meas + cfg.Tx_bias
        e_t = g.Tx_lim - Tx_m
        w_gov = gov.out(e_s)
        w_tl = tl.out(e_t)
        cands = [w_gov, w_tl]
        if arch != "single":
            e_g = 1.01 - Ng
            w_gg = ggl.out(e_g)
            cands.append(w_gg)
        w_sel = min(cands)
        w_rate = np.clip(w_sel, w_dem_prev - g.rate_dn * Ts, w_dem_prev + g.rate_up * Ts)
        w_dem = float(np.clip(w_rate, g.w_min, g.w_max))
        # integrators: anti-windup by clamping losing paths to (w_dem + headroom); winner holds when rate/limit saturated
        H = 0.12
        paths = [(gov, e_s, w_gov), (tl, e_t, w_tl)]
        if arch != "single":
            paths.append((ggl, e_g, w_gg))
        saturated = abs(w_dem - w_sel) > 1e-6
        for pi_, e_, wv in paths:
            if wv > w_dem + H:
                pi_.I = (w_dem + H) - pi_.Kp * e_
            elif saturated and wv <= w_sel + 1e-9:
                pass
            else:
                pi_.step(e_, Ts)
        w_dem_prev = w_dem
        # staging
        n_air = (N if arch == "single" else Ng)
        wp_c, wm_c, n_c, phi_c = CT.staging(w_dem, h2_est if cfg.compensate else cfg.h2_cal, m_air_pu=n_air)
        n_dwell += Ts
        if (n_c != n_cur) and n_dwell > 2.0:
            n_cur = max(n_c, 0) if n_c > 0 else 0
            n_dwell = 0.0
        if n_c == 0:
            wp_c, wm_c = w_dem, 0.0
        elif n_cur == 0:
            n_cur = n_c
        if n_cur == 0:
            wp_c, wm_c = w_dem, 0.0
        x_cmd = mapper.position(wm_c, h2_est, P_m) if wm_c > 0 else 0.0
        # ---- protection ----
        if cfg.trip_enabled and not tripped:
            if prot.check(t, N if arch == "single" else Np, Tx_true, flame):
                tripped = True
        if tripped or (cfg.valve_fail_close_at is not None and t >= cfg.valve_fail_close_at):
            x_cmd = 0.0
            wp_c = 0.0
        # ---- plant sub-steps ----
        for _ in range(nsub):
            pr = props(cfg.h2(t))
            # valve actuator (first order + rate limit 2 /s fail-safe close faster)
            tau_v = cfg.tau_valve
            x_v += (x_cmd - x_v) * dt / tau_v
            Av = FS.valve_area(x_v, A_vmax) * 0.85
            mv = FS.mass_flow(Av, P_UP, P_m, T_F, pr["R"], pr["gamma"])
            sa += ((CT.CUM[n_cur - 1] if n_cur > 0 else 0.0) - sa) * dt / 0.8
            Ai = A_inj * sa * 0.85
            P3 = P3_R * (N if arch == "single" else Ng) ** 2
            mi = FS.mass_flow(Ai, P_m, P3, T_F, pr["R"], pr["gamma"]) if Ai > 0 else 0.0
            if Ai == 0.0:
                mi = 0.0
            P_m += (pr["gamma"] * pr["R"] * T_F / V_M) * (mv - mi) * dt
            P_m = max(P_m, P3)
            # pilot path (first-order)
            w_pilot += (wp_c - w_pilot) * dt / 0.3
            w_in = mi * pr["LHV"] / Q_REF + w_pilot
            if cfg.flame_out_at is not None and t >= cfg.flame_out_at:
                flame = False
                w_in = 0.0
            w_c += (w_in - w_c) * dt / 0.1
            eta_ratio = 1.0 + 0.02 * h2      # H2O-richer products: ~+2 % shaft work per unit heat (cycle model)
            if arch == "single":
                G = eta_ratio * (1.3 * (w_c - 0.23) + 0.5 * (1 - N))
                if w_c < 0.05:
                    G = -0.35 * min(N, 1.2) ** 2
                N += dt * (G - Pe / max(N, 0.3)) / cfg.tau_R
                N = max(N, 0.0)
                Ng_state = N
                Tx_true = TX_R - 389 * (1 - w_c) + 306 * (1 - N)
            else:
                tgt = eta_ratio * 1.3 * (w_c - 0.23 * _Ngss(w_c) ** 3)
                if w_c < 0.05:
                    tgt = -0.2
                pgp += (tgt - pgp) * dt / cfg.tau_g
                if arch == "three":
                    pgp2 += (pgp - pgp2) * dt / cfg.tau_lp
                    ppt = pgp2
                else:
                    ppt = pgp
                Ng_ss = _Ngss(w_c) if w_c > 0.05 else 0.3
                Ng += (Ng_ss - Ng) * dt / cfg.tau_g
                Nlp += (Ng - Nlp) * dt / cfg.tau_lp
                Pl = Np ** 3
                Np += dt * (ppt / max(Np, 0.3) - Pl / max(Np, 0.3)) / cfg.tau_pt
                Tx_true = TX_R - 389 * (1 - w_c) + 306 * (1 - Ng)
            Tx_meas += (Tx_true - Tx_meas) * dt / 2.0
            t += dt
        rows.append(dict(t=t, N=N if arch == "single" else Np, Ng=(N if arch == "single" else Ng), Pe=Pe if arch == "single" else Np ** 3,
                         h2=h2, h2_est=h2_est, w_dem=w_dem, w_c=w_c, w_main=mi * pr["LHV"] / Q_REF, w_pilot=w_pilot,
                         x_v=x_v, P_m_bar=P_m / 1e5, dP_inj=(P_m - P3) / P3, n_stage=n_cur, phi_main=phi_c if n_cur > 0 else 0.0,
                         Tx=Tx_true, Tx_meas=Tx_meas, Tx_lim=g.Tx_lim, tripped=int(tripped), m_main=mi, WI=pr["WI"],
                         air_pu=(N if arch == "single" else Ng), flame=int(flame), MW=pr["MW"],
                         phi_act=((mi / (M_AIR_R * max(N if arch == "single" else Ng, 0.05) * CT.ALPHA_PZ * sa)) / pr["FA_st"]) if (mi > 1e-6 and sa > 1e-3) else 0.0))
        if tripped and rows[-1]["N"] < 0.5:
            pass
    df = pd.DataFrame(rows)
    df.attrs["trip_reason"] = prot.reason
    df.attrs["t_trip"] = prot.t_trip
    return df
