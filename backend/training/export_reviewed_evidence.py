"""Copies admin-approved live-exam violation evidence into its own isolated review folder,
same discipline as prepare_personal_phone_video_review.py: new sources never land directly in
annotation_batch/, they get draft-labeled and human-corrected from their own folder first (see
ai_examguard_backend_gotchas memory - auto_annotate_oep.py once clobbered already-reviewed work
by skipping this).

This script only moves bytes out of the live evidence store and stamps training_exported_at so
RetentionService's 90-day purge can proceed on the original. It does NOT auto-annotate or retrain -
run one of the existing auto_annotate_*.py scripts against OUT_DIR next, then finetune + gate on
evaluate_frozen_holdout.py exactly like every other training batch in this project.

Only PHONE_DETECTED/MULTIPLE_PEOPLE evidence is ever eligible (see
TRAINING_CANDIDATE_EVENT_TYPES in violation_service.py) - no student-identity frames flow through
this pipeline.

Usage: ../../.venv/Scripts/python.exe export_reviewed_evidence.py
"""
import csv
import os
import shutil
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.database import SessionLocal  # noqa: E402
from app.models.violation import Violation  # noqa: E402

OUT_DIR = os.path.join(os.path.dirname(__file__), "datasets", "live_evidence_review")
MANIFEST_PATH = os.path.join(OUT_DIR, "manifest.csv")


def main():
    db = SessionLocal()
    try:
        approved = (
            db.query(Violation)
            .filter(Violation.training_review_status == "APPROVED")
            .filter(Violation.training_exported_at.is_(None))
            .filter(Violation.evidence_path.isnot(None))
            .all()
        )

        if not approved:
            print("Nothing new to export.")
            return

        os.makedirs(OUT_DIR, exist_ok=True)
        write_header = not os.path.exists(MANIFEST_PATH)

        with open(MANIFEST_PATH, "a", newline="") as manifest_file:
            writer = csv.writer(manifest_file)
            if write_header:
                writer.writerow(["violation_id", "event_type", "created_at", "image_file"])

            exported = 0
            for v in approved:
                if not os.path.exists(v.evidence_path):
                    continue

                image_file = f"violation_{v.id}.jpg"
                shutil.copy2(v.evidence_path, os.path.join(OUT_DIR, image_file))
                writer.writerow([v.id, v.event_type, v.created_at.isoformat(), image_file])

                v.training_exported_at = datetime.now(timezone.utc)
                exported += 1

            db.commit()
            print(f"Exported {exported} image(s) to {OUT_DIR}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
