"""Fast interpolated fuel property table for the dynamic models (built once from Cantera)."""
import functools
import numpy as np
import cantera as ct
from . import fuels as F

_GRID = np.linspace(0.0, 1.0, 21)


@functools.lru_cache(maxsize=1)
def _table():
    rows = []
    for h in _GRID:
        g = ct.Solution(F.MECH)
        g.TPX = 300.0, 101325.0, F.fuel_X(h)
        rows.append([F.lhv_mass(h), 8314.462 / g.mean_molecular_weight, g.cp_mass / g.cv_mass,
                     F.stoich_FA(h), F.wobbe(h), g.mean_molecular_weight])
    return np.array(rows)


@functools.lru_cache(maxsize=4096)
def _props_cached(h):
    t = _table()
    v = [np.interp(h, _GRID, t[:, i]) for i in range(t.shape[1])]
    return dict(LHV=v[0], R=v[1], gamma=v[2], FA_st=v[3], WI=v[4], MW=v[5])


def props(h2_vol: float) -> dict:
    return _props_cached(round(float(np.clip(h2_vol, 0, 1)), 3))


def _props_uncached(h2_vol: float) -> dict:
    t = _table()
    h = float(np.clip(h2_vol, 0, 1))
    v = [np.interp(h, _GRID, t[:, i]) for i in range(t.shape[1])]
    return dict(LHV=v[0], R=v[1], gamma=v[2], FA_st=v[3], WI=v[4], MW=v[5])
