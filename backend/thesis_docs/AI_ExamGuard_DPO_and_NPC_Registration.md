# Data Protection Officer Designation & NPC Registration Readiness — AI ExamGuard

**Status: Thesis documentation of compliance readiness — not a completed legal appointment or an
actual NPC filing.** Nothing in this document has been notarized, submitted to the NPC, or
formally adopted by an institution. It exists so that, when a real appointment/filing is decided
on, the substantive information is already assembled rather than starting from nothing. Companion
to `AI_ExamGuard_DPIA.md`, which this closes out Section 9, items 1 and 3 of.

**Prepared:** August 13, 2026, following NPC Advisory 2017-03, the NPC's "Five Pillars of
Compliance," DPA Sec. 21–22 (DPO duties), and current NPCRS registration requirements (NPC Form
2022-01 for DPO registration; separate registration for qualifying data processing systems) —
researched directly for this document, not assumed from general knowledge.

---

## Part 1 — Data Protection Officer Designation

### 1.1 Designated DPO (for documentation purposes)

**Name:** Laurence [surname to be confirmed by the DPO before this is used for anything formal]
**Contact:** aueteeap2026@gmail.com
**Role in the project:** Project owner/operator of AI ExamGuard

This designation is made here **for thesis-documentation purposes**, reflecting the project
owner's decision to take on this role. It is **not yet**:
- A notarized NPC Form 2022-01 (the actual, system-generated, mandatory form for DPO registration
  — see 1.4)
- Backed by a formal appointment instrument from an institution/board (relevant if AI ExamGuard is
  ever operated by a registered legal entity rather than an individual — see Part 3)
- Reflected anywhere in the live application (there is no `DataProtectionOfficer` record or
  public-facing DPO contact page in the current codebase — a real gap if this designation is ever
  made operative, since DPA requires the DPO's contact details be made known to data subjects and
  the NPC)

### 1.2 DPO responsibilities under DPA Sec. 21–22 and NPC guidance

A DPO for AI ExamGuard, once formally appointed, is responsible for:

1. Monitoring the organization's compliance with the DPA, its IRR, and NPC issuances
2. Ensuring the conduct of Privacy Impact Assessments for new or materially changed processing
   activities (this DPIA is the first; per its own Section 10, review is due annually or on
   material change — e.g., adding a new biometric signal or third-party integration)
3. Advising on data protection matters, including this project's own real precedent of catching
   privacy-relevant issues at design time (e.g., the consent-and-scope pause taken this session
   before building the continuous-training pipeline, which excluded face-identity data from reuse
   specifically because a DPO-level judgment call was needed)
4. Serving as the contact point between AI ExamGuard, data subjects (students/instructors), and
   the NPC — required contact channel does not yet exist in-app (see 1.1)
5. Cooperating with the NPC on investigations, complaints, or compliance checks
6. Ensuring proper data breach and security incident management (a written procedure does not yet
   exist — DPIA Section 9, item 4)
7. Advising on and reviewing Data Sharing Agreements and Data Processing Agreements, relevant here
   given the platform's multi-tenant, multi-school structure (Part 3)

### 1.3 Qualifications check (informational, not a substitute for the DPO's own confirmation)

NPC guidance expects a DPO to have "expertise in relevant privacy or data protection policies and
practices" appropriate to the org's processing activities — no specific certification is legally
mandated for most organizations. Worth the named DPO's own honest self-assessment before formal
registration, not asserted here on their behalf.

### 1.4 What remains to make this a real, legal appointment

1. Confirm the DPO's full legal name and complete contact information (phone number, mailing
   address — required NPCRS fields beyond email)
2. Log into the NPC's NPCRS portal and generate **NPC Form 2022-01** (system-generated, not a
   form Claude can produce outside that portal)
3. **Have it notarized** — a real, in-person (or authorized remote) legal step
4. Submit within **90 days** of the appointment being treated as effective
5. Add a real, discoverable DPO contact mechanism to the application itself (e.g., a
   `dpo@aiexamguard.com` address and a reference on `/privacy-policy`) — currently missing

---

## Part 2 — NPC Registration Readiness Assessment

### 2.1 Do the mandatory registration thresholds apply?

