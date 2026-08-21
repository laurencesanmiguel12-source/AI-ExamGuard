# Deploy notes — 2026-08-20 session (updated again)

Six commits ready on `origin/master`, none deployed to the live host yet as of this update. Three
of them (`9e8d174`, `7c21c35`, `14b6ce6`) are fixes for bugs reported from the live host itself —
worth prioritizing this deploy round over waiting.

```
9e8d174  Raise client-side audit-poll frequency 1-in-12 -> 1-in-3
14b6ce6  Skip LBPH identity verification on the MediaPipe client-crop path
7c21c35  Require explicit roster entry before a student can see/take an exam
1dc0afb  Expand risk model training data from 11 to 24 real OEP subjects
497c9e9  Add MediaPipe client-side face pre-filter (Phase 1 of client-side inference)
03ffc57  Raise STATIC_IMAGE_DIFF_THRESHOLD 3.0->8.0 for rigid-mount photo spoofs
```

Verified before handing off: full backend suite 86/86 passing (re-run after each new commit),
`pnpm install --frozen-lockfile` clean, frontend `pnpm build` clean. No DB migrations, no `.env`
changes, no extension/manifest changes in any of these six.

## On the host PC

### 1. Pull

```
cd <repo>
git pull origin master
```

### 2. Backend (Docker)

```
docker compose up -d --build
```

The Dockerfile has its own build-time self-check for the opencv-contrib-python/LBPH collision
(fails loudly at build time if it regresses), so this is safe to run unattended. Migrations run
automatically on container start (`alembic upgrade head`) — none are new this round, no-op if so.

**Confirm before trusting the public URL** (per this project's own standing rule — a tunnel with
nothing listening behind it just looks like a silent dead process):
```
docker ps                          # backend + db both up
curl http://localhost:8000/docs    # responds locally
```

### 3. Frontend (`vite preview`, confirmed via the host's own `bbcd791` commit)

```
cd frontend
pnpm install     # picks up @mediapipe/tasks-vision if not already present
pnpm build
```

Then restart whatever process is running `vite preview` on this host so it picks up the new
`dist/`.

### 4. Immediately worth checking post-deploy

- **Roster flip (`7c21c35`) has a real consequence**: any exam with zero roster rows becomes
  invisible to every student the moment this deploys, until an instructor explicitly rosters them
  via Exams → the exam's roster page. If there are real students expecting to see an exam right
  now, roster them BEFORE or immediately after this deploy, not after — check with instructors on
  the live system first if timing matters.
- **Face-mismatch fix (`14b6ce6`)**: the next real exam session should show `identity_match: null`
  (no false MISMATCH badge) on client-side-detected polls instead of random false positives — spot
  check this with a real enrolled student if possible.
- **Head-down fix (`9e8d174`)**: real full-frame face-check polls now happen ~every 15s instead of
  ~every 60s (audit frequency 1-in-12 → 1-in-3) — this is a real, deliberate server-load increase
  for face-check specifically, not a bug. Worth a quick eye on server responsiveness after
  deploying, especially if multiple students are testing at once (see
  `[[ai_examguard_load_testing]]` memory — face-check was already the more load-sensitive endpoint
  before this change).
- Standard check: `https://api.aiexamguard.com/` health payload, `https://aiexamguard.com/` loads.

### 5. Still open, not part of this deploy

Phone detection reported as "taking too long to trigger" — investigated, not resolved. Turns out
`Violation` never stored a confidence value at all (nothing to pull from the host DB, that
suggestion was wrong). Ran a real local smoke-test instead (real phone, real webcam, temporary
debug logging, reverted after): confidence flickered 0.000–0.42 poll-to-poll and a real
`PHONE_DETECTED` violation fired within ~20-30s of the phone appearing — didn't reproduce "slow"
here. Doesn't rule out something host-specific (camera quality, lighting, how the phone's actually
held). See `[[ai_examguard_live_production_bugs_2026_08_20]]` memory for the full writeup. Next
step if this keeps coming up: either add permanent confidence logging so real host data
accumulates, or get a direct description of how the phone is held when it's slow on the host.

### 6. Cleanup

Delete this file once deployed — it's a one-off handoff note, not meant to stick around in the repo.

---

## What each commit actually changes

- **03ffc57** — `STATIC_IMAGE_DIFF_THRESHOLD` 3.0→8.0, tightens liveness detection for a *rigidly
  mounted* phone spoof specifically. No behavior change for genuine students; hand-held spoofs
  unaffected (documented, separate ceiling).
- **497c9e9** — adds client-side face detection (MediaPipe, self-hosted WASM+model) as a pre-filter
  ahead of server-side detection, reducing server load per poll.
- **1dc0afb** — risk-scoring model retrained on 11→24 real OEP subjects. Same three input signals,
  same integration — better-calibrated coefficients from more real evidence.
- **7c21c35** — exam visibility now requires an instructor to explicitly roster a student first,
  flipped from the previous course-wide-by-default behavior. See the consequence note above.
- **14b6ce6** — fixes a real bug `497c9e9` introduced: MediaPipe's face crop has a different
  framing convention than the server's YuNet crop, and LBPH (the identity-matching algorithm) was
  only ever calibrated against YuNet's convention. This caused real, systematic false
  IDENTITY_MISMATCH flags on the client-detected path — confirmed via live A/B testing on the same
  real face, not assumed. Identity verification is now skipped on that specific path, falling back
  to the audited full-frame poll instead.
- **9e8d174** — fixes a second real bug `497c9e9` introduced: MediaPipe stays "confident" (0.50-
  0.77) through a genuine head-down tilt, unlike the server's YuNet detector which reliably loses
  the face in that exact pose (the original reason a pose-fallback mechanism existed at all).
  Because the client-crop path also skips head-pose tracking entirely, PROLONGED_HEAD_DOWN was
  only catching real head-down episodes when MediaPipe happened to lose the face by chance — live-
  confirmed via direct testing. Raised the audit-poll frequency 1-in-12 → 1-in-3 to restore
  reliable real-frame checks, verified live that a real head-down tilt now fires the violation
  without depending on MediaPipe's own instability.
