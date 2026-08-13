# Data Protection Impact Assessment — AI ExamGuard

**Status: DRAFT — for review and adoption by a designated Data Protection Officer (DPO) or legal
counsel before it is relied upon as a compliance instrument.** This document was prepared by
reviewing the actual, currently deployed system (code, configuration, and infrastructure) rather
than from a generic template — every claim about what the system does or doesn't do is grounded in
a specific, checkable part of the implementation, cited inline. It has **not** been through formal
stakeholder consultation, legal review, or NPC engagement.

**Prepared:** August 13, 2026
**Framework:** Republic Act No. 10173, the Data Privacy Act of 2012 (DPA), its Implementing Rules
and Regulations, and National Privacy Commission (NPC) Advisory No. 2017-03 ("Guidelines on
Privacy Impact Assessments"), which this document follows in structure. This is Pillar 2 of the
NPC's "Five Pillars of Compliance" — the other four (DPO appointment, a Privacy Management Program
and Manual, implemented privacy/security measures, and a breach-reporting procedure) are addressed
only where they intersect with this assessment; a complete compliance program needs all five, not
this document alone.

---

## 1. Executive Summary

AI ExamGuard is a multi-tenant, self-hosted online exam proctoring platform. It processes
personal information — including **sensitive personal information in the form of biometric face
data** — belonging to students, instructors, and administrators across every school that registers
on the platform. Under NPC guidance, biometric-data processing and AI-driven profiling are
explicitly identified as high-risk activities that warrant a PIA, which is the reason this
assessment was undertaken now that the system is live and processing real users' data, rather than
staying in a development/test environment.

**Overall assessment**: the system has substantive, real technical and procedural safeguards
already built and verified (Section 8) — this is not a bare system with a PIA bolted on
afterward. However, several accountability-layer gaps remain open (Section 9) that should be
closed before this assessment can be considered to demonstrate full compliance: no Data Protection
Officer has been appointed, NPC registration status has not been determined, there is no written
breach-response procedure, and there has been no formal data-subject consultation.

---

## 2. System Description

AI ExamGuard (`aiexamguard.com`) lets a school register itself, add instructors/students, and run
proctored online exams. During an exam, the student's webcam is periodically sampled (roughly
every 15 seconds) to check for face presence/identity match and for a phone or additional people
in frame; a companion browser extension detects navigation to AI-chatbot or search-engine tabs.
Detected irregularities ("violations") are logged, contribute to a transparent, explainable risk
score visible to the instructor, and can be appealed by the student. The system is self-hosted (a
single Windows PC, not a cloud data-processing agreement with a third party beyond the network
transport layer — see Section 6.4) and reachable publicly via a Cloudflare Tunnel.

## 3. Data Protection Officer / Accountable Party

**Not yet appointed.** RA 10173 and the NPC's Five Pillars require every personal information
controller to designate a DPO responsible for overseeing compliance. This is a real, open gap
(see Section 9.1) — until it is closed, there is no single accountable party for this PIA's
findings, for data-subject rights requests, or for breach response.

## 4. Description of the Processing Operations

### 4.1 Categories of data subjects
Students, instructors, and school administrators, across every school tenant on the platform.

### 4.2 Categories of personal information collected

| Data element | Subject | Classification | Source |
|---|---|---|---|
| Name, username, email, password (hashed) | All users | Personal information | `User` model — `backend/app/models/user.py` |
| Student number, course/school enrollment | Student | Personal information | `Student` model |
| Accommodation notes, extra-time/check-skip flags | Student (where applicable) | Personal information (may reveal disability/health context) | `Student.accommodation_notes` etc. |
| **Trained face-recognition model** (LBPH model file, not raw photos) | Student | **Sensitive personal information — biometric data** | `FaceService.enroll` — `face_service.py`; raw enrollment photos are deliberately never persisted, only the trained model, per the code's own documented design |
| Webcam evidence frames on a flagged violation (face-lost, identity-mismatch, phone/person detected) | Student | **Sensitive personal information — biometric/image data** | `ViolationService.log_violation`, stored at `backend/storage/violation_evidence/` |
| Exam answers, scores, appeal text | Student | Personal information (academic record) | `StudentAnswer`, `ExamSession`, `Violation.appeal_reason` |
| Audit trail of staff access to the above | Instructor/Admin (acting) | Personal information | `AuditLog` model |
| IP address (ephemeral, for rate limiting only) | All users | Personal information | `app/core/rate_limit.py` — not persisted to the database, held only in the rate limiter's in-memory counters |

**No government-issued ID numbers, financial information, health records beyond the optional
free-text accommodation note, or genetic/sexual-life/religious/political data are collected.**

