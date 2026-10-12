"""Open-cycle Brayton model with real-gas mixture properties (Cantera) for a reference platform.

Reference platforms are GENERIC and assumed (not any OEM machine) - platform selection is
gate G1 of the HERRSCHER roadmap. Combustion is solved at overall (diluted) turbine inlet
temperature; primary-zone phi is handled in combustor.py.
"""
from dataclasses import dataclass, asdict
import numpy as np
import cantera as ct
from scipy.optimize import brentq
from . import fuels as F

R_UNIV = 8314.462


@dataclass
class Platform:
    name: str = "GT-A (single-shaft, generator drive)"
    PR: float = 12.0            # overall pressure ratio
    TIT: float = 1300.0         # turbine inlet temperature [K] (overall, after dilution)
    m_air: float = 20.0         # inlet air mass flow at ISO [kg/s]
    eta_c: float = 0.84         # compressor isentropic efficiency (polytropic-equivalent, lumped)
    eta_t: float = 0.88         # turbine isentropic efficiency
    dp_in: float = 0.01
    dp_comb: float = 0.04
    dp_exh: float = 0.01
    eta_mech: float = 0.99
    eta_gen: float = 0.97
    cooling_air: float = 0.0    # fraction of compressor flow bled for hot-section cooling (simple)


def _air(T, P):
    g = ct.Solution(F.MECH); g.TPX = T, P, F.AIR
    return g


def run(plat: Platform, h2_vol: float, T_amb=288.15, P_amb=101325.0, T_fuel=300.0, TIT=None):
    """Return dict of cycle results for a given fuel blend."""
    TIT = plat.TIT if TIT is None else TIT
    m_air = plat.m_air * 288.15 / T_amb                       # fixed-volume-flow machine
    P1 = P_amb * (1 - plat.dp_in)
    g = _air(T_amb, P1); h1, s1 = g.enthalpy_mass, g.entropy_mass
    P2 = P1 * plat.PR
    g.SP = s1, P2; h2s = g.enthalpy_mass
    h2 = h1 + (h2s - h1) / plat.eta_c
    g.HP = h2, P2; T2 = g.T
    P3 = P2 * (1 - plat.dp_comb)

    gf = ct.Solution(F.MECH); gf.TPX = T_fuel, P3, F.fuel_X(h2_vol)
    hf = gf.enthalpy_mass
    ga = _air(T2, P3)
    ga.HP = h2, P3
    ha = ga.enthalpy_mass

    mix = ct.Solution(F.MECH)

    def T_of_fa(fa):
        mix.TPY = T2, P3, (ga.Y + fa * gf.Y) / (1 + fa) if False else _mix_Y(ga, gf, fa)
        mix.HP = (ha + fa * hf) / (1 + fa), P3
        mix.equilibrate("HP")
        return mix.T

    fa = brentq(lambda x: T_of_fa(x) - TIT, 1e-5, 0.09, xtol=1e-9)
    T_of_fa(fa)
    h3, s3 = mix.enthalpy_mass, mix.entropy_mass
    Y3 = mix.Y.copy()
    P4 = P_amb * (1 + plat.dp_exh)
    mix.SP = s3, P4; h4s = mix.enthalpy_mass
    h4 = h3 - plat.eta_t * (h3 - h4s)
    mix.HP = h4, P4; T4 = mix.T

    m_f = fa * m_air * (1 - plat.cooling_air)
    m_gas = m_air * (1 - plat.cooling_air) * (1 + fa) + m_air * plat.cooling_air
    W_t = m_gas * (h3 - h4)
    W_c = m_air * (h2 - h1)
    P_shaft = (W_t - W_c) * plat.eta_mech
    Q = m_f * F.lhv_mass(h2_vol)
    st = F.stoich_FA(h2_vol)
    return dict(h2_vol=h2_vol, T_amb=T_amb, m_air=m_air, T2=T2, P2=P2, P3=P3, TIT=TIT, T4=T4, FA=fa,
                phi_overall=fa / st, m_fuel=m_f, m_gas=m_gas, Q_in=Q, P_shaft=P_shaft,
                P_elec=P_shaft * plat.eta_gen, eta_shaft=P_shaft / Q, eta_elec=P_shaft * plat.eta_gen / Q,
                heat_rate_kJkWh=3600.0 / (P_shaft * plat.eta_gen / Q), W_c=W_c, W_t=W_t,
                x_H2O_exh=float(mix.X[mix.species_index("H2O")]),
                x_O2_exh=float(mix.X[mix.species_index("O2")]), mix_Y3=Y3)


def _mix_Y(ga, gf, fa):
    y = (ga.Y + fa * gf.Y)
    return y / y.sum()
