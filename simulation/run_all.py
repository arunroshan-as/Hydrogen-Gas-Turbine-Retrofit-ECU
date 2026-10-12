"""Reproduce every figure and data file in results/ (about 10-15 min on one CPU core).
   python simulation/run_all.py            # everything
   python simulation/run_all.py --fast     # skip the slow flame-speed chemistry (re-use cached CSVs)
"""
import os, sys, json, glob, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); DATA = os.path.join(HERE, "..", "results", "data")


def run(*args):
    print(">>", *args, flush=True); subprocess.check_call([sys.executable, *args], cwd=HERE)


if __name__ == "__main__":
    fast = "--fast" in sys.argv
    if not (fast and os.path.exists(os.path.join(DATA, "flame_speed.csv"))):
        run("fuel_study.py")
    run("static_figs.py")
    run("dynamic_figs.py")
    m = {}
    for f in sorted(glob.glob(os.path.join(DATA, "metrics_fig*.json"))):
        m.update(json.load(open(f)))
    json.dump(m, open(os.path.join(DATA, "metrics_all.json"), "w"), indent=1)
    print("all done")
