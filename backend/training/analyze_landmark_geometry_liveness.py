"""Empirical test of a landmark-geometry liveness idea, proposed as a refinement of the
already-tried-and-shelved frame-differencing check (STATIC_IMAGE_DIFF_THRESHOLD in
face_service.py - see ai_examguard_face_recognition_threshold_finding memory). That check compares
raw pixel differences between consecutive poll crops and hit a real ceiling: a hand-held photo's
natural tremor produces pixel motion (diffs 7.2-20.3) that overlaps genuine still-sitting motion
(11.3-30.9) - the whole photo moves as one rigid unit, but rigid motion still moves pixels.

The idea here: instead of raw pixel diff, fit the best-explaining RIGID 2D transform (scale +
rotation + translation) between two polls' landmarks using only skeletally-rigid points (forehead/
nose-bridge/cheekbones - stable regardless of expression), then measure how well that SAME rigid
transform predicts the NON-rigid points (eyelid contour, mouth corners). A held photo - however
much a hand shakes it - is physically one flat rigid surface: every point on it, rigid or not,
moves by the exact same transform. A real face is not: eyelids and mouth move independently of the
skull's rigid motion (blinks, micro-expressions) even while the head itself holds still or drifts
slightly. So the *residual* after removing rigid motion should be small for a photo and larger for
a genuine face - a different signal than raw pixel diff, specifically targeting the confound
(rigid tremor) that broke the pixel-diff approach.

Methodology, explicitly a favorable-case proxy, not a live test:
- GENUINE condition: real consecutive frames from the personal_phone_video_review dataset (one
  real person, real webcam, 15.16fps), paired ~5s apart (76 frames) to match ExamRoom.jsx's real
  face-check poll cadence (setInterval(checkOnce, 5000) - confirmed by reading the file, not
  assumed) - natural head/expression variation over that real interval.
- SYNTHETIC-TREMOR condition: 8 different real single frames, each used as a stand-in "held
  photo", each perturbed by 4 small random rigid 2D similarity transforms (translation/rotation/
  scale calibrated to reproduce the 7.2-20.3 raw-diff range the original live hand-held-photo test
  found - see the memory above) via cv2.warpAffine on the whole image.
- This is a FAVORABLE-case test for the technique: a warpAffine-perturbed photo is by
  construction perfectly rigid (the only "non-rigidity" is landmark-detection noise), whereas a
  real held photo could show screen glare, slight paper flex, or a genuine 3D tilt a pure 2D
  warp can't reproduce. A live smoke-test (holding a real photo to a real webcam, same discipline
  as every other threshold in this project) is still the real bar before trusting this - this
  script is the offline-mechanism-validation step that should happen BEFORE burning that live
  test, same order as every prior threshold in this codebase.

Usage: python analyze_landmark_geometry_liveness.py
Needs `pip install mediapipe` (not in requirements.txt - not yet an adopted production dependency,
same "not fetched by this repo" convention as finetune_phone_face.py's dataset) and the face
landmark model bundle downloaded into this directory first:
    python -c "import urllib.request as u; u.urlretrieve(
        'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task',
        'face_landmarker.task')"
"""
import glob
import os
import random
import sys

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

REVIEW_DIR = os.path.join(
    os.path.dirname(__file__), "datasets", "oep-msu", "personal_phone_video_review"
)
MODEL_PATH = os.path.join(os.path.dirname(__file__), "face_landmarker.task")

# Skeletally-rigid landmarks (forehead / nose bridge / cheekbones) - stable regardless of
# blinking or talking, used to fit the rigid transform.
RIGID_IDX = [10, 168, 6, 197, 234, 454]
# Non-rigid landmarks - eyelid contour (both eyes) + mouth corners/lip center, expected to move
# independently of the skull's rigid motion in a genuine live face.
NON_RIGID_IDX = [33, 160, 158, 133, 153, 144, 263, 387, 385, 362, 380, 373, 61, 291, 0, 17]

