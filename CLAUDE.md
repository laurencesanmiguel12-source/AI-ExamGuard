# AI ExamGuard

Full-stack exam proctoring app: FastAPI backend (`backend/`), React/Vite frontend (`frontend/`),
Chrome extension (`extension/`) for tab-monitoring. Real trained models (OpenCV YuNet+LBPH for
face, fine-tuned YOLOv8 for phone detection, logistic regression for risk scoring) — no mocked ML.

## Deployment target

Self-hosted on a dedicated PC via a named Cloudflare Tunnel (`cloudflared`), not a cloud host —
picked over Render for cost (free vs ~$106/mo) and specs. `docker-compose.yml` at repo root
containerizes Postgres 18 + the FastAPI backend, both `restart: unless-stopped`.

Steps, in order, on the host machine:
1. Point the domain at Cloudflare (nameservers).
2. `cloudflared tunnel login` → `cloudflared tunnel create ai-examguard` → `cloudflared tunnel route dns ai-examguard api.yourdomain.com`.
3. Copy `deploy/cloudflared.config.yml.example` → `~/.cloudflared/config.yml`, fill in the tunnel
   UUID from step 2. Ingress routes `api.yourdomain.com` → `http://localhost:8000`.
4. `cloudflared service install` — run as a persistent Windows service, not a foreground terminal.
5. Once the real frontend origin is known: `python scripts/set_deploy_origin.py https://your-frontend-origin`
   (patches the extension's `EXPECTED_ORIGIN`/`externally_connectable`). Then by hand: set
   `backend/.env`'s `ALLOWED_ORIGINS` and `frontend/.env`'s `VITE_API_BASE_URL` before `vite build`;
   reload the unpacked extension in `chrome://extensions`.
6. Review `docker-compose.yml`/`backend/.env` secrets before exposing anything live.
7. `docker compose up -d --build`, end-to-end test through the real tunnel URL.
8. UPS on the host — exams are scheduled events, mid-session downtime is costly.

**A tunnel with nothing listening on the port it forwards to just looks like a silent dead
background process** — always confirm `docker ps` shows the backend running and
`curl http://localhost:8000/docs` works locally on the host *before* trusting the public tunnel URL.

## Fresh machine / fresh clone setup

`backend/.env` isn't in git — copy `backend/.env.example` to `backend/.env` and fill in real values
(`DATABASE_URL`, `SECRET_KEY` via `python -c "import secrets; print(secrets.token_hex(32))"`).

```
CREATE DATABASE ai_examguard;      -- via psql
cd backend && alembic upgrade head
pip install -r requirements.txt
```

That `pip install` reliably hits two known breaks on any fresh install — fix both, don't assume
they self-heal:
- **bcrypt/passlib incompatibility**: anything above `bcrypt==4.0.1` breaks `hash_password`/
  `verify_password` against this `passlib==1.7.4` (`AttributeError: module 'bcrypt' has no
  attribute '__about__'`, then a misleading `password cannot be longer than 72 bytes` ValueError).
  `requirements.txt` pins `4.0.1` — if login breaks, `pip show bcrypt` and re-downgrade.
- **opencv-python vs opencv-contrib-python collision**: `ultralytics` drags in `opencv-python`,
  which silently deletes `cv2.face.LBPHFaceRecognizer_create` even though `cv2` still imports
  clean. After ANY `pip install -r requirements.txt`, verify:
  `python -c "import cv2; assert hasattr(cv2.face, 'LBPHFaceRecognizer_create')"`. If it fails:
  `pip uninstall opencv-python -y && pip install --force-reinstall --no-deps opencv-contrib-python`.

Frontend: `pnpm` often isn't installed and `corepack enable` needs admin rights this user doesn't
have — use `npm install -g pnpm` instead, then `cd frontend && pnpm install`.

Docker's `postgres:18` image needs its volume mounted at `/var/lib/postgresql`, NOT the pre-18
convention `/var/lib/postgresql/data` — already correct in `docker-compose.yml`, but if any future
compose file setup reports `dependency db failed to start`/unhealthy, check the volume path first.

`docker compose up -d --build` brings up both services; migrations run automatically on every
container start. The Docker image is deliberately CPU-only (no GPU passthrough) even if the host
has CUDA-capable local dev — that's intentional, not a bug.

## Conventions

- Never use `window.confirm()`/`alert()`/`prompt()` in the frontend — freezes browser automation
  and is worse UX. Use `frontend/src/components/ConfirmDialog.jsx`.
- Backend permission model is inconsistent by design: Courses/Subjects/Students/Instructors need
  `require_admin`; exam mutations need `require_instructor` specifically (not admin). Read the
  actual `Depends(...)` on a route, don't assume from the resource's apparent ownership.
- Check the SQLAlchemy model, not just the Pydantic schema, when a create/update 500s with an
  `IntegrityError` on a NOT NULL column — schemas have drifted out of sync with models before.
- After registering a new router in `main.py`, register literal-path routes (e.g. `/live`, `/me`)
  *before* any router with an overlapping `{param}` path, or the param route silently swallows it.
- `uvicorn --reload` on this codebase is unreliable for verifying changes: it can serve stale code
  with no error, and a killed reloader can leave an orphaned worker still serving traffic
  disconnected from its own log. For real verification (and always in prod), kill everything on
  port 8000 and start a fresh non-`--reload` process, or just trust the Docker container.
