import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useSchoolNav } from "../../hooks/useSchoolNav";
import { ArrowLeft, CheckCircle, XCircle, MinusCircle } from "lucide-react";
import { getExamSession } from "../../api/examSessions";
import { getAnswers } from "../../api/studentAnswers";
import { getExam } from "../../api/exams";
import { getExamQuestions } from "../../api/questions";
import { getSessionViolations } from "../../api/violations";
import Card from "../../components/ui/Card";
import SectionTag from "../../components/ui/SectionTag";
import ViolationsPanel from "../../components/ViolationsPanel";

export default function ResultDetail() {
  const { sessionId } = useParams();
  const navigate = useSchoolNav();

  const [phase, setPhase] = useState("loading");
  const [session, setSession] = useState(null);
  const [exam, setExam] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [choicesByQuestion, setChoicesByQuestion] = useState({});
  const [answersByQuestion, setAnswersByQuestion] = useState({});
  const [violations, setViolations] = useState([]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const sessionData = await getExamSession(sessionId);
        if (cancelled) return;

        const [examData, answers, examQuestionsRaw, sessionViolations] = await Promise.all([
          getExam(sessionData.exam_id),
          getAnswers(sessionId),
          getExamQuestions(sessionData.exam_id),
          getSessionViolations(sessionId),
        ]);
        if (cancelled) return;

        const examQuestions = [...examQuestionsRaw].sort((a, b) => a.order_number - b.order_number);

        const grouped = {};
        for (const q of examQuestions) {
          grouped[q.id] = q.choices;
        }

        const answerMap = Object.fromEntries(answers.map((a) => [a.question_id, a]));

        setSession(sessionData);
        setExam(examData);
        setQuestions(examQuestions);
        setChoicesByQuestion(grouped);
        setAnswersByQuestion(answerMap);
        setViolations(sessionViolations);
        setPhase("ready");
      } catch {
        if (!cancelled) setPhase("error");
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  function handleAppealed(updated) {
    setViolations((vs) => vs.map((v) => (v.id === updated.id ? updated : v)));
  }

  if (phase === "loading") {
    return (
      <div className="text-sm text-muted-foreground font-mono uppercase tracking-widest">Loading…</div>
    );
  }

  if (phase === "error") {
    return <div className="text-sm text-red-600">Couldn't load this result.</div>;
  }

  return (
    <div>
      <button
        onClick={() => navigate("/results")}
        className="flex items-center gap-1.5 text-[11px] font-mono uppercase tracking-widest text-muted-foreground hover:text-foreground transition-colors mb-6"
      >
        <ArrowLeft className="w-3.5 h-3.5" /> Back to Results
      </button>

      <div className="mb-8">
        <SectionTag text="Exam Review" />
        <h2 className="font-display font-black text-foreground text-4xl">{exam.title}</h2>
        <p className="text-muted-foreground text-sm mt-1">
          Submitted {new Date(session.submitted_at).toLocaleString()}
        </p>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-8">
        <Card className="p-4 text-center">
          <div className="font-display text-2xl font-black text-foreground">
            {session.score}/{exam.total_points}
          </div>
          <div className="text-[10px] font-mono text-muted-foreground mt-0.5">Score</div>
        </Card>
        <Card className="p-4 text-center">
          <div className="font-display text-2xl font-black text-foreground">
            {session.percentage.toFixed(1)}%
          </div>
          <div className="text-[10px] font-mono text-muted-foreground mt-0.5">Percentage</div>
        </Card>
        <Card className={`p-4 text-center ${session.passed ? "bg-emerald-50" : "bg-red-50"}`}>
          <div className={`font-display text-2xl font-black ${session.passed ? "text-emerald-700" : "text-red-600"}`}>
            {session.passed ? "PASS" : "FAIL"}
          </div>
          <div className="text-[10px] font-mono text-muted-foreground mt-0.5">Result</div>
        </Card>
      </div>

      {session.status === "FLAGGED_RETAKE" && (
        <div className="mb-8 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          This session was flagged for a risk review. Your instructor is checking whether a retake
          is warranted — you'll be notified once they decide.
        </div>
      )}
      {session.status === "RETAKE_GRANTED" && (
        <div className="mb-8 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          Your instructor granted a retake for this exam. You can start a new attempt.
        </div>
      )}
      {session.status === "RETAKE_DENIED" && (
        <div className="mb-8 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          Your instructor reviewed this session and denied a retake.
        </div>
      )}

      <Card className="p-6 mb-8">
        <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest mb-4">
          Proctoring Violations
        </div>
        <ViolationsPanel violations={violations} mode="appeal" onAppealed={handleAppealed} />
      </Card>

      <div className="space-y-4">
        {questions.map((q, i) => {
          const answer = answersByQuestion[q.id];
          const choices = choicesByQuestion[q.id] ?? [];
          const ungraded = q.question_type === "Identification";

          return (
            <Card key={q.id} className="p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-8 h-8 rounded-xl bg-primary/8 border border-primary/20 flex items-center justify-center flex-shrink-0">
                  <span className="text-primary font-mono font-bold text-sm">{i + 1}</span>
                </div>
                <p className="text-foreground text-base leading-relaxed flex-1">{q.question_text}</p>
                {ungraded ? (
                  <MinusCircle className="w-5 h-5 text-muted-foreground flex-shrink-0" />
                ) : answer?.is_correct ? (
                  <CheckCircle className="w-5 h-5 text-emerald-700 flex-shrink-0" />
                ) : (
                  <XCircle className="w-5 h-5 text-red-600 flex-shrink-0" />
                )}
                <span className="text-[11px] font-mono text-muted-foreground flex-shrink-0">
                  {answer?.points_awarded ?? 0}/{q.points} pts
                </span>
              </div>

              {ungraded ? (
                <div className="rounded-xl border border-dashed border-orange-200 bg-orange-50 px-4 py-3 text-sm text-orange-700">
                  Free-text answers aren't gradable yet — this question wasn't scored.
                </div>
              ) : (
                <div className="space-y-2">
                  {choices.map((choice) => {
                    const wasSelected = answer?.choice_id === choice.id;
                    const isCorrect = choice.is_correct;
                    const style = isCorrect
                      ? "bg-emerald-50 border-emerald-200 text-emerald-800"
                      : wasSelected
                      ? "bg-red-50 border-red-200 text-red-800"
                      : "bg-secondary border-border text-foreground/70";

                    return (
                      <div
                        key={choice.id}
                        className={`flex items-center gap-3 px-4 py-2.5 rounded-xl border text-sm ${style}`}
                      >
                        <div
                          className={`w-4 h-4 rounded-full border flex-shrink-0 ${
                            wasSelected ? "border-current bg-current/20" : "border-border"
                          }`}
                        />
                        <span className="flex-1">{choice.choice_text}</span>
                        {wasSelected && (
                          <span className="text-[10px] font-mono uppercase tracking-wider">Your answer</span>
                        )}
                        {isCorrect && !wasSelected && (
                          <span className="text-[10px] font-mono uppercase tracking-wider">Correct</span>
                        )}
                      </div>
                    );
                  })}
                  {!answer?.choice_id && (
                    <div className="text-[11px] font-mono text-muted-foreground italic">Not answered</div>
                  )}
                </div>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}
