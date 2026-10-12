"""Fuel-chemistry study at representative compressor-discharge conditions (Cantera / GRI-Mech 3.0).
Writes CSVs to results/data. Slow part: laminar flame speeds (cached)."""
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from gtretro import fuels as F

OUT = os.path.join(os.path.dirname(__file__), "..", "results", "data")
os.makedirs(OUT, exist_ok=True)
T2, P2 = 650.0, 12 * 101325.0          # assumed compressor-discharge state (reference platform)
H2_SET = [0.0, 0.5, 1.0]                 # surrogate family: 0 / 50 / 100 vol% H2 in CH4

def aft_table():
    rows = []
    for h in H2_SET:
        for phi in np.arange(0.30, 0.801, 0.025):
            rows.append(dict(h2_vol=h, phi=phi, T_flame=F.aft(h, phi, T2, P2)))
    pd.DataFrame(rows).to_csv(f"{OUT}/aft_vs_phi.csv", index=False)

def ignition_table():
    rows = []
    for h in H2_SET:
        for T in np.arange(700, 1101, 25):
            rows.append(dict(h2_vol=h, T_K=T, tau_s=F.ignition_delay(h, 0.5, T, P2, t_max=2.0)))
    pd.DataFrame(rows).to_csv(f"{OUT}/ignition_delay.csv", index=False)

def nox_table():
    rows = []
    for h in H2_SET:
        for phi in np.arange(0.35, 0.651, 0.05):
            for tr in (0.005, 0.010, 0.020):
                rows.append(dict(h2_vol=h, phi=phi, t_res_ms=tr * 1e3, NOx_ppm15=F.thermal_no_ppm(h, phi, T2, P2, tr)))
    pd.DataFrame(rows).to_csv(f"{OUT}/nox_premixed.csv", index=False)

def flame_table():
    path = f"{OUT}/flame_speed.csv"
    rows = []
    for h in H2_SET:
        for phi in (0.45, 0.50, 0.55):
            sl = F.laminar_flame_speed(h, phi, T2, P2)
            al = F.thermal_diffusivity(h, phi, T2, P2)
            rows.append(dict(h2_vol=h, phi=phi, S_L=sl, alpha=al, g_crit=sl**2 / al, d_quench_mm=1e3 * 40 * al / sl))
            pd.DataFrame(rows).to_csv(path, index=False)
            print("flame", h, phi, sl, flush=True)

if __name__ == "__main__":
    aft_table(); print("aft done", flush=True)
    ignition_table(); print("ign done", flush=True)
    nox_table(); print("nox done", flush=True)
    flame_table(); print("flame done", flush=True)
