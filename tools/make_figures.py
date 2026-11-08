"""Generate the paper figures from the result files.

Every number is read from ``results/*.json`` or computed from the package; nothing
is transcribed by hand.  Output: vector PDF plus a 300 dpi PNG preview per figure.

    python tools/make_figures.py
"""

from __future__ import annotations

import json
import math
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dbound import bound  # noqa: E402

RESULTS = ROOT / "results"
FIGS = ROOT / "figures"
FIGS.mkdir(exist_ok=True)

plt.rcParams.update({
    "font.size": 8,
    "axes.labelsize": 8,
    "axes.titlesize": 8,
    "legend.fontsize": 7,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02,
})
SINGLE = 3.5
DOUBLE = 7.1


def save(fig, name: str) -> None:
    fig.savefig(FIGS / f"{name}.pdf")
    fig.savefig(FIGS / f"{name}.png", dpi=300)
    plt.close(fig)
    print(f"  wrote figures/{name}.pdf and .png")


def fig1_energy() -> None:
    xs, es = bound.energy_curve()
    dp = np.sqrt(es)
    fig, ax = plt.subplots(figsize=(SINGLE, 2.6))

    ax.loglog(xs, dp, "o-", ms=2.2, lw=1.0, color="#1f4e79", label=r"$\sqrt{E(a/L)}$")
    # asymptote guides, anchored on the curve
    anchor_small = xs[0]
    a3 = dp[0] * (xs / anchor_small) ** 3
    ax.loglog(xs, a3, "--", lw=0.8, color="#c00000")
    big = xs > 12
    c = dp[big][0] / xs[big][0] ** 1.5
    ax.loglog(xs, c * xs ** 1.5, ":", lw=0.9, color="#548235")

    ax.axvline(1.0, color="0.6", lw=0.6, ls="-")
    ax.text(1.05, dp.min() * 1.4, "voxel size", rotation=90, fontsize=6, color="0.4")
    ax.text(0.30, a3[1] * 2.2, r"$\propto x^{3}$", fontsize=7, color="#c00000")
    ax.text(13.0, c * 13.0 ** 1.5 * 3.2, r"$\propto x^{3/2}$", fontsize=7, color="#548235")
    ax.set_xlabel(r"flaw size / PSF width,  $x = a/L$")
    ax.set_ylabel(r"deflection factor  $\sqrt{E}$")
    ax.set_xlim(0.2, 24)
    ax.legend(frameon=False, loc="upper left")
    save(fig, "fig1_energy")


def fig2_pod() -> None:
    xs, es = bound.energy_curve()
    sq = np.sqrt(es)
    z = bound.z_from_p(0.99)
    fig, ax = plt.subplots(figsize=(SINGLE, 2.6))
    for ratio, colour in zip((1, 2, 5, 10), ("#9dc3e6", "#5b9bd5", "#1f4e79", "#0b2e4f")):
        pod = np.array([bound.ndtr(ratio * s - z) for s in sq])
        ax.semilogx(xs, pod, lw=1.2, color=colour, label=rf"$\Delta I/\sigma={ratio}$")
    ax.axhline(0.9, color="0.4", lw=0.7, ls="--")
    ax.text(4.6, 0.915, "POD = 0.9", fontsize=6, color="0.35")
    ax.set_xlabel(r"$x = a/L$")
    ax.set_ylabel(r"POD bound at $\alpha = 0.01$")
    ax.set_ylim(-0.02, 1.02)
    ax.set_xlim(0.2, 24)
    ax.legend(frameon=False, loc="upper left")
    save(fig, "fig2_pod")


