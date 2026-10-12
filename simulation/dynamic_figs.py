"""Figures 08-15: ECU-in-the-loop dynamic scenarios and start-up sequence. Writes figures + CSV (0.1 s decimated)."""
import os, sys, json, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "src")); sys.path.insert(0, HERE)
from plotstyle import *
setup()
from gtretro import plant as P, control as CT, startup as ST

DATA = os.path.join(HERE, "..", "results", "data"); FIG = os.path.join(HERE, "..", "results", "figures")
os.makedirs(DATA, exist_ok=True); os.makedirs(FIG, exist_ok=True)
METRICS = {}


def save(df, name):
    d = df.iloc[::max(1, int(round(0.1 / (df.t.iloc[1] - df.t.iloc[0]))))]
    d.to_csv(f"{DATA}/{name}.csv", index=False)


def spans(ax, df):
    pass


def fig08_load_step():
    cfg = P.Config(arch="single", t_end=60, Pe=lambda t: 0.5 if t < 20 else 0.8)
    df = P.simulate(cfg); save(df, "sim_load_step_h2"); t = df.t
    fig, ax = plt.subplots(2, 3, figsize=(13, 6.2)); ax = ax.ravel()
    ax[0].plot(t, df.N * 100, color="#111827"); ax[0].set_ylabel("Shaft speed [% rated]"); ax[0].set_title("(a) Speed (isochronous governor)")
    ax[1].plot(t, df.w_dem, "--", color="#6b7280", label="ECU demand"); ax[1].plot(t, df.w_c, color="#dc2626", label="heat release (after fuel-path lag)")
    ax[1].plot(t, df.w_pilot, color="#2563eb", label="pilot"); ax[1].set_ylabel("Energy flow [pu of rated heat input]"); ax[1].set_title("(b) Fuel energy flow"); ax[1].legend(loc="lower right")
    ax[2].plot(t, df.Tx_meas, color="#dc2626", label="exhaust T (measured)"); ax[2].axhline(df.Tx_lim.iloc[0], color="#6b7280", ls="--", label="limiter set-point")
    ax[2].set_ylabel("Exhaust temperature [K]"); ax[2].set_title("(c) Exhaust temperature vs limiter"); ax[2].legend(loc="lower right")
    ax[3].plot(t, df.x_v, color="#111827"); ax[3].set_ylabel("Valve position [-]"); ax[3].set_title("(d) Metering valve and manifold pressure")
    b = ax[3].twinx(); b.plot(t, df.P_m_bar, color="#2563eb"); b.set_ylabel("Manifold pressure [bar]", color="#2563eb"); b.grid(False); b.spines["right"].set_visible(True)
    ax[4].plot(t, np.where(df.phi_act > 0, df.phi_act, np.nan), color="#dc2626"); ax[4].axhspan(0.45, 0.55, color="#fde68a", alpha=0.4, lw=0)
    ax[4].set_ylim(0.3, 0.65); ax[4].set_ylabel("Main-stage $\\phi$"); ax[4].set_title("(e) Primary-zone $\\phi$ and stage count")
    c = ax[4].twinx(); c.step(t, df.n_stage, color="#6b7280", where="post"); c.set_ylabel("Active stages", color="#6b7280"); c.grid(False); c.spines["right"].set_visible(True); c.set_ylim(0, 7)
    ax[5].plot(t, df.dP_inj * 100, color="#059669"); ax[5].set_ylabel("Injector $\\Delta p / p_3$ [%]"); ax[5].set_title("(f) Injector pressure drop")
    for a in ax: a.set_xlabel("Time [s]")
    for a in ax: a.axvline(20, color="#9ca3af", lw=0.8, ls=":")
    METRICS["load_step"] = dict(N_min_pct=float(df.N.min() * 100), N_end_pct=float(df.N.iloc[-1] * 100), Tx_max_K=float(df.Tx.max()),
                                t_recover_1pct_s=float(df[(df.t > df.t[df.N.idxmin()]) & (abs(df.N - 1) < 0.01)].t.min() - 20),
                                phi_min=float(df[df.phi_act > 0].phi_act.min()), phi_max=float(df.phi_act.max()))
    fig.suptitle("Single-shaft generator drive, 100 % H$_2$: load step 0.5 -> 0.8 pu at t = 20 s", y=0.995, fontsize=10)
    foot(fig); fig.tight_layout(rect=(0, 0.02, 1, 0.98)); fig.savefig(f"{FIG}/fig08_load_step_response.png"); plt.close(fig)


