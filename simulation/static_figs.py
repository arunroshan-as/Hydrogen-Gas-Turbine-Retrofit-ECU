"""Figures 01-07: fuel chemistry, cycle, fuel system, thermal protection, staging map (no dynamics)."""
import os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "src")); sys.path.insert(0, HERE)
from plotstyle import *
setup()
from gtretro import fuels as F, cycle as C, fuel_system as FS, control as CT, plant as P
from gtretro.props import props

DATA = os.path.join(HERE, "..", "results", "data")
FIG = os.path.join(HERE, "..", "results", "figures")
os.makedirs(FIG, exist_ok=True)
T2, P2 = 650.0, 12 * 101325.0


def fig01_fuel_chemistry():
    aft = pd.read_csv(f"{DATA}/aft_vs_phi.csv"); fl = pd.read_csv(f"{DATA}/flame_speed.csv")
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
    for h in (0.0, 0.5, 1.0):
        d = aft[aft.h2_vol == h]; ax[0].plot(d.phi, d.T_flame, color=COL[h], label=LAB[h])
        f = fl[fl.h2_vol == h]; ax[1].plot(f.phi, f.S_L, "o-", color=COL[h], label=LAB[h])
    for a in ax: a.axvspan(0.45, 0.55, color="#fde68a", alpha=0.35, lw=0)
    ax[0].set_xlabel("Equivalence ratio $\\phi$ (primary zone)"); ax[0].set_ylabel("Adiabatic flame temperature [K]")
    ax[0].set_title("(a) Flame temperature at compressor-discharge conditions"); ax[0].legend(loc="upper left")
    ax[0].text(0.46, 1330, "target lean band\n0.45-0.55", fontsize=8, color="#92400e")
    ax[1].set_yscale("log"); ax[1].set_xlabel("Equivalence ratio $\\phi$"); ax[1].set_ylabel("Laminar burning velocity $S_L$ [m/s]")
    ax[1].set_title("(b) Laminar flame speed (GRI-Mech 3.0)")
    r = fl[(fl.h2_vol == 1.0) & (fl.phi == 0.5)].S_L.values[0] / fl[(fl.h2_vol == 0.0) & (fl.phi == 0.5)].S_L.values[0]
    ax[1].annotate(f"H$_2$/CH$_4$ at $\\phi$=0.5: {r:.1f}x", xy=(0.5, 0.8), xytext=(0.462, 0.33), fontsize=8, arrowprops=dict(arrowstyle="-", color="#6b7280"))
    fig.suptitle("Fuel chemistry at T = 650 K, p = 12 bar (assumed compressor-discharge state)", y=1.0, fontsize=10)
    foot(fig); fig.tight_layout(rect=(0, 0.02, 1, 1)); fig.savefig(f"{FIG}/fig01_fuel_chemistry.png"); plt.close(fig)


def fig02_ignition():
    d = pd.read_csv(f"{DATA}/ignition_delay.csv")
    fig, ax = plt.subplots(figsize=(5.6, 3.8))
    for h in (0.0, 0.5, 1.0):
        x = d[d.h2_vol == h]; xx = x[np.isfinite(x.tau_s)]
        ax.semilogy(xx.T_K, xx.tau_s * 1e3, "o-", ms=3, color=COL[h], label=LAB[h])
    ax.axhspan(5, 20, color="#fde68a", alpha=0.4, lw=0); ax.text(705, 7, "typical premixer residence time 5-20 ms", fontsize=7.5, color="#92400e")
    ax.axvline(650, color="#6b7280", ls=":"); ax.text(654, 1.0, "assumed T$_2$ = 650 K: no ignition within 2 s", fontsize=7, rotation=90, color="#6b7280")
    ax.set_xlim(640, 1110); ax.set_ylim(0.7, 3000)
    ax.set_xlabel("Premixer inlet temperature [K] (12 bar, $\\phi$ = 0.5)"); ax.set_ylabel("Autoignition delay [ms]")
    ax.set_title("Autoignition margin (no curve = no ignition within 2 s)"); ax.legend(loc="upper right")
    ax.text(650, 1.0, "", fontsize=1)
    fig.text(0.99, 0.01, "GRI-Mech 3.0 is uncertain for H$_2$ at high p / low T: treat as indicative", fontsize=6.5, ha="right", color="#6b7280")
    foot(fig); fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(f"{FIG}/fig02_autoignition_margin.png"); plt.close(fig)


