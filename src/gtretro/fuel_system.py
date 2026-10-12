"""Gas fuel-system hydraulics: compressible orifice flow, valve characteristic, manifold dynamics."""
import numpy as np


def psi(r, gamma):
    """Compressible-orifice flow function for pressure ratio r = P_dn/P_up (choked below critical)."""
    rc = (2.0 / (gamma + 1.0)) ** (gamma / (gamma - 1.0))
    if r <= rc:
        return np.sqrt(gamma) * (2.0 / (gamma + 1.0)) ** ((gamma + 1.0) / (2.0 * (gamma - 1.0)))
    r = min(r, 1.0)
    return np.sqrt(2.0 * gamma / (gamma - 1.0) * (r ** (2.0 / gamma) - r ** ((gamma + 1.0) / gamma)))


def mass_flow(A_eff, P_up, P_dn, T, R, gamma):
    """Mass flow [kg/s] through effective area A_eff [m2] (Cd*A)."""
    if A_eff <= 0.0 or P_up <= P_dn:
        return 0.0
    return A_eff * P_up * psi(P_dn / P_up, gamma) / np.sqrt(R * T)


def area_for_flow(m, P_up, P_dn, T, R, gamma):
    return m * np.sqrt(R * T) / (P_up * psi(P_dn / P_up, gamma))


def valve_area(x, A_max, rangeability=50.0):
    """Equal-percentage inherent characteristic, zero at x=0, A_max at x=1."""
    x = np.clip(x, 0.0, 1.0)
    return A_max * (rangeability ** (x - 1.0) - 1.0 / rangeability) / (1.0 - 1.0 / rangeability)


def valve_pos_for_area(A, A_max, rangeability=50.0):
    f = np.clip(A / A_max, 0.0, 1.0)
    return float(np.clip(1.0 + np.log(f * (1.0 - 1.0 / rangeability) + 1.0 / rangeability) / np.log(rangeability), 0.0, 1.0))


def line_velocity(m, P, T, R, D):
    """Bulk velocity [m/s] in a pipe of internal diameter D."""
    rho = P / (R * T)
    return m / (rho * np.pi * D ** 2 / 4.0)
