"""Parses analyze_blink_detection_feasibility.py's stdout log and flags candidate blink frames -
both eyes' scores dropping together to well below a local rolling-median baseline (not just a
global threshold, since baseline drifts with lighting/distance across a long sequence). Only a
candidate list, not a verdict - always visually spot-check the actual face crop at each flagged
index (see _extract_face_crops.py) before trusting one as a real blink. 2026-08-08: every
candidate found this way, across three real datasets, turned out to be a head-pose/motion
artifact, not a genuine isolated blink - see analyze_blink_detection_feasibility.py's docstring.

Usage: python _find_blink_candidates.py <log_path>
"""
import re
import sys

log_path = sys.argv[1]

rows = []
with open(log_path, encoding="utf-8") as f:
    for line in f:
        m = re.match(r"(frame_\d+\.jpg)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)", line)
        if m:
            name, r, l, mn = m.groups()
            rows.append((name, float(r), float(l), float(mn)))

print(f"{len(rows)} usable frames")

WINDOW = 10
candidates = []
for i in range(WINDOW, len(rows) - WINDOW):
    name, r, l, mn = rows[i]
    neighborhood = [rows[j][3] for j in range(i - WINDOW, i + WINDOW + 1) if j != i]
    baseline = sorted(neighborhood)[len(neighborhood) // 2]
    if baseline > 0 and mn < baseline * 0.35 and r < baseline * 0.6 and l < baseline * 0.6:
        candidates.append((name, r, l, mn, baseline))

print(f"{len(candidates)} candidate dip frames (both eyes < 60% of local baseline, min < 35%)")
for c in candidates:
    print(f"  {c[0]}: R={c[1]:.1f} L={c[2]:.1f} min={c[3]:.1f} local_baseline={c[4]:.1f}")