random.seed(20260812)
np.random.seed(20260812)


def _make_landmarker():
    base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.FaceLandmarkerOptions(base_options=base_options, num_faces=1)
    return vision.FaceLandmarker.create_from_options(options)


def _landmarks_px(landmarker, image_bgr):
    h, w = image_bgr.shape[:2]
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    result = landmarker.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
    if not result.face_landmarks:
        return None
    lm = result.face_landmarks[0]
    return np.array([(p.x * w, p.y * h) for p in lm], dtype=np.float64)


def _fit_similarity(src, dst):
    """Umeyama closed-form best-fit 2D similarity transform (scale, rotation, translation)
    minimizing sum ||s*R@src_i + t - dst_i||^2. Deterministic least-squares, not RANSAC - the
    rigid landmark set is small (6 points) and trusted, no outlier rejection needed."""
    mu_src, mu_dst = src.mean(axis=0), dst.mean(axis=0)
    src0, dst0 = src - mu_src, dst - mu_dst
    cov = (dst0.T @ src0) / len(src)
    U, D, Vt = np.linalg.svd(cov)
    S = np.eye(2)
    if np.linalg.det(U @ Vt) < 0:
        S[1, 1] = -1
    R = U @ S @ Vt
    var_src = (src0 ** 2).sum() / len(src)
    scale = np.trace(np.diag(D) @ S) / var_src
    t = mu_dst - scale * R @ mu_src
    return scale, R, t


def _apply(scale, R, t, pts):
    return (scale * (R @ pts.T)).T + t


def _rigid_residual_and_nonrigid_residual(lm_a, lm_b):
    rigid_a, rigid_b = lm_a[RIGID_IDX], lm_b[RIGID_IDX]
    scale, R, t = _fit_similarity(rigid_a, rigid_b)

    rigid_pred = _apply(scale, R, t, rigid_a)
    rigid_residual = float(np.mean(np.linalg.norm(rigid_pred - rigid_b, axis=1)))

    non_rigid_a, non_rigid_b = lm_a[NON_RIGID_IDX], lm_b[NON_RIGID_IDX]
    non_rigid_pred = _apply(scale, R, t, non_rigid_a)
    non_rigid_residual = float(np.mean(np.linalg.norm(non_rigid_pred - non_rigid_b, axis=1)))

    return rigid_residual, non_rigid_residual


def _raw_pixel_diff(image_a, image_b, lm_a):
    """Same metric as face_service._check_static_image (mean absolute grayscale pixel diff on
    a face-centered crop) - reproduced here as a baseline, not imported, since that function
    expects a YuNet-cropped face rather than a FaceMesh landmark set."""
    xs, ys = lm_a[:, 0], lm_a[:, 1]
    x1, y1, x2, y2 = int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())
    h, w = image_a.shape[:2]
    x1, y1 = max(x1, 0), max(y1, 0)
    x2, y2 = min(x2, w), min(y2, h)
    crop_a = cv2.resize(image_a[y1:y2, x1:x2], (160, 160))
    crop_b = cv2.resize(image_b[y1:y2, x1:x2], (160, 160))
    return float(np.mean(np.abs(crop_b.astype(np.int16) - crop_a.astype(np.int16))))


def _tremor_warp(image, translate_px, rotate_deg, scale_jitter):
    h, w = image.shape[:2]
    center = (w / 2, h / 2)
    M = cv2.getRotationMatrix2D(center, rotate_deg, 1.0 + scale_jitter)
    M[0, 2] += translate_px[0]
    M[1, 2] += translate_px[1]
    return cv2.warpAffine(image, M, (w, h), borderMode=cv2.BORDER_REPLICATE)


