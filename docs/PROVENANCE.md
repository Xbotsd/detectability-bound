# Provenance: what is measured, what is derived, what is synthetic

This file exists so that a reader can tell, without reading the code, which
number came from where.

## Three categories

| category | what it is | where it appears |
|---|---|---|
| **measured** | read off the public XCT data with an estimator stated in the paper | σ, PSF width, κ, measured POD |
| **derived** | computed from the model, no data involved | E(x), d′, POD bound, design rule, the 3 and 3/2 exponents |
| **synthetic** | exact-truth computation used only to check the algebra | `results/verify_algebra.json` |

The synthetic entry is the one place where no data is involved. It exists because
Propositions 1 and 2 are statements about a formula, and a formula is checked by
computing it, not by measuring a sample. It is reported separately in the paper
and is never described as an experiment.

Everything empirical — every κ, every POD, every design-rule number quoted for
real material — comes from the Zenodo record in `data/README.md`.

## The one injection

The real-data experiment places *known* spheres into *real* metal and measures
whether the detector finds them. The background, the noise correlation, the
reconstruction artefacts and the microstructure are the scanner's; only the flaw
is planted. This is stated explicitly in the paper (Section 5) and in the code
(`src/dbound/realdata.py`, `pod_curve_real`), and it is the standard way to obtain
ground truth in real imaging data without manufacturing a specimen.

No number in the paper comes from a simulated volume.

## Estimators, and why these ones

* **σ** — 1.4826 × MAD of the along-column second difference inside the material.
  A plain standard deviation inside the material returns the microstructure
  (the ablation in `results/ablation.json` shows the size of the difference).
* **L** — half-width of the noise autocorrelation inside the material, converted
  to a Gaussian FWHM (factor √2). The edge-spread estimator is kept as an
  independent check; it returns NaN when the specimen fills the field of view,
  which is the case for this sample, and that is reported rather than papered
  over.
* **κ** — standard deviation of the matched-filter statistic on real material
  divided by its white-noise value σ‖T‖, with a bootstrap interval over patches.

## What would falsify the reported result

* If κ came out below 1, the bound would be violated and the model wrong. It does
  not: κ ranges from 24 to 125.
* If the edge-spread and autocorrelation estimates of L disagreed by much, the
  PSF measurement would be suspect. The edge estimator is unavailable here, so
  this check is open and is listed as a limitation.
* If the annihilation test (template with δI = 0) produced a POD above α, the
  threshold calibration would be wrong. It is checked in the test suite.
