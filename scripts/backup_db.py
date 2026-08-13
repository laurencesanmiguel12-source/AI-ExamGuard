"""Daily Postgres backup for the self-hosted deploy - there was no backup strategy at all before
this (confirmed: nothing in docker-compose.yml, no cron/Task Scheduler entry, no cloud sync
anywhere in the repo), which on a single self-hosted PC with real student data (grades, biometric
evidence, appeals) means a drive failure is unrecoverable data loss, not an inconvenience.

Dumps the `db` service (see docker-compose.yml) via `docker compose exec`, gzipped, into
backups/ (gitignored - these are real dumps of production data, never commit them). Rotates:
deletes dumps older than KEEP_DAYS so this doesn't grow unbounded.

This only covers LOCAL backups (protects against a bad migration, accidental deletion, or
corruption) - it does NOT protect against the drive/PC itself failing, since the dump lands on the
same disk as the live data. Copying backups/ offsite (rclone to a free cloud tier, Cloudflare R2,
even a manual periodic copy to another machine) is the natural next step and a real decision left
to the user - not built here.

Usage: python scripts/backup_db.py
Schedule on the host via Windows Task Scheduler (daily, e.g. 3am):
    schtasks /create /tn "AI ExamGuard DB Backup" /tr "\"<path to venv python>\" \"<path to this script>\"" /sc daily /st 03:00
(Or Task Scheduler's GUI: Action = start a program, Program = the venv's python.exe, Arguments =
the full path to this script, Start in = the repo root so docker compose finds docker-compose.yml.)
"""
import gzip
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKUP_DIR = REPO_ROOT / "backups"
DB_NAME = "ai_examguard"
DB_USER = "postgres"
KEEP_DAYS = 14


def run_backup() -> Path:
    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = BACKUP_DIR / f"{DB_NAME}_{timestamp}.sql.gz"

    result = subprocess.run(
        ["docker", "compose", "exec", "-T", "db", "pg_dump", "-U", DB_USER, DB_NAME],
        cwd=REPO_ROOT,
        capture_output=True,
    )
    if result.returncode != 0:
        raise SystemExit(f"pg_dump failed (exit {result.returncode}): {result.stderr.decode(errors='replace')}")

    with gzip.open(out_path, "wb") as f:
        f.write(result.stdout)

    return out_path


def rotate_old_backups():
    cutoff = time.time() - KEEP_DAYS * 86400
    removed = 0
    for f in BACKUP_DIR.glob(f"{DB_NAME}_*.sql.gz"):
        if f.stat().st_mtime < cutoff:
            f.unlink()
            removed += 1
    return removed


def main():
    out_path = run_backup()
    size_kb = out_path.stat().st_size / 1024
    print(f"Backup written: {out_path} ({size_kb:.1f} KB)")

    removed = rotate_old_backups()
    print(f"Rotated {removed} backup(s) older than {KEEP_DAYS} days")


if __name__ == "__main__":
    main()
