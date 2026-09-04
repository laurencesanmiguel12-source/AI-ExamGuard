import { useEffect, useState } from "react";
import { useSchoolNav } from "../../hooks/useSchoolNav";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { BookOpen, ArrowRight, UserCheck } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { getExams } from "../../api/exams";
import { getExamSessions } from "../../api/examSessions";
import { getStudents } from "../../api/students";
import { getSessionRiskSummary, getSessionViolations } from "../../api/violations";
import Card from "../../components/ui/Card";
import SectionTag from "../../components/ui/SectionTag";
import StatusDot from "../../components/ui/StatusDot";
import EnrollmentPromptModal from "../../components/EnrollmentPromptModal";

// sessionStorage (not localStorage) - "dismissed for this session", not forever. A fresh login
// (new tab/browser session) prompts again; navigating around the dashboard within the same
// session after dismissing once doesn't nag on every visit.
const DISMISS_KEY = "enrollmentPromptDismissed";

// A finished exam's risk score/timeline used to be recomputed here in JS, mirroring
// risk_service.py's WEIGHTS by hand (the backend's /risk endpoint only scores a trailing 120s
// window from *now*, meaningful only for a live in-progress session). That stopped being viable
// once part of the backend's scoring became a fitted model (RiskModelService) rather than a fixed
// weight dict - GET /exam-sessions/{id}/risk-summary now does this server-side instead.

const TT = { background: "#fff", border: "1px solid rgba(0,0,0,0.1)", borderRadius: 8, fontSize: 11, fontFamily: "JetBrains Mono", color: "#0f172a" };
const TT_LABEL = { color: "#64748b" };
const TICK = { fill: "#94a3b8", fontSize: 11, fontFamily: "JetBrains Mono" };

