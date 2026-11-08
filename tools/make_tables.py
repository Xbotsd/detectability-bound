"""Regenerate the design-rule table from the package, so Table 2 has a data file.

    python tools/make_tables.py          # writes results/design_rule.json
"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dbound import bound  # noqa: E402

FLAWS = (50.0, 100.0, 200.0, 500.0)
RATIOS = (2.0, 5.0, 10.0)
POD, ALPHA = 0.90, 0.01


def main() -> None:
    rows = []
    for a in FLAWS:
        voxel = {}
        for r in RATIOS:
            req = bound.required_voxel(a, r, 1.0, POD, ALPHA)
            voxel[str(r)] = {"x_star": req.x_star, "voxel_max": req.voxel_max}
        noise = {}
        for r in RATIOS:
            noise[str(r)] = bound.required_noise(a, a / 2.0, r, POD, ALPHA)
        rows.append({"a_um": a, "voxel_max_um": voxel,
                     "sigma_max_at_L_eq_a_over_2": noise})

    repeats = {str(k): bound.repeats_to_match_resolution(k) for k in (1.5, 2.0, 3.0, 4.0)}
    out = {"pod_target": POD, "alpha": ALPHA, "flaws_um": list(FLAWS),
           "ratios": list(RATIOS), "rows": rows, "repeats_equivalent": repeats}
    dest = ROOT / "results" / "design_rule.json"
    dest.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"wrote {dest.relative_to(ROOT)}")
    for r in rows:
        cells = "  ".join(f"{r['voxel_max_um'][str(x)]['voxel_max']:7.1f}" for x in RATIOS)
        print(f"  a={r['a_um']:5.0f} um -> {cells}")


if __name__ == "__main__":
    main()
