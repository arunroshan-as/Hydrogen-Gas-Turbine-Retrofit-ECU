# Safety architecture (conceptual)

Design intent only. It is subject to HAZID / HAZOP, functional-safety assessment (IEC 61508 / 61511 style SIL allocation) and testing. No operating instructions or safety guarantees are given.

```
Detection  ->  Control decision  ->  Fuel isolation  ->  Purge / safe shutdown
```

## Layers
1. **Process control** (S7-410-class PLC): normal control, limiters, soft trip requests.
2. **Independent protection**: hard-wired ESD / safety PLC (F-CPU), voted sensors (2oo3 flame, overspeed, H2 detection), fail-safe valves (spring-return to closed on loss of power or signal).
3. **Mechanical**: relief devices, block-and-bleed valve groups, vent to a safe location, flame arrestors in fuel lines (quench distance of H2 is about 0.55 mm at the combustor condition by a Peclet-number (Pe = 40) estimate, see `results/data/flame_speed.csv`; at line conditions it must be established by test).

## Findings from the simulations that shape the design

* **Pre-start purge.** Start-up holds the crank speed until at least 5 volume changes of an assumed 15 m3 gas path have passed: 22.5 s at 20 % speed (fig13). No fuel is admitted earlier (`tests/test_models.py`).
* **Flame loss with hydrogen** (fig14, 100 % H2, 0.7 pu load): the trip is requested within one scan, but the mixture of unburnt fuel entering the exhaust stream peaks at about **6.5 mol %, above the 4 % lower flammable limit**, for 0.04 s (0.1 s valve) to 0.24 s (1.5 s valve). The methane case peaks at 2.1 %, below its 5 % limit. Faster isolation valves reduce, but do not remove, the excursion.
* **Trapped inventory.** After the isolation valve shuts, the manifold gas keeps discharging through the injectors (manifold still about 5 bar after 12 s). A **vent / bleed valve to a safe location** on the manifold is needed in addition to the block valves; purge air flow and duct volume must be sized in the HAZOP.
* **Load rejection** (fig09): peak speed 104.3 % for both fuels with the isochronous governor, below the 110 % trip.

## Open items
Hazardous-area classification of the skid and enclosure, H2 detector placement and voting, SIL targets, purge-volume proof, fail-safe valve selection and testing intervals, interaction with the OEM protection system.
