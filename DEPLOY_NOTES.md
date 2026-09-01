# Deploy notes — pending release (written 2026-09-01)

**Read this on the host PC before deploying. Delete this file once the deploy is verified live.**

These notes are for whoever (or whatever) runs the deploy on the host machine. They were written
on a dev PC that is *not* the host — it has no `~/.cloudflared/config.yml` and no tunnel service,
so it could not deploy, only push. Everything below is verified on that dev PC against a real
Postgres 18 and a real uvicorn server, but **nothing is live yet**.

## What is being deployed

Commit `b5caa9c` — fixes the live report that instructor accounts could not find students in any
list. Three independent causes, plus a follow-up commit fixing a super-admin UI lockout found
while tracing them. Full reasoning is in the commit messages; the short version:

1. `require_exam_owner` used `Subject` without importing it → `NameError` → **HTTP 500 for every
   admin/super_admin** on exam roster, exam content, reports, and exam update/delete. The
   instructor branch never touched `Subject`, which is why the existing tests passed.
2. Instructors had **no route to a student list at all** — `/students` was admin-only in both
   `App.jsx` and `Sidebar.jsx`, even though `GET /students/` already allowed any authenticated
   user scoped to their own school.
3. `users.username` was **globally unique across every school while nothing ever read it** (login
   and every lookup key on email). Its only live effect was rejecting registrations with
   "Username already exists." when an unrelated school had taken the name — so a second school's
   student never got an account and was correctly absent from every roster. Column dropped.
4. `super_admin` was absent from every `roles`/`allowedRoles` array while `ProtectedRoute` did a
   literal `includes(user.role_name)` → empty sidebar, bounced off every page, and fell through
   to the student dashboard. Now goes through `frontend/src/utils/roles.js`.

## Deploy order — backend FIRST. This matters.

The new backend **accepts and ignores** a `username` field, so the currently-deployed frontend
keeps working after the backend goes up (verified: HTTP 200). The reverse is not true — the new
frontend omits `username` and the old backend rejects that with 422. So:

**Backend first, then frontend.** No synchronized deploy or downtime window is needed.

### 1. Backend (this host)

```bash
cd <repo>
python scripts/backup_db.py      # DO NOT SKIP - migration drops a column from live data
git pull
docker compose up -d --build     # `alembic upgrade head` runs automatically on container start
docker ps                        # confirm the backend container is actually running
curl http://localhost:8000/docs  # confirm LOCALLY before trusting the public tunnel URL
```

A tunnel with nothing listening on its port looks like a silent dead background process — always
confirm the two commands above locally first.

### 2. Frontend (Cloudflare Pages)

The tunnel only exposes the API (`deploy/cloudflared.config.yml.example`); the frontend is on
Cloudflare Pages. It did **not** auto-deploy from the push (polled for ~4 minutes after
`b5caa9c` landed, bundle hash unchanged), so it needs whatever manual Pages deploy step this
project normally uses:

```bash
cd frontend && pnpm install && pnpm build
# then deploy frontend/dist/ to Pages
```

Confirm `frontend/.env`'s `VITE_API_BASE_URL` and `backend/.env`'s `ALLOWED_ORIGINS` are still
correct before building.

## How to verify it actually went live

Before the deploy this returns **422 `username Field required`**. After, it must not mention
`username` at all (a 404/400 about the bogus `course_id` is the expected success signal):

```bash
curl -X POST https://api.aiexamguard.com/auth/register -H 'Content-Type: application/json' \
  -d '{"email":"x@x.com","password":"x","first_name":"a","last_name":"b","course_id":999999}'
```

Frontend — the live bundle currently still contains `{to:'/students',...roles:['admin']}` and 4
"Username" labels. After the Pages deploy, neither should be present:

```bash
B=$(curl -s https://aiexamguard.com | grep -oE '/assets/index-[A-Za-z0-9_-]+\.js' | head -1)
curl -s "https://aiexamguard.com$B" | grep -c -i username    # expect 0
```

Then log in as an instructor and confirm a **Students** entry appears in the sidebar, and as an
admin open an exam roster and confirm it loads instead of erroring.

## Rollback

Migration `b4e1c0a97d32` has a working `downgrade()` — verified against a seeded Postgres 18. It
re-adds `username`, backfills it from `email`, and restores the NOT NULL + UNIQUE constraints. The
**original usernames are not recoverable**, which is fine because nothing read them, but it is why
the backup step above is not optional.

```bash
docker compose exec backend alembic downgrade 0a75dc28ca83
```

## Verified before push (on the dev PC, not here)

- Backend suite 109/109; full `test_system_smoke.py` end-to-end flow passes.
- Migration up **and** down against real Postgres 18 seeded with existing rows.
- Real uvicorn + real HTTP: two schools each registered a "John Smith" (both 200, the exact case
  that used to fail); duplicate email still rejected including mixed case; a stale client still
  sending `username` still gets 200; instructor `GET /students/` returned only their own school's
  students.
- `node frontend/src/utils/roles.selfcheck.mjs` passes; frontend lint and build clean.

## Still open — not fixed, do not assume these are done

- If instructors *still* report missing students after this deploy, the next suspect is
  `ExamRosterService.get_available_students`, which filters `Student.course_id ==
  subject.course_id`. A student who registered under a different course than the exam's subject is
  invisible to that roster **by design**, not by bug. That is a data/workflow question, not a code
  fix — check what course the missing students actually registered under before changing anything.
- There is no super-admin UI for managing schools or platform users; those routes exist on the
  backend with no page in front of them. The super-admin fix here only stops the lockout from the
  normal admin UI.