def fig03_nox():
    d = pd.read_csv(f"{DATA}/nox_premixed.csv"); d = d[d.t_res_ms == 10]
    fig, ax = plt.subplots(figsize=(5.6, 3.8))
    for h in (0.0, 0.5, 1.0):
        x = d[d.h2_vol == h]; ax.semilogy(x.phi, np.maximum(x.NOx_ppm15, 1e-3), "o-", color=COL[h], label=LAB[h])
    ax.axvspan(0.45, 0.55, color="#fde68a", alpha=0.35, lw=0)
    ax.set_xlabel("Primary-zone equivalence ratio $\\phi$"); ax.set_ylabel("Thermal NO$_x$ [ppmvd @ 15% O$_2$]")
    ax.set_title("Best-case (perfectly premixed) NO$_x$ indicator, 10 ms residence"); ax.legend(loc="lower right")
    ax.text(0.352, 3e-3, "Imperfect mixing raises local $\\phi$ and NO$_x$ - to be\nquantified by CFD / rig tests", fontsize=7, color="#6b7280")
    foot(fig); fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(f"{FIG}/fig03_nox_indicator.png"); plt.close(fig)


def fig04_cycle():
    plat = C.Platform(); hs = np.linspace(0, 1, 11)
    rows = [C.run(plat, h) for h in hs]
    df = pd.DataFrame([{k: v for k, v in r.items() if k != "mix_Y3"} for r in rows])
    for r in df.itertuples(): pass
    # fuel volumetric flow ratio (same pressure/temperature) vs CH4
    vr = []
    for h in hs:
        p = props(h); vr.append((df.loc[df.h2_vol == h, "m_fuel"].values[0] * p["R"]))
    df["vol_flow_rel_CH4"] = np.array(vr) / vr[0]
    df.to_csv(f"{DATA}/cycle_vs_h2.csv", index=False)
    amb = np.arange(273.15, 320, 5.0)
    pa = {h: [C.run(plat, h, T_amb=T)["P_elec"] for T in amb] for h in (0.0, 1.0)}
    pd.DataFrame({"T_amb_K": amb, "P_elec_CH4": pa[0.0], "P_elec_H2": pa[1.0]}).to_csv(f"{DATA}/ambient_derate.csv", index=False)
    # primary-zone air fraction
    fig, ax = plt.subplots(1, 4, figsize=(14, 3.6))
    ax[0].plot(hs * 100, df.P_elec / 1e6, "o-", color="#111827"); ax[0].set_ylabel("Electrical power [MW]"); ax[0].set_title("(a) Output at constant TIT = 1300 K")
    ax2 = ax[0].twinx(); ax2.plot(hs * 100, df.eta_elec * 100, "s--", color="#dc2626", ms=3); ax2.set_ylabel("Electrical efficiency [%]", color="#dc2626"); ax2.grid(False)
    ax2.spines["right"].set_visible(True)
    ax[1].plot(hs * 100, df.vol_flow_rel_CH4, "o-", color="#2563eb"); ax[1].set_ylabel("Volumetric fuel flow / CH$_4$ case [-]"); ax[1].set_title("(b) Fuel volume flow (same p, T)")
    for T, c in ((0.45, "#6b7280"), (0.50, "#2563eb"), (0.55, "#dc2626")):
        ax[2].plot(hs * 100, df.phi_overall / T, "o-", ms=3, color=c, label=f"$\\phi_{{pz}}$ = {T:.2f}")
    ax[2].set_ylabel("Air fraction to primary zone [-]"); ax[2].set_title("(c) Air split needed for target $\\phi_{pz}$"); ax[2].legend()
    ax[3].plot((amb - 273.15), np.array(pa[0.0]) / 1e6, "o-", color=COL[0.0], label="CH$_4$"); ax[3].plot((amb - 273.15), np.array(pa[1.0]) / 1e6, "o-", color=COL[1.0], label="100% H$_2$")
    ax[3].set_ylabel("Electrical power [MW]"); ax[3].set_xlabel("Ambient temperature [$^\\circ$C]"); ax[3].set_title("(d) Ambient derating (const. TIT)"); ax[3].legend()
    for a in ax[:3]: a.set_xlabel("H$_2$ in fuel [vol%]")
    foot(fig, "Reference platform GT-A: PR 12, 20 kg/s, $\\eta_c$ 0.84, $\\eta_t$ 0.88."); fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(f"{FIG}/fig04_brayton_cycle.png"); plt.close(fig)


