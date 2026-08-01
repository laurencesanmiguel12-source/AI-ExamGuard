"""A second honest proxy slice of the demographic bias audit (see
ai_examguard_thesis_scope_recommendations memory, priority item #1) - the "camera/webcam quality"
axis, alongside lighting_bias_proxy_analysis.py's brightness proxy.

Real webcam-quality diversity (built-in laptop cam vs. an old external webcam, different sensors/
compression) isn't something this project has recruited for, and scraping random low-quality photos
off the web would carry unknown provenance and no reliable "this photo IS low camera quality, not
just badly lit" label. Synthetically degrading this project's own already-labeled real OEP frames is
more controlled and honest: the degradation itself is fully specified, reproducible, and disclosed,
rather than a proxy of unknown origin.

What this measures: real YuNet face-detection rate on each existing frame at baseline vs. under three
synthetic degradations (blur, low-quality JPEG re-encoding, downscale+upscale) - both overall and
per-subject/per-batch, to check whether any group's face detection degrades disproportionately under
quality loss (the fairness-relevant question) rather than just how much detection drops on average.

Usage: ../.venv/Scripts/python.exe camera_quality_bias_proxy_analysis.py
"""
import os

import cv2

BATCH_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "annotation_batch")
HOLDOUT_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "frozen_holdout")
YUNET_PATH = os.path.join(os.path.dirname(__file__), "..", "app", "resources", "face_detection_yunet_2023mar.onnx")

GROUP_PREFIXES = (
    "subject01", "subject02", "subject03", "subject04", "subject06", "subject09",
    "subject10", "subject11", "subject12", "subject13", "subject24",
    "backface_capture", "backface_lit2", "backface_100", "backface4",
)


def _blur(image):
    return cv2.GaussianBlur(image, (9, 9), 0)


def _low_quality_jpeg(image):
    ok, buf = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 15])
    return cv2.imdecode(buf, cv2.IMREAD_COLOR) if ok else image


def _downscale_upscale(image):
    h, w = image.shape[:2]
    small = cv2.resize(image, (max(1, w // 4), max(1, h // 4)), interpolation=cv2.INTER_AREA)
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)


DEGRADATIONS = {
    "blur": _blur,
    "low_jpeg": _low_quality_jpeg,
    "downscale": _downscale_upscale,
}


def group_of(fname):
    for prefix in GROUP_PREFIXES:
        if fname.startswith(prefix):
            return prefix
    return None


def collect_frames():
    groups = {}
    for source_dir in (BATCH_DIR, HOLDOUT_DIR):
        for fname in sorted(os.listdir(source_dir)):
            if not fname.lower().endswith(".jpg"):
                continue
            g = group_of(fname)
            if g is None:
                continue
            groups.setdefault(g, []).append(os.path.join(source_dir, fname))
    return groups


def detect_face(detector, image):
    h, w = image.shape[:2]
    detector.setInputSize((w, h))
    _, faces = detector.detect(image)
    return faces is not None and len(faces) > 0


def main():
    detector = cv2.FaceDetectorYN_create(YUNET_PATH, "", (320, 320), 0.6, 0.3, 5000)
    groups = collect_frames()

    rows = []
    agg = {"n": 0, "baseline": 0, **{k: 0 for k in DEGRADATIONS}}

    for g in sorted(groups):
        counts = {"n": 0, "baseline": 0, **{k: 0 for k in DEGRADATIONS}}
        for path in groups[g]:
            image = cv2.imread(path)
            if image is None:
                continue
            counts["n"] += 1
            counts["baseline"] += int(detect_face(detector, image))
            for name, fn in DEGRADATIONS.items():
                counts[name] += int(detect_face(detector, fn(image)))

        n = counts["n"]
        if n == 0:
            continue
        rates = {k: counts[k] / n for k in ("baseline", *DEGRADATIONS)}
        worst_drop = max(rates["baseline"] - rates[k] for k in DEGRADATIONS)
        rows.append((g, n, rates, worst_drop))
        agg["n"] += n
        for k in ("baseline", *DEGRADATIONS):
            agg[k] += counts[k]

    header = f"{'group':<20} {'n':>5} {'baseline':>9} {'blur':>7} {'low_jpeg':>9} {'downscale':>10} {'worst_drop':>11}"
    print(header)
    for g, n, rates, worst_drop in rows:
        print(f"{g:<20} {n:>5} {rates['baseline']:>9.3f} {rates['blur']:>7.3f} "
              f"{rates['low_jpeg']:>9.3f} {rates['downscale']:>10.3f} {worst_drop:>11.3f}")

    overall_rates = {k: agg[k] / agg["n"] for k in ("baseline", *DEGRADATIONS)} if agg["n"] else None
    if overall_rates:
        overall_worst = max(overall_rates["baseline"] - overall_rates[k] for k in DEGRADATIONS)
        print(f"{'OVERALL':<20} {agg['n']:>5} {overall_rates['baseline']:>9.3f} {overall_rates['blur']:>7.3f} "
              f"{overall_rates['low_jpeg']:>9.3f} {overall_rates['downscale']:>10.3f} {overall_worst:>11.3f}")

    print("\nGroups whose worst-case degradation drop exceeds the overall worst-case by >15pts "
          "(disproportionately fragile to quality loss - the fairness-relevant signal, not just "
          "'detection drops under blur/compression', which is expected for everyone to some degree):")
    flagged = False
    if overall_rates:
        for g, n, rates, worst_drop in rows:
            if worst_drop - overall_worst > 0.15:
                print(f"  {g}: worst-case drop {worst_drop:.3f} vs overall {overall_worst:.3f}")
                flagged = True
    if not flagged:
        print("  none")


if __name__ == "__main__":
    main()
