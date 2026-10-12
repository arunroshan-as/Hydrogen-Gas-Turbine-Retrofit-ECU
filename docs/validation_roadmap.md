# Validation roadmap (aligned with the concept note, Table 12)

| Phase | Scope | What exists in this repo | What is still needed |
|---|---|---|---|
| P0 Platform baseline | select representative turbine, baseline model | generic reference platform, Brayton model | real platform data, OEM interface, controller access |
| P1 Fuel characterisation | H2 + proprietary fuel properties | H2-CH4 surrogate chemistry | measured properties under NDA |
| P2 Injector / nozzle | candidate concepts, mixing, dP | staging abstraction, dP bookkeeping | CFD, geometry |
| P3 Combustor CFD | reacting flow, thermal | none (1-D wall estimate only) | CFD with validated kinetics |
| P4 Small-scale rig | stability, flashback margin, emissions | chemistry indicators only | rig data |
| P5 Prototype combustor | component tests | - | hardware |
| P6 Integrated fuel-system test | fuel train, controls, safety chain | ECU logic, PLC reference code, trip studies | **hardware-in-the-loop** on the S7-410 with this plant model, then a real fuel train |
| P7-P9 | turbine and industrial demonstration | - | - |

Suggested next steps for the control work: (1) HIL with the S7-410 and the Python plant, (2) real valve and sensor dynamics, (3) replace lumped multi-spool lags with a map-based model once a platform is chosen, (4) rate-shaping of the composition feed-forward (fig10 step case), (5) FMEA / HAZOP-driven trip and purge logic.
