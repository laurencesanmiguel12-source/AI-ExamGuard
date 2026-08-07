import { useEffect, useState } from "react";
import { useSchoolNav } from "../../hooks/useSchoolNav";
import { CheckCircle, XCircle, ChevronRight } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { getExamSessions } from "../../api/examSessions";
import { getExams } from "../../api/exams";
import { getStudents } from "../../api/students";
import Card from "../../components/ui/Card";
import SectionTag from "../../components/ui/SectionTag";

// Any status submit_exam can leave a session in - not just "SUBMITTED" literally (see the
// backend's GRADED_STATUSES). FLAGGED_RETAKE/RETAKE_GRANTED/RETAKE_DENIED are still a real,
// scored, completed attempt the student needs to see and click into, just also under risk review.
const GRADED_STATUSES = ["SUBMITTED", "FLAGGED_RETAKE", "RETAKE_GRANTED", "RETAKE_DENIED"];

export default function Results() {
  const { user } = useAuth();
  const navigate = useSchoolNav();

  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errored, setErrored] = useState(false);
  const [noProfile, setNoProfile] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [sessions, exams, students] = await Promise.all([
          getExamSessions(),
          getExams(),
          getStudents(),
        ]);
        if (cancelled) return;

        const me = students.find((s) => s.user_id === user.id);
        if (!me) {
          setNoProfile(true);
          return;
        }

        const examsById = Object.fromEntries(exams.map((e) => [e.id, e]));
        const mine = sessions
          .filter((s) => s.student_id === me.id && GRADED_STATUSES.includes(s.status))
          .map((s) => ({ ...s, exam: examsById[s.exam_id] }))
          .sort((a, b) => new Date(b.submitted_at) - new Date(a.submitted_at));

        setRows(mine);
      } catch {
        if (!cancelled) setErrored(true);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [user.id]);

  return (
    <div>
      <div className="mb-8">
        <SectionTag text="Exam History" />
        <h2 className="font-display font-black text-foreground text-4xl">My Results</h2>
      </div>

      <Card>
        <div className="px-6 py-4 border-b border-border flex items-center justify-between">
          <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest">
            Submitted Attempts
          </div>
          <span className="text-[10px] font-mono text-primary bg-primary/8 border border-primary/20 px-2 py-0.5 rounded-full">
            {rows.length} total
          </span>
        </div>
        <div className="divide-y divide-border">
          {loading && <div className="px-6 py-6 text-sm text-muted-foreground">Loading…</div>}
          {errored && <div className="px-6 py-6 text-sm text-red-600">Couldn't load your results.</div>}
          {noProfile && !loading && (
            <div className="px-6 py-6 text-sm text-muted-foreground">
              Your account isn't linked to a student record yet. Ask an admin to provision one.
            </div>
          )}
          {!loading && !errored && !noProfile && rows.length === 0 && (
            <div className="px-6 py-6 text-sm text-muted-foreground">
              You haven't submitted any exams yet.
            </div>
          )}
          {rows.map((row) => (
            <button
              key={row.id}
              onClick={() => navigate(`/results/${row.id}`)}
              className="w-full px-6 py-4 flex items-center gap-4 hover:bg-secondary/50 transition-colors text-left"
            >
              <div
                className={`w-10 h-10 rounded-xl border flex items-center justify-center flex-shrink-0 ${
                  row.passed ? "bg-emerald-50 border-emerald-200" : "bg-red-50 border-red-200"
                }`}
              >
                {row.passed ? (
                  <CheckCircle className="w-5 h-5 text-emerald-600" />
                ) : (
                  <XCircle className="w-5 h-5 text-red-600" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-foreground text-sm font-medium">
                  {row.exam?.title ?? `Exam #${row.exam_id}`}
                </div>
                <div className="flex items-center gap-3 text-[11px] font-mono text-muted-foreground mt-0.5">
                  <span>{new Date(row.submitted_at).toLocaleString()}</span>
                  <span>·</span>
                  <span>
                    {row.score}/{row.exam?.total_points ?? "?"} pts
                  </span>
                </div>
              </div>
              <div className="text-right">
                <div className={`font-display text-xl font-black ${row.passed ? "text-emerald-600" : "text-red-600"}`}>
                  {row.percentage.toFixed(1)}%
                </div>
                <div className="text-[10px] font-mono text-muted-foreground">
                  {row.status === "FLAGGED_RETAKE"
                    ? "Under Review"
                    : row.status === "RETAKE_GRANTED"
                    ? "Retake Granted"
                    : row.status === "RETAKE_DENIED"
                    ? "Retake Denied"
                    : row.passed
                    ? "Passed"
                    : "Failed"}
                </div>
              </div>
              <ChevronRight className="w-4 h-4 text-muted-foreground flex-shrink-0" />
            </button>
          ))}
        </div>
      </Card>
    </div>
  );
}
