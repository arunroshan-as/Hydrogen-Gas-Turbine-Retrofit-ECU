"""ECU / PLC control logic (reference implementation in Python; mirrors plc/GT_Fuel_Control.scl).

Structure: speed governor, exhaust-temperature limiter and acceleration/rate limiter combined by a
minimum-select with bumpless integrator tracking; Wobbe-compensated fuel mapping; pilot/main staging;
protection (trip) logic. Gains are preliminary and tuned on the reduced-order plant only.
"""
from dataclasses import dataclass
import numpy as np
from . import fuel_system as FS
from .props import props

# Main premix zones are staged with UNEQUAL sizes (cumulative fraction of main premix air), as in staged DLE practice.
CUM = np.array([0.20, 0.275, 0.38, 0.52, 0.72, 1.00])
N_STAGES = len(CUM)
ALPHA_PZ = 0.50          # fraction of compressor air routed through the main premix zones (design)
PHI_MAX, PHI_MIN = 0.55, 0.45   # target lean band (primary zone)


@dataclass
class Gains:
    Kp: float = 20.0       # pu fuel / pu speed
    Ti: float = 5.0        # s
    Kt: float = 0.02       # pu fuel / K  (temperature limiter)
    Tit: float = 6.0       # s
    rate_up: float = 0.60  # pu fuel / s (max fuel increase rate)
    rate_dn: float = 1.0
    w_min: float = 0.15    # lean-blowout / flame-retention floor (pu energy flow)
    w_max: float = 1.10
    Tx_lim: float = 795.0  # K exhaust-temperature limit


class PI:
    def __init__(self, Kp, Ti, out0=0.0):
        self.Kp, self.Ti, self.I = Kp, Ti, out0

    def out(self, e):
        return self.Kp * e + self.I

    def step(self, e, dt):
        self.I += self.Kp / self.Ti * e * dt

    def track(self, e, target):
        self.I = target - self.Kp * e


def pilot_loaded(w):
    """Pilot-chamber energy (pu of rated heat input) when main stages are lit: 10 % at low load -> 4 % at full load."""
    return 0.10 - 0.06 * min(1.0, max(0.0, (w - 0.10) / 0.90))


def staging(w, h2_est, m_air_pu=1.0, Q_rated=16.5e6, m_air_rated=20.0):
    """Return (pilot_pu, main_pu, n_stages, phi_main).
    Chooses the fewest main stages keeping phi <= PHI_MAX. If even the first stage cannot hold phi >= ~0.9*PHI_MIN,
    all fuel goes to the (spark-lit, diffusion-stabilised) pilot chamber: this is the start / idle / FSNL regime."""
    p = props(h2_est)
    m_pz = m_air_rated * m_air_pu * ALPHA_PZ

    def phi_of(wm, n):
        return (wm * Q_rated / p["LHV"]) / (m_pz * CUM[n - 1]) / p["FA_st"]

    w_p = pilot_loaded(w)
    w_m = max(w - w_p, 0.0)
    if w_m <= 0 or phi_of(w_m, 1) < 0.9 * PHI_MIN:
        return w, 0.0, 0, 0.0
    n = 1
    while n < N_STAGES and phi_of(w_m, n) > PHI_MAX:
        n += 1
    return w_p, w_m, n, phi_of(w_m, n)


class FuelMapper:
    """Maps energy-flow demand (pu) to valve position using a fuel-property estimate (Wobbe compensation)."""

    def __init__(self, A_max, P_up, T_f=300.0, Q_rated=16.5e6, compensate=True, h2_cal=0.0, rangeability=50.0, Cd=0.85):
        self.A_max, self.P_up, self.T_f, self.Q = A_max, P_up, T_f, Q_rated
        self.comp, self.h2_cal, self.rg, self.Cd = compensate, h2_cal, rangeability, Cd

    def position(self, w_main_pu, h2_est, P_m):
        pr = props(h2_est if self.comp else self.h2_cal)
        m_dem = w_main_pu * self.Q / pr["LHV"]
        if m_dem <= 0:
            return 0.0
        A = FS.area_for_flow(m_dem, self.P_up, P_m, self.T_f, pr["R"], pr["gamma"]) / self.Cd
        return FS.valve_pos_for_area(A, self.A_max, self.rg)


class Protection:
    """Trip logic (software level; the hard-wired ESD chain is independent - see docs/safety_architecture.md)."""

    def __init__(self, N_trip=1.10, Tx_trip=840.0, dp_trip=0.30):
        self.N_trip, self.Tx_trip, self.dp_trip = N_trip, Tx_trip, dp_trip
        self.tripped, self.reason, self.t_trip = False, "", None

    def check(self, t, N, Tx, flame, leak=False, Pm_ratio=1.0):
        if self.tripped:
            return True
        r = ""
        if N > self.N_trip: r = "OVERSPEED"
        elif Tx > self.Tx_trip: r = "EXH_TEMP_HIGH"
        elif not flame: r = "FLAME_LOSS"
        elif leak: r = "H2_LEAK"
        if r:
            self.tripped, self.reason, self.t_trip = True, r, t
        return self.tripped