def fig05_fuel_system():
    plat = C.Platform(); hs = np.linspace(0, 1, 11)
    P_up, P_m, P3 = 30e5, 12.25e5, 11.556e5
    rows = []
    for h in hs:
        r = C.run(plat, h); p = props(h); m = r["m_fuel"]
        A_v = FS.area_for_flow(m, P_up, P_m, 300, p["R"], p["gamma"]) / 0.85
        A_i = FS.area_for_flow(m, P_m, P3, 300, p["R"], p["gamma"]) / 0.85
        u = FS.line_velocity(m, P_up, 300, p["R"], 0.0525)
        rows.append(dict(h2_vol=h, m_fuel=m, A_valve_mm2=A_v * 1e6, A_inj_mm2=A_i * 1e6, v_line_30bar=u)) 
    d = pd.DataFrame(rows); d.to_csv(f"{DATA}/fuel_system_sizing.csv", index=False)
    fig, ax = plt.subplots(1, 3, figsize=(12, 3.6))
    ax[0].plot(hs * 100, d.A_valve_mm2 / d.A_valve_mm2[0], "o-", color="#2563eb", label="metering valve $A_{eff}$")
    ax[0].plot(hs * 100, d.A_inj_mm2 / d.A_inj_mm2[0], "s-", color="#dc2626", label="injector total $A_{eff}$ ($\\Delta p$ = 6 %)")
    ax[0].set_ylabel("Required area / CH$_4$ case [-]"); ax[0].set_title("(a) Flow area for equal heat input"); ax[0].legend(); ax[0].set_ylim(0.95, 1.4)
    ax[1].plot(hs * 100, d.v_line_30bar, "o-", color="#111827"); ax[1].set_ylabel("Bulk velocity [m/s]"); ax[1].set_title("(b) Velocity in a 52.5 mm bore at 30 bar")
    ax[2].plot(hs * 100, d.m_fuel * 3600, "o-", color="#059669"); ax[2].set_ylabel("Fuel mass flow [kg/h]"); ax[2].set_title("(c) Mass flow at rated heat input")
    for a in ax: a.set_xlabel("H$_2$ in fuel [vol%]")
    foot(fig, "Compressible orifice model, C$_d$ = 0.85."); fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(f"{FIG}/fig05_fuel_system_sizing.png"); plt.close(fig)


