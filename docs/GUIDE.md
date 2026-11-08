# User guide

Everything the package does, in the order you are likely to need it.

Contents
1. [The idea in five minutes](#1-the-idea-in-five-minutes)
2. [Install](#2-install)
3. [Commands](#3-commands)
4. [Tutorials](#4-tutorials)
5. [Reading the output files](#5-reading-the-output-files)
6. [FAQ and troubleshooting](#6-faq-and-troubleshooting)

---

## 1. The idea in five minutes

### The question

You have an inspection — X-ray CT, an ultrasonic scan, an acoustic sensor — and a
flaw of some size. **Could this inspection see that flaw at all?** Not "does my
network find it", but "is there enough signal in the data for anything to find it".

### Three numbers

| symbol | meaning | where it comes from |
|---|---|---|
| `ΔI/σ` | flaw contrast divided by noise | your scan: grey level of the flaw vs the background noise |
| `a/L` | flaw size divided by resolution | your scan: flaw diameter vs voxel (or PSF) width |
| `N` | independent looks | 1 for a single scan; more for repeats |

No detector can do better than these three numbers allow. That is the whole point:
the answer is fixed before you choose an algorithm.

### The bound

```
d'(a) = (ΔI / σ) · √E(a/L) · √N

POD(a) ≤ Φ( d'(a) − z_{1−α} )
```

`d'` is the deflection — signal-to-noise of the best possible test. `Φ` is the normal
CDF, `α` the false-alarm rate. At `α = 0.01`, `z = 2.33`, so you need `d' > 2.33`
before the detection probability rises above 1%.

### Why it is a bound and not a model

For a known flaw and additive noise, the likelihood-ratio test is optimal
(Neyman–Pearson), and its deflection is `‖s‖/σ`; by Cauchy–Schwarz no other
statistic reaches it. So the matched filter defines the ceiling, and the ceiling is
computable in closed form. Nothing about the classifier enters — which is why no
amount of training moves the ceiling.

### The two regimes

`E(a/L)` is the squared norm of the flaw image after blurring:

| regime | behaviour | what it means |
|---|---|---|
| `a ≪ L` | `d' ∝ (a/L)³` | below the voxel size a flaw is a *volume*: halving it costs a factor of eight |
| `a ≫ L` | `d' ∝ (a/L)^{3/2}` | above it, ordinary energy-versus-noise |

Corollary worth remembering: **halving the voxel size equals 64 repeat scans** in the
first regime, and 8 in the second. Below the voxel size, buying dose is a bad trade.

### What real data does to it

The bound assumes white noise. Real reconstructions do not have white noise: the
matched filter integrates microstructure. The package measures the correction

```
κ = std(matched-filter statistic on real material) / (σ ‖T‖)
```

so the operative statement is `POD ≤ Φ((ΔI/κσ)√E·√N − z)`. On a public XCT stack of
laser powder-bed AlSi10Mg, κ runs from 24 to 125 and grows with the template support.
The geometry survives; the level must be measured.

---

## 2. Install

```bash
git clone https://github.com/Xbotsd/detectability-bound.git
cd detectability-bound

python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -e .
pytest -q
```

Expected: `11 passed`. Dependencies are `numpy`, `scipy`, `pydicom` — nothing else.

If you only want the theory and no imaging, `numpy` is enough; `pydicom` is imported
lazily by `dbound.realdata`.

---

## 3. Commands

Run everything through the module entry point:

```bash
python -m dbound <command> [options]
```

| command | what it does | typical runtime |
|---|---|---|
| `bound --a --L --dI-over-sigma` | one bound from the shell, no data needed | instant |
| `verify` | checks Propositions 1–2 and the tightness of the bound | ~4 min |
| `manifest <folder>` | SHA-256 of every DICOM slice in a folder | seconds |
| `measure <folder>` | σ, PSF width, κ(a/L), POD table on a real stack | 2–5 min |
| `ablate <folder>` | one-factor-at-a-time ablation at a = 8 voxels | ~10 min |
| `compare <folder>` | oracle / scanned / peak detectors at matched false alarm | 1–2 min |
| `all --data-root data --out results` | all of the above on every `vol_*` folder | ~20 min |

### `bound` — one number, no data

```bash
python -m dbound bound --a 100 --L 40 --dI-over-sigma 5
```

```json
{"a": 100.0, "L": 40.0, "x": 2.5, "dprime": 9.50, "pod_bound": 1.0,
 "voxel_max_for_target": 66.12, "energy_needed_for_target": 0.52,
 "repeats_equal_halving_voxel": 64.0}
```

Reads as: a 100 µm flaw seen at 40 µm voxels with contrast five times the noise has
a deflection of 9.5 and is therefore detected with probability 1 at α = 0.01; if you
only needed 90%, you could get away with 66 µm voxels. Anything larger than that and
this flaw is outside the bound.

### `verify` — check the mathematics

```bash
python -m dbound verify
```

Prints JSON with the fitted exponent below the voxel size (expect ≈ 3), the local
exponents above it (decreasing toward 1.5), the mean gap between the bound and three
detectors, and the number of violations. Use it after changing anything in
`bound.py`:

```json
{"small_exponent": 3.156, "mean_gap": {"pod_mf": 0.003, "pod_maxmf": 0.297, ...}}
```

This is a computation with exact truth — a check of the algebra, not an experiment.

### `manifest` — fingerprint your data

```bash
python -m dbound manifest data/vol_gd --out data/manifest.json
```

Records name, size and SHA-256 per slice. Commit that file, not the slices, and
anyone can verify they are working on the same data:

```bash
python data/fetch.py --verify --dest data/vol_gd --manifest data/manifest.json
# 212 files checked, 0 problems
```

### `measure` — the real-data numbers

```bash
python -m dbound measure data/vol_gd --out results/measure_vol_gd.json
```

Produces σ, both PSF estimates, the κ curve over `a = 1 … 16` voxels, and POD versus
the bound at three sizes.

### `ablate` — which choice matters

```bash
python -m dbound ablate data/vol_gd --a 8 --out results/ablation.json
```

Varies one thing at a time: template construction, noise estimator, PSF estimator,
padding, false-alarm level. Read it when you doubt a number — the σ row alone is
worth knowing (a plain standard deviation returns 872 where the robust estimator
returns 98.5, because the first measures microstructure).

### `compare` — detectors at the same false alarm

```bash
python -m dbound compare data/vol_gd --a 4 --ratio 8 --out results/comparison.json
```

Oracle matched filter, scanned matched filter, template-free peak. All three hit the
nominal `α`; the differences between them are the price of not knowing where the
flaw is.

---

## 4. Tutorials

### T1 — a bound for your own inspection, ten lines

```python
from dbound import bound

a_um, L_um = 100.0, 40.0          # flaw diameter, voxel size
contrast, sigma = 500.0, 100.0    # grey levels
alpha = 0.01

p = bound.pod_bound(contrast, sigma, a_um / L_um, alpha)
print(f"POD at a = {a_um} um: {p:.3f}")

req = bound.required_voxel(a_um, contrast, sigma, pod=0.9, alpha=alpha)
print(f"largest voxel for POD 0.9: {req.voxel_max:.1f} um")
print(f"repeats equal to halving the voxel: {bound.repeats_to_match_resolution(2.0):.0f}")
```

### T2 — κ on your own CT stack

```python
import numpy as np
from dbound import psf, realdata

s = realdata.load_series("data/vol_gd")           # any folder of .dcm slices
mask = realdata.material_mask(s.volume)
sigma = realdata.sigma_second_diff(s.volume, mask)
L = psf.psf_from_autocorrelation(s.volume, mask)

k = realdata.kappa(s.volume, mask, sigma, a=8.0, fwhm=L, n_trials=400)
print(f"sigma={sigma:.1f}  L={L:.2f} vox  kappa={k['kappa']:.1f}"
      f"  [{k['kappa_lo']:.1f}, {k['kappa_hi']:.1f}]")
```

Two things to check before trusting it: `L` should be between 1 and 3 voxels for a
well-sampled reconstruction, and κ should come out above 1. If κ < 1 the bound is
violated and something is wrong with the mask or the noise estimate.

### T3 — reproduce the paper

```bash
python -m dbound verify                                        # §3
python data/fetch.py --group GD --from-manifest data/manifest.json --dest data/vol_gd
python data/fetch.py --verify --dest data/vol_gd --manifest data/manifest.json
python -m dbound measure data/vol_gd --out results/measure_vol_gd.json   # §5.1-5.3
python -m dbound ablate  data/vol_gd --out results/ablation.json         # §5.4
python -m dbound compare data/vol_gd --out results/comparison.json       # §5.6
```

The cross-reconstruction table (§5.5) uses `vol_g1` and `vol_g2` fetched the same way;
`experiments.cross_group` takes a dict of folder paths.

---

## 5. Reading the output files

### `measure_*.json`

| field | meaning |
|---|---|
| `sigma` | voxel noise, from the MAD of the second difference |
| `psf_fwhm_autocorr` | PSF width in voxels, from the noise autocorrelation |
| `psf_fwhm_edge` | independent estimate from the edge spread function; `null` when the specimen fills the field of view |
| `kappa[].a`, `.x` | flaw size in voxels and `a/L` |
| `kappa[].kappa`, `.kappa_lo`, `.kappa_hi` | clutter inflation and its 95% bootstrap interval |
| `kappa[].sqrt_E` | `√E(a/L)`, the geometric factor |
| `kappa[].increment` | statistic gain per unit of injected contrast |
| `kappa[].threshold` | decision threshold at the requested `α` |
| `pod[]` | bound versus measured POD for each contrast level |

### `ablation.json`

Nested by factor: `templates.{dc,zero_mean,annular}`, `sigmas.{...}`, `psfs.{...}`,
`padding`, `alpha`. Each leaf is a κ record, except the `sigmas`/`psfs` blocks which
are the estimates themselves.

### `verify_algebra.json`

`small_exponent`, `large_slopes`, `mean_gap`, `violations`, `rows`. `mean_gap` is
`POD_bound − POD_detector`, so a positive number means the detector fell short of the
ceiling, which is what should happen for every detector except the oracle.

---

## 6. FAQ and troubleshooting

**κ looks absurdly large — is it a bug?**
On metal XCT it is genuinely large, and the ablation shows why. Before blaming the
code, check the template: a template with a nonzero mean measures the local grey
level and inflates κ by 2×. `ammonitor`-style checks are in `ablate`.

**`Required voxel` returns `nan`.**
The target lies outside the tabulated curve — either the required contrast is below
what any voxel size can deliver, or above the range `E` covers. Check
`bound.energy_curve()`.

**`psf_fwhm_edge` is `null`.**
The estimator needs a specimen boundary inside the field of view. A sample that fills
the frame gives nothing. That is reported rather than papered over; use the
autocorrelation estimate and say so.

**`load_series` raises on my DICOMs.**
`pydicom` must be installed, and the folder must contain only `.dcm` slices of one
series. Mixed series will be sorted wrongly; split them first.

**How many trials do I need?**
400 patches gives a κ interval of about ±10%. Fewer than 100 is not usable; the
`n` field records what was actually used.

**`python -m dbound` says "No module named dbound".**
Either the package is not installed (`pip install -e .`) or you are outside the repo.
`PYTHONPATH=src python -m dbound ...` works without installing.
