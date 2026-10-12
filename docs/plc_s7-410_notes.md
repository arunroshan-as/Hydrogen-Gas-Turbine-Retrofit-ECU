# S7-410 (SIMATIC S7-400H class) implementation notes

Status: **preliminary**. A Siemens SIMATIC S7-410 or similar PLC is the intended controller; the logic here has been developed on the Python model only.

## Task structure (proposal)
| OB | Cycle | Content |
|---|---|---|
| OB35 | 20 ms | speed / temperature governor (`FB_GT_FuelDemand`), valve position loop, stage-valve sequencing |
| OB32 | 100 ms | fuel-mapper (`FC_FuelToValve`), staging selection, composition estimate, trip logic |
| OB1 | background | sequencer (start / stop), HMI, diagnostics |
| OB121/122 | event | programming / I-O access errors -> fail-safe |

## Why 20 ms for the governor (fig12)
Same gains, 7 scan times, 0.5 -> 0.8 pu load step:

| Scan time | min speed after step | IAE [pu s] |
|---|---|---|
| 10 ms | 96.3 % | 0.29 |
| 20 ms | 96.2 % | 0.30 |
| 50 ms | 96.0 % | 0.32 |
| 100 ms | 95.0 % | 0.45 |
| 250 ms | 94.7 % | 0.49 |
| 500 ms | 92.6 % | 0.84 |
| 1000 ms | unstable (speed collapses) | - |

So 20 - 50 ms costs almost nothing; 100 ms or slower visibly degrades the response in this model. Real margin depends on the real plant and I/O latency.

## Indicative I/O list
| Type | Signal |
|---|---|
| AI | shaft speed (2 or 3 redundant pickups), gas-generator speed, exhaust thermocouples (mid-value select), compressor discharge pressure, fuel supply pressure, manifold pressure per circuit, fuel temperature, valve feedback, vibration |
| DI | flame detectors (2oo3), H2 detectors, ESD status, valve proof-of-closure, breaker status |
| AO / DO | metering valve (pilot, main), stage valves, vent/bleed valve, purge valve, spark exciter, starter, trip relays |
| Comms | PROFINET / PROFIBUS to valves and analyzers, Modbus gateway for gas chromatograph, OEM controller interface (platform-dependent) |

## Porting checklist
1. Re-implement `plc/GT_Fuel_Control.scl` in STEP 7 / TIA and compile; replace pragmas and block numbers.
2. Rebuild the anti-windup logic and run the load-step and trip tests from `tests/` as acceptance cases (hardware-in-the-loop with the Python plant or a PLCSIM-based plant).
3. Add sensor validation, voting, rate-of-change checks and bumpless transfer.
4. Keep the safety functions in an F-CPU or hard-wired chain, not in the standard program.
