"""Fuel property utilities (Cantera-based).

The HERRSCHER proprietary fuel is NOT represented here. Variable fuel properties are
represented by an H2-CH4 surrogate family (0-100 vol% H2), the standard way to study
Wobbe-index and flame-speed variation. Replace/extend with characterised properties
only under the confidentiality framework (see docs/ip_and_scope.md).
"""
import numpy as np
import cantera as ct

MECH = "gri30.yaml"
AIR = "O2:0.21, N2:0.79"
M_AIR = 28.85  # kg/kmol (dry air, approx)
_N_SPECIES = ("NO", "NO2", "N2O", "NH3", "HCN", "NCO", "N", "NH", "NH2", "HNO", "NNH", "CN", "HCNN", "HNCO", "HOCN", "NH")


def fuel_X(h2_vol: float) -> str:
    """Mole-fraction string for an H2/CH4 surrogate blend (h2_vol in 0..1)."""
    h2_vol = float(np.clip(h2_vol, 0.0, 1.0))
    return f"H2:{h2_vol:.6f}, CH4:{1.0 - h2_vol:.6f}"


def _fuel_gas(h2_vol, T=288.15, P=ct.one_atm):
    g = ct.Solution(MECH)
    g.TPX = T, P, fuel_X(h2_vol)
    return g


def lhv_mass(h2_vol: float) -> float:
    """Lower heating value [J/kg] (water as vapour)."""
    g = _fuel_gas(h2_vol, 298.15)
    lhv_mol = h2_vol * 241.83e6 + (1 - h2_vol) * 802.34e6  # J/kmol
    return lhv_mol / g.mean_molecular_weight


def lhv_vol_norm(h2_vol: float) -> float:
    """LHV [J/Nm3] at 0 C, 1 atm."""
    g = _fuel_gas(h2_vol, 273.15)
    return lhv_mass(h2_vol) * g.density


def specific_gravity(h2_vol: float) -> float:
    return _fuel_gas(h2_vol).mean_molecular_weight / M_AIR


def wobbe(h2_vol: float) -> float:
    """Lower Wobbe index [MJ/Nm3] = LHV_vol / sqrt(SG)."""
    return lhv_vol_norm(h2_vol) / np.sqrt(specific_gravity(h2_vol)) / 1e6


def stoich_FA(h2_vol: float) -> float:
    """Stoichiometric fuel/air mass ratio."""
    g = ct.Solution(MECH)
    g.set_equivalence_ratio(1.0, fuel_X(h2_vol), AIR)
    Y = g.Y
    yf = sum(Y[g.species_index(s)] for s in ("H2", "CH4"))
    return yf / (1 - yf)


def _mixed_state(h2_vol, phi, T_air, P, T_fuel=300.0):
    ga = ct.Solution(MECH); ga.TPX = T_air, P, AIR
    gf = ct.Solution(MECH); gf.TPX = T_fuel, P, fuel_X(h2_vol)
    q = ct.Quantity(ga, mass=1.0) + ct.Quantity(gf, mass=phi * stoich_FA(h2_vol))
    g = ct.Solution(MECH)
    g.TPY = q.T, P, q.Y
    g.HP = q.enthalpy_mass, P
    return g


def aft(h2_vol, phi, T_air, P, T_fuel=300.0) -> float:
    """Adiabatic (equilibrium, HP) flame temperature [K]."""
    g = _mixed_state(h2_vol, phi, T_air, P, T_fuel)
    g.equilibrate("HP")
    return g.T


def laminar_flame_speed(h2_vol, phi, T, P, width=0.03):
    """Laminar burning velocity [m/s], GRI-Mech 3.0, 1-D freely propagating flame."""
    g = ct.Solution(MECH)
    g.set_equivalence_ratio(phi, fuel_X(h2_vol), AIR)
    g.TP = T, P
    f = ct.FreeFlame(g, width=width)
    f.set_refine_criteria(ratio=4, slope=0.08, curve=0.15)
    f.transport_model = "mixture-averaged"
    f.solve(loglevel=0, auto=True)
    return float(f.velocity[0])


def thermal_diffusivity(h2_vol, phi, T, P):
    g = ct.Solution(MECH)
    g.set_equivalence_ratio(phi, fuel_X(h2_vol), AIR)
    g.TP = T, P
    return g.thermal_conductivity / (g.density * g.cp_mass)


def ignition_delay(h2_vol, phi, T, P, t_max=0.5):
    """Autoignition delay [s] (constant-pressure reactor, max dT/dt)."""
    g = ct.Solution(MECH)
    g.set_equivalence_ratio(phi, fuel_X(h2_vol), AIR)
    g.TP = T, P
    r = ct.IdealGasConstPressureReactor(g)
    net = ct.ReactorNet([r])
    t, Tprev, tprev = 0.0, T, 0.0
    best, t_best = 0.0, np.nan
    while t < t_max:
        t = net.step()
        dTdt = (r.T - Tprev) / max(t - tprev, 1e-15)
        if dTdt > best:
            best, t_best = dTdt, t
        Tprev, tprev = r.T, t
        if r.T > T + 400:
            break
    return t_best if r.T > T + 400 else np.inf


def thermal_no_ppm(h2_vol, phi, T_air, P, t_res, T_fuel=300.0, o2_ref=0.15):
    """Best-case (perfectly premixed) NOx [ppmvd @15% O2] formed in residence time t_res [s].
    Starts from the equilibrium product state with all N-species removed. Indicator only."""
    g = _mixed_state(h2_vol, phi, T_air, P, T_fuel)
    g.equilibrate("HP")
    Y = g.Y.copy()
    for s in _N_SPECIES:
        if s in g.species_names:
            Y[g.species_index(s)] = 0.0
    g.TPY = g.T, P, Y / Y.sum()
    r = ct.IdealGasConstPressureReactor(g)
    net = ct.ReactorNet([r])
    net.advance(t_res)
    X = r.thermo.X
    xno = X[g.species_index("NO")] + X[g.species_index("NO2")]
    xh2o = X[g.species_index("H2O")]
    xo2 = X[g.species_index("O2")]
    xno_dry, xo2_dry = xno / (1 - xh2o), xo2 / (1 - xh2o)
    return xno_dry * 1e6 * (0.21 - o2_ref) / (0.21 - xo2_dry)
