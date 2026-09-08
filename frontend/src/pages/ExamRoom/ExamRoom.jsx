import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { useSchoolNav } from "../../hooks/useSchoolNav";
import { CheckCircle, Eye } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { getExam } from "../../api/exams";
import { getExamQuestions } from "../../api/questions";
import { getStudents } from "../../api/students";
import { getExamSessions, startExamSession, submitExamSession } from "../../api/examSessions";
import { saveAnswer, getAnswers } from "../../api/studentAnswers";
import { getSessionRisk } from "../../api/violations";
import { checkFace } from "../../api/faceEnrollment";
import { checkObjects } from "../../api/objectDetection";
import ViolationAlertModal from "./ViolationAlertModal";
import { shouldRaiseAlert } from "../../utils/violationAlerts";
import useProctoring from "../../hooks/useProctoring";
import useExtensionMonitor from "../../hooks/useExtensionMonitor";
import useCamera from "../../hooks/useCamera";
import useClientFaceDetector from "../../hooks/useClientFaceDetector";
import Card from "../../components/ui/Card";
import StatusDot from "../../components/ui/StatusDot";
import RiskPill from "../../components/ui/RiskPill";
import PreExamModal from "./PreExamModal";
import { EXTENSION_STORE_URL } from "../../constants/extension";

// How often a webcam frame is grabbed and sent for face/object checks. Was 5000 (0.2 fps).
// This is a per-student poll rate; at 1 fps this is 2 backend ML requests/sec/student, so a 50-
// student exam is ~100 req/s - the load test that found DB pool exhaustion ran at 0.2 fps. Raise
// back toward 2000-5000 if p95 latency or face-check accuracy degrades under real concurrency.
const CAPTURE_INTERVAL_MS = 1000;
// Server-side audit polls stay at ~15s (see the comment on faceCheckPollCountRef) no matter what
// CAPTURE_INTERVAL_MS is, because the head-down constants were tuned against that cadence.
const AUDIT_EVERY_N_POLLS = Math.max(1, Math.round(15000 / CAPTURE_INTERVAL_MS));

function useCountdown(deadline) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  const remaining = Math.max(0, deadline - now);
  const totalSeconds = Math.floor(remaining / 1000);
  const mm = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
  const ss = String(totalSeconds % 60).padStart(2, "0");
  return { mm, ss, expired: remaining <= 0 };
}