def fig09_load_rejection():
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.8)); out = {}
    for h in (0.0, 1.0):
        cfg = P.Config(arch="single", t_end=40, h2=(lambda t, h=h: h), Pe=lambda t: 0.8 if t < 10 else 0.0)
        df = P.simulate(cfg); save(df, f"sim_load_rejection_h2_{int(h*100)}")
        ax[0].plot(df.t, df.N * 100, color=COL[h], label=LAB[h]); ax[1].plot(df.t, df.w_c, color=COL[h]); ax[2].plot(df.t, df.P_m_bar, color=COL[h])
        out[f"h2_{int(h*100)}"] = dict(N_peak_pct=float(df.N.max() * 100), t_peak_s=float(df.t[df.N.idxmax()] - 10), tripped=bool(df.tripped.max()))
    ax[0].axhline(110, color="#6b7280", ls="--"); ax[0].text(25, 110.4, "overspeed trip 110 %", fontsize=7.5, color="#6b7280")
    ax[0].set_ylabel("Shaft speed [% rated]"); ax[0].set_title("(a) Speed after full load rejection"); ax[0].legend(loc="center right")
    ax[1].set_ylabel("Heat release [pu]"); ax[1].set_title("(b) Fuel energy flow"); ax[2].set_ylabel("Manifold pressure [bar]"); ax[2].set_title("(c) Fuel-manifold pressure")
    for a in ax: a.set_xlabel("Time [s]"); a.axvline(10, color="#9ca3af", lw=0.8, ls=":")
    METRICS["load_rejection"] = out
    foot(fig, "0.8 pu -> 0 load at t = 10 s (breaker open), same retrofit hardware for both fuels."); fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(f"{FIG}/fig09_load_rejection.png"); plt.close(fig)


def fig10_fuel_switch():
    ramp = lambda t: float(np.clip((t - 20) / 120.0, 0, 1))
    step = lambda t: 0.0 if t < 20 else 1.0
    VAR = {"nocomp": dict(compensate=False), "analyzer": dict(compensate=True, analyzer_delay=6.0, analyzer_lag=3.0),
           "ratio": dict(compensate=True, analyzer_delay=0.0, analyzer_lag=0.3)}
    cc = {"nocomp": "#dc2626", "analyzer": "#f59e0b", "ratio": "#059669"}
    ll = {"nocomp": "ECU with natural-gas calibration (no compensation)", "analyzer": "compensated, composition from analyzer (6 s delay + 3 s lag)",
          "ratio": "compensated, composition from blend-ratio flow meters (0.3 s lag)"}
    res = {}
    for name, hfun, tend in (("ramp", ramp, 180), ("step", step, 80)):
        for v, kw in VAR.items():
            df = P.simulate(P.Config(arch="single", t_end=tend, h2=hfun, Pe=lambda t: 0.7, Ts=0.05, **kw)); res[(name, v)] = df; save(df, f"sim_fuel_switch_{name}_{v}")
    fig, ax = plt.subplots(2, 4, figsize=(15.5, 6.4))
    for r, name in enumerate(("ramp", "step")):
        for v in VAR:
            df = res[(name, v)]; t = df.t
            ax[r, 0].plot(t, df.N * 100, color=cc[v], label=ll[v], lw=1.2)
            ax[r, 1].plot(t, df.w_c, color=cc[v], lw=1.2); ax[r, 1].plot(t, df.w_dem, color=cc[v], lw=0.9, ls=":")
            ax[r, 2].plot(t, df.x_v, color=cc[v], lw=1.2)
            ax[r, 3].plot(t, np.where(df.phi_act > 0, df.phi_act, np.nan), color=cc[v], lw=1.1)
        ax[r, 0].ticklabel_format(useOffset=False); ax[r, 0].set_ylabel("Speed [% rated]"); ax[r, 1].set_ylabel("Energy flow [pu]"); ax[r, 2].set_ylabel("Valve position [-]"); ax[r, 3].set_ylabel("Actual main-stage $\\phi$")
        ax[r, 3].axhspan(0.45, 0.55, color="#fde68a", alpha=0.4, lw=0); ax[r, 3].set_ylim(0.3, 0.75)
        for a in ax[r]: a.set_xlabel("Time [s]")
        ttl = (["(a) Speed", "(b) Energy: delivered (solid) vs ECU demand (dotted)", "(c) Metering-valve position", "(d) Actual primary-zone $\\phi$"] if r == 0 else
               ["(e) Speed", "(f) Energy: delivered (solid) vs ECU demand (dotted)", "(g) Metering-valve position", "(h) Actual primary-zone $\\phi$"])
        for a, tt in zip(ax[r], ttl): a.set_title(tt, fontsize=9)
    ax[0, 0].legend(loc="upper left", fontsize=6.3)
    fig.suptitle("Fuel switching at 0.7 pu load: top - 0 -> 100 % H$_2$ ramp over 120 s; bottom - instantaneous composition step at t = 20 s (stress case)", y=0.995, fontsize=10)
    m = {}
    for (name, v), df in res.items():
        d = df[df.t > 20]; dt = np.diff(d.t.values, prepend=d.t.values[0])
        m[f"{name}_{v}"] = dict(N_dev_max_pct=float((df.N - 1).abs().max() * 100), Tx_max_K=float(df.Tx.max()),
                                phi_act_max=float(df.phi_act.max()), phi_act_min=float(df[df.phi_act > 0].phi_act.min()),
                                t_phi_above_0p55_s=float(dt[(d.phi_act.values > 0.55)].sum()), valve_x_max=float(df.x_v.max()),
                                final_demand_over_delivered=float(df.w_dem.iloc[-1] / df.w_c.iloc[-1]))
    METRICS["fuel_switch"] = m
    foot(fig, "Staging uses the ECU's composition estimate; 'phi' is the ACTUAL value computed from delivered flow."); fig.tight_layout(rect=(0, 0.02, 1, 0.98)); fig.savefig(f"{FIG}/fig10_fuel_switching.png"); plt.close(fig)


