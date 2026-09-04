"""Report exams whose passing_score looks like it was entered as POINTS rather than a percentage.

Background: passing_score is a percentage - exam_session_service computes
`passed = score / total_points * 100 >= passing_score`. The exam form's hint used to say the
opposite ("Points needed to pass, out of the total above - not a percentage"), so values entered
before that was corrected may mean something different from what the instructor intended. On a
50-point exam, an instructor typing "30" meant 30 points (60%); the scorer reads it as 30%, i.e.
15 points - a much more lenient exam than intended, with nothing anywhere reporting the mismatch.

READ-ONLY. This prints what it finds and the UPDATE that would fix each row; it changes nothing.
Deciding what a given exam was meant to require is a judgement about the instructor's intent, not
something to infer automatically - a genuine 30% pass mark is indistinguishable from a mis-entered
"30 points" without asking.

Exams totalling exactly 100 points are unaffected by construction (the two readings coincide) and
are reported as OK. So are exams already submitted against, where changing the threshold now would
retroactively alter results that students have already been shown - those are flagged separately
and deliberately left for a human to decide.

Usage (from the repo root, with backend/.env pointing at the database to audit):
  python scripts/audit_passing_score.py
"""
import os
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", ".env")

QUERY = text("""
    SELECT e.id, e.title, e.total_points, e.passing_score,
           (SELECT COUNT(*) FROM exam_sessions s
             WHERE s.exam_id = e.id AND s.submitted_at IS NOT NULL) AS submitted
      FROM exams e
     ORDER BY e.id
""")


def main():
    load_dotenv(ENV_PATH)
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit(f"DATABASE_URL not set - looked in {ENV_PATH}")

    # Say which database, so this is never run against production believing it to be dev.
    print(f"Auditing {url.rsplit('@', 1)[-1]}\n")

    with create_engine(url).connect() as conn:
        rows = conn.execute(QUERY).fetchall()

    suspect = []
    for exam_id, title, total_points, passing_score, submitted in rows:
        if not total_points or total_points == 100:
            status = "OK (100-point exam, both readings agree)" if total_points == 100 else \
                     "SKIP (no total_points set)"
            print(f"  [{exam_id}] {title[:38]:<38} {status}")
            continue

        as_percentage = passing_score
        as_points = passing_score / total_points * 100
        print(f"  [{exam_id}] {title[:38]:<38} total={total_points:<4} passing_score={passing_score}")
        print(f"        currently requires {as_percentage}% "
              f"({as_percentage / 100 * total_points:.4g} of {total_points} points)")
        print(f"        if it was meant as POINTS, it should be {as_points:.4g}%"
              f"{'  <-- and %d submitted attempt(s) already scored against the current value' % submitted if submitted else ''}")
        suspect.append((exam_id, title, round(as_points), submitted))

    if not suspect:
        print("\nNothing to review - no exam can be read both ways.")
        return

    print(f"\n{len(suspect)} exam(s) where the two readings differ. Review each against what the "
          f"instructor intended;\nif it was entered as points, the corrected value is:\n")
    for exam_id, title, corrected, submitted in suspect:
        warn = "  -- WARNING: has submitted attempts, changing this alters recorded results" \
            if submitted else ""
        print(f"  UPDATE exams SET passing_score = {corrected} WHERE id = {exam_id};"
              f"  -- {title}{warn}")


if __name__ == "__main__":
    sys.exit(main())
