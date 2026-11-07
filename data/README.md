# Data

## Source

The study uses one public X-ray computed tomography archive:

> *Tomographic image stacks for the study "Analysis of Porosity in AlSi10Mg Using
> Tomographic Image Processing"*, Zenodo, doi:10.5281/zenodo.17602110,
> licence CC BY 4.0.

Three laser powder-bed AlSi10Mg samples, reconstructed at **37.0 µm isotropic
voxels** (PixelSpacing 0.037011 mm; slice spacing from `ImagePositionPatient`),
672 × 465 pixels per slice. The archive holds three groups:

| group | slices | role in this study |
|---|---|---|
| `GD` | 399 | primary volume, 212 slices used |
| `G1` | 939 | second reconstruction condition, 120 slices used |
| `G2` | 1014 | third reconstruction condition, 120 slices used |

## What is in this repository

The raw DICOM slices are **not** committed — 200–400 MB of third-party imaging
does not belong in a git history. What is committed instead:

* `manifest.json` — file name, size and SHA-256 for every slice used, so the
  exact data set behind every number in the paper can be verified;
* `fetch.py` — reproduces that exact set by HTTP range requests;
* `../results/*.json` — the derived measurements (σ, PSF width, κ, POD tables).

## Why range requests

The archive is 2.5 GB and Zenodo throttles to roughly 130 KB/s per connection; a
whole-file download takes hours and a fetch of a contiguous span degrades further
with size. Slices of one stack are stored contiguously, so `fetch.py` opens the
archive through its central directory, reads the byte span covering a run of six
members with a single request, and parses the local headers itself. This is what
was done for the study, so the reproduction path is the same path.

## Reproduce

```bash
# the exact 212 slices used for the primary volume
python fetch.py --group GD --from-manifest manifest.json --dest data/vol_gd
python fetch.py --verify --dest data/vol_gd --manifest manifest.json
```

`--verify` recomputes every SHA-256 and reports mismatches. A clean run prints
`212 files checked, 0 problems`.

## Citation

If you use this data, cite the Zenodo record above, not this repository.
