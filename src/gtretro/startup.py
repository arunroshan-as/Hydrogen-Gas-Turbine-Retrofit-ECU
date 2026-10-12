"""Indicative start-up sequence: purge crank -> spark-lit pilot (minimum fuel) -> warm-up -> acceleration ->
FSNL idle on pilot/early stages -> synchronise -> load ramp. Power-balance rotor model, assumed parameters.
Timing is indicative only; real start logic depends on the OEM start curve and starter capability."""
import numpy as np
import pandas as pd
from . import control as CT
from .props import props
from .plant import Q_REF, M_AIR_R

STATES = ["READY", "CRANK", "PURGE", "IGNITION", "WARM-UP", "ACCEL", "IDLE (FSNL)", "SYNC / LOAD"]


def run(h2=1.0, dt=0.05, V_sys=15.0, n_purge_volumes=5.0, Ts_torque=0.06, tau_R=8.0, load_target=0.7, load_rate=0.02, t_end=240.0):
    pr = props(h2)
    N, t = 0.0, 0.0
    state = 0
    t_state = 0.0
    w, w_pilot, w_main, n_st, phi = 0.0, 0.0, 0.0, 0, 0.0
    vol_air = 0.0
    I = 0.23
    Pe = 0.0
    rows = []
    sync = False
    n_cur, n_dwell = 0, 0.0
    spark = False
    flame = False
    while t < t_end:
        t_state += dt
        starter = 0.0
        rho_air = 1.2
        # ----------------------------------------------------------- sequencer
        if state == 0:                           # leak test / valve proving / permissives
            if t_state >= 8.0: state, t_state = 1, 0.0
        elif state == 1:                         # crank to purge speed
            starter = Ts_torque * max(N, 0.02)
            if N >= 0.20: state, t_state, vol_air = 2, 0.0, 0.0
        elif state == 2:                         # purge: >= n volume changes of the gas path, no fuel
            starter = min(Ts_torque * max(N, 0.02), 0.3 * N ** 3 + 0.0) if N >= 0.20 else Ts_torque * N
            vol_air += (M_AIR_R * N / rho_air) * dt
            if vol_air >= n_purge_volumes * V_sys and t_state >= 10.0: state, t_state, spark = 3, 0.0, True
        elif state == 3:                         # spark on, minimum pilot fuel, flame proving
            starter = 0.3 * N ** 3
            w = min(0.06, w + 0.02 * dt)
            if t_state >= 5.0: state, t_state, flame = 4, 0.0, True
            if t_state >= 2.5: spark = False if t_state >= 4.0 else spark
        elif state == 4:                         # warm-up on pilot
            starter = 0.3 * N ** 3
            if t_state >= 6.0: state, t_state = 5, 0.0
        elif state == 5:                         # acceleration on schedule, starter assists to ~0.55
            starter = Ts_torque * N * max(0.0, min(1.0, (0.70 - N) / 0.15)) if N < 0.70 else 0.0
            if N >= 0.995 and t_state > 5.0: state, t_state = 6, 0.0
        elif state == 6:                         # idle at rated speed, pilot / early stages
            if t_state >= 8.0: state, t_state, sync = 7, 0.0, True
        elif state == 7:
            Pe = min(load_target, Pe + load_rate * dt)
        # ----------------------------------------------------------- fuel control
        if state >= 3:
            w_acc = 0.10 + 0.30 * N
            w_gov = I + 20.0 * (1.0 - N)
            if state == 3 or state == 4:
                w_dem = w
            elif state == 5:
                e = 1.0 - N
                w_gov_raw = I + 20.0 * e
                if w_acc < w_gov_raw:
                    I = w_acc - 20.0 * e          # anti-windup: governor tracks the acceleration schedule
                else:
                    I += 20.0 / 5.0 * e * dt
                w_dem = min(w_acc, I + 20.0 * e, w + 0.05 * dt)   # fuel ramp limited to 0.05 pu/s
            else:
                e = 1.0 - N
                I += 20.0 / 5.0 * e * dt
                w_dem = I + 20.0 * e
                w_dem = float(np.clip(w_dem, 0.15, 1.1))
            w = w_dem
            if state == 7:      # main premix stages engage only after synchronisation (pilot/start circuit carries everything before)
                w_pilot, w_main, n_st, phi = CT.staging(w, h2, m_air_pu=max(N, 0.3))
            else:
                w_pilot, w_main, n_st, phi = w, 0.0, 0, 0.0
        # ----------------------------------------------------------- rotor power balance
        eps = N ** 1.5
        P_t = 1.3 * eps * w if flame else 0.0
        P_net = P_t - 0.299 * N ** 3 + starter - Pe + (0.0 if state != 0 else 0.0)
        if state in (1, 2) and N >= 0.20 and state == 2:
            # starter holds purge speed (speed-controlled): cancel drag so N stays ~0.20
            N += 0.0
        else:
            N += dt * P_net / (tau_R * max(N, 0.05))
        N = max(N, 0.0)
        if state == 2: N = max(N, 0.20)
        t += dt
        rows.append(dict(t=t, N=N, state=state, state_name=STATES[state], w=w, w_pilot=w_pilot, w_main=w_main, n_stage=n_st,
                         phi_main=phi, Pe=Pe, spark=int(spark), flame=int(flame), purge_volumes=vol_air / V_sys if state >= 2 else 0.0))
    return pd.DataFrame(rows)
