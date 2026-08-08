"""Same tiling technique as _build_video_contact_sheet.py, but draws each frame's current draft
boxes on top (phone=red, face=green) so a reviewer can judge box correctness, not just frame
content - used for the AI-assisted labeling pass replacing a manual LabelImg session (2026-08-08,
at the user's explicit request: "go label it for me").

Usage: python _build_labeled_contact_sheet.py [start_frame] [end_frame] [step] [cols] [out_name]
"""
import glob
import os
import sys

import cv2
import numpy as np

REVIEW_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "personal_phone_video_review")
CELL_SIZE = (160, 90)
FPS = 15.16
COLORS = {0: (0, 0, 255), 1: (0, 255, 0)}  # phone=red, face=green (BGR)


def draw_boxes(img, label_path):
    height, width = img.shape[:2]
    if not os.path.exists(label_path):
        return img
    with open(label_path) as f:
        for line in f:
            parts = line.split()
            if not parts:
                continue
            cls_id = int(parts[0])
            cx, cy, w, h = (float(x) for x in parts[1:5])
            x1 = int((cx - w / 2) * width)
            y1 = int((cy - h / 2) * height)
            x2 = int((cx + w / 2) * width)
            y2 = int((cy + h / 2) * height)
            cv2.rectangle(img, (x1, y1), (x2, y2), COLORS.get(cls_id, (255, 255, 0)), 2)
    return img


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
        label_path = paths[frame_idx].replace(".jpg", ".txt")
        img = draw_boxes(img, label_path)
        thumb = cv2.resize(img, CELL_SIZE)
        r, c = divmod(i, cols)
        y0, x0 = r * CELL_SIZE[1], c * CELL_SIZE[0]
        sheet[y0:y0 + CELL_SIZE[1], x0:x0 + CELL_SIZE[0]] = thumb
        label = f"{frame_idx} {frame_idx/FPS:.1f}s"
        cv2.putText(sheet, label, (x0 + 2, y0 + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (0, 255, 255), 1)

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
