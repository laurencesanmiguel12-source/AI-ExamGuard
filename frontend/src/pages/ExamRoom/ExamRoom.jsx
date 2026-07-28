import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
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
import useProctoring from "../../hooks/useProctoring";
import useExtensionMonitor from "../../hooks/useExtensionMonitor";
import useCamera from "../../hooks/useCamera";
import Card from "../../components/ui/Card";
import StatusDot from "../../components/ui/StatusDot";
import RiskPill from "../../components/ui/RiskPill";
import PreExamModal from "./PreExamModal";

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
  const navigate = useNavigate();

  const [phase, setPhase] = useState("loading");
  const [error, setError] = useState("");
  const [exam, setExam] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [choicesByQuestion, setChoicesByQuestion] = useState({});
  const [session, setSession] = useState(null);
  const [answers, setAnswers] = useState({});
  const [current, setCurrent] = useState(0);
  const [result, setResult] = useState(null);
  const [risk, setRisk] = useState(0);
  const [lastTabSwitchAt, setLastTabSwitchAt] = useState(0);
  const [faceDetected, setFaceDetected] = useState(true);
  const [phoneDetected, setPhoneDetected] = useState(false);
  const [extensionAlert, setExtensionAlert] = useState(null);

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
    return new Date(session.started_at).getTime() + exam.duration_minutes * 60 * 1000;
  }, [session, exam]);

  const { mm, ss, expired } = useCountdown(deadline);

  useEffect(() => {
    if (expired && phase === "in-progress") {
      handleSubmit();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [expired, phase]);

  useProctoring(session?.id, phase === "in-progress", (eventType) => {
    if (eventType === "TAB_SWITCH") setLastTabSwitchAt(Date.now());
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

  const { videoRef, error: cameraError, ready: cameraReady, captureFrame } = useCamera(
    phase === "in-progress"
  );

  useEffect(() => {
    if (phase !== "in-progress" || !session || !cameraReady) return;
    let cancelled = false;

    async function checkOnce() {
      try {
        const blob = await captureFrame();
        if (!blob || cancelled) return;

        const faceResult = await checkFace(session.id, blob).catch(() => null);
        if (!cancelled && faceResult?.face_detected !== null && faceResult?.face_detected !== undefined) {
          setFaceDetected(faceResult.face_detected);
        }

        const objectResult = await checkObjects(session.id, blob).catch(() => null);
        if (!cancelled && objectResult) {
          setPhoneDetected(objectResult.phone_detected);
        }
      } catch {
        // best-effort; next check will retry naturally
      }
    }

    checkOnce();
    const id = setInterval(checkOnce, 5000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase, session, cameraReady]);

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
              <div className={`font-display text-2xl font-black ${result.passed ? "text-emerald-600" : "text-red-600"}`}>
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
                only). Install it from your instructor's provided link, then retry.
              </p>
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
                {cameraError ? (
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
                { label: "Face Detected", ok: faceDetected, alertLabel: "ALERT" },
                { label: "Phone", ok: !phoneDetected, alertLabel: "ALERT" },
                { label: "Tab Focus", ok: tabFocusOk, alertLabel: "ALERT" },
                {
                  label: "Tab Monitor",
                  ok: !extensionAlert,
                  alertLabel:
                    extensionAlert?.eventType === "AI_TOOL_DETECTED" ? "AI TOOL" : "SEARCH ENGINE",
                },
              ].map(({ label, ok, alertLabel }) => (
                <div key={label} className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground flex items-center gap-1.5">{label}</span>
                  <span className={`text-[10px] font-mono font-bold ${ok ? "text-emerald-600" : "text-red-600"}`}>
                    {ok ? "OK" : alertLabel}
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
