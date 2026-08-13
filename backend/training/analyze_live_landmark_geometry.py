"""Live smoke-test gate for analyze_landmark_geometry_liveness.py's offline finding (clean
genuine/tremor separation using MediaPipe FaceMesh's rigid-vs-non-rigid landmark residual). That
result used a synthetic warpAffine perturbation as a stand-in for hand tremor; this script runs the
identical metric against real frames captured by capture_live_frames.py - a real held photo (glare,
paper-flex, natural 3D tilt), not a pure 2D warp.

Usage: python analyze_live_landmark_geometry.py <captures_dir> <genuine_labels> <spoof_labels>
<genuine_labels>/<spoof_labels> accept comma-separated lists to pool multiple capture rounds -
pairs are only ever formed within a single round's own consecutive frames, never across rounds
(rounds aren't 5s apart from each other), then residuals are pooled across rounds for the
final overlap check.
"""
import glob
import os
import sys

import cv2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from analyze_landmark_geometry_liveness import (  # noqa: E402
    _landmarks_px,
    _make_landmarker,
    _raw_pixel_diff,
    _rigid_residual_and_nonrigid_residual,
)


# Rigid-fit-quality gate: a genuine skull is always well-modeled by a 2D similarity transform
# between two 5s-apart polls (bones don't flex). A hand-held flat object undergoing real 3D tilt
# sometimes isn't - the 2D model itself breaks down, inflating BOTH residuals, not just non-rigid.
# Comfortably above every genuine rigid-fit residual seen in the first live round (max 5.5).
RIGID_FIT_GATE = 10.0


def _consecutive_pair_stats(landmarker, paths, condition_label, round_label):
    rows = []
    for a, b in zip(paths, paths[1:]):
        img_a, img_b = cv2.imread(a), cv2.imread(b)
        lm_a, lm_b = _landmarks_px(landmarker, img_a), _landmarks_px(landmarker, img_b)
        if lm_a is None or lm_b is None:
            print(f"  [{round_label}] {os.path.basename(a)} -> {os.path.basename(b)}: no face landmarks, skipping")
            continue
        r, n = _rigid_residual_and_nonrigid_residual(lm_a, lm_b)
        pd = _raw_pixel_diff(img_a, img_b, lm_a)
        rows.append((r, n, pd))
        print(f"  [{round_label}] {os.path.basename(a)} -> {os.path.basename(b)}: rigid={r:.2f} non-rigid={n:.2f} pixdiff={pd:.2f}")

    print(f"\n{condition_label} round '{round_label}' (n pairs={len(rows)}):")
    for name, idx in [("raw pixel diff        ", 2), ("rigid-fit residual    ", 0), ("non-rigid residual    ", 1)]:
        vals = sorted(v[idx] for v in rows)
        if vals:
            n = len(vals)
            print(f"  {name}: n={n} min={vals[0]:.2f} median={vals[n // 2]:.2f} max={vals[-1]:.2f}")
        else:
            print(f"  {name}: no usable pairs")
    return rows


def _pool(landmarker, captures_dir, labels, condition_label):
    all_rows = []
    for label in labels:
        paths = sorted(glob.glob(os.path.join(captures_dir, f"{label}_*.jpg")))
        all_rows.extend(_consecutive_pair_stats(landmarker, paths, condition_label, label))
    return all_rows


def _range_str(vals):
    return f"[{min(vals):.1f}, {max(vals):.1f}]" if vals else "(no data)"


def _report_overlap(name, genuine_vals, spoof_vals):
    print(f"\n{name}: genuine {_range_str(genuine_vals)} (n={len(genuine_vals)})  "
          f"vs spoof {_range_str(spoof_vals)} (n={len(spoof_vals)})")
    if not genuine_vals or not spoof_vals:
        print("  Not enough usable pairs to compare.")
        return
    overlap = max(min(genuine_vals), min(spoof_vals)) <= min(max(genuine_vals), max(spoof_vals))
    print("  *** OVERLAP - does not cleanly separate ***" if overlap else "  Clean separation")


def main(captures_dir: str, genuine_labels: str, spoof_labels: str):
    landmarker = _make_landmarker()

    genuine_rows = _pool(landmarker, captures_dir, genuine_labels.split(","), "GENUINE (real sitting)")
    spoof_rows = _pool(landmarker, captures_dir, spoof_labels.split(","), "SPOOF (real held photo)")

    genuine_nonrigid = [r[1] for r in genuine_rows]
    spoof_nonrigid = [r[1] for r in spoof_rows]

    print(f"\n=== POOLED (n genuine pairs={len(genuine_rows)}, n spoof pairs={len(spoof_rows)}) ===")
    _report_overlap("Non-rigid residual, naive (no gate)", genuine_nonrigid, spoof_nonrigid)

    # Gated: only compare non-rigid residual for pairs where the rigid-fit model itself fit well.
    genuine_gated = [r[1] for r in genuine_rows if r[0] < RIGID_FIT_GATE]
    spoof_gated = [r[1] for r in spoof_rows if r[0] < RIGID_FIT_GATE]
    spoof_failed_gate = sum(1 for r in spoof_rows if r[0] >= RIGID_FIT_GATE)
    genuine_failed_gate = sum(1 for r in genuine_rows if r[0] >= RIGID_FIT_GATE)
    print(f"\nRigid-fit gate (residual < {RIGID_FIT_GATE}): "
          f"genuine {len(genuine_rows) - genuine_failed_gate}/{len(genuine_rows)} passed, "
          f"spoof {len(spoof_rows) - spoof_failed_gate}/{len(spoof_rows)} passed "
          f"({spoof_failed_gate} spoof pair(s) failed the gate - themselves a suspicious signal)")
    _report_overlap("Non-rigid residual, gated", genuine_gated, spoof_gated)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