export default function StudentDashboard() {
  const { user } = useAuth();
  const navigate = useSchoolNav();
  const [exams, setExams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errored, setErrored] = useState(false);
  const [stats, setStats] = useState(null);
  const [me, setMe] = useState(null);
  const [riskTimeline, setRiskTimeline] = useState([]);
  const [showEnrollPrompt, setShowEnrollPrompt] = useState(false);

  useEffect(() => {
    getExams()
      .then(setExams)
      .catch(() => setErrored(true))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    let cancelled = false;

    Promise.all([getExamSessions(), getStudents()])
      .then(async ([sessions, students]) => {
        if (cancelled) return;
        const found = students.find((s) => s.user_id === user.id);
        if (!found) return;
        setMe(found);
        const submitted = sessions.filter((s) => s.student_id === found.id && s.status === "SUBMITTED");
        const avgScore =
          submitted.length === 0
            ? null
            : submitted.reduce((sum, s) => sum + s.percentage, 0) / submitted.length;

        if (submitted.length === 0) {
          setStats({ examsTaken: 0, avgScore, avgRisk: null, violationsCount: null });
          return;
        }

        const [violationsBySession, riskSummaries] = await Promise.all([
          Promise.all(submitted.map((s) => getSessionViolations(s.id).catch(() => []))),
          Promise.all(submitted.map((s) => getSessionRiskSummary(s.id).catch(() => null))),
        ]);
        if (cancelled) return;

        const sessionScores = riskSummaries.map((r) => r?.risk_score ?? 0);
        const avgRisk = sessionScores.reduce((sum, s) => sum + s, 0) / sessionScores.length;
        const violationsCount = violationsBySession.reduce((sum, v) => sum + v.length, 0);
        setStats({ examsTaken: submitted.length, avgScore, avgRisk, violationsCount });

        const lastIndex = submitted.reduce(
          (bestIdx, s, idx, arr) =>
            new Date(s.submitted_at) > new Date(arr[bestIdx].submitted_at) ? idx : bestIdx,
          0
        );
        const lastTimeline = riskSummaries[lastIndex]?.timeline ?? [];
        setRiskTimeline(
          lastTimeline.map((point) => ({
            time: new Date(point.time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            risk: point.risk,
          }))
        );
      })
      .catch(() => {});

    return () => {
      cancelled = true;
    };
  }, [user.id]);

  useEffect(() => {
    if (!me) return;
    const needsEnrollment = !me.skip_face_check && !me.face_model_path;
    if (needsEnrollment && sessionStorage.getItem(DISMISS_KEY) !== "1") {
      setShowEnrollPrompt(true);
    }
  }, [me]);

  function dismissEnrollPrompt() {
    sessionStorage.setItem(DISMISS_KEY, "1");
    setShowEnrollPrompt(false);
  }

  // Every exam is proctored by default (no per-exam opt-out) - the only way to skip face
  // enrollment is the student-level accommodation flag. The backend enforces this too in
  // exam_session_service.start_exam; this is UX, not the real gate.
  //
  // Component-level rather than per exam row: the banner below needs it even when the student
  // has no exams yet, which is exactly when they have time to get it done. The modal above is
  // the one-off interruption and can be dismissed for the session; the banner is the standing
  // reminder that does not go away until they actually enrol.
  const needsEnrollment = !!me && !me.skip_face_check && !me.face_model_path;

  return (
    <div>
      {showEnrollPrompt && (
        <EnrollmentPromptModal
          onEnrollNow={() => {
            dismissEnrollPrompt();
            navigate("/face-enrollment");
          }}
          onDismiss={dismissEnrollPrompt}
        />
      )}

      {/* The role used to be the small print above a big "Welcome, name", which told you who you
          were but not where you were. Reversed: the screen names itself first, and the greeting
          becomes context underneath it. */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <SectionTag text="Student" />
          <h2 className="font-display font-black text-foreground text-4xl">Student Dashboard</h2>
          <p className="text-muted-foreground text-sm mt-2 max-w-2xl">
            Welcome, {user?.first_name}. Exams you have been added to appear here — start one when
            it opens, and check your results once it is marked. Set up face enrolment before your
            first exam.
          </p>
        </div>
      </div>

      {/* Three columns only at 2xl: with the 224px sidebar and 48px padding, an xl window (1280)
          leaves ~1008px here, which is ~320px per column - too tight for these cards. 2xl
          (1536) leaves ~1264px, so ~405px each. Two columns cover everything in between. */}
      {/* A prerequisite, not a statistic. It used to live in a side card and as small print
          inside each exam row, so a student with no exam yet never discovered it - and one with
          an exam met it only at the moment they tried to start. */}
      {needsEnrollment && (
        <Card className="mb-6 border-amber-200 bg-amber-50 p-5">
          <div className="flex flex-wrap items-center gap-4">
            <UserCheck className="h-5 w-5 shrink-0 text-amber-700" />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-foreground">Set up face verification first</p>
              <p className="mt-0.5 text-sm text-muted-foreground">
                Your exams are proctored, so we need to recognise you before you can start one. It
                takes a minute and only has to be done once.
              </p>
            </div>
            <button
              onClick={() => navigate("/face-enrollment")}
              className="shrink-0 rounded-xl bg-primary px-4 py-2 text-[11px] font-mono uppercase tracking-wider text-white transition-colors hover:bg-primary/90"
            >
              Set up now
            </button>
          </div>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 2xl:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <div className="px-6 py-4 border-b border-border flex items-center justify-between">
              <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest">
                Your Exams
              </div>
              <span className="text-[10px] font-mono text-primary bg-primary/8 border border-primary/20 px-2 py-0.5 rounded-full">
                {exams.length} total
              </span>
            </div>
            <div className="divide-y divide-border">
              {loading && <div className="px-6 py-6 text-sm text-muted-foreground">Loading…</div>}
              {errored && <div className="px-6 py-6 text-sm text-red-600">Couldn't load exams.</div>}
              {!loading && !errored && exams.length === 0 && (
                <div className="px-6 py-10 text-center">
                  <p className="text-sm font-medium text-foreground">No exams yet</p>
                  <p className="mx-auto mt-1.5 max-w-md text-sm text-muted-foreground">
                    Your instructor adds you to an exam when it is ready. It will appear here, and
                    you can start it once it opens.
                  </p>
                </div>
              )}
              {exams.map((e) => {
                return (
                <div key={e.id} className="px-6 py-4 flex items-center gap-4 hover:bg-secondary/50 transition-colors">
                  <div className="w-10 h-10 rounded-xl bg-secondary border border-border flex items-center justify-center flex-shrink-0">
                    <BookOpen className="w-5 h-5 text-blue-500" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-foreground text-sm font-medium">{e.title}</span>
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                          e.is_active
                            ? "text-emerald-700 border-emerald-200 bg-emerald-50"
                            : "text-muted-foreground border-border bg-secondary"
                        }`}
                      >
                        {e.is_active ? "active" : "inactive"}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-[11px] font-mono text-muted-foreground">
                      <span>{new Date(e.start_time).toLocaleString()}</span>
                      <span>·</span>
                      <span>{e.duration_minutes} min</span>
                      <span>·</span>
                      <span>{e.total_points} pts</span>
                    </div>
                    {needsEnrollment && (
                      <div className="text-[10px] font-mono text-amber-700 mt-1">
                        Face enrollment required before starting
                      </div>
                    )}
                  </div>
                  <button
                    onClick={() =>
                      needsEnrollment ? navigate("/face-enrollment") : navigate(`/take-exam/${e.id}`)
                    }
                    disabled={!e.is_active}
                    title={needsEnrollment ? "Enroll your face before starting a proctored exam" : undefined}
                    className="flex items-center gap-1.5 bg-primary hover:bg-primary/90 disabled:opacity-40 text-white text-[11px] font-mono uppercase tracking-wider px-3 py-2 rounded-lg transition-colors"
                  >
                    {needsEnrollment ? "Enroll First" : "Start"} <ArrowRight className="w-3 h-3" />
                  </button>
                </div>
                );
              })}
            </div>
          </Card>

          <Card>
            <div className="px-6 py-4 border-b border-border">
              <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest">
                Last Exam — Risk Timeline
              </div>
            </div>
            <div className="p-6">
              {riskTimeline.length === 0 ? (
                <div className="h-[180px] flex items-center justify-center text-sm text-muted-foreground">
                  No submitted exams yet.
                </div>
              ) : (
                <ResponsiveContainer width="100%" height={180}>
                  <AreaChart data={riskTimeline}>
                    <defs>
                      <linearGradient id="rg1" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#c8192e" stopOpacity={0.15} />
                        <stop offset="95%" stopColor="#c8192e" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="time" tick={TICK} axisLine={false} tickLine={false} />
                    <YAxis domain={[0, 100]} tick={TICK} axisLine={false} tickLine={false} />
                    <Tooltip contentStyle={TT} labelStyle={TT_LABEL} />
                    <Area type="monotone" dataKey="risk" stroke="#c8192e" strokeWidth={2} fill="url(#rg1)" />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </div>
          </Card>
        </div>

        <div className="space-y-4">
          <Card className="p-5">
            <div className="flex items-center gap-4 mb-5">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-500 to-primary flex items-center justify-center text-white font-display font-black text-2xl flex-shrink-0">
                {user?.first_name?.[0]}
              </div>
              <div>
                <div className="text-foreground font-semibold">
                  {user?.first_name} {user?.last_name}
                </div>
                <div className="text-[11px] font-mono text-muted-foreground truncate">{user?.email}</div>
                <div className="flex items-center gap-1.5 mt-1">
                  <div className={`w-1.5 h-1.5 rounded-full ${user?.is_active ? "bg-emerald-500" : "bg-red-500"}`} />
                  <span className={`text-[10px] font-mono ${user?.is_active ? "text-emerald-700" : "text-red-600"}`}>
                    {user?.is_active ? "Active" : "Inactive"}
                  </span>
                </div>
              </div>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground">Email</span>
                <span className="text-foreground/80 font-mono">{user?.email}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground">Role</span>
                <span className="text-foreground/80 font-mono uppercase">{user?.role_name}</span>
              </div>
            </div>
          </Card>

          <Card className="p-5">
            <div className="flex items-center gap-2 mb-4">
              <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest">
                Biometric Status
              </div>
            </div>
            <div className="flex items-center gap-3 mb-4">
              <div
                className={`w-10 h-10 rounded-xl border flex items-center justify-center ${
                  me?.face_model_path ? "bg-emerald-50 border-emerald-200" : "bg-secondary border-border"
                }`}
              >
                <UserCheck className={`w-5 h-5 ${me?.face_model_path ? "text-emerald-700" : "text-muted-foreground"}`} />
              </div>
              <div>
                <div className="text-foreground text-sm font-medium">
                  {me?.face_model_path ? "Enrolled" : "Not Enrolled"}
                </div>
                <div className="text-[11px] font-mono text-muted-foreground">
                  {me?.face_model_path ? "Ready for exam verification" : "Required before proctored exams"}
                </div>
              </div>
            </div>
            <div className="space-y-2 mb-4">
              <StatusDot on={!!me?.face_model_path} label="Face model trained" />
              <StatusDot on={!!me?.face_model_path} label="Ready for verification" />
            </div>
            {me && (
              <button
                onClick={() => navigate("/face-enrollment")}
                className="w-full bg-primary hover:bg-primary/90 text-white py-2 rounded-xl text-[11px] font-mono uppercase tracking-widest transition-colors"
              >
                {me.face_model_path ? "Re-enroll" : "Enroll Now"}
              </button>
            )}
          </Card>

          <Card className="p-5">
            <div className="flex items-center gap-2 mb-4">
              <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest">My Stats</div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              {[
                { val: stats ? String(stats.examsTaken) : "—", label: "Exams Taken", color: "text-blue-600" },
                {
                  val: stats?.avgScore != null ? `${stats.avgScore.toFixed(0)}%` : "—",
                  label: "Avg Score",
                  color: "text-emerald-700",
                },
              ].map(({ val, label, color }) => (
                <div key={label} className="bg-secondary border border-border rounded-xl p-3 text-center">
                  <div className={`font-display text-2xl font-black ${color}`}>{val}</div>
                  <div className="text-[10px] font-mono text-muted-foreground mt-0.5 flex items-center justify-center gap-1">
                    {label}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
