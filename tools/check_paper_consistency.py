"""Check that every number in the manuscript is backed by a result file.

The paper quotes five tables.  Each of them is generated from a JSON file in
``results/``; this tool parses the markdown and compares, so a stale table cannot
survive an experiment rerun.

    python tools/check_paper_consistency.py

Exit code 0 when everything matches, 1 otherwise.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
MD = ROOT / "manuscript.md"
TOL = {"kappa": 0.15, "pod": 0.01, "voxel": 0.15, "length": 0.05, "int": 1.0}


def load(name: str) -> dict:
    return json.loads((RESULTS / name).read_text(encoding="utf-8"))


def tables(text: str) -> list[tuple[str, list[list[str]]]]:
    """Every pipe table as (header, rows)."""
    out, block = [], []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("|"):
            block.append(s)
        elif block:
            out.append(block)
            block = []
    if block:
        out.append(block)

    parsed = []
    for b in out:
        rows = [[c.strip() for c in r.strip("|").split("|")] for r in b]
        header = rows[0]
        body = [r for r in rows[1:] if not all(set(c) <= set("-: ") for c in r)]
        parsed.append((" ".join(header).lower(), body))
    return parsed


def find(parsed, *keys):
    for head, body in parsed:
        if all(k.lower() in head for k in keys):
            return body
    return None


def num(s: str) -> float | None:
    s = s.replace(" ", "").replace("−", "-").replace("%", "")
    s = re.sub(r"[^0-9eE+\-.]", "", s)
    try:
        return float(s)
    except ValueError:
        return None


def close(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


def main() -> int:
    text = MD.read_text(encoding="utf-8")
    parsed = tables(text)
    problems: list[str] = []

    # ---- Table 4: kappa curve ------------------------------------------
    body = find(parsed, "a (voxels)", "x = a/l")
    if body is None:
        problems.append("kappa table not found")
    else:
        ref = load("measure_vol_gd.json")["kappa"]
        if len(body) != len(ref):
            problems.append(f"kappa rows {len(body)} != {len(ref)} in json")
        for row, r in zip(body, ref):
            a, x, k, ci = num(row[0]), num(row[1]), num(row[2]), row[3]
            lo, hi = [num(v) for v in ci.strip("[]").split(",")]
            if not (a and x and k):
                problems.append(f"kappa row unparsable: {row}")
                continue
            if not close(a, r["a"], TOL["int"]):
                problems.append(f"kappa a {a} != {r['a']}")
            if not close(x, r["x"], TOL["int"]):
                problems.append(f"kappa x {x} != {r['x']:.2f}")
            if not close(k, r["kappa"], TOL["kappa"]):
                problems.append(f"kappa {k} != {r['kappa']:.2f}")
            if not close(lo, r["kappa_lo"], TOL["kappa"]):
                problems.append(f"kappa lo {lo} != {r['kappa_lo']:.1f}")
            if not close(hi, r["kappa_hi"], TOL["kappa"]):
                problems.append(f"kappa hi {hi} != {r['kappa_hi']:.1f}")

    # ---- Table 2: design rule ------------------------------------------
    body = find(parsed, "flaw a", "Δi/σ")
    if body is None:
        problems.append("design-rule table not found")
    else:
        ref = load("design_rule.json")
        ratios = [str(x) for x in ref["ratios"]]
        for row, r in zip(body, ref["rows"]):
            if not close(num(row[0]), r["a_um"], TOL["int"]):
                problems.append(f"design a {row[0]} != {r['a_um']}")
            for j, ratio in enumerate(ratios, start=1):
                want = r["voxel_max_um"][ratio]["voxel_max"]
                got = num(row[j])
                if not close(got, want, TOL["voxel"]):
                    problems.append(
                        f"design a={r['a_um']:.0f} ratio={ratio}: {got} != {want:.1f}")

    # ---- Table 6: cross-group -------------------------------------------
    body = find(parsed, "group", "slices", "κ at a = 2")
    if body is None:
        problems.append("cross-group table not found")
    else:
        ref = load("cross_group.json")
        for row in body:
            name = row[0].strip()
            key = {"GD": "vol_gd", "G1": "vol_g1", "G2": "vol_g2"}.get(name)
            if key is None or key not in ref:
                problems.append(f"cross-group row unknown: {name}")
                continue
            g = ref[key]
            if not close(num(row[1]), g["series"]["n_slices"], TOL["int"]):
                problems.append(f"{name} slices {row[1]} != {g['series']['n_slices']}")
            if not close(num(row[2]), g["sigma"], 0.5):
                problems.append(f"{name} sigma {row[2]} != {g['sigma']:.1f}")
            if not close(num(row[3]), g["fwhm"], TOL["length"]):
                problems.append(f"{name} L {row[3]} != {g['fwhm']:.2f}")
            for j, k in enumerate(g["kappa"]):
                got = num(row[4 + j])
                if not close(got, k["kappa"], TOL["kappa"]):
                    problems.append(f"{name} kappa(a={k['a']}) {got} != {k['kappa']:.1f}")

    # ---- Table 7: detectors ---------------------------------------------
    body = find(parsed, "detector", "null s.d.")
    if body is None:
        problems.append("detector table not found")
    else:
        ref = load("comparison.json")
        key_map = {0: "mf", 1: "mm", 2: "pk"}
        for i, row in enumerate(body):
            k = key_map.get(i)
            if k is None:
                continue
            sd, thr, pod = num(row[1]), num(row[2]), num(row[3])
            if not close(sd, ref["null_sd"][k], 2.0):
                problems.append(f"detector {k} sd {sd} != {ref['null_sd'][k]:.0f}")
            if not close(thr, ref["threshold"][k], 2.0):
                problems.append(f"detector {k} thr {thr} != {ref['threshold'][k]:.0f}")
            if not close(pod, ref["pod"][k], TOL["pod"]):
                problems.append(f"detector {k} pod {pod} != {ref['pod'][k]:.3f}")

    # ---- ablation: check the three template kappas ----------------------
    body = find(parsed, "factor", "setting")
    if body is None:
        problems.append("ablation table not found")
    else:
        ref = load("ablation.json")
        want = {"raw sphere": ref["templates"]["dc"]["kappa"],
                "zero-mean": ref["templates"]["zero_mean"]["kappa"],
                "annular": ref["templates"]["annular"]["kappa"]}
        for row in body:
            setting = row[1].lower()
            for key, value in want.items():
                if key in setting:
                    got = num(row[2])
                    if not close(got, value, TOL["kappa"]):
                        problems.append(f"ablation {key}: {got} != {value:.1f}")

    if problems:
        print(f"FAILED — {len(problems)} inconsistencies")
        for p in problems:
            print("  -", p)
        return 1
    print("OK — all five table groups agree with results/*.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
