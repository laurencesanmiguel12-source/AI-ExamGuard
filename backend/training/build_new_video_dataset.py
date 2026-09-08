"""Turn the reviewed new_video draft labels into a YOLO train split + an untouched multi-person
holdout, subject-split so no person appears on both sides.

Person map (from visual review of contact sheets, 2026-09-08):
  p1  man, beige wall           1788827228145881/147403/147533   - DROPPED: draft misses many
                                                                   held-low white phones (FN-heavy),
                                                                   labels not reliable enough to train on
  p2  young man, guitar room    WIN_20260907_17_56_50 + 0908_08_30_06 + 0908_08_32_05
  p3  girl, blouse, TV room     WIN_20260908_01_55_53 / 01_59_07 / 02_04_42 / 02_07_53
  p6  girl, cardigan, bedroom   WIN_20260908_01_45_12 / 01_48_26 / 01_51_53
  --- held out (never trained on) ---
  p4  young man, pink shirt     WIN_20260907_23_46_13          - phone-heavy, draft ~clean
  p5  girl, decorated case      Copy_of_WIN_20260907_23_45_14   - phone-heavy + head-down, draft clean

Label cleanup applied to every kept frame:
  * drop phone boxes stuck to the bottom edge (cy>0.92, wide, short) - desk/monitor-strip FPs
    seen in p3's videos during review.

Train frames are stride-sampled (STRIDE) because 1fps webcam frames are near-duplicates - keeps the
4-person new contribution from swamping the ~1.8k-frame OEP portion of the training set the way the
single-person personal video did (see ai_examguard_phone_detection_personal_video_labeling).

Usage: ../.venv/Scripts/python.exe build_new_video_dataset.py
"""
import glob
import os
import shutil

HERE = os.path.dirname(__file__)
FRAMES = os.path.join(HERE, "datasets", "new_video", "frames")
OUT = os.path.join(HERE, "datasets", "new_video")
STRIDE = 2

PERSON_VIDEOS = {
    "p2": ["WIN_20260907_17_56_50_Pro", "WIN_20260908_08_30_06_Pro", "WIN_20260908_08_32_05_Pro"],
    "p3": ["WIN_20260908_01_55_53_Pro", "WIN_20260908_01_59_07_Pro",
           "WIN_20260908_02_04_42_Pro", "WIN_20260908_02_07_53_Pro"],
    "p6": ["WIN_20260908_01_45_12_Pro", "WIN_20260908_01_48_26_Pro", "WIN_20260908_01_51_53_Pro"],
    "p4": ["WIN_20260907_23_46_13_Pro"],
    "p5": ["Copy_of_WIN_20260907_23_45_14_Pro"],
}
TRAIN_PEOPLE = ["p2", "p3", "p6"]
HOLDOUT_PEOPLE = ["p4", "p5"]

VIDEO_TO_PERSON = {v: p for p, vs in PERSON_VIDEOS.items() for v in vs}


def clean_lines(txt_path):
    out = []
    dropped = 0
    for ln in open(txt_path):
        q = ln.split()
        if len(q) != 5:
            continue
        cls = q[0]
        cx, cy, bw, bh = map(float, q[1:])
        if cls == "0" and cy > 0.92 and bw > 0.15 and bh < 0.09:
            dropped += 1
            continue
        out.append(ln.strip())
    return out, dropped


def reset(d):
    if os.path.isdir(d):
        shutil.rmtree(d)
    os.makedirs(os.path.join(d, "images"))
    os.makedirs(os.path.join(d, "labels"))


def main():
    train_dir = os.path.join(OUT, "split", "train")
    hold_dir = os.path.join(OUT, "holdout")
    reset(train_dir)
    reset(hold_dir)

    counts = {}
    total_dropped = 0
    per_video_idx = {}

    for img in sorted(glob.glob(os.path.join(FRAMES, "*.jpg"))):
        base = os.path.basename(img)
        video = base.rsplit("_f", 1)[0]
        person = VIDEO_TO_PERSON.get(video)
        if person is None:
            continue  # p1 - dropped
        txt = img[:-4] + ".txt"
        if not os.path.exists(txt):
            continue

        if person in HOLDOUT_PEOPLE:
            dest = hold_dir
        elif person in TRAIN_PEOPLE:
            i = per_video_idx.get(video, 0)
            per_video_idx[video] = i + 1
            if i % STRIDE != 0:
                continue
            dest = train_dir
        else:
            continue

        lines, dropped = clean_lines(txt)
        total_dropped += dropped
        name = f"{person}_{base}"
        shutil.copy2(img, os.path.join(dest, "images", name))
        with open(os.path.join(dest, "labels", name[:-4] + ".txt"), "w") as f:
            f.write("\n".join(lines) + ("\n" if lines else ""))

        key = ("holdout" if dest is hold_dir else "train", person)
        c = counts.setdefault(key, {"frames": 0, "phone": 0})
        c["frames"] += 1
        c["phone"] += any(l.startswith("0 ") for l in lines)

    print(f"dropped {total_dropped} bottom-edge phone FP boxes\n")
    for (split, person), c in sorted(counts.items()):
        print(f"  {split:8s} {person}  frames={c['frames']:4d}  phone-positive={c['phone']:4d}")
    tr = sum(c["frames"] for (s, _), c in counts.items() if s == "train")
    ho = sum(c["frames"] for (s, _), c in counts.items() if s == "holdout")
    print(f"\ntrain: {tr} frames -> {train_dir}")
    print(f"holdout: {ho} frames -> {hold_dir} (NEVER add to data.yaml)")
    print("\nNext: append the train images path to datasets/phone-face-yolo/data.yaml, then "
          "finetune_phone_face.py --epochs 8 --batch 8 --imgsz 416")


if __name__ == "__main__":
    main()