def fig11_spools():
    fig, ax = plt.subplots(1, 4, figsize=(15, 3.8)); out = {}
    df = P.simulate(P.Config(arch="single", t_end=60, Pe=lambda t: 0.5 if t < 20 else 0.8)); save(df, "sim_arch_single")
    ax[0].plot(df.t, df.N * 100, color="#111827"); ax[0].set_title("(a) 1 spool: load step 0.5->0.8 pu"); ax[0].set_ylabel("Controlled speed [%]")
    out["single"] = dict(N_min_pct=float(df.N.min() * 100))
    ref = lambda t: 0.85 if t < 20 else 0.95
    for arch, lab, col, kw in (("two", "gas generator + power turbine (2 shafts)", "#2563eb", dict(gains=CT.Gains(Kp=2.0, Ti=4.0))), ("three", "LP + HP spools + power turbine (3 shafts)", "#dc2626", dict(tau_lp=1.5, gains=CT.Gains(Kp=1.5, Ti=4.0)))):
        d = P.simulate(P.Config(arch=arch, t_end=70, N_ref=ref, **kw)); save(d, f"sim_arch_{arch}")
        ax[1].plot(d.t, d.N * 100, color=col, label=lab); ax[2].plot(d.t, d.Ng * 100, color=col); ax[3].plot(d.t, d.w_dem, color=col)
        e = d[d.t > 20]; ov = (e.N.max() - 0.95) / 0.10 * 100
        t90 = e[e.N >= 0.85 + 0.9 * 0.10].t.min() - 20
        out[arch] = dict(overshoot_pct_of_step=float(max(ov, 0)), t90_s=float(t90), Ng_max_pct=float(d.Ng.max() * 100), Tx_max_K=float(d.Tx.max()))
    ax[1].plot([0, 70], [85, 85], alpha=0); ax[1].step([0, 20, 70], [85, 95, 95], color="#9ca3af", where="post", ls="--", label="reference")
    ax[1].set_title("(b) Mech. drive: PT speed ref 0.85->0.95"); ax[1].set_ylabel("Power-turbine speed [%]"); ax[1].legend(fontsize=6.5, loc="lower right")
    ax[2].set_title("(c) Gas-generator speed (limiter 101 %)"); ax[2].set_ylabel("GG speed [%]"); ax[3].set_title("(d) Fuel energy demand"); ax[3].set_ylabel("pu")
    for a in ax: a.set_xlabel("Time [s]")
    METRICS["spool_architectures"] = out
    foot(fig, "Governor gains tuned per architecture (1 spool: Kp 20; 2 shafts: Kp 2; 3 shafts: Kp 1.5). Multi-spool dynamics are lumped lag chains (assumed constants)."); fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(f"{FIG}/fig11_spool_architectures.png"); plt.close(fig)


