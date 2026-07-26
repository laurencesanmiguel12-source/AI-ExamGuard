"""Extract webcam stills from a subset of the MSU OEP dataset (see
https://cvlab.cse.msu.edu/project-OEP.html), as raw material for manually annotating phone/face
bounding boxes - the OEP dataset itself only has event-level cheat-type timestamps (gt.txt), not
bounding boxes, so this is a starting point for labeling, not a finished dataset.

Only extracts from the *webcam* .avi (not the wearcam) - the wearcam is a first-person view from
glasses, a completely different framing than the laptop-webcam angle this app actually captures at
inference time. Per READ_ME.txt, each subject folder has exactly two .avi files sharing a common
(real-name) prefix, differing only in a trailing "1" (webcam) or "2" (wearcam) before the
extension - e.g. "Yousef1.avi"/"Yousef2.avi", "huangpi21.avi"/"huangpi22.avi".

Deliberately never touches or propagates those source filenames: the OEP subject folders are
already anonymized as "subjectN", but the .avi/.wav filenames inside leak the participants' real
usernames (confirmed in READ_ME.txt - "we use the username as the name of the audio file").
Output frames are named purely from the subject NUMBER, so that real name never appears anywhere
in the derived dataset.

Usage: ../../.venv/Scripts/python.exe extract_oep_frames.py [--fps 1] [--subjects 1,2,3,4,10,11,12,13]
"""
import argparse
import os

import cv2

OEP_ROOT = r"C:\Users\maryj\Downloads\OEP_database\OEP database"
OUT_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "raw_frames")

# From READ_ME.txt: 15 "actor" subjects (told to improvise cheating) vs 9 "real exam" subjects
# (covertly prompted by a proctor). Default subset takes 4 of each for behavioral diversity.
ACTOR_SUBJECTS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 17, 20, 21, 22, 23, 24]
REAL_SUBJECTS = [10, 11, 12, 13, 14, 15, 16, 18, 19]
DEFAULT_SUBSET = [1, 2, 3, 4, 10, 11, 12, 13]


def find_webcam_avi(subject_dir):
    avis = [f for f in os.listdir(subject_dir) if f.lower().endswith(".avi")]
    if len(avis) != 2:
        raise ValueError(f"expected exactly 2 .avi files in {subject_dir}, found {len(avis)}")

    stems = [os.path.splitext(f)[0] for f in avis]
    a, b = stems
    if a[:-1] != b[:-1] or {a[-1], b[-1]} != {"1", "2"}:
        raise ValueError(f"unexpected .avi naming in {subject_dir}: {avis}")

    webcam_stem = a if a[-1] == "1" else b
    return os.path.join(subject_dir, webcam_stem + ".avi")


def extract_subject(subject_num, sample_fps):
    subject_dir = os.path.join(OEP_ROOT, f"subject{subject_num}")
    webcam_path = find_webcam_avi(subject_dir)

    cap = cv2.VideoCapture(webcam_path)
    video_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_interval = max(1, round(video_fps / sample_fps))

    out_subdir = os.path.join(OUT_DIR, f"subject{subject_num:02d}")
    os.makedirs(out_subdir, exist_ok=True)

    frame_idx = 0
    saved = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if frame_idx % frame_interval == 0:
            out_path = os.path.join(out_subdir, f"subject{subject_num:02d}_frame{saved:05d}.jpg")
            cv2.imwrite(out_path, frame)
            saved += 1
        frame_idx += 1
    cap.release()

    return saved


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fps", type=float, default=1.0, help="frames to sample per second of video")
    parser.add_argument(
        "--subjects", type=str, default=",".join(str(s) for s in DEFAULT_SUBSET),
        help="comma-separated subject numbers (1-24)"
    )
    args = parser.parse_args()
    subjects = [int(s) for s in args.subjects.split(",")]

    if not os.path.isdir(OEP_ROOT):
        raise SystemExit(f"{OEP_ROOT} not found - update OEP_ROOT if you extracted it elsewhere.")

    total = 0
    for subject_num in subjects:
        kind = "actor" if subject_num in ACTOR_SUBJECTS else "real-exam"
        saved = extract_subject(subject_num, args.fps)
        total += saved
        print(f"subject{subject_num:02d} ({kind}): {saved} frames -> {OUT_DIR}/subject{subject_num:02d}/")

    print(f"\n{total} frames extracted from {len(subjects)} subjects to {OUT_DIR}")
    print("Next step: annotate phone/face boxes in these frames (see earlier discussion on CVAT/LabelImg).")


if __name__ == "__main__":
    main()
