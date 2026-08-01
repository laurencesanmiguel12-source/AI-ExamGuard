"""A single curl connection to FACET's CDN URLs (scontent.*.fbcdn.net) crawls at ~5-20KB/s and
never errors out - it just never finishes (ETA computed in DAYS during shard 2's download). That's
consistent with per-connection throttling on Facebook's CDN edge, not a real network problem (a
retry loop doesn't help when the connection never actually fails, just idles near-zero). The CDN
confirmed `Accept-Ranges: bytes` on every shard, so the standard fix for exactly this situation is
what this script does: split the file into N byte ranges and fetch them concurrently over N
separate connections - if the throttle is per-connection (the common case), aggregate throughput
scales with N even though each individual connection stays slow.

Each chunk gets its own retry loop with resume (tracks bytes already written for that chunk and
adjusts the Range start on retry, same idea as curl's -C - but scoped per-chunk instead of
per-file, so one stalled chunk doesn't waste the progress already made by the others).

Usage: ../.venv/Scripts/python.exe parallel_range_download.py <url> <output_path> [--workers 8]
"""
import argparse
import os
import sys
import threading
import time

import requests

CHUNK_TIMEOUT_CONNECT = 15
CHUNK_TIMEOUT_READ = 30
STREAM_BLOCK_SIZE = 1024 * 256

_progress_lock = threading.Lock()
_progress = {}


def _download_chunk(url, path, worker_id, start, end, max_retries=5000):
    """Downloads bytes [start, end] inclusive, resuming this chunk (not the whole file) on
    failure. Writes directly into the pre-allocated output file at the right offset - safe
    because each worker uses its own file handle and disjoint byte ranges never overlap.

    The CDN cuts every connection at ~5MB regardless of range size (confirmed empirically -
    every failure lands within a few hundred KB of a 5MB multiple), so for a >1GB chunk this
    isn't a rare transient error to retry a handful of times, it's the *normal* download shape -
    ~300 reconnects per worker is expected, not exceptional. max_retries is set high accordingly;
    a short fixed backoff (not exponential) matches that it's a deterministic cap, not overload."""
    written = 0
    target = end - start + 1
    failures = 0

    for attempt in range(max_retries):
        try:
            headers = {"Range": f"bytes={start + written}-{end}"}
            with requests.get(url, headers=headers, stream=True,
                               timeout=(CHUNK_TIMEOUT_CONNECT, CHUNK_TIMEOUT_READ)) as resp:
                resp.raise_for_status()
                with open(path, "r+b") as f:
                    f.seek(start + written)
                    for block in resp.iter_content(chunk_size=STREAM_BLOCK_SIZE):
                        f.write(block)
                        written += len(block)
                        with _progress_lock:
                            _progress[worker_id] = written
            if written >= target:
                return
        except (requests.exceptions.RequestException, OSError) as e:
            failures += 1
            if failures <= 2 or failures % 50 == 0:
                print(f"  [worker {worker_id}] reconnect #{failures} at {written}/{target} "
                      f"bytes ({e})", flush=True)
            time.sleep(0.5)

    raise RuntimeError(f"Worker {worker_id} exhausted retries at {written}/{target} bytes")


def _reporter(total_size, stop_event):
    start_time = time.time()
    while not stop_event.wait(60):
        with _progress_lock:
            done = sum(_progress.values())
        elapsed = time.time() - start_time
        rate_mb_s = (done / 1_000_000) / elapsed if elapsed > 0 else 0
        pct = 100 * done / total_size
        print(f"  {done / 1_000_000:.0f}MB / {total_size / 1_000_000:.0f}MB "
              f"({pct:.1f}%), {rate_mb_s:.2f}MB/s aggregate", flush=True)


def download(url, output_path, workers):
    head = requests.head(url, timeout=15, allow_redirects=True)
    head.raise_for_status()
    total_size = int(head.headers["Content-Length"])
    print(f"Total size: {total_size / 1_000_000_000:.2f}GB, {workers} parallel connections")

    # Pre-allocate so every worker can seek+write into its own region independently.
    with open(output_path, "wb") as f:
        f.truncate(total_size)

    chunk_size = total_size // workers
    ranges = []
    for i in range(workers):
        start = i * chunk_size
        end = (start + chunk_size - 1) if i < workers - 1 else total_size - 1
        ranges.append((start, end))
        _progress[i] = 0

    stop_event = threading.Event()
    reporter = threading.Thread(target=_reporter, args=(total_size, stop_event), daemon=True)
    reporter.start()

    threads = []
    errors = []
    for i, (start, end) in enumerate(ranges):
        t = threading.Thread(target=lambda i=i, s=start, e=end: (
            errors.append(sys.exc_info()) if _try_chunk(url, output_path, i, s, e) is False else None
        ))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()
    stop_event.set()

    actual_size = os.path.getsize(output_path)
    if actual_size != total_size or errors:
        raise SystemExit(f"Download incomplete: got {actual_size}, expected {total_size}, "
                          f"{len(errors)} worker(s) failed permanently.")
    print(f"Done: {output_path} ({actual_size} bytes)")


def _try_chunk(url, path, worker_id, start, end):
    try:
        _download_chunk(url, path, worker_id, start, end)
        return True
    except RuntimeError as e:
        print(f"  [worker {worker_id}] PERMANENTLY FAILED: {e}", flush=True)
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("output_path")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    download(args.url, args.output_path, args.workers)


if __name__ == "__main__":
    main()