### 4.3 Purpose of processing
Verifying a student's identity and physical presence during a remotely-taken exam, and detecting
behavior indicative of academic dishonesty (unauthorized devices/persons, use of AI tools or
search engines), for the purpose of academic integrity — a purpose specific, legitimate, and
disclosed to the data subject before processing begins (see Section 4.6).

### 4.4 Legal basis for processing sensitive personal information
Under DPA Sec. 13, processing of sensitive personal information is prohibited except under
enumerated conditions. This system currently relies on **consent** as its basis: a student must
affirmatively enroll their face and click through `PreExamModal.jsx`'s disclosure and checklist
(covering identity verification, phone/person detection, and — as of this session — training-data
reuse) before an exam session can start. **Gap**: this consent is not currently captured as a
standalone, timestamped, revocable database record (see Section 9.2) — it is a UI gate, not a
retained proof of consent, which weakens the ability to demonstrate consent was actually given if
ever challenged.

### 4.5 Data flow summary
Collection (webcam capture in-browser) → transmission over TLS (Cloudflare Tunnel, see 6.4) →
server-side inference (face/object detection, in-process, no third-party ML API call) → violation
record + evidence file written to local disk/DB → visible to the owning instructor/school admin
(scoped, see 8.2) → retained 90 days → automatically purged (Section 4.7) unless a training-review
or appeal hold applies.

### 4.6 Transparency to data subjects
`PreExamModal.jsx` discloses, before every exam, what is monitored and why, in plain language
(not buried in a EULA) — confirmed current copy: face verification against the enrolled profile,
detection of a held-up photo, phone/multiple-person detection, prolonged downward gaze, and that
"violations raise my risk score and will be reviewed by my instructor" (i.e., not an automatic
penalty). A separate web-app privacy policy (`/privacy-policy`, added this session) discloses
retention, the training-data-reuse pathway, and an opt-out contact. **Gap**: neither document has
been reviewed against the DPA's specific content requirements for a privacy notice (Section 9.4).

### 4.7 Retention and disposal
Violation evidence (the sensitive image data) is retained for a fixed, documented **90 days**
(`RetentionService.EVIDENCE_RETENTION_DAYS`), after which it is hard-deleted from disk (not merely
flagged) via an admin-triggered purge, audit-logged. A pending appeal, or a pending/approved-but-
not-yet-exported training-review candidate, holds the evidence past 90 days for that specific,
documented reason (Section 4.9) — this is a real, enforced exception path, not an unbounded one.
Trained face models and academic records are retained for the life of the student's enrollment;
no automatic disposal policy exists for those yet (Section 9.3).

### 4.8 Recipients / third parties
**None**, beyond the network transport layer. All inference (face detection/recognition, object
detection, risk scoring) runs in-process on the self-hosted server — no frame or derived data is
sent to a third-party AI API. The only external party in the data path is **Cloudflare**, acting
purely as a TLS-terminating network tunnel/CDN between the student's browser and the self-hosted
origin server — Cloudflare does not have access to application-level plaintext data beyond what
any TLS-terminating reverse proxy would (see Section 6.4 for the cross-border implication of this).

### 4.9 A note on the training-data-reuse pathway
As of this session, a subset of *non-identity* violation evidence (phone-detection and multiple-
person frames only — never face-identity evidence) may, after individual human review and
approval by a school admin, be reused to improve the detection models. This is disclosed in the
privacy policy, gated behind a real admin-review queue (not automatic), and explicitly excludes
biometric-identity data from reuse. See `[[ai_examguard_continuous_training_consent]]` in the
project's engineering memory for the full build rationale. This is called out here because it is a
secondary processing purpose beyond the original exam-proctoring purpose, and DPA Sec. 12/13
require the legal basis to cover the purpose actually being served — worth explicit DPO/legal
sign-off that consent-via-privacy-policy is sufficient for this secondary purpose, or whether a
separate opt-in is warranted (Section 9.2 already flags the broader consent-capture gap).

## 5. Necessity and Proportionality Assessment

| Practice | Necessary for stated purpose? | Proportionality note |
|---|---|---|
| Webcam sampled only during an active exam session, not continuously | Yes | Confirmed by code: capture only occurs inside `ExamRoom.jsx`'s in-progress phase, and `useCamera.js` releases the stream on unmount |
| Only a trained model kept, not raw enrollment photos | Yes | Deliberate design choice (`FaceService.enroll`), already minimizes what's retained |
| 90-day evidence retention, not indefinite | Yes | Explicitly documented in code as a deliberate choice, "not indefinite storage of biometric evidence" |
| Full webcam frame captured on a flagged violation (not a cropped/redacted region) | Partially | A legitimate evidentiary need for instructor/appeal review, but no minimization (e.g., blurring background) is applied — worth a DPO judgment call, not fixed here |
| Accommodation notes as free text | Borderline | Free text can capture more health/disability detail than strictly necessary for the `skip_face_check`/`skip_object_check` flags it supports — structuring this input would reduce over-collection |