def fig12_scan_time():
    Tss = [0.01, 0.02, 0.05, 0.1, 0.25, 0.5, 1.0]; rows = []
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.8)); cm = plt.cm.viridis(np.linspace(0, 0.9, len(Tss)))
    for Ts, c in zip(Tss, cm):
        df = P.simulate(P.Config(arch="single", t_end=60, Ts=Ts, Pe=lambda t: 0.5 if t < 20 else 0.8))
        if Ts in (0.01, 0.1, 0.5, 1.0): ax[0].plot(df.t, df.N * 100, color=c, label=f"{Ts*1e3:.0f} ms")
        late = df[df.t > 40]
        iae = float(np.trapezoid(abs(df.N - 1), df.t))
        rows.append(dict(Ts_ms=Ts * 1e3, N_min_pct=df.N.min() * 100, N_max_pct=df.N.max() * 100, IAE=iae, ripple_pct=(late.N.max() - late.N.min()) * 100))
    d = pd.DataFrame(rows); d.to_csv(f"{DATA}/scan_time_sensitivity.csv", index=False)
    ax[0].set_ylabel("Speed [% rated]"); ax[0].set_title("(a) Load step vs controller scan time"); ax[0].legend(title="scan time", fontsize=7)
    dp = d[d.Ts_ms <= 500]; ax[0].set_ylim(91, 100.5)
    ax[1].semilogx(dp.Ts_ms, dp.N_min_pct, "o-", color="#dc2626"); ax[1].set_ylabel("Minimum speed after step [%]"); ax[1].set_title("(b) Speed dip")
    ax[2].semilogx(dp.Ts_ms, dp.IAE, "o-", color="#111827"); ax[2].set_ylabel("IAE of speed error [pu$\\cdot$s]"); ax[2].set_title("(c) Integrated speed error")
    for a in ax[1:]: a.set_xlabel("Scan time [ms]")
    ax[0].set_xlabel("Time [s]")
    METRICS["scan_time"] = d.round(4).to_dict(orient="records")
    foot(fig, "Same gains for all scan times (tuned at 20 ms). At 1000 ms scan the loop is unstable in this model (speed collapses) - omitted from plots, kept in CSV."); fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(f"{FIG}/fig12_scan_time_sensitivity.png"); plt.close(fig)


def fig13_startup():
    out = {}
    df = ST.run(h2=1.0); df.iloc[::2].to_csv(f"{DATA}/sim_startup_h2.csv", index=False)
    fig, ax = plt.subplots(4, 1, figsize=(10, 9), sharex=True)
    cols = ["#e5e7eb", "#dbeafe", "#bfdbfe", "#fde68a", "#fed7aa", "#bbf7d0", "#a7f3d0", "#ddd6fe"]
    for a in ax:
        for i, nm in enumerate(ST.STATES):
            s = df[df.state == i]
            if len(s): a.axvspan(s.t.min(), s.t.max(), color=cols[i], alpha=0.55, lw=0)
    SHORT = ["READY", "CRANK", "PURGE", "IGN", "WARM", "ACCEL", "IDLE", "SYNC / LOAD"]
    for i, nm in enumerate(SHORT):
        s = df[df.state == i]
        if len(s): ax[0].text((s.t.min() + s.t.max()) / 2, 1.07, nm, rotation=0, fontsize=6.5, ha="center", va="bottom", clip_on=False)
    ax[0].plot(df.t, df.N * 100, color="#111827"); ax[0].set_ylabel("Speed [% rated]"); ax[0].set_ylim(0, 105)
    ax[1].plot(df.t, df.w_pilot, color="#2563eb", label="pilot (spark-lit chamber)"); ax[1].plot(df.t, df.w_main, color="#dc2626", label="main premix stages")
    ax[1].set_ylabel("Fuel energy flow [pu]"); ax[1].legend(loc="upper left")
    ax[2].step(df.t, df.n_stage, where="post", color="#6b7280"); ax[2].set_ylabel("Active main stages")
    b = ax[2].twinx(); b.plot(df.t, np.where(df.phi_main > 0, df.phi_main, np.nan), color="#dc2626"); b.set_ylabel("Main-stage $\\phi$", color="#dc2626"); b.set_ylim(0.3, 0.65); b.grid(False); b.spines["right"].set_visible(True)
    ax[3].plot(df.t, df.Pe, color="#059669", label="electrical load [pu]"); ax[3].plot(df.t, df.purge_volumes / 5.0, color="#9ca3af", label="purge progress (1.0 = 5 volume changes)")
    ax[3].plot(df.t, df.spark, color="#f59e0b", label="spark"); ax[3].legend(loc="center left", fontsize=7); ax[3].set_ylabel("-"); ax[3].set_xlabel("Time [s]")
    st = df.groupby("state_name").t.agg(["min", "max"]); tt = {k: [float(v["min"]), float(v["max"])] for k, v in st.iterrows()}
    out = dict(state_times_s=tt, purge_time_s=float(tt["PURGE"][1] - tt["PURGE"][0]), time_to_idle_s=float(tt["IDLE (FSNL)"][0]), time_to_0p7_load_s=float(df[df.Pe >= 0.699].t.min()))
    METRICS["startup"] = out
    fig.suptitle("Indicative H$_2$ start-up sequence: purge crank -> spark pilot (minimum fuel) -> accelerate -> idle -> synchronise -> load", y=0.995, fontsize=10)
    foot(fig, "Purge >= 5 volume changes of an assumed 15 m$^3$ gas path before any fuel."); fig.tight_layout(rect=(0, 0.02, 1, 0.97), h_pad=0.6); fig.savefig(f"{FIG}/fig13_startup_sequence.png"); plt.close(fig)


