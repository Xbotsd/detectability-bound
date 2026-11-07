"""Tests for the analytic part: asymptotes, bound, inversion, templates."""

from __future__ import annotations

import math
import pathlib
import sys

import numpy as np
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from dbound import bound, detectors, psf  # noqa: E402


def test_small_flaw_exponent_is_three():
    xs, es = bound.energy_curve()
    sel = xs <= 0.45
    slope = np.polyfit(np.log(xs[sel]), np.log(np.sqrt(es[sel])), 1)[0]
    assert 2.7 < slope < 3.4, slope


def test_large_flaw_exponent_decreases_toward_three_halves():
    xs, _ = bound.energy_curve()
    big = [x for x in xs if x > 8]
    slopes = [bound.local_dprime_exponent(float(x)) for x in big]
    assert all(1.4 < s < 1.7 for s in slopes), slopes
    assert slopes[-1] < slopes[0]


def test_energy_is_monotone_in_size():
    xs, es = bound.energy_curve()
    assert np.all(np.diff(es) > 0)


def test_pod_bound_is_monotone_and_bounded():
    prev = -1.0
    for x in (0.2, 0.5, 1.0, 2.0, 4.0):
        v = bound.pod_bound(10.0, 1.0, x, alpha=0.01)
        assert 0.0 <= v <= 1.0
        assert v >= prev
        prev = v


def test_required_voxel_inverts_the_bound():
    a, dI, sigma = 100.0, 1.0, 0.25
    req = bound.required_voxel(a, dI, sigma, pod=0.9, alpha=0.01)
    assert math.isfinite(req.voxel_max)
    # at the returned voxel size the target POD is met, just below it is not
    assert bound.pod_bound(dI, sigma, a / req.voxel_max, 0.01) == pytest.approx(
        0.9, abs=0.01)
    assert bound.pod_bound(dI, sigma, a / (1.1 * req.voxel_max), 0.01) < 0.9


def test_repeats_equivalence():
    assert bound.repeats_to_match_resolution(2.0) == pytest.approx(64.0)
    assert bound.repeats_to_match_resolution(3.0) == pytest.approx(729.0)


def test_z_and_ndtr_round_trip():
    for p in (0.5, 0.9, 0.99, 0.999):
        assert bound.ndtr(bound.z_from_p(p)) == pytest.approx(p, abs=1e-6)


def test_annular_template_is_close_to_zero_mean():
    t = detectors.template(6.0, 1.4, kind="annular")
    assert abs(t.mean()) < 1e-3 * np.abs(t).max()


def test_dc_template_has_nonzero_mean():
    t = detectors.template(6.0, 1.4, kind="dc")
    assert abs(t.mean()) > 1e-4


def test_signal_energy_matches_sphere_volume_for_large_flaws():
    """For a >> L the energy approaches the flaw volume."""
    a = 24.0
    e = detectors.signal_energy(a, 1.0)
    assert 0.7 * (math.pi / 6) * a ** 3 < e < 1.15 * (math.pi / 6) * a ** 3


def test_psf_kernel_is_normalised():
    k = psf.gaussian_kernel(32, 1.2)
    assert k.sum() == pytest.approx(1.0)
