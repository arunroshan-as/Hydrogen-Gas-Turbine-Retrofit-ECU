"""Fast sanity tests (about 1-2 min). Run:  pytest -q"""
import os, sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import numpy as np
import pytest
from gtretro import fuels as F, cycle as C, control as CT, plant as P, startup as ST, fuel_system as FS
from gtretro.props import props


def test_wobbe_ratio_h2_vs_ch4():
    assert 0.80 < F.wobbe(1.0) / F.wobbe(0.0) < 0.90          # ~0.85 classical result


def test_wobbe_is_not_monotonic_in_h2_fraction():
    w = [F.wobbe(h) for h in np.linspace(0, 1, 11)]
    assert min(w) < w[-1]                                      # minimum near 80-90 % H2


def test_h2_volumetric_flow_is_about_3x():
    p = C.Platform(); r0, r1 = C.run(p, 0.0), C.run(p, 1.0)
    ratio = (r1["m_fuel"] * props(1.0)["R"]) / (r0["m_fuel"] * props(0.0)["R"])
    assert 2.8 < ratio < 3.8


def test_cycle_energy_balance_plausible():
    r = C.run(C.Platform(), 1.0)
    assert 4e6 < r["P_elec"] < 7e6 and 0.25 < r["eta_elec"] < 0.40
    assert r["TIT"] == pytest.approx(1300.0)


def test_orifice_flow_inverse():
    p = props(1.0)
    m = FS.mass_flow(1e-4, 30e5, 12e5, 300, p["R"], p["gamma"])
    A = FS.area_for_flow(m, 30e5, 12e5, 300, p["R"], p["gamma"])
    assert A == pytest.approx(1e-4, rel=1e-9)


def test_staging_keeps_phi_below_limit_at_rated():
    for h in (0.0, 0.5, 1.0):
        wp, wm, n, phi = CT.staging(1.0, h)
        assert n == CT.N_STAGES and phi <= CT.PHI_MAX + 1e-9 and wp + wm == pytest.approx(1.0)


def test_staging_pilot_only_at_idle():
    wp, wm, n, phi = CT.staging(0.2, 1.0)
    assert n == 0 and wm == 0 and wp == pytest.approx(0.2)


def test_load_step_recovers():
    df = P.simulate(P.Config(arch="single", t_end=45, Ts=0.05, Pe=lambda t: 0.5 if t < 15 else 0.8))
    assert df.N.min() > 0.93 and abs(df.N.iloc[-1] - 1.0) < 0.002 and not df.tripped.any()
    assert df.Tx.max() < 795.0


def test_flame_loss_trips_and_closes_valve():
    df = P.simulate(P.Config(arch="single", t_end=20, Ts=0.02, Pe=lambda t: 0.7, flame_out_at=10.0))
    assert df.attrs["trip_reason"] == "FLAME_LOSS" and df.x_v.iloc[-1] < 0.01


def test_overspeed_protection_not_reached_on_load_rejection():
    df = P.simulate(P.Config(arch="single", t_end=25, Ts=0.02, Pe=lambda t: 0.8 if t < 10 else 0.0))
    assert df.N.max() < 1.10


def test_startup_sequence_order_and_purge():
    df = ST.run()
    order = list(dict.fromkeys(df.state_name))
    assert order == ST.STATES
    assert df.purge_volumes.max() >= 5.0
    first_fuel = df[df.w > 0].t.min(); purge_done = df[df.state >= 3].t.min()
    assert first_fuel >= purge_done                            # no fuel before purge completes
    assert df.N.iloc[-1] > 0.99
