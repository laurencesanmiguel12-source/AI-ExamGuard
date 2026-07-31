"""Ad-hoc helper: build contact sheets covering only the single-phone-box frames for a given
subject (the drop candidates under the validated rule in build_phone_box_contact_sheets.py's
review - see subject01_06_09_24 fairness-audit thread), so they can be scanned in bulk for any
that don't match the expected isolated-eye-tracker-device shape.

Usage: ../.venv/Scripts/python.exe build_singlebox_sheets.py subject06
"""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import build_phone_box_contact_sheets as m  # noqa: E402


def main():
    subject = sys.argv[1]
    fnames = sorted(
        f for f in os.listdir(m.BATCH_DIR)
        if f.startswith(subject) and f.lower().endswith(".jpg")
    )
    frames = []
    for fname in fnames:
        img_path = os.path.join(m.BATCH_DIR, fname)
        label_path = os.path.splitext(img_path)[0] + ".txt"
        image = cv2.imread(img_path)
        if image is None:
            continue
        h, w = image.shape[:2]
        boxes = m.load_phone_boxes(label_path, w, h)
        if len(boxes) == 1:
            frames.append((fname, boxes))

    print(f"{subject}: {len(frames)} single-phone-box frames")
    per_sheet = m.COLS * m.ROWS
    cell_h = m.TILE + m.CAPTION_H
    for sheet_idx in range(0, len(frames), per_sheet):
        chunk = frames[sheet_idx:sheet_idx + per_sheet]
        sheet = np.full((cell_h * m.ROWS, m.TILE * m.COLS, 3), 255, dtype=np.uint8)
        for i, (fname, boxes) in enumerate(chunk):
            r, c = divmod(i, m.COLS)
            short = fname.replace(subject + "_", "").replace(".jpg", "")
            tile = m.make_tile(os.path.join(m.BATCH_DIR, fname), boxes)
            tile = m.caption(tile, short)
            sheet[r * cell_h:(r + 1) * cell_h, c * m.TILE:(c + 1) * m.TILE] = tile
        sn = sheet_idx // per_sheet
        out_path = os.path.join(m.OUT_DIR, f"{subject}_singlebox_sheet{sn:02d}.png")
        cv2.imwrite(out_path, sheet)
        print(f"  wrote {out_path}")


if __name__ == "__main__":
    main()
