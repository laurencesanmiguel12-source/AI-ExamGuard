"""A third slice of the demographic bias audit proxy work (see
ai_examguard_thesis_scope_recommendations memory, priority item #1), and the one that actually needs
external data: this project's own OEP dataset has zero head-covering variation to test against, and
scraping random photos off the web for this would carry no consent, no license, and no reliable
"this person is wearing a headscarf" label - a bad foundation for a fairness claim in a thesis that
has otherwise been careful about honest, disclosed evaluation.

Meta's FACET dataset (https://ai.meta.com/datasets/facet/) is the deliberate alternative: licensed
(not scraped) photography, expert-annotated for exactly the "headscarf" and "lighting condition"
attributes this project scoped in (see the 2026-08-01 scope-narrowing note in
ai_examguard_thesis_scope_recommendations - skin tone was dropped, lighting/camera-quality/head-
coverings were kept). It's gated behind Meta's research-use license (an account/agreement step at
the URL above - not something this script can do for you).

What this measures: the real YuNet face detector's detection rate, grouped by FACET's `has_headscarf`
flag and derived lighting-condition label - same "does the app's actual detector work as well for
this group" question fairness_audit.py asks of the OEP subjects, just on a dataset that actually has
this attribute to group by.

**Reads directly out of the images tar, never extracts it to disk** - FACET's image archive is
~12.3GB, which didn't fit in the free space available when this was built. tarfile can stream
individual members out of an uncompressed tar without extracting the rest, so this does one
sequential pass and decodes only the images actually needed (deduplicated by filename, since a
photo with multiple annotated people has one row per person but the face-detection result is
whole-image-level either way).

**FACET's images are split across multiple downloadable shards** (confirmed 2026-08-01: the first
downloaded tar only contained 10,567 of the 31,702 filenames the annotations reference - it was one
shard, not the whole set, and the disk doesn't have room to hold more than one shard at a time
alongside everything else in this repo). Results persist to `--cache-file` (a filename -> bool JSON
map) across runs, so the intended workflow is: download one shard, run this script against it,
delete the shard, download the next, rerun (already-cached filenames are skipped, so this only ever
scans the *new* shard's contents) - repeat until `missing` in the printed summary reaches the
irreducible "genuinely not in any shard" floor. Running with no tar present at all just re-reports
from whatever's cached so far.

Column names confirmed against the real downloaded annotations.csv (49,551 person-rows, 31,702
unique images): `filename`, `has_headscarf` (clean binary flag), and five `lighting_*` one-hot-ish
columns (`lighting_underexposed/dimly_lit/well_lit/na/overexposed` - not always strictly one-hot,
~9% of rows have a 2-way tie between two lighting columns and ~0.7% have none set; the per-row label
below is just the argmax, so ties are broken by column order, not a deliberate judgment call).

Usage: ../.venv/Scripts/python.exe facet_headwear_lighting_audit.py
  [--annotations datasets/facet/annotations/annotations.csv] [--images-tar datasets/facet/facet_imgs.tar]
  [--cache-file datasets/facet/face_detection_cache.json]
"""
import argparse
import concurrent.futures
import json
import os
import tarfile
import time

import cv2
import numpy as np
import pandas as pd

YUNET_PATH = os.path.join(os.path.dirname(__file__), "..", "app", "resources", "face_detection_yunet_2023mar.onnx")
FACET_DIR = os.path.join(os.path.dirname(__file__), "datasets", "facet")

_WORKER_DETECTOR = None


def _init_worker():
    # OpenCV parallelizes each detect() call internally across cores by default - fine for one
    # image at a time, but counterproductive once we're also parallelizing across images: pin
    # each worker to one thread so process-level parallelism does the work instead.
    cv2.setNumThreads(1)
    global _WORKER_DETECTOR
    _WORKER_DETECTOR = cv2.FaceDetectorYN_create(YUNET_PATH, "", (320, 320), 0.6, 0.3, 5000)


def _decode_and_detect(name_and_bytes):
    name, data = name_and_bytes
    array = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        return name, None
    h, w = image.shape[:2]
    _WORKER_DETECTOR.setInputSize((w, h))
    _, faces = _WORKER_DETECTOR.detect(image)
    return name, faces is not None and len(faces) > 0


def load_cache(cache_path):
    if os.path.exists(cache_path):
        with open(cache_path) as f:
            return json.load(f)
    return {}


def save_cache(cache, cache_path):
    # Write-then-rename so an interrupted save (e.g. this shard's scan gets killed mid-write)
    # can't leave a truncated/corrupt cache file behind.
    tmp_path = cache_path + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(cache, f)
    os.replace(tmp_path, cache_path)