def fig14_flameout():
    LFL = {1.0: 4.0, 0.0: 5.0}
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.9)); rows = []
    for h in (0.0, 1.0):
        for tv in (0.1, 0.5, 1.5):
            cfg = P.Config(arch="single", t_end=30, Ts=0.02, h2=(lambda t, h=h: h), Pe=lambda t: 0.7, flame_out_at=15.0, tau_valve=tv)
            df = P.simulate(cfg); d = df[df.t >= 15].copy()
            nf = d.m_main / d.MW; na = 20.0 * d.air_pu / 28.85
            d["x_fuel_pct"] = 100 * nf / (nf + na)
            dtt = np.diff(d.t.values, prepend=d.t.values[0])
            m_unb = float((d.m_main.values * dtt).sum())
            t_above = float(dtt[d.x_fuel_pct.values > LFL[h]].sum())
            rows.append(dict(h2_vol=h, tau_valve_s=tv, peak_exhaust_fuel_pct=float(d.x_fuel_pct.max()), LFL_pct=LFL[h], time_above_LFL_s=t_above, unburnt_fuel_kg=m_unb,
                             t_trip_s=float(df.attrs["t_trip"] - 15) if df.attrs["t_trip"] else None, trip_reason=df.attrs["trip_reason"]))
            if tv == 0.5:
                ax[0].plot(d.t - 15, d.x_fuel_pct, color=COL[h], label=LAB[h]); ax[1].plot(d.t - 15, d.P_m_bar, color=COL[h])
                save(df, f"sim_flameout_h2_{int(h*100)}_tv0p5")
    d = pd.DataFrame(rows); d.to_csv(f"{DATA}/flameout_summary.csv", index=False)
    ax[0].axhline(4.0, color=COL[1.0], ls="--", lw=0.9); ax[0].text(8, 4.15, "H$_2$ LFL 4 %", color=COL[1.0], fontsize=7.5)
    ax[0].axhline(5.0, color=COL[0.0], ls="--", lw=0.9); ax[0].text(8, 5.15, "CH$_4$ LFL 5 %", color=COL[0.0], fontsize=7.5)
    ax[0].set_xlim(-0.5, 12); ax[0].set_ylabel("Unburnt fuel in exhaust stream [mol %]"); ax[0].set_title("(a) After flame loss (valve closes in 0.5 s)"); ax[0].legend(loc="upper right", fontsize=7)
    ax[1].text(1.0, 11.2, "inventory keeps discharging through the injectors\nunless a vent / bleed valve opens", fontsize=7, color="#6b7280"); ax[1].set_xlim(-0.5, 12); ax[1].set_ylabel("Manifold pressure [bar]"); ax[1].set_title("(b) Trapped inventory venting through injectors")
    for h in (0.0, 1.0):
        x = d[d.h2_vol == h]; ax[2].plot(x.tau_valve_s, x.unburnt_fuel_kg * 1000, "o-", color=COL[h])
    ax[2].set_xlabel("Isolation-valve closing time [s]"); ax[2].set_ylabel("Unburnt fuel released [g]"); ax[2].set_title("(c) Unburnt release vs valve speed")
    ax[0].set_xlabel("Time after flame loss [s]"); ax[1].set_xlabel("Time after flame loss [s]")
    METRICS["flameout"] = d.round(4).to_dict(orient="records")
    foot(fig, "Estimate of mixture entering the exhaust duct (fuel + rundown air); excludes duct dilution/volume effects - purge sizing is a HAZOP item."); fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(f"{FIG}/fig14_flame_loss_isolation.png"); plt.close(fig)


if __name__ == "__main__":
    which = sys.argv[1:] or ["fig08_load_step", "fig09_load_rejection", "fig10_fuel_switch", "fig11_spools", "fig12_scan_time", "fig13_startup", "fig14_flameout"]
    for n in which:
        print("running", n, flush=True); globals()[n]()
        json.dump(METRICS, open(f"{DATA}/metrics_{n}.json", "w"), indent=1, default=float)
    print("done", flush=True)
