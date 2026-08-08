"""Tiles evenly-sampled frames from personal_phone_video_review/ into a labeled contact-sheet
grid, for fast visual scanning - same technique as build_phone_box_contact_sheets.py (fairness
audit work), used here because the automated real-vs-bogus phone-box heuristics
(_map_real_vs_bogus_phone_boxes.py, two variants tried) were both too unreliable to trust: the
face-shaped false positive fires inconsistently (sometimes one box, sometimes two), so neither
overlap-based nor count-based classification cleanly separates it from a genuine second detection.

Usage: python _build_video_contact_sheet.py [start_frame] [end_frame] [step] [cols] [out_name]
Denser follow-up pass (2026-08-08): splits the video into chunks and samples every Nth frame
within each chunk (rather than evenly across the whole video), for close-up sequences dense
enough to see exactly which frame a phone enters/leaves view.
"""
import glob
import os
import sys

import cv2
import numpy as np

REVIEW_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "personal_phone_video_review")
CELL_SIZE = (160, 90)
FPS = 15.16


def main(start: int, end: int, step: int, cols: int, out_name: str):
    paths = sorted(
        glob.glob(os.path.join(REVIEW_DIR, "*.jpg")),
        key=lambda p: int(os.path.basename(p).split("_")[-1].split(".")[0]),
    )
    total = len(paths)
    end = min(end, total)
    sampled_indices = list(range(start, end, step))

    rows = (len(sampled_indices) + cols - 1) // cols
    sheet = np.full((rows * CELL_SIZE[1], cols * CELL_SIZE[0], 3), 40, dtype=np.uint8)

    for i, frame_idx in enumerate(sampled_indices):
        img = cv2.imread(paths[frame_idx])
        if img is None:
            continue
        thumb = cv2.resize(img, CELL_SIZE)
        r, c = divmod(i, cols)
        y0, x0 = r * CELL_SIZE[1], c * CELL_SIZE[0]
        sheet[y0:y0 + CELL_SIZE[1], x0:x0 + CELL_SIZE[0]] = thumb
        label = f"{frame_idx} {frame_idx/FPS:.1f}s"
        cv2.putText(sheet, label, (x0 + 2, y0 + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (0, 255, 0), 1)

    out_path = os.path.join(REVIEW_DIR, out_name)
    cv2.imwrite(out_path, sheet)
    print(f"Saved {len(sampled_indices)} samples ({cols}x{rows} grid), frames {start}-{end} step {step} -> {out_path}")


if __name__ == "__main__":
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    end = int(sys.argv[2]) if len(sys.argv) > 2 else 1773
    step = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    cols = int(sys.argv[4]) if len(sys.argv) > 4 else 10
    out_name = sys.argv[5] if len(sys.argv) > 5 else "contact_sheet.png"
    main(start, end, step, cols, out_name)
