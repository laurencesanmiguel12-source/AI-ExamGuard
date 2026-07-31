"""Contact-sheet generator for the last unswept fairness-audit item: subjects 01/06/09/24, the
four OEP subjects gt.txt documents *real* phone-use for (see ai_examguard_fairness_audit_findings
memory). The other seven subjects got a blanket phone-box strip after full visual review found
100% of their "phone" boxes were actually the study's own clip-on eye-tracking camera, background
clutter, or a pen. These four can't get the same treatment - they have a genuine mix of real held
phones and possibly the same confounders - so each phone-positive frame needs an individual
keep/drop judgment instead of a blanket rule.

This script doesn't judge anything itself. It crops a padded region around each frame's phone box
(so the reviewer can see the object plus a little surrounding context, not the whole 640x480 frame
at thumbnail size where a small device is unreadable), tiles crops into labeled grid sheets, and
writes them out for visual review via the Read tool. Each tile is captioned with the frame's numeric
id so a decision can be mapped back to the source file.

Usage: ../.venv/Scripts/python.exe build_phone_box_contact_sheets.py [--subject subject01]
       (default: all four subjects, one set of sheets per subject)
"""
import argparse
import os

import cv2
import numpy as np

BATCH_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "annotation_batch")
OUT_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "subject01_06_09_24_review_sheets")

SUBJECTS = ("subject01", "subject06", "subject09", "subject24")
PHONE_CLASS = "0"

TILE = 160          # thumbnail size (square) for each crop
COLS, ROWS = 6, 6   # 36 frames per sheet
PAD_FRAC = 1.2       # padding around the box, as a fraction of the box's own size


BOX_COLORS = [(0, 0, 255), (0, 220, 0), (255, 140, 0), (255, 0, 255)]  # per-box-index colors, BGR


def load_phone_boxes(label_path, img_w, img_h):
    """Returns a list of ALL phone-class boxes in the frame (a frame can have more than one -
    e.g. the eye-tracker device AND a separately-boxed genuine held phone in the same frame)."""
    if not os.path.exists(label_path):
        return []
    boxes = []
    with open(label_path) as f:
        for line in f:
            parts = line.split()
            if not parts or parts[0] != PHONE_CLASS:
                continue
            cx, cy, w, h = (float(v) for v in parts[1:5])
            x1, y1 = (cx - w / 2) * img_w, (cy - h / 2) * img_h
            x2, y2 = (cx + w / 2) * img_w, (cy + h / 2) * img_h
            boxes.append((x1, y1, x2, y2))
    return boxes


def make_tile(img_path, boxes):
    """boxes: list of (x1,y1,x2,y2) - crop covers the union of all of them, each drawn numbered
    in its own color so a frame with an eye-tracker box AND a separate genuine-phone box can be
    told apart at a glance."""
    image = cv2.imread(img_path)
    h, w = image.shape[:2]
    ux1 = min(b[0] for b in boxes)
    uy1 = min(b[1] for b in boxes)
    ux2 = max(b[2] for b in boxes)
    uy2 = max(b[3] for b in boxes)
    bw, bh = ux2 - ux1, uy2 - uy1
    pad_x, pad_y = bw * PAD_FRAC, bh * PAD_FRAC
    cx1 = max(0, int(ux1 - pad_x))
    cy1 = max(0, int(uy1 - pad_y))
    cx2 = min(w, int(ux2 + pad_x))
    cy2 = min(h, int(uy2 + pad_y))
    crop = image[cy1:cy2, cx1:cx2].copy()
    if crop.size == 0:
        crop = image.copy()
        cx1, cy1 = 0, 0

    for i, (x1, y1, x2, y2) in enumerate(boxes):
        rx1, ry1 = int(x1 - cx1), int(y1 - cy1)
        rx2, ry2 = int(x2 - cx1), int(y2 - cy1)
        color = BOX_COLORS[i % len(BOX_COLORS)]
        cv2.rectangle(crop, (rx1, ry1), (rx2, ry2), color, 1)
        cv2.putText(crop, str(i), (rx1, max(10, ry1 - 2)), cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1, cv2.LINE_AA)

    # keep aspect ratio, letterbox onto a square TILE x TILE canvas
    ch, cw = crop.shape[:2]
    scale = min(TILE / cw, TILE / ch)
    nw, nh = max(1, int(cw * scale)), max(1, int(ch * scale))
    resized = cv2.resize(crop, (nw, nh))
    canvas = np.full((TILE, TILE, 3), 40, dtype=np.uint8)
    ox, oy = (TILE - nw) // 2, (TILE - nh) // 2
    canvas[oy:oy + nh, ox:ox + nw] = resized
    return canvas


CAPTION_H = 16


def caption(tile, text):
    out = np.full((TILE + CAPTION_H, TILE, 3), 255, dtype=np.uint8)
    out[:TILE, :] = tile
    cv2.putText(out[TILE:], text, (2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (0, 0, 0), 1, cv2.LINE_AA)
    return out


def build_sheets(subject):
    fnames = sorted(
        f for f in os.listdir(BATCH_DIR)
        if f.startswith(subject) and f.lower().endswith(".jpg")
    )
    frames = []
    for fname in fnames:
        img_path = os.path.join(BATCH_DIR, fname)
        label_path = os.path.splitext(img_path)[0] + ".txt"
        image = cv2.imread(img_path)
        if image is None:
            continue
        h, w = image.shape[:2]
        boxes = load_phone_boxes(label_path, w, h)
        if not boxes:
            continue
        frames.append((fname, boxes))

    print(f"{subject}: {len(frames)} phone-positive frames")
    os.makedirs(OUT_DIR, exist_ok=True)

    per_sheet = COLS * ROWS
    cell_h = TILE + CAPTION_H
    manifest_lines = []
    for sheet_idx in range(0, len(frames), per_sheet):
        chunk = frames[sheet_idx:sheet_idx + per_sheet]
        sheet = np.full((cell_h * ROWS, TILE * COLS, 3), 255, dtype=np.uint8)
        for i, (fname, boxes) in enumerate(chunk):
            r, c = divmod(i, COLS)
            # short id: the zero-padded frame number, e.g. "00042"
            short = fname.replace(subject + "_frame", "").replace(".jpg", "")
            if len(boxes) > 1:
                short += f" x{len(boxes)}"
            tile = make_tile(os.path.join(BATCH_DIR, fname), boxes)
            tile = caption(tile, short)
            sheet[r * cell_h:(r + 1) * cell_h, c * TILE:(c + 1) * TILE] = tile
        sheet_num = sheet_idx // per_sheet
        out_path = os.path.join(OUT_DIR, f"{subject}_sheet{sheet_num:02d}.png")
        cv2.imwrite(out_path, sheet)
        manifest_lines.append(f"{subject}_sheet{sheet_num:02d}.png: {[f for f, _ in chunk]}")

    manifest_path = os.path.join(OUT_DIR, f"{subject}_manifest.txt")
    with open(manifest_path, "w") as f:
        f.write("\n".join(manifest_lines) + "\n")
    print(f"  {len(frames)} frames -> {(len(frames) + per_sheet - 1) // per_sheet} sheets, manifest at {manifest_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", choices=SUBJECTS, default=None)
    args = parser.parse_args()

    targets = [args.subject] if args.subject else list(SUBJECTS)
    for subject in targets:
        build_sheets(subject)


if __name__ == "__main__":
    main()