def build_face_detection_cache(tar_path, filenames_needed, workers, cache, cache_path, batch_size=500):
    """Streams raw bytes sequentially out of the tar (I/O, unavoidably single-threaded - tarfile
    only supports one read position), then decodes+detects each image in a process pool. Batched
    submission keeps memory bounded (~batch_size images' worth of JPEG bytes at a time, not all
    ~31k buffered at once). Updates `cache` in place and saves it to disk after every batch, since
    FACET's images are split across multiple shards this script gets re-run once per shard - a
    filename already in `cache` from a prior shard is skipped here, and this shard's new results
    get persisted so nothing already found has to be re-scanned on the next shard's run."""
    needed = set(filenames_needed) - set(cache)
    total = len(needed)
    if total == 0:
        print("Every needed filename is already in the cache - nothing new to scan in this tar.")
        return
    done = 0
    start = time.time()

    with tarfile.open(tar_path, "r") as tar, \
         concurrent.futures.ProcessPoolExecutor(max_workers=workers, initializer=_init_worker) as pool:
        batch = []
        for member in tar:
            if not needed:
                break
            if not member.isfile():
                continue
            name = os.path.basename(member.name)
            if name not in needed:
                continue
            f = tar.extractfile(member)
            if f is None:
                continue
            batch.append((name, f.read()))
            needed.discard(name)

            if len(batch) >= batch_size:
                for bname, hit in pool.map(_decode_and_detect, batch):
                    cache[bname] = hit
                save_cache(cache, cache_path)
                done += len(batch)
                elapsed = time.time() - start
                print(f"  {done}/{total} new images processed ({elapsed:.0f}s elapsed, "
                      f"{done / elapsed:.1f}/s, ~{(total - done) / (done / elapsed):.0f}s left)",
                      flush=True)
                batch = []

        if batch:
            for bname, hit in pool.map(_decode_and_detect, batch):
                cache[bname] = hit
            save_cache(cache, cache_path)
            done += len(batch)
            print(f"  {done}/{total} new images processed (final batch, {time.time() - start:.0f}s total)",
                  flush=True)


def report_by_group(df, group_labels, filename_col, cache, label):
    print(f"\n--- face detection rate by {label} ---")
    grouped = df.groupby(group_labels)
    for group_value, group_df in grouped:
        hits, n = 0, 0
        for fname in group_df[filename_col].unique():
            result = cache.get(fname)
            if result is None:
                continue
            n += 1
            hits += int(result)
        rate = hits / n if n else float("nan")
        rate_str = f"{rate:.3f}" if rate == rate else "n/a"
        print(f"  {group_value!r:<25} n={n:<6} face_detection_rate={rate_str}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--annotations", default=os.path.join(FACET_DIR, "annotations", "annotations.csv"))
    parser.add_argument("--images-tar", default=os.path.join(FACET_DIR, "facet_imgs.tar"))
    # Deliberately outside datasets/ (gitignored wholesale) so the finished result can be
    # committed without needing FACET's ~24.5GB of images re-downloaded to reproduce it.
    parser.add_argument("--cache-file", default=os.path.join(
        os.path.dirname(__file__), "facet_face_detection_cache.json"))
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    args = parser.parse_args()

    if not os.path.exists(args.annotations):
        raise SystemExit(
            f"Expected annotations at {args.annotations}.\n"
            "Download FACET from https://ai.meta.com/datasets/facet/ (requires agreeing to Meta's "
            "research-use license) and point --annotations at wherever you put it."
        )

    df = pd.read_csv(args.annotations)

    if "filename" not in df.columns or "has_headscarf" not in df.columns:
        raise SystemExit(
            "Expected 'filename' and 'has_headscarf' columns, didn't find them.\n"
            f"Actual columns: {list(df.columns)}\n"
            "The schema may have changed since this script was written - update the hardcoded "
            "column names above to match."
        )

    lighting_cols = [c for c in df.columns if c.startswith("lighting_")]
    if not lighting_cols:
        raise SystemExit(f"No lighting_* columns found. Actual columns: {list(df.columns)}")
    df["_lighting_label"] = df[lighting_cols].idxmax(axis=1).str.replace("lighting_", "", regex=False)

    needed_filenames = df["filename"].unique()
    cache = load_cache(args.cache_file)
    print(f"Cache at {args.cache_file} already has {len(cache)} images from prior shard(s).")

    if os.path.exists(args.images_tar):
        print(f"Scanning {args.images_tar} for {len(needed_filenames)} unique images "
              f"({len(df)} person-rows total, {args.workers} worker processes)...")
        build_face_detection_cache(args.images_tar, needed_filenames, args.workers, cache, args.cache_file)
    else:
        print(f"No tar at {args.images_tar} - reporting from the cache only, no new shard to scan.")

    found = sum(1 for fname in needed_filenames if cache.get(fname) is not None)
    missing = len(needed_filenames) - found
    print(f"Cache now covers {found}/{len(needed_filenames)} needed images "
          f"({missing} not found in any shard scanned so far).")

    report_by_group(df, df["has_headscarf"], "filename", cache, "has_headscarf")
    report_by_group(df, df["_lighting_label"], "filename", cache, "lighting condition")


if __name__ == "__main__":
    main()
