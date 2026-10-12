# Simulation methodology and validity limits

All models are reduced-order, written for a **generic, assumed reference platform** (platform selection is gate G1 of the roadmap). Nothing is calibrated against measured data.

## Models

| Model | File | Basis | Main assumptions |
|---|---|---|---|
| Fuel properties | `fuels.py`, `props.py` | Cantera 3, GRI-Mech 3.0; LHV from formation enthalpies | H2-CH4 surrogate family; 0 - 100 vol% H2 |
| Flame temperature | `fuels.aft` | equilibrium HP at compressor-discharge T, p | fuel at 300 K; perfectly premixed |
| Laminar flame speed | `fuels.laminar_flame_speed` | 1-D freely propagating flame, mixture-averaged transport | 650 K, 12 bar |
| Autoignition delay | `fuels.ignition_delay` | constant-pressure reactor, max dT/dt | GRI-Mech 3.0 is uncertain for H2 at high p / low T |
| Thermal NOx indicator | `fuels.thermal_no_ppm` | reactor from equilibrium products with N-species removed | **best case**: perfectly premixed, 10 ms; no mixing non-uniformity |
| Brayton cycle | `cycle.py` | real-mixture enthalpies, equilibrium combustion to fixed TIT | PR 12, 20 kg/s, eta_c 0.84, eta_t 0.88, TIT 1300 K, no cooling-air model |
| Fuel hydraulics | `fuel_system.py` | compressible orifice (choked / subsonic), equal-percentage valve | Cd 0.85; supply 30 bar; manifold 10 L |
| Liner wall | `static_figs.fig06_tbc` | 1-D steady conduction, film cooling effectiveness 0.35 | h_g 1800, h_c 2500 W/m2K, k_TBC 1.0, k_metal 22 W/mK |
| Dynamic plant | `plant.py` | Rowen-type normalised model (Rowen 1983) + gas-manifold states + staging | torque = 1.3 (w - 0.23) + 0.5 (1 - N); Tx = 790 - 389 (1 - w) + 306 (1 - N) K; rotor time constant 8 s |
| Two / three-shaft | `plant.py` | lumped lag chains (gas generator tau 1.5 s, LP spool 1 - 1.5 s), process load ~ N^3 | **not** a physical map-based model |
| Start-up | `startup.py` | power-balance rotor model, assumed starter torque | indicative timing only |

## What the dynamic plant captures well enough for control-architecture work
* Interaction of the speed governor, temperature limiter, rate limit and fuel path.
* Fuel-property effects on valve position, manifold dynamics and the **actual** primary-zone phi.
* Sampling-time sensitivity of the PLC loop.
* Qualitative effect of stored fuel inventory after a trip.

## What it does not capture
* Compressor / turbine maps, surge margin, IGV scheduling, bleed valves.
* Combustion dynamics (thermoacoustics), flashback, blow-off, CO burnout, real NOx (needs CFD and rig data).
* Real liner heat flux and radiation (H2O-rich products).
* Valve stiction, positioner dynamics, sensor noise, communication delays.
* Any OEM controller interface.

## Reproduce
```bash
pip install -r requirements.txt
python simulation/run_all.py          # all figures and data (about 10-15 min, 1 core)
PYTHONPATH=src pytest -q              # 11 sanity tests, about 10 s
```