| Trigger | Applies to AI ExamGuard? | Basis |
|---|---|---|
| Employs 250+ persons | **No**, almost certainly | This is a small/individual-operated project, not a 250-person organization |
| Processes sensitive personal information of 1,000+ individuals | **Undetermined — needs a real number.** Query the live database (`SELECT COUNT(*) FROM students WHERE face_model_path IS NOT NULL`, across all school tenants) before concluding either way. Given the platform is newly public and multi-tenant (any school can self-register), this could cross 1,000 sooner than expected as adoption grows | NPC's stated threshold |
| Processing that "poses risk to data subjects" | **Likely yes, regardless of the count above.** NPC guidance already treats biometric-data processing and AI-driven profiling (this system's risk-scoring) as inherently high-risk/PIA-triggering (see `AI_ExamGuard_DPIA.md` intro) — this is a separate, independent trigger from the raw headcount threshold |

**Working conclusion**: registration is very likely required once this is treated as a real,
operating system — the "poses risk" trigger alone plausibly applies today, independent of user
count. This should be treated as the DPO's formal determination to make, not a self-executing
fact — but the honest read of NPC's own stated criteria points toward "yes, register."

### 2.2 A structural question this readiness check surfaces, not yet resolved

AI ExamGuard is multi-tenant: any school self-registers and operates its own students/instructors/
exams under its own tenant. Two different legal framings are both defensible, and which one
applies changes who actually has the registration obligation:

- **Framing A** — each **school** is the Personal Information Controller (they decide to collect
  their own students' biometric data for their own institutional purpose); AI ExamGuard is a
  Personal Information Processor providing the platform on each school's behalf. Under this
  framing, each school's *own* registration obligation is assessed against *its own* user count,
  and AI ExamGuard needs a **Data Processing Agreement** with each school, plus its own registration
  as a PIP.
- **Framing B** — AI ExamGuard itself is the PIC (it designed the processing, sets the retention
  policy, controls the risk-scoring logic centrally across all tenants) and schools are more like
  data subjects' enrolling institutions than independent controllers.

**This document does not resolve which framing is correct** — it depends on facts about how AI
ExamGuard is actually operated/marketed to schools (do schools meaningfully control processing
decisions, or just consume a fixed platform?) that are a real legal judgment call, not a code
question. Flagging this explicitly rather than picking one arbitrarily, since it changes who files
what.

### 2.3 Registration submission packet — pre-filled where possible

The following is what NPCRS registration for a qualifying data processing system asks for,
pre-filled from the actual system so a real filing (once thresholds/framing are resolved) is
largely data entry:

| Field | Value |
|---|---|
| System/process name | AI ExamGuard — Online Exam Proctoring Platform |
| Purpose of processing | Identity verification and academic-integrity monitoring during remotely-administered exams (see DPIA §4.3) |
| Categories of personal information processed | See DPIA §4.2 — name/contact/academic records (personal information), enrolled face-recognition model and violation evidence frames (sensitive personal information / biometric) |
| Categories of data subjects | Students, instructors, school administrators (DPIA §4.1) |
| Data flow description | DPIA §4.5 |
| Retention period | 90 days for evidence (enforced in code — DPIA §4.7); indefinite for academic records pending a disposal policy decision (DPIA §9, item — not yet separately itemized, worth adding) |
| Security measures | DPIA §8 |
| Recipients/third parties | None beyond Cloudflare as network transport (DPIA §4.8) |
| DPO name and contact | See Part 1.1 — pending the confirmation steps in 1.4 |
| Risk assessment | `AI_ExamGuard_DPIA.md` in full, as the supporting PIA document NPC registration explicitly expects |

### 2.4 What remains before an actual filing

1. Resolve the PIC/PIP framing question (2.2) — likely needs actual legal advice, not a
   self-determination
2. Get a real current count of students with enrolled biometric data, across all school tenants
3. Complete the DPO's own NPC Form 2022-01 registration first (data-processing-system registration
   references the DPO registration)
4. File within **20 days of first operation** for the data processing system once the above is
   resolved — worth noting AI ExamGuard has already been live longer than 20 days as of this
   writing, so if registration is ultimately determined to be required, that determination should
   happen promptly rather than continuing to defer it
5. Budget for **annual renewal** (registration certificates are valid one year, renewable within
   30 days of expiry) as an ongoing, not one-time, obligation

---

*Prepared alongside `AI_ExamGuard_DPIA.md` by reviewing the live AI ExamGuard system directly.
Legal/regulatory content (thresholds, form names, notarization requirement, filing deadlines) was
researched for currency rather than recalled from general knowledge, and is cited as such — still
not a substitute for review by the named DPO or actual legal counsel before any real filing.*
