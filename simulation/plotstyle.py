import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

COL = {0.0: "#6b7280", 0.5: "#2563eb", 1.0: "#dc2626"}
LAB = {0.0: "CH$_4$ (natural-gas surrogate)", 0.5: "50 vol% H$_2$ / 50 vol% CH$_4$", 1.0: "100 vol% H$_2$"}
FOOT = "Preliminary simulation, assumed generic reference platform - not validated against hardware"


def setup():
    plt.rcParams.update({
        "figure.dpi": 130, "savefig.dpi": 160, "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
        "axes.grid": True, "grid.alpha": 0.25, "axes.spines.top": False, "axes.spines.right": False,
        "legend.frameon": False, "legend.fontsize": 8, "figure.facecolor": "white",
    })


def foot(fig, extra=""):
    fig.text(0.01, 0.005, (extra + "  " if extra else "") + FOOT, fontsize=6.5, color="#6b7280", ha="left", va="bottom")