def fig06_tbc():
    t = np.linspace(0, 600e-6, 61)
    hg, hc, kt, km, tm, Tc, eta_f = 1800.0, 2500.0, 1.0, 22.0, 2.5e-3, 650.0, 0.35
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    out = []
    for h in (0.0, 1.0):
        Tg = F.aft(h, 0.5, T2, P2); Taw = Tg - eta_f * (Tg - Tc)
        for scale, ls in ((1.0, "-"), (0.75, ":"), (1.25, ":")):
            R = 1 / (hg * scale) + t / kt + tm / km + 1 / hc
            q = (Taw - Tc) / R
            Th = Taw - q / (hg * scale)
            Tm = Th - q * t / kt  # metal hot-side temperature (below the TBC)
            if scale == 1.0:
                ax.plot(t * 1e6, Tm, ls, color=COL[h], label=f"{LAB[h]} ($T_{{ad}}$ = {Tg:.0f} K)")
            else:
                ax.plot(t * 1e6, Tm, ls, color=COL[h], lw=0.9)
            out.append(pd.DataFrame(dict(h2_vol=h, hg_scale=scale, tbc_um=t * 1e6, T_metal_hot_K=Tm, q_MWm2=q / 1e6)))
    pd.concat(out).to_csv(f"{DATA}/tbc_metal_temperature.csv", index=False)
    ax.axhline(1200, color="#6b7280", ls="--"); ax.text(10, 1170, "indicative superalloy liner limit ~1200 K", fontsize=7.5, color="#6b7280")
    ax.set_xlabel("YSZ thermal-barrier coating thickness [$\\mu$m]"); ax.set_ylabel("Liner metal hot-side temperature [K]")
    ax.set_title("1-D liner wall estimate, primary-zone gas at $\\phi$ = 0.5 (dotted: $h_g$ $\\pm$25 %)")
    ax.legend(loc="center right", fontsize=7.5, bbox_to_anchor=(1.0, 0.72))
    foot(fig, "Assumed: h$_g$ 1800, h$_c$ 2500, k$_{TBC}$ 1.0, k$_{metal}$ 22, film eff. 0.35.")
    fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(f"{FIG}/fig06_tbc_wall_temperature.png"); plt.close(fig)


def fig07_staging():
    w = np.linspace(0.05, 1.0, 400)
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.8)); rows = []
    for h in (0.0, 0.5, 1.0):
        res = [CT.staging(x, h) for x in w]
        phi = np.array([r[3] for r in res]); n = np.array([r[2] for r in res]); wp = np.array([r[0] for r in res]); wm = np.array([r[1] for r in res])
        ax[0].plot(w, np.where(phi > 0, phi, np.nan), color=COL[h], label=LAB[h], lw=1.3)
        ax[1].step(w, n, where="post", color=COL[h], lw=1.3)
        ax[2].plot(w, wp / w * 100, color=COL[h], lw=1.3)
        inb = ((phi >= 0.45 - 1e-6) & (phi <= 0.55 + 1e-6))[(w >= 0.3)].mean() * 100
        rows.append(dict(h2_vol=h, share_of_load_range_in_band_pct=inb, phi_min=np.nanmin(np.where(phi > 0, phi, np.nan)[w >= 0.3]), phi_max=phi.max()))
        pd.DataFrame(dict(h2_vol=h, load_pu=w, pilot_pu=wp, main_pu=wm, n_stage=n, phi_main=phi)).to_csv(f"{DATA}/staging_h2_{int(h*100)}.csv", index=False)
    pd.DataFrame(rows).to_csv(f"{DATA}/staging_band_summary.csv", index=False)
    ax[0].axhspan(0.45, 0.55, color="#fde68a", alpha=0.35, lw=0); ax[0].set_ylim(0.3, 0.65)
    ax[0].set_ylabel("Main-stage primary-zone $\\phi$"); ax[0].set_title("(a) $\\phi$ vs load (staged premix)"); ax[0].legend(loc="lower right", fontsize=7)
    ax[1].set_ylabel("Active main premix stages"); ax[1].set_title("(b) Stage schedule (0 = pilot only)")
    ax[2].set_ylabel("Pilot share of heat input [%]"); ax[2].set_title("(c) Pilot fraction (100 % = start / idle)"); ax[2].set_ylim(0, 105)
    for a in ax: a.set_xlabel("Fuel energy demand [pu of rated heat input]")
    foot(fig, "6 unequal premix stages, ECU selects fewest stages with $\\phi \\leq$ 0.55."); fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(f"{FIG}/fig07_staging_schedule.png"); plt.close(fig)
    print(pd.DataFrame(rows))


if __name__ == "__main__":
    for f in (fig01_fuel_chemistry, fig02_ignition, fig03_nox, fig04_cycle, fig05_fuel_system, fig06_tbc, fig07_staging):
        print(f.__name__, flush=True); f()
