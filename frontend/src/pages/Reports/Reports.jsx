import { useEffect, useMemo, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";
import { CheckCircle, XCircle } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { getExams } from "../../api/exams";
import { getInstructors } from "../../api/instructors";
import { getExamReport } from "../../api/reports";
import Card from "../../components/ui/Card";
import SectionTag from "../../components/ui/SectionTag";
import { SelectField } from "../../components/ui/FormField";

const TT = { background: "#fff", border: "1px solid rgba(0,0,0,0.1)", borderRadius: 8, fontSize: 11, fontFamily: "JetBrains Mono", color: "#0f172a" };
const TT_LABEL = { color: "#64748b" };
const TICK = { fill: "#94a3b8", fontSize: 11, fontFamily: "JetBrains Mono" };

const BUCKETS = [
  { label: "0-59", min: 0, max: 60 },
  { label: "60-69", min: 60, max: 70 },
  { label: "70-79", min: 70, max: 80 },
  { label: "80-89", min: 80, max: 90 },
  { label: "90-100", min: 90, max: 101 },
];

function accuracyColor(accuracy) {
  return accuracy >= 75 ? "#10b981" : accuracy >= 50 ? "#f97316" : "#ef4444";
}

export default function Reports() {
  const { user } = useAuth();

  const [exams, setExams] = useState([]);
  const [loadingExams, setLoadingExams] = useState(true);
  const [selectedExamId, setSelectedExamId] = useState("");
  const [report, setReport] = useState(null);
  const [loadingReport, setLoadingReport] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([getInstructors(), getExams()])
      .then(([instructors, allExams]) => {
        const me = instructors.find((i) => i.user_id === user.id);
        const mine = me ? allExams.filter((e) => e.instructor_id === me.id) : [];
        setExams(mine);
        if (mine.length > 0) setSelectedExamId(mine[0].id);
      })
      .finally(() => setLoadingExams(false));
  }, [user.id]);

  useEffect(() => {
    if (!selectedExamId) return;
    let cancelled = false;
    setLoadingReport(true);
    setError("");
    getExamReport(selectedExamId)
      .then((data) => {
        if (!cancelled) setReport(data);
      })
      .catch(() => {
        if (!cancelled) setError("Couldn't load this exam's report.");
      })
      .finally(() => {
        if (!cancelled) setLoadingReport(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedExamId]);

  const distribution = useMemo(() => {
    if (!report) return [];
    const submitted = report.attempts.filter((a) => a.status === "SUBMITTED");
    return BUCKETS.map((b) => ({
      label: b.label,
      count: submitted.filter((a) => a.percentage >= b.min && a.percentage < b.max).length,
    }));
  }, [report]);

  const passFail = useMemo(() => {
    if (!report) return [];
    return [
      { name: "Passed", value: report.pass_count, fill: "#10b981" },
      { name: "Failed", value: report.fail_count, fill: "#ef4444" },
    ];
  }, [report]);

  return (
    <div>
      <div className="flex items-start justify-between mb-8 gap-6">
        <div>
          <SectionTag text="Reports & Analytics" />
          <h2 className="font-display font-black text-foreground text-4xl">Exam Reports</h2>
        </div>
        {exams.length > 0 && (
          <div className="w-72">
            <SelectField
              label="Exam"
              value={selectedExamId}
              onChange={(e) => setSelectedExamId(Number(e.target.value))}
            >
              {exams.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.title}
                </option>
              ))}
            </SelectField>
          </div>
        )}
      </div>

      {!loadingExams && exams.length === 0 && (
        <Card className="p-8 text-center">
          <p className="text-sm text-muted-foreground">
            You don't have any exams assigned to your instructor profile yet.
          </p>
        </Card>
      )}

      {error && <div className="mb-4 rounded-xl bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-600">{error}</div>}

      {loadingReport && <div className="text-sm text-muted-foreground">Loading report…</div>}

      {report && !loadingReport && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <Card className="p-5">
              <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest mb-2">Submitted</div>
              <div className="font-display text-4xl font-black text-blue-600">{report.submitted_count}</div>
            </Card>
            <Card className="p-5">
              <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest mb-2">In Progress</div>
              <div className="font-display text-4xl font-black text-orange-600">{report.in_progress_count}</div>
            </Card>
            <Card className="p-5">
              <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest mb-2">Avg Score</div>
              <div className="font-display text-4xl font-black text-foreground">
                {report.average_percentage.toFixed(1)}%
              </div>
            </Card>
            <Card className="p-5">
              <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest mb-2">Pass Rate</div>
              <div className="font-display text-4xl font-black text-emerald-600">{report.pass_rate.toFixed(1)}%</div>
            </Card>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mb-6">
            <Card className="xl:col-span-2">
              <div className="px-6 py-4 border-b border-border text-[11px] font-mono text-muted-foreground uppercase tracking-widest">
                Score Distribution
              </div>
              <div className="p-6">
                {report.submitted_count === 0 ? (
                  <p className="text-sm text-muted-foreground">No submitted attempts yet.</p>
                ) : (
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={distribution}>
                      <XAxis dataKey="label" tick={TICK} axisLine={false} tickLine={false} />
                      <YAxis allowDecimals={false} tick={TICK} axisLine={false} tickLine={false} />
                      <Tooltip contentStyle={TT} labelStyle={TT_LABEL} />
                      <Bar dataKey="count" fill="#1a4fa8" radius={[6, 6, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </div>
            </Card>

            <Card>
              <div className="px-6 py-4 border-b border-border text-[11px] font-mono text-muted-foreground uppercase tracking-widest">
                Pass / Fail
              </div>
              <div className="p-6">
                {report.submitted_count === 0 ? (
                  <p className="text-sm text-muted-foreground">No submitted attempts yet.</p>
                ) : (
                  <>
                    <ResponsiveContainer width="100%" height={160}>
                      <PieChart>
                        <Pie data={passFail} cx="50%" cy="50%" innerRadius={40} outerRadius={70} dataKey="value" paddingAngle={3}>
                          {passFail.map((e, i) => (
                            <Cell key={i} fill={e.fill} />
                          ))}
                        </Pie>
                        <Tooltip contentStyle={TT} labelStyle={TT_LABEL} />
                      </PieChart>
                    </ResponsiveContainer>
                    <div className="space-y-1.5 mt-1">
                      {passFail.map((v) => (
                        <div key={v.name} className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: v.fill }} />
                            <span className="text-[11px] text-muted-foreground">{v.name}</span>
                          </div>
                          <span className="font-mono text-[11px] text-foreground/70">{v.value}</span>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </div>
            </Card>
          </div>

          <Card className="mb-6">
            <div className="px-6 py-4 border-b border-border text-[11px] font-mono text-muted-foreground uppercase tracking-widest">
              Question Accuracy
            </div>
            <div className="divide-y divide-border">
              {report.questions.length === 0 && (
                <div className="px-6 py-6 text-sm text-muted-foreground">This exam has no questions yet.</div>
              )}
              {report.questions.map((q, i) => (
                <div key={q.question_id} className="px-6 py-4">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-[11px] font-mono text-muted-foreground w-5">{i + 1}.</span>
                    <span className="text-sm text-foreground flex-1 truncate">{q.question_text}</span>
                    <span className="text-[11px] font-mono text-muted-foreground">
                      {q.correct_count}/{q.answered_count} correct
                    </span>
                    <span
                      className="font-mono text-xs font-bold w-12 text-right"
                      style={{ color: accuracyColor(q.accuracy) }}
                    >
                      {q.accuracy.toFixed(0)}%
                    </span>
                  </div>
                  <div className="h-1.5 bg-black/8 rounded-full overflow-hidden ml-8">
                    <div
                      className="h-full rounded-full"
                      style={{ width: `${q.accuracy}%`, backgroundColor: accuracyColor(q.accuracy), transition: "width 0.8s ease" }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </Card>

          <Card>
            <div className="px-6 py-4 border-b border-border text-[11px] font-mono text-muted-foreground uppercase tracking-widest">
              Attempts
            </div>
            <div className="divide-y divide-border">
              {report.attempts.length === 0 && (
                <div className="px-6 py-6 text-sm text-muted-foreground">No attempts yet.</div>
              )}
              {report.attempts.map((a) => (
                <div key={a.session_id} className="px-6 py-3 flex items-center gap-4">
                  <span className="font-mono text-xs text-foreground/80 w-28">{a.student_number}</span>
                  <span className="text-[11px] font-mono text-muted-foreground flex-1">
                    {a.submitted_at ? new Date(a.submitted_at).toLocaleString() : "In progress"}
                  </span>
                  <span
                    className={`text-[10px] font-mono px-2 py-0.5 rounded border uppercase tracking-wider ${
                      a.status === "SUBMITTED"
                        ? "text-blue-700 border-blue-200 bg-blue-50"
                        : "text-orange-700 border-orange-200 bg-orange-50"
                    }`}
                  >
                    {a.status}
                  </span>
                  {a.status === "SUBMITTED" && (
                    <>
                      <span className="font-mono text-xs text-foreground/80 w-20 text-right">
                        {a.score}/{report.total_points} pts
                      </span>
                      <span className="font-mono text-xs font-bold w-16 text-right">{a.percentage.toFixed(1)}%</span>
                      {a.passed ? (
                        <CheckCircle className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                      ) : (
                        <XCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
                      )}
                    </>
                  )}
                </div>
              ))}
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