## 6. Risk Register

Each risk is rated Likelihood × Impact (Low/Medium/High) per NPC PIA guidance, with the **current,
already-implemented** mitigation and the residual risk after that mitigation. "Current mitigation"
here means something real and verifiable in the codebase today, not a planned control.

| # | Risk | L | I | Current mitigation (real, implemented) | Residual risk |
|---|---|---|---|---|---|
| 6.1 | Unauthorized access to another student's biometric evidence or exam data | Was High | High | Every session/violation/evidence-access route is auth-gated and ownership-checked (`session_access.py`); a real, documented cross-tenant leak sweep found and fixed multiple gaps (`[[ai-examguard-multi-tenancy]]`, `[[ai_examguard_cleanup_audit_2026_08_08]]`); every staff view of evidence is audit-logged | **Low** — contingent on no *new* route being added without the same ownership-check discipline |
| 6.2 | Credential-stuffing / brute-force login against student accounts | Was Medium-High (public+no protection) | High | Per-IP rate limiting on `/auth/login` (10/min), `/auth/register` (5/min), `/schools/register` (3/hr), added this session, load-tested; bcrypt password hashing | **Low-Medium** — rate limiting is per-IP, a distributed attack from many IPs is not mitigated by this alone |
| 6.3 | A held-up photo defeating identity verification (spoofing) | Medium | Medium | `STATIC_IMAGE_SUSPECTED` frame-difference heuristic flags it; **explicitly, honestly disclosed as an imperfect signal** to students and backstopped by mandatory human instructor review + appeal, not an automatic penalty | **Medium** — this is a documented, conscious ceiling (three separate anti-spoofing techniques were tried and each hit a real, evidence-backed limit — `[[ai_examguard_face_recognition_threshold_finding]]`), not something further tuning fixes; the human-review backstop is the accepted mitigation |
| 6.4 | Cross-border data transit via Cloudflare's global network | Low-Medium | Medium | TLS end-to-end; Cloudflare acts as network transport only, never persists application data | **Open** — DPA Sec. 21's cross-border transfer safeguards (and whether Cloudflare's standard terms satisfy them) have not been formally reviewed; worth explicit DPO sign-off |
| 6.5 | Single self-hosted PC as a single point of failure (data loss) | Was High (zero backups existed) | High | Daily automated local DB backup added this session (`scripts/backup_db.py`, gzip, 14-day rotation, verified against a real restorable dump) | **Medium** — backup is local-only, on the same disk as the live data; a drive/PC failure still loses both the live DB and its backups together. Offsite copy is the clear next step, not yet built |
| 6.6 | Silent outage during a live exam window going unnoticed | Was Medium-High | Medium | Free external uptime monitoring (UptimeRobot) on both the frontend and backend, checking a real app-level health signal every 5 minutes, confirmed live this session | **Low** | 
| 6.7 | Concurrent load (a whole class polling face/phone-check simultaneously) causing errors or unacceptable delay | Was unknown/untested | Medium | Load-tested this session; a real DB connection-pool exhaustion bug (causing 500 errors at 50 concurrent users) was found and fixed (`[[ai_examguard_load_testing]]`) | **Medium** — fix confirmed to eliminate errors, but latency still degrades meaningfully under load and the root cause of face-check's disproportionate slowdown wasn't fully isolated |
| 6.8 | A breach going undetected or unreported within DPA's required timeframe | High | High | None currently — no written incident-response/breach-notification procedure exists | **High — open, see 9.5** |
| 6.9 | Excessive/indefinite retention of biometric data | Was High | Medium | Enforced 90-day purge with audit log, real code (not policy-only) — see 4.7 | **Low** |
| 6.10 | A data subject unable to exercise access/correction/erasure/objection rights | Medium | Medium | Appeal workflow (contest a specific violation), account-level accommodation edits, opt-out contact for the training-review pathway | **Medium** — no unified, discoverable "request your data" or "delete my account" mechanism exists yet; rights are exercised piecemeal through different channels |
| 6.11 | Encryption of data at rest (the Postgres volume / evidence files on disk) | Unknown | Medium-High | None confirmed at the application layer — whatever protection exists depends entirely on the host machine's own disk encryption (e.g., BitLocker), which has not been verified from this review | **Open — see 9.6** |

## 7. Data Subject Rights — Current Implementation

| Right (DPA Sec. 16, 18, 34) | Current mechanism | Gap |
|---|---|---|
| Right to be informed | `PreExamModal.jsx` + `/privacy-policy` | Not yet checked against DPA's specific notice-content requirements |
| Right to object | Accommodation flags (`skip_face_check`/`skip_object_check`); training-review opt-out via school admin contact | No self-service opt-out; requires going through an admin |
| Right to access | None dedicated — a student can view their own violations/results in-app | No formal "export my data" request path |
| Right to rectification | Appeal workflow contests a specific violation's accuracy | No path to correct account-level data (name, etc.) without admin intervention |
| Right to erasure/blocking | `StudentService.delete` removes the account and its face model file (confirmed fixed in an earlier cleanup pass) | No student-initiated deletion request path; deletion is admin-only |
| Right to damages | N/A (institutional/legal matter, not a system feature) | — |
| Right to data portability | None | Not implemented |

## 8. Security Measures Already in Place

**Technical:**
- TLS in transit (Cloudflare Tunnel — confirmed live via direct `curl` this session)
- Password hashing via bcrypt (never plaintext)
- JWT-based authentication on every route; ownership/scoping checks on every session-, violation-,
  and school-scoped resource (real sweep-and-fix history, not an assumption — see 6.1)
- Per-IP rate limiting on public signup/login endpoints
- Role-based access control (student / instructor / admin), with school-level tenant isolation
- Audit logging of staff access to sensitive evidence, and of retention purges and training-review
  decisions
- Raw face-enrollment photos never persisted, only the trained recognition model
- Automatic, enforced (not just documented) 90-day evidence retention limit
- Daily local database backups with rotation

**Organizational:**
- Written, disclosed rules shown to students before every exam
- Human review required before any flagged violation affects a student (appeal + instructor
  review workflow; training-data reuse requires individual admin approval)
- A documented (in code comments and project memory) discipline of choosing conservative defaults
  and stating known limitations honestly rather than overclaiming detection accuracy

**Not yet in place (see Section 9):** DPO appointment, written breach-response procedure, offsite
backup, confirmed disk encryption at rest, formal NPC registration determination, unified
data-subject rights request channel.

## 9. Open Gaps and Recommended Actions

These are the items that should be closed before this PIA can be cited as demonstrating full DPA
compliance, in rough priority order:

1. **Appoint a Data Protection Officer** and register them with the NPC. Nothing in this section
   has an accountable owner until this happens.
2. **Capture consent as a real, timestamped, revocable record**, not just a UI click-through —
   particularly for the secondary training-data-reuse purpose (Section 4.9), which is a weaker
   fit for "implied by exam disclosure" than the core proctoring purpose is.
3. **Determine and act on NPC registration status.** Given this system processes sensitive
   personal information (biometric data) as a matter of course, registration of the data
   processing system (and the DPO) with the NPC is very likely required regardless of the
   organization's employee count.
4. **Write and adopt a breach-response procedure** meeting the DPA's 72-hour notification
   requirement to both the NPC and affected data subjects. This does not exist today.
5. **Confirm or implement encryption at rest** for the database volume and evidence file storage,
   or document the host machine's existing disk-encryption posture if one already exists.
6. **Add an offsite backup copy** — the local backup added this session protects against
   accidental deletion/corruption, not a drive or PC failure, which would still lose everything.
7. **Build a unified data-subject rights request path** (access/export, correction, deletion)
   rather than the current piecemeal, admin-mediated mechanisms.
8. **Review the privacy notice and consent flow against the DPA's specific required content**
   (not just "is something disclosed," but "does it cover everything Sec. 16/18/20 requires").
9. **Get an explicit DPO/legal opinion on the Cloudflare cross-border transit question**
   (Section 6.4) — likely low-risk given Cloudflare's role is transport-only, but not yet formally
   assessed.
10. **Hold a real consultation** with a sample of data subjects (students/instructors) or their
    representatives, per NPC PIA guidance's "in consultation with stakeholders" requirement — this
    document was prepared through code/system review only.

## 10. Conclusion

AI ExamGuard's *technical* posture is unusually mature for a system at this stage — the risk
register above reflects real, already-shipped mitigations for most of the risks that matter most
(cross-tenant leaks, credential stuffing, biometric over-retention, silent outages, untested
concurrent load), each with its own verification (tests, live smoke-tests, or load-test data)
rather than being asserted. The gaps that remain are almost entirely **accountability and
governance** gaps (Section 9) — a DPO, a breach procedure, formal consent records, an NPC
registration decision — not missing engineering. Closing Section 9's items, in the order listed,
is the recommended path to a defensible compliance posture; this PIA should be revisited once they
are, and at minimum annually thereafter or whenever the processing changes materially (e.g., a new
biometric signal, a new third-party integration, or a significant change in scale).

---

*This document was prepared by reviewing the AI ExamGuard codebase and live deployment directly
(commit history through `9a5e84a`) rather than by interview or generic template. Where a claim
depends on infrastructure this review could not directly verify (e.g., host disk encryption), it
is marked as such rather than assumed. It is not a substitute for review by a qualified Data
Protection Officer or legal counsel, and should not be represented to the NPC, a school, or any
data subject as a completed compliance instrument until Section 9 is addressed and it has been
formally adopted.*