export default function ExamRoom() {
  const { examId } = useParams();
  const { user } = useAuth();
  const navigate = useSchoolNav();

  const [phase, setPhase] = useState("loading");
  const [error, setError] = useState("");
  const [exam, setExam] = useState(null);
  const [student, setStudent] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [choicesByQuestion, setChoicesByQuestion] = useState({});
  const [session, setSession] = useState(null);
  const [answers, setAnswers] = useState({});
  const [current, setCurrent] = useState(0);
  const [result, setResult] = useState(null);
  const [risk, setRisk] = useState(0);
  const [lastTabSwitchAt, setLastTabSwitchAt] = useState(0);
  const [faceDetected, setFaceDetected] = useState(true);
  const [identityMatch, setIdentityMatch] = useState(true);
  // True when a face check comes back with no facial landmarks but the pose-model fallback still
  // sees a person - i.e. a head-down tilt, not an empty chair. Lets the badge below read "HEAD
  // DOWN" instead of the more alarming "NO FACE" for this case.
  const [personPresent, setPersonPresent] = useState(true);
  // Distinguishes "not enrolled" (backend intentionally returns face_detected: null and skips
  // detection entirely) from a real check result - without this, an unenrolled student's row
  // silently keeps the useState(true) default forever, showing a false "OK".
  const [faceCheckUnavailable, setFaceCheckUnavailable] = useState(false);
  const [phoneDetected, setPhoneDetected] = useState(false);

  // Student-facing violation alerts.
  //
  // Raised once per incident, not once per detection poll. The object check runs every few
  // seconds, so a phone left in view would otherwise reopen this modal continuously and make the
  // exam unusable - the very thing the student is being asked to fix. Server-side flags are
  // therefore raised on the rising edge only (see the poll below), and every type additionally
  // sits behind a cooldown so a repeated event cannot interrupt again immediately.
  const [violationAlert, setViolationAlert] = useState(null);
  const violationAlertLastShown = useRef({});
  const violationCounts = useRef({});

  const raiseViolationAlert = useCallback((eventType) => {
    // Counted even when it does not interrupt, so the modal can say "this has now happened N
    // times" the next time it is allowed to appear.
    violationCounts.current[eventType] = (violationCounts.current[eventType] ?? 0) + 1;

    if (!shouldRaiseAlert(violationAlertLastShown.current, eventType, Date.now())) return;

    // Never replace an alert the student is still reading - the first one is the one they were
    // interrupted for, and swapping the text under them would be worse than showing nothing.
    setViolationAlert((current) =>
      current ?? { eventType, count: violationCounts.current[eventType] }
    );
  }, []);
  const [multiplePeople, setMultiplePeople] = useState(false);
  const [extensionAlert, setExtensionAlert] = useState(null);

  // Read via a ref (not `current`/`questions` directly) inside checkOnce below, since that
  // effect's dependency array intentionally excludes them - polling shouldn't restart every
  // time the student clicks between questions, but each poll still needs the question they're
  // *currently* on, not whichever one was current when the effect last ran.
  const currentQuestionRef = useRef(null);
  useEffect(() => {
    currentQuestionRef.current = questions[current] ?? null;
  }, [current, questions]);

  useEffect(() => {
    let cancelled = false;

    async function init() {
      try {
        const [examData, students, examQuestionsRaw] = await Promise.all([
          getExam(examId),
          getStudents(),
          getExamQuestions(examId),
        ]);

        if (cancelled) return;

        if (!examData.is_active) {
          setExam(examData);
          setPhase("inactive");
          return;
        }

        const me = students.find((s) => s.user_id === user.id);
        if (!me) {
          setPhase("no-profile");
          return;
        }
        setStudent(me);

        const examQuestions = [...examQuestionsRaw].sort((a, b) => a.order_number - b.order_number);

        const grouped = {};
        for (const q of examQuestions) {
          grouped[q.id] = q.choices;
        }

        setExam(examData);
        setQuestions(examQuestions);
        setChoicesByQuestion(grouped);

        const sessions = await getExamSessions();
        const activeSession = sessions.find(
          (s) => s.student_id === me.id && s.exam_id === Number(examId) && s.status === "IN_PROGRESS"
        );

        const activeOrNew = activeSession ?? (await startExamSession(Number(examId)));
        if (cancelled) return;

        setSession(activeOrNew);

        const existingAnswers = await getAnswers(activeOrNew.id);
        if (cancelled) return;

        const answerMap = {};
        for (const a of existingAnswers) {
          if (a.choice_id != null) answerMap[a.question_id] = a.choice_id;
        }
        setAnswers(answerMap);
        setPhase("guidelines");
      } catch (err) {
        if (cancelled) return;
        if (err.response?.status === 403) {
          setPhase("wrong-course");
          return;
        }
        setError(err.response?.data?.detail ?? "Couldn't load this exam.");
        setPhase("error");
      }
    }

    init();
    return () => {
      cancelled = true;
    };
  }, [examId, user.id]);

  const deadline = useMemo(() => {
    if (!session || !exam) return Infinity;
    const totalMinutes = exam.duration_minutes + (student?.extra_time_minutes ?? 0);
    return new Date(session.started_at).getTime() + totalMinutes * 60 * 1000;
  }, [session, exam, student]);

  const { mm, ss, expired } = useCountdown(deadline);

  useEffect(() => {
    if (expired && phase === "in-progress") {
      handleSubmit();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [expired, phase]);

  useProctoring(session?.id, phase === "in-progress", (eventType) => {
    if (eventType === "TAB_SWITCH") setLastTabSwitchAt(Date.now());
    raiseViolationAlert(eventType);
  });

  const extensionActive = phase === "extension-check" || phase === "in-progress";
  const { status: extensionStatus, retry: retryExtensionCheck } = useExtensionMonitor(
    session?.id,
    extensionActive,
    phase === "in-progress",
    (eventType, domain) => setExtensionAlert({ eventType, domain })
  );

  useEffect(() => {
    if (phase !== "in-progress" || !session) return;
    let cancelled = false;

    async function poll() {
      try {
        const value = await getSessionRisk(session.id);
        if (!cancelled) setRisk(value);
      } catch {
        // best-effort; next poll will retry naturally
      }
    }

    poll();
    const id = setInterval(poll, 5000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [phase, session]);

  const needsFaceCheck = !student?.skip_face_check;
  const needsObjectCheck = !student?.skip_object_check;
  const needsCamera = needsFaceCheck || needsObjectCheck;

  const { videoRef, error: cameraError, ready: cameraReady, captureFrame } = useCamera(
    phase === "in-progress" && needsCamera
  );
  const { detect: detectFaceLocally } = useClientFaceDetector(
    phase === "in-progress" && needsFaceCheck
  );
  // Every AUDIT_EVERY_N_POLLS-th poll (~15s regardless of capture rate) forces a full server-side check
  // regardless of what the local detector reports - both an independent audit sample (catches a
  // tampered/lying client reporting "confident" every poll) and, as important, PROLONGED_HEAD_DOWN's
  // only real data source: face_service.py's client_confident_crop path skips _track_head_down
  // entirely (no raw frame to estimate pose from), so real duration tracking only ever advances on
  // these audited polls. Raised from every 12th (2026-08-20): live-tested that MediaPipe still
  // reports 0.50-0.77 confidence (above its own 0.5 "trust this" cutoff) during a genuine head-down
  // tilt on 3 of 4 real polls sampled, only dropping to 0 detections intermittently - meaning a
  // sustained head-down episode could see NO real pose check at all for a full audit interval,
  // purely by chance of whether MediaPipe happened to lose the face. The ~15s real-check cadence is
  // what HEAD_DOWN_DURATION_THRESHOLD_SECONDS=25s and HEAD_DOWN_MISS_TOLERANCE=1 were empirically
  // tuned against, so AUDIT_EVERY_N_POLLS is derived from the capture interval rather than fixed -
  // changing the capture rate must not silently change the audit cadence those constants assume.
  // (HEAD_DOWN_MISS_TOLERANCE counts *polls*, not seconds: a fixed 1-in-3 at 1s capture would give
  // it a ~3s forgiveness window instead of the ~30s it was swept at, and the feature would stop
  // firing.) See face_service.py's client_confident_crop docstring for the server-side half.
  const faceCheckPollCountRef = useRef(0);

  useEffect(() => {
    if (phase !== "in-progress" || !session || !needsCamera || !cameraReady) return;
    let cancelled = false;
    // A face + object round-trip regularly takes longer than CAPTURE_INTERVAL_MS at 1 fps, and
    // setInterval doesn't wait - without this the in-flight checks stack up unboundedly and the
    // backend sees a growing pile-up per student. Skipping a tick is the correct behavior: the
    // effective rate just degrades to whatever the backend can actually keep up with.
    let inFlight = false;

    async function checkOnce() {
      if (inFlight) return;
      inFlight = true;
      try {
        const blob = await captureFrame();
        if (!blob || cancelled) return;

        if (needsFaceCheck) {
          const pollCount = ++faceCheckPollCountRef.current;
          const isAuditPoll = pollCount % AUDIT_EVERY_N_POLLS === 0;

          let faceBlob = blob;
          let clientConfidentCrop = false;
          if (!isAuditPoll) {
            const localCrop = await detectFaceLocally(videoRef.current).catch(() => null);
            if (localCrop) {
              faceBlob = localCrop;
              clientConfidentCrop = true;
            }
          }

          const faceResult = await checkFace(
            session.id, faceBlob, currentQuestionRef.current, clientConfidentCrop
          ).catch(() => null);
          if (!cancelled && faceResult) {
            if (faceResult.face_detected === null || faceResult.face_detected === undefined) {
              // Backend skipped the check entirely - not accommodated (needsFaceCheck is true),
              // so this means no enrolled face model exists yet.
              setFaceCheckUnavailable(true);
            } else {
              setFaceCheckUnavailable(false);
              setFaceDetected(faceResult.face_detected);
              setIdentityMatch(faceResult.identity_match !== false);
              setPersonPresent(faceResult.face_detected || faceResult.person_present === true);
            }
          }
        }

        if (needsObjectCheck) {
          const objectResult = await checkObjects(session.id, blob).catch(() => null);
          if (!cancelled && objectResult) {
            const nowPhone = objectResult.phone_detected;
            const nowCrowd = objectResult.person_count > 1;
            // Rising edge: alert when a flag first appears, not on every poll it stays true for.
            setPhoneDetected((was) => {
              if (nowPhone && !was) raiseViolationAlert("PHONE_DETECTED");
              return nowPhone;
            });
            setMultiplePeople((was) => {
              if (nowCrowd && !was) raiseViolationAlert("MULTIPLE_PEOPLE");
              return nowCrowd;
            });
          }
        }
      } catch {
        // best-effort; next check will retry naturally
      } finally {
        inFlight = false;
      }
    }

    checkOnce();
    const id = setInterval(checkOnce, CAPTURE_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase, session, cameraReady, needsCamera, needsFaceCheck, needsObjectCheck]);

  async function handleSelectChoice(questionId, choiceId) {
    setAnswers((a) => ({ ...a, [questionId]: choiceId }));
    try {
      await saveAnswer(session.id, questionId, choiceId);
    } catch {
      // best-effort; the next selection or submit will retry naturally
    }
  }

  async function handleSubmit() {
    setPhase("submitting");
    try {
      const updatedSession = await submitExamSession(session.id);
      setResult(updatedSession);
      setPhase("submitted");
    } catch {
      setError("Couldn't submit this exam. Please try again.");
      setPhase("in-progress");
    }
  }

  if (phase === "loading") {
    return (
      <div className="flex h-screen items-center justify-center text-muted-foreground font-mono text-sm uppercase tracking-widest">
        Loading exam…
      </div>
    );
  }

  if (phase === "inactive") {
    return (
      <div className="flex h-screen items-center justify-center px-6">
        <Card className="p-8 max-w-md text-center">
          <h2 className="font-display font-black text-2xl text-foreground mb-2">Exam Not Available</h2>
          <p className="text-sm text-muted-foreground mb-6">
            "{exam?.title}" isn't currently active. Check back when your instructor opens it.
          </p>
          <button
            onClick={() => navigate("/dashboard")}
            className="bg-primary hover:bg-primary/90 text-white px-4 py-2.5 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors"
          >
            Back to Dashboard
          </button>
        </Card>
      </div>
    );
  }

  if (phase === "no-profile") {
    return (
      <div className="flex h-screen items-center justify-center px-6">
        <Card className="p-8 max-w-md text-center">
          <h2 className="font-display font-black text-2xl text-foreground mb-2">No Student Profile</h2>
          <p className="text-sm text-muted-foreground mb-6">
            Your account isn't linked to a student record yet. Ask an admin to provision one before
            you can take exams.
          </p>
          <button
            onClick={() => navigate("/dashboard")}
            className="bg-primary hover:bg-primary/90 text-white px-4 py-2.5 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors"
          >
            Back to Dashboard
          </button>
        </Card>
      </div>
    );
  }

  if (phase === "wrong-course") {
    return (
      <div className="flex h-screen items-center justify-center px-6">
        <Card className="p-8 max-w-md text-center">
          <h2 className="font-display font-black text-2xl text-foreground mb-2">Not Available For Your Course</h2>
          <p className="text-sm text-muted-foreground mb-6">
            This exam isn't offered to your course. If you believe this is a mistake, contact your
            instructor.
          </p>
          <button
            onClick={() => navigate("/dashboard")}
            className="bg-primary hover:bg-primary/90 text-white px-4 py-2.5 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors"
          >
            Back to Dashboard
          </button>
        </Card>
      </div>
    );
  }

  if (phase === "error") {
    return (
      <div className="flex h-screen items-center justify-center px-6">
        <Card className="p-8 max-w-md text-center">
          <h2 className="font-display font-black text-2xl text-foreground mb-2">Something Went Wrong</h2>
          <p className="text-sm text-red-600 mb-6">{error}</p>
          <button
            onClick={() => navigate("/dashboard")}
            className="bg-primary hover:bg-primary/90 text-white px-4 py-2.5 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors"
          >
            Back to Dashboard
          </button>
        </Card>
      </div>
    );
  }

  if (phase === "submitted") {
    return (
      <div className="flex h-screen items-center justify-center px-6">
        <Card className="p-8 max-w-md text-center">
          <CheckCircle className={`w-12 h-12 mx-auto mb-4 ${result.passed ? "text-emerald-500" : "text-red-500"}`} />
          <h2 className="font-display font-black text-2xl text-foreground mb-1">Exam Submitted</h2>
          <p className="text-sm text-muted-foreground mb-6">{exam.title}</p>
          <div className="grid grid-cols-3 gap-3 mb-6">
            <div className="bg-secondary border border-border rounded-xl p-3">
              <div className="font-display text-2xl font-black text-foreground">{result.score}</div>
              <div className="text-[10px] font-mono text-muted-foreground mt-0.5">Score</div>
            </div>
            <div className="bg-secondary border border-border rounded-xl p-3">
              <div className="font-display text-2xl font-black text-foreground">{result.percentage.toFixed(1)}%</div>
              <div className="text-[10px] font-mono text-muted-foreground mt-0.5">Percentage</div>
            </div>
            <div className="bg-secondary border border-border rounded-xl p-3">
              <div className={`font-display text-2xl font-black ${result.passed ? "text-emerald-700" : "text-red-600"}`}>
                {result.passed ? "PASS" : "FAIL"}
              </div>
              <div className="text-[10px] font-mono text-muted-foreground mt-0.5">Result</div>
            </div>
          </div>
          <button
            onClick={() => navigate("/dashboard")}
            className="w-full bg-primary hover:bg-primary/90 text-white py-2.5 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors"
          >
            Back to Dashboard
          </button>
        </Card>
      </div>
    );
  }

  if (phase === "guidelines") {
    return (
      <PreExamModal
        examTitle={exam.title}
        onConfirm={() => setPhase("extension-check")}
        onCancel={() => navigate("/dashboard")}
      />
    );
  }

  if (phase === "extension-check") {
    return (
      <div className="flex h-screen items-center justify-center px-6">
        <Card className="p-8 max-w-md text-center">
          {extensionStatus === "checking" && (
            <>
              <h2 className="font-display font-black text-2xl text-foreground mb-2">
                Checking for Tab Monitor Extension…
              </h2>
              <p className="text-sm text-muted-foreground mb-6">
                We're checking whether the AI-ExamGuard Tab Monitor browser extension is installed.
              </p>
            </>
          )}
          {extensionStatus === "connected" && (
            <>
              <h2 className="font-display font-black text-2xl text-foreground mb-2">
                Tab Monitor Extension Detected
              </h2>
              <p className="text-sm text-muted-foreground mb-6">
                This exam flags activity if you visit Google Search, ChatGPT, or similar tools in
                another tab while it's in progress.
              </p>
              <button
                onClick={() => setPhase("in-progress")}
                className="w-full bg-primary hover:bg-primary/90 text-white py-2.5 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors"
              >
                Start Exam
              </button>
            </>
          )}
          {extensionStatus === "unavailable" && (
            <>
              <h2 className="font-display font-black text-2xl text-foreground mb-2">
                Extension Not Detected
              </h2>
              <p className="text-sm text-muted-foreground mb-6">
                This exam requires the AI-ExamGuard Tab Monitor browser extension (Chrome/Edge
                only). Install it from the Chrome Web Store below, then retry.
              </p>
              <a
                href={EXTENSION_STORE_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="block w-full text-center bg-card border border-border hover:bg-muted text-foreground py-2.5 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors mb-3"
              >
                Get Extension
              </a>
              <button
                onClick={retryExtensionCheck}
                className="w-full bg-primary hover:bg-primary/90 text-white py-2.5 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors"
              >
                Retry Check
              </button>
            </>
          )}
        </Card>
      </div>
    );
  }

  const q = questions[current];
  const tabFocusOk = Date.now() - lastTabSwitchAt > 10000;

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Mounted here rather than inside the question area so it is not unmounted when the
          student navigates between questions mid-alert. */}
      {violationAlert && (
        <ViolationAlertModal
          eventType={violationAlert.eventType}
          count={violationAlert.count}
          onDismiss={() => setViolationAlert(null)}
        />
      )}

      <div className="border-b border-border bg-card px-6 py-3 flex items-center gap-4 flex-shrink-0 shadow-sm">
        <div className="flex-1">
          <div className="text-foreground text-sm font-semibold">{exam.title}</div>
          <div className="text-[11px] font-mono text-muted-foreground">
            {questions.length} question{questions.length === 1 ? "" : "s"} · {exam.total_points} pts
          </div>
          {extensionAlert && (
            <div className="text-[11px] font-mono text-red-600 mt-0.5">
              {extensionAlert.eventType === "AI_TOOL_DETECTED" ? "AI Tool Detected" : "Search Engine Detected"}
              {" · "}
              {extensionAlert.domain}
            </div>
          )}
        </div>
        <div className="flex items-center gap-4">
          <div className="text-center">
            <div className="font-mono text-2xl font-bold text-foreground">
              {mm}:{ss}
            </div>
            <div className="text-[10px] font-mono text-muted-foreground">Remaining</div>
          </div>
          <div className="w-px h-8 bg-border" />
          <div className="flex items-center gap-1.5">
            <RiskPill value={Math.round(risk)} />
          </div>
          <div className="w-px h-8 bg-border" />
          <StatusDot on={true} label="Session Active" />
        </div>
      </div>

      {questions.length === 0 ? (
        <div className="flex flex-1 items-center justify-center">
          <Card className="p-8 max-w-md text-center">
            <p className="text-sm text-muted-foreground">This exam has no questions yet.</p>
          </Card>
        </div>
      ) : (
        <div className="flex flex-1 max-w-screen-xl mx-auto w-full px-6 py-8 gap-8">
          <div className="flex-1 space-y-6">
            <div className="flex flex-wrap gap-2">
              {questions.map((question, i) => (
                <button
                  key={question.id}
                  onClick={() => setCurrent(i)}
                  className={`w-9 h-9 rounded-xl text-sm font-mono font-bold transition-all ${
                    i === current
                      ? "bg-primary text-white"
                      : answers[question.id] !== undefined
                      ? "bg-blue-50 border border-blue-200 text-blue-700"
                      : "bg-secondary border border-border text-muted-foreground hover:border-foreground/20 hover:text-foreground"
                  }`}
                >
                  {i + 1}
                </button>
              ))}
            </div>

            <Card className="p-6">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-8 h-8 rounded-xl bg-primary/8 border border-primary/20 flex items-center justify-center">
                  <span className="text-primary font-mono font-bold text-sm">{current + 1}</span>
                </div>
                <span
                  className={`text-[10px] font-mono px-2 py-0.5 rounded border uppercase tracking-wider ${
                    q.question_type === "Multiple Choice"
                      ? "text-blue-700 border-blue-200 bg-blue-50"
                      : q.question_type === "True/False"
                      ? "text-emerald-700 border-emerald-200 bg-emerald-50"
                      : "text-orange-700 border-orange-200 bg-orange-50"
                  }`}
                >
                  {q.question_type}
                </span>
                <span className="text-[11px] font-mono text-muted-foreground ml-auto">{q.points} pts</span>
              </div>

              <p className="text-foreground text-base leading-relaxed mb-6">{q.question_text}</p>

              {q.question_type === "Identification" ? (
                <div className="rounded-xl border border-dashed border-orange-200 bg-orange-50 px-4 py-3 text-sm text-orange-700">
                  Free-text answers aren't gradable yet — this question won't be scored. Skip ahead.
                </div>
              ) : (
                <div className="space-y-3">
                  {(choicesByQuestion[q.id] ?? []).map((choice) => (
                    <button
                      key={choice.id}
                      onClick={() => handleSelectChoice(q.id, choice.id)}
                      className={`w-full flex items-center gap-4 px-4 py-3.5 rounded-xl border text-sm text-left transition-all ${
                        answers[q.id] === choice.id
                          ? "bg-primary/8 border-primary/30 text-foreground"
                          : "bg-secondary border-border text-foreground/70 hover:border-foreground/20 hover:text-foreground"
                      }`}
                    >
                      <div
                        className={`w-5 h-5 rounded-full border flex-shrink-0 flex items-center justify-center ${
                          answers[q.id] === choice.id ? "border-primary bg-primary" : "border-border"
                        }`}
                      >
                        {answers[q.id] === choice.id && <div className="w-2 h-2 rounded-full bg-white" />}
                      </div>
                      {choice.choice_text}
                    </button>
                  ))}
                </div>
              )}

              <div className="flex justify-between mt-6 pt-5 border-t border-border">
                <button
                  onClick={() => setCurrent((c) => Math.max(0, c - 1))}
                  disabled={current === 0}
                  className="px-4 py-2 border border-border hover:border-foreground/20 disabled:opacity-30 text-muted-foreground hover:text-foreground rounded-xl text-sm font-mono uppercase tracking-wider transition-colors"
                >
                  ← Previous
                </button>
                {current < questions.length - 1 ? (
                  <button
                    onClick={() => setCurrent((c) => c + 1)}
                    className="px-4 py-2 bg-primary hover:bg-primary/90 text-white rounded-xl text-sm font-mono uppercase tracking-wider transition-colors"
                  >
                    Next →
                  </button>
                ) : (
                  <button
                    onClick={handleSubmit}
                    disabled={phase === "submitting"}
                    className="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-xl text-sm font-mono uppercase tracking-wider transition-colors"
                  >
                    {phase === "submitting" ? "Submitting…" : "Submit Exam"}
                  </button>
                )}
              </div>
            </Card>
          </div>

          <div className="w-64 flex-shrink-0 space-y-4">
            <Card className="overflow-hidden">
              <div className="flex items-center gap-2 px-3 py-2 border-b border-border bg-secondary">
                <Eye className="w-3 h-3 text-muted-foreground" />
                <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest">AI Monitor</span>
              </div>
              <div className="relative aspect-[4/3] bg-secondary flex items-center justify-center">
                {!needsCamera ? (
                  <span className="text-[11px] font-mono text-muted-foreground px-4 text-center">
                    Camera not required — accommodation active
                  </span>
                ) : cameraError ? (
                  <span className="text-[11px] font-mono text-muted-foreground px-4 text-center">
                    Camera unavailable
                  </span>
                ) : (
                  <video ref={videoRef} autoPlay muted playsInline className="w-full h-full object-cover" />
                )}
              </div>
            </Card>

            <Card className="p-4 space-y-2.5">
              <div className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest">Detection Status</div>
              {[
                needsFaceCheck && faceCheckUnavailable
                  ? { label: "Face Verification", ok: false, alertLabel: "NOT ENROLLED" }
                  : {
                      label: "Face Verification",
                      ok: (!needsFaceCheck || (faceDetected && identityMatch)) && (!needsObjectCheck || !multiplePeople),
                      alertLabel: needsFaceCheck && !faceDetected
                        ? (personPresent ? "HEAD DOWN" : "NO FACE")
                        : needsFaceCheck && !identityMatch
                          ? "MISMATCH"
                          : "MULTIPLE PEOPLE",
                      accommodation: !needsFaceCheck && !needsObjectCheck,
                    },
                needsObjectCheck
                  ? { label: "Phone", ok: !phoneDetected, alertLabel: "ALERT" }
                  : { label: "Phone", ok: true, alertLabel: "ALERT", accommodation: true },
                { label: "Tab Focus", ok: tabFocusOk, alertLabel: "ALERT" },
                {
                  label: "Tab Monitor",
                  ok: !extensionAlert,
                  alertLabel:
                    extensionAlert?.eventType === "AI_TOOL_DETECTED" ? "AI TOOL" : "SEARCH ENGINE",
                },
              ].map(({ label, ok, alertLabel, accommodation }) => (
                <div key={label} className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground flex items-center gap-1.5">{label}</span>
                  <span
                    className={`text-[10px] font-mono font-bold ${
                      accommodation ? "text-muted-foreground" : ok ? "text-emerald-700" : "text-red-600"
                    }`}
                  >
                    {accommodation ? "N/A" : ok ? "OK" : alertLabel}
                  </span>
                </div>
              ))}
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
