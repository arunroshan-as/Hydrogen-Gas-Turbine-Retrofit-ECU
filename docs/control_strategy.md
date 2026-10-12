# Control strategy

Reference implementation: `src/gtretro/control.py`. PLC mirror: `plc/GT_Fuel_Control.scl`.

## 1. Fuel-demand loop

Three PI paths and a minimum selector (standard gas-turbine practice):

| Path | Controlled variable | Notes |
|---|---|---|
| Speed governor | generator speed (single-shaft) or power-turbine speed (two/three-shaft) | isochronous PI, Kp = 20 / 2 / 1.5 (1 / 2 / 3-spool tuning) |
| Exhaust-temperature limiter | measured exhaust temperature vs limit (795 K in the model) | thermocouple lag 2 s in the plant |
| Gas-generator speed limiter | Ng vs 1.01 pu | multi-shaft machines only |

`W_dem = min(governor, temperature limiter, GG limiter)` -> rate limit (up 0.6 pu/s, down 1.0 pu/s) -> floor 0.15 pu (flame retention) -> ceiling 1.10 pu.
Losing paths are clamped to `W_dem + 0.12` (anti-windup) and the winning path holds its integrator while saturated.

> **Bug found during development (kept in the history on purpose):** a first version made the losing paths *track* `W_dem` exactly. Because the minimum selector then always picked the tracked path, the demand could never increase and a 0.3 pu load step ended in a speed collapse. Head-room clamping fixed it. Any PLC re-implementation should be tested for this behaviour.

## 2. Fuel-property compensation (Wobbe index)

At fixed valve position and pressures, the **energy** flow scales with the Wobbe index, not with volume flow. For H2 vs CH4 the lower Wobbe index ratio is about 0.85, and for H2/CH4 blends it is **non-monotonic with a minimum near 80 - 90 vol% H2** (about 38.5 MJ/Nm3 vs 40.8 for pure H2, 48.0 for CH4). The ECU therefore maps *energy* demand to valve position through the inverse compressible-orifice relation, using the current fuel's LHV, R and gamma (`FuelMapper`, `FC_FuelToValve`).
Composition source options studied (fig10):

1. no compensation (natural-gas calibration),
2. analyzer (6 s transport delay + 3 s lag),
3. blend-ratio flow meters (0.3 s lag). Since the retrofit controls the blend itself, the composition is known from the flow ratio, and the analyzer is better used as a cross-check.

## 3. Pilot / main staging

* Pilot-only (start, idle): all fuel to the spark-lit pilot chamber.
* Loaded: pilot 10 % -> 4 % of rated heat input, remainder to main premix stages.
* Six unequal stages (cumulative air fractions 0.20, 0.275, 0.38, 0.52, 0.72, 1.00). The ECU lights the **fewest stages that keep primary-zone phi <= 0.55**. The resulting phi is a sawtooth between about 0.40 and 0.55 (fig07); 57 - 66 % of the 30 - 100 % load range lies inside the 0.45 - 0.55 target band.
* The phi calculation uses the composition estimate, so a wrong estimate silently moves the real phi (fig10, no-compensation case: real phi drifts to 0.33).

## 4. Protection (software layer)

Overspeed (> 1.10 pu), exhaust temperature (> 840 K), flame loss, hydrogen leak, fuel-pressure window. On trip: fuel valves closed, pilot cut, generator breaker opened. This is **not** the safety layer; see `safety_architecture.md`.

## 5. Tuning status

Gains are tuned by hand on the reduced-order plant. They are starting values for hardware-in-the-loop work, not commissioning values.
