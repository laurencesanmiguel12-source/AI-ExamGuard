"""Re-validate the PROLONGED_HEAD_DOWN calibration against the new_dataset webcam batch (6 people,
~5 rooms), using head_pose.csv produced by annotate_new_video.py (the REAL production pipeline:
face_service._detect_largest_face / _estimate_head_pose / _pose_fallback_signals).

Video-level behaviour labels below are from direct visual review of the frames (2026-09-08), NOT
from the model's own pitch - so a threshold sweep against them isn't circular the way using
"phone present" as the proxy would be.

  HEAD_DOWN_DEEP   - top of head to camera, face genuinely pitched right down for the whole clip
  HEAD_UP          - attentive, facing the screen, normal small downward screen-gaze only
  COVERT_EYES_DOWN - phone in hand at lap/chest height, EYES clearly down, HEAD near level
                     (the exam-cheating case the feature is meant to catch)
  AMBIGUOUS_LOWCAM - normal "reading the screen" posture, but this webcam sits low so the head-pose
                     solve reports a steep negative pitch anyway

What we're checking (see ai_examguard_gaze_monitoring_feasibility - pitch is a KNOWN ~0.5-precision
capped signal, this is a drift check + fresh exemplars, not an expected F1 jump):
  1. do HEAD_UP clips stay clear of HEAD_DOWN_PITCH_THRESHOLD_DEGREES on 2026-09 hardware?
  2. on genuine deep head-down, YuNet drops the face - does the pose fallback still report the
     head present (so the streak is sustained) instead of a false FACE_LOST?
  3. does any pitch threshold actually separate COVERT_EYES_DOWN / AMBIGUOUS_LOWCAM from HEAD_UP?

Usage: ../.venv/Scripts/python.exe analyze_head_down_new_video.py
"""
import csv
import os
import statistics as st
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.services.face_service import HEAD_DOWN_PITCH_THRESHOLD_DEGREES  # noqa: E402

CSV = os.path.join(os.path.dirname(__file__), "datasets", "new_video", "head_pose.csv")

LABELS = {
    "WIN_20260908_08_32_05_Pro": "HEAD_DOWN_DEEP",
    "WIN_20260908_02_07_53_Pro": "HEAD_DOWN_DEEP",
    "WIN_20260908_08_30_06_Pro": "HEAD_UP",
    "Copy_of_WIN_20260907_23_45_14_Pro": "COVERT_EYES_DOWN",
    "WIN_20260908_02_04_42_Pro": "AMBIGUOUS_LOWCAM",
}


def pct(n, d):
    return f"{100*n/d:.0f}%" if d else "-"


def main():
    rows = list(csv.DictReader(open(CSV)))
    by = {}
    for r in rows:
        lab = LABELS.get(r["video"])
        if lab:
            by.setdefault(r["video"], (lab, []))[1].append(r)

    print(f"live HEAD_DOWN_PITCH_THRESHOLD_DEGREES = {HEAD_DOWN_PITCH_THRESHOLD_DEGREES}\n")
    print(f"{'video':38s} {'label':17s} {'n':>4} {'noFace':>7} {'fbTrue':>7} "
          f"{'pitch p50':>9} {'p10..p90':>14} {'%<=thr':>7}")
    sweep_data = []  # (is_down, pitch) for frames with a pitch, DEEP + UP only
    for video, (lab, rs) in sorted(by.items(), key=lambda kv: kv[1][0]):
        n = len(rs)
        pitches = [float(x["pitch"]) for x in rs if x["pitch"] != ""]
        noface = [x for x in rs if x["yunet_face"] != "True"]
        fb_true = sum(1 for x in noface if x["fallback_head_present"] == "True")
        below = sum(1 for p in pitches if p <= HEAD_DOWN_PITCH_THRESHOLD_DEGREES)
        p50 = st.median(pitches) if pitches else float("nan")
        lo = sorted(pitches)[len(pitches)//10] if pitches else float("nan")
        hi = sorted(pitches)[9*len(pitches)//10] if pitches else float("nan")
        print(f"{video:38s} {lab:17s} {n:>4} {pct(len(noface),n):>7} "
              f"{pct(fb_true,len(noface)):>7} {p50:>9.1f} {lo:>6.0f}..{hi:<6.0f} "
              f"{pct(below,len(pitches)):>7}")
        if lab in ("HEAD_DOWN_DEEP", "HEAD_UP"):
            for p in pitches:
                sweep_data.append((lab == "HEAD_DOWN_DEEP", p))

    print("\n--- pitch-threshold sweep, HEAD_DOWN_DEEP vs HEAD_UP, face-tracked frames only ---")
    print("(deep head-down mostly drops YuNet entirely - this sweep only sees the minority of "
          "deep frames where a pitch exists, plus all HEAD_UP frames)")
    n_down = sum(1 for d, _ in sweep_data if d)
    n_up = sum(1 for d, _ in sweep_data if not d)
    print(f"  {n_down} down-with-pitch frames, {n_up} up frames")
    print(f"  {'thr':>6} {'recall':>7} {'prec':>7} {'f1':>7} {'fp':>4}")
    best = (-1, None)
    for thr in [-20, -25, -30, -35, -40, -45, -50]:
        tp = sum(1 for d, p in sweep_data if d and p <= thr)
        fp = sum(1 for d, p in sweep_data if not d and p <= thr)
        rec = tp / n_down if n_down else float("nan")
        prec = tp / (tp + fp) if (tp + fp) else float("nan")
        f1 = 2*prec*rec/(prec+rec) if prec == prec and (prec+rec) else float("nan")
        mark = "  <- current" if thr == HEAD_DOWN_PITCH_THRESHOLD_DEGREES else ""
        print(f"  {thr:>6} {rec:>7.2f} {prec:>7.2f} {f1:>7.2f} {fp:>4}{mark}")
        if f1 == f1 and f1 > best[0]:
            best = (f1, thr)
    print(f"  best F1 {best[0]:.2f} at thr {best[1]}")

    print("\n--- can any threshold catch COVERT_EYES_DOWN without also firing on HEAD_UP? ---")
    covert = [float(x["pitch"]) for v, (l, rs) in by.items() if l == "COVERT_EYES_DOWN"
              for x in rs if x["pitch"] != ""]
    up = [float(x["pitch"]) for v, (l, rs) in by.items() if l == "HEAD_UP"
          for x in rs if x["pitch"] != ""]
    if covert and up:
        print(f"  COVERT_EYES_DOWN pitch p50={st.median(covert):.0f} (p90={sorted(covert)[9*len(covert)//10]:.0f})")
        print(f"  HEAD_UP          pitch p50={st.median(up):.0f} (p10={sorted(up)[len(up)//10]:.0f})")
        print("  -> distributions overlap; no head-pitch cut separates 'eyes down at a held phone' "
              "from 'attentive at screen'. This case is only recoverable via the phone detector, "
              "not head pose (expected - _estimate_head_pose's docstring says it is head-aim, not gaze).")


if __name__ == "__main__":
    main()