def fig3_kappa() -> None:
    meas = json.loads((RESULTS / "measure_vol_gd.json").read_text(encoding="utf-8"))
    cross = json.loads((RESULTS / "cross_group.json").read_text(encoding="utf-8"))

    x = np.array([r["x"] for r in meas["kappa"]])
    k = np.array([r["kappa"] for r in meas["kappa"]])
    lo = np.array([r["kappa_lo"] for r in meas["kappa"]])
    hi = np.array([r["kappa_hi"] for r in meas["kappa"]])

    fig, ax = plt.subplots(figsize=(SINGLE, 2.7))
    ax.errorbar(x, k, yerr=[k - lo, hi - k], fmt="o-", ms=2.6, lw=1.0,
                capsize=2, color="#1f4e79", label="GD (212 slices)")
    for name, marker, colour in (("vol_g1", "s", "#c00000"), ("vol_g2", "^", "#548235")):
        rows = cross[name]["kappa"]
        xg = np.array([r["x"] for r in rows])
        kg = np.array([r["kappa"] for r in rows])
        ax.plot(xg, kg, marker + "--", ms=3.2, lw=0.8, color=colour,
                label=name.replace("vol_", "").upper())

    # local slope of the measured curve above x = 4
    sel = (x > 4) & (x > 0)
    if sel.sum() >= 2:
        p = np.polyfit(np.log(x[sel]), np.log(k[sel]), 1)[0]
        ax.text(0.04, 0.80, rf"GD slope above $x=4$: $x^{{{p:.2f}}}$",
                transform=ax.transAxes, fontsize=6.5, color="0.3")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(r"$x = a/L$")
    ax.set_ylabel(r"clutter inflation $\kappa$")
    ax.legend(frameon=False, loc="lower right")
    save(fig, "fig3_kappa")


def fig4_detectors() -> None:
    comp = json.loads((RESULTS / "comparison.json").read_text(encoding="utf-8"))
    abl = json.loads((RESULTS / "ablation.json").read_text(encoding="utf-8"))

    fig, axes = plt.subplots(1, 3, figsize=(DOUBLE, 2.2),
                             gridspec_kw={"width_ratios": [1.1, 1.0, 1.0]})

    ax = axes[0]
    labels = ["oracle\nmatched filter", "searched\nmatched filter", "template-free\npeak"]
    vals = [comp["pod"]["mf"], comp["pod"]["mm"], comp["pod"]["pk"]]
    bars = ax.bar(range(3), vals, color=["#1f4e79", "#5b9bd5", "#9dc3e6"], width=0.62)
    ax.axhline(1.0, color="#c00000", lw=0.9, ls="--")
    ax.text(2.3, 0.94, "white-noise bound", fontsize=6, color="#c00000", ha="right")
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.02, f"{v:.3f}",
                ha="center", fontsize=6.5)
    ax.set_xticks(range(3))
    ax.set_xticklabels(labels, fontsize=6.2)
    ax.set_ylabel(r"POD at $\alpha = 0.01$")
    ax.set_ylim(0, 1.12)
    ax.set_title("(a) detectors, real data", fontsize=7.5)

    ax = axes[1]
    kinds = ["dc", "zero_mean", "annular"]
    kv = [abl["templates"][k]["kappa"] for k in kinds]
    ax.bar(range(3), kv, color=["#c00000", "#ed7d31", "#548235"], width=0.6)
    for i, v in enumerate(kv):
        ax.text(i, v + 2, f"{v:.0f}", ha="center", fontsize=6.5)
    ax.set_xticks(range(3))
    ax.set_xticklabels(["raw\n(no mean)", "global\nzero-mean", "annular\n(used)"], fontsize=6.2)
    ax.set_ylabel(r"$\kappa$ at $a = 8$ voxels")
    ax.set_title("(b) template construction", fontsize=7.5)

    ax = axes[2]
    sig = abl["sigmas"]
    names = ["second_diff_mad", "percentile_99", "plain_std"]
    sv = [sig[n] for n in names]
    ax.bar(range(3), sv, color=["#548235", "#ed7d31", "#c00000"], width=0.6)
    for i, v in enumerate(sv):
        ax.text(i, v + 12, f"{v:.0f}", ha="center", fontsize=6.5)
    ax.set_xticks(range(3))
    ax.set_xticklabels(["2nd-diff\nMAD (used)", "99th\npercentile", "plain\nstd"], fontsize=6.2)
    ax.set_ylabel(r"noise estimate $\sigma$")
    ax.set_title("(c) noise estimator", fontsize=7.5)

    fig.tight_layout(w_pad=1.2)
    save(fig, "fig4_detectors_ablation")


def main() -> None:
    print("figures:")
    fig1_energy()
    fig2_pod()
    fig3_kappa()
    fig4_detectors()


if __name__ == "__main__":
    main()