def main():
    landmarker = _make_landmarker()
    files = sorted(glob.glob(os.path.join(REVIEW_DIR, "personal_video_review_*.jpg")))
    print(f"Found {len(files)} frames in review video")

    # --- GENUINE: real frames ~5s apart (76 frames @ 15.16fps), spread across the video ---
    genuine_pairs = []
    step = 76
    for start in range(0, len(files) - step, step * 3):  # spread out, don't overlap heavily
        genuine_pairs.append((files[start], files[start + step]))
    genuine_pairs = genuine_pairs[:25]
    print(f"Genuine pairs: {len(genuine_pairs)}")

    genuine_rigid, genuine_nonrigid, genuine_pixdiff = [], [], []
    for pa, pb in genuine_pairs:
        img_a, img_b = cv2.imread(pa), cv2.imread(pb)
        lm_a, lm_b = _landmarks_px(landmarker, img_a), _landmarks_px(landmarker, img_b)
        if lm_a is None or lm_b is None:
            continue
        rigid_res, nonrigid_res = _rigid_residual_and_nonrigid_residual(lm_a, lm_b)
        genuine_rigid.append(rigid_res)
        genuine_nonrigid.append(nonrigid_res)
        genuine_pixdiff.append(_raw_pixel_diff(img_a, img_b, lm_a))

    # --- SYNTHETIC TREMOR: 8 diverse base frames, 4 perturbed "polls" each ---
    base_indices = np.linspace(0, len(files) - 1, 8).astype(int)
    tremor_rigid, tremor_nonrigid, tremor_pixdiff = [], [], []
    for bi in base_indices:
        base_img = cv2.imread(files[bi])
        lm_prev = _landmarks_px(landmarker, base_img)
        if lm_prev is None:
            continue
        img_prev = base_img
        for _ in range(4):
            # Calibrated to land in the documented real hand-held-photo raw-diff range
            # (7.2-20.3) - see analyze_static_image_threshold.py's earlier live-test findings.
            translate = (random.uniform(-6, 6), random.uniform(-6, 6))
            rotate = random.uniform(-1.2, 1.2)
            scale_jit = random.uniform(-0.01, 0.01)
            img_next = _tremor_warp(base_img, translate, rotate, scale_jit)
            lm_next = _landmarks_px(landmarker, img_next)
            if lm_next is None:
                img_prev, lm_prev = img_next, lm_next if lm_next is not None else lm_prev
                continue
            rigid_res, nonrigid_res = _rigid_residual_and_nonrigid_residual(lm_prev, lm_next)
            tremor_rigid.append(rigid_res)
            tremor_nonrigid.append(nonrigid_res)
            tremor_pixdiff.append(_raw_pixel_diff(img_prev, img_next, lm_prev))
            img_prev, lm_prev = img_next, lm_next

    def stats(name, vals):
        vals = sorted(vals)
        n = len(vals)
        print(f"  {name}: n={n} min={vals[0]:.2f} median={vals[n // 2]:.2f} max={vals[-1]:.2f}")

    print(f"\nGenuine (n={len(genuine_nonrigid)}):")
    stats("raw pixel diff        ", genuine_pixdiff)
    stats("rigid-fit residual    ", genuine_rigid)
    stats("non-rigid residual    ", genuine_nonrigid)

    print(f"\nSynthetic tremor (n={len(tremor_nonrigid)}):")
    stats("raw pixel diff        ", tremor_pixdiff)
    stats("rigid-fit residual    ", tremor_rigid)
    stats("non-rigid residual    ", tremor_nonrigid)

    print("\nOverlap check (does the synthetic-tremor range overlap genuine?):")
    print(f"  raw pixel diff:     genuine [{min(genuine_pixdiff):.1f}, {max(genuine_pixdiff):.1f}]"
          f"  vs tremor [{min(tremor_pixdiff):.1f}, {max(tremor_pixdiff):.1f}]")
    print(f"  non-rigid residual: genuine [{min(genuine_nonrigid):.1f}, {max(genuine_nonrigid):.1f}]"
          f"  vs tremor [{min(tremor_nonrigid):.1f}, {max(tremor_nonrigid):.1f}]")


if __name__ == "__main__":
    main()
