import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { BookOpen, ArrowRight, UserCheck } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { getExams } from "../../api/exams";
import { getExamSessions } from "../../api/examSessions";
import { getStudents } from "../../api/students";
import Card from "../../components/ui/Card";
import StatusDot from "../../components/ui/StatusDot";
import PreviewBadge from "../../components/ui/PreviewBadge";

const riskTimeline = [
  { time: "09:00", risk: 5 }, { time: "09:05", risk: 8 }, { time: "09:10", risk: 12 },
  { time: "09:15", risk: 55 }, { time: "09:20", risk: 48 }, { time: "09:25", risk: 20 },
  { time: "09:30", risk: 72 }, { time: "09:35", risk: 88 }, { time: "09:40", risk: 61 },
  { time: "09:45", risk: 30 }, { time: "09:50", risk: 18 },
];

const TT = { background: "#fff", border: "1px solid rgba(0,0,0,0.1)", borderRadius: 8, fontSize: 11, fontFamily: "JetBrains Mono", color: "#0f172a" };
const TT_LABEL = { color: "#64748b" };
const TICK = { fill: "#94a3b8", fontSize: 11, fontFamily: "JetBrains Mono" };

export default function StudentDashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [exams, setExams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errored, setErrored] = useState(false);
  const [stats, setStats] = useState(null);

  useEffect(() => {
    getExams()
      .then(setExams)
      .catch(() => setErrored(true))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    let cancelled = false;

    Promise.all([getExamSessions(), getStudents()])
      .then(([sessions, students]) => {
        if (cancelled) return;
        const me = students.find((s) => s.user_id === user.id);
        if (!me) return;
        const submitted = sessions.filter((s) => s.student_id === me.id && s.status === "SUBMITTED");
        const avgScore =
          submitted.length === 0
            ? null
            : submitted.reduce((sum, s) => sum + s.percentage, 0) / submitted.length;
        setStats({ examsTaken: submitted.length, avgScore });
      })
      .catch(() => {});

    return () => {
      cancelled = true;
    };
  }, [user.id]);

  return (
    <div>
      <div className="flex items-start justify-between mb-8">
        <div>
          <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest mb-1">
            Student Dashboard
          </div>
          <h2 className="font-display font-black text-foreground text-4xl">
            Welcome, {user?.first_name}
          </h2>
          <p className="text-muted-foreground text-sm mt-1">{user?.email}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <div className="px-6 py-4 border-b border-border flex items-center justify-between">
              <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest">
                Available Exams
              </div>
              <span className="text-[10px] font-mono text-primary bg-primary/8 border border-primary/20 px-2 py-0.5 rounded-full">
                {exams.length} total
              </span>
            </div>
            <div className="divide-y divide-border">
              {loading && <div className="px-6 py-6 text-sm text-muted-foreground">Loading…</div>}
              {errored && <div className="px-6 py-6 text-sm text-red-600">Couldn't load exams.</div>}
              {!loading && !errored && exams.length === 0 && (
                <div className="px-6 py-6 text-sm text-muted-foreground">No exams available yet.</div>
              )}
              {exams.map((e) => (
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
                  </div>
                  <button
                    onClick={() => navigate(`/take-exam/${e.id}`)}
                    disabled={!e.is_active}
                    className="flex items-center gap-1.5 bg-primary hover:bg-primary/90 disabled:opacity-40 text-white text-[11px] font-mono uppercase tracking-wider px-3 py-2 rounded-lg transition-colors"
                  >
                    Start <ArrowRight className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
          </Card>

          <Card>
            <div className="px-6 py-4 border-b border-border flex items-center gap-2">
              <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest">
                Last Exam — Risk Timeline
              </div>
              <PreviewBadge />
            </div>
            <div className="p-6">
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
                <div className="text-[11px] font-mono text-muted-foreground">{user?.username}</div>
                <div className="flex items-center gap-1.5 mt-1">
                  <div className={`w-1.5 h-1.5 rounded-full ${user?.is_active ? "bg-emerald-500" : "bg-red-500"}`} />
                  <span className={`text-[10px] font-mono ${user?.is_active ? "text-emerald-600" : "text-red-600"}`}>
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
              <PreviewBadge />
            </div>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-secondary border border-border flex items-center justify-center">
                <UserCheck className="w-5 h-5 text-muted-foreground" />
              </div>
              <div>
                <div className="text-foreground text-sm font-medium">Not Enrolled</div>
                <div className="text-[11px] font-mono text-muted-foreground">Face enrollment ships in Phase 9</div>
              </div>
            </div>
            <div className="space-y-2">
              <StatusDot on={false} label="Face encoding saved" />
              <StatusDot on={false} label="Reference images stored" />
              <StatusDot on={false} label="Identity verified" />
            </div>
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
                  color: "text-emerald-600",
                },
                { val: "—", label: "Avg Risk", color: "text-emerald-600", preview: true },
                { val: "—", label: "Violations", color: "text-orange-600", preview: true },
              ].map(({ val, label, color, preview }) => (
                <div key={label} className="bg-secondary border border-border rounded-xl p-3 text-center">
                  <div className={`font-display text-2xl font-black ${color}`}>{val}</div>
                  <div className="text-[10px] font-mono text-muted-foreground mt-0.5 flex items-center justify-center gap-1">
                    {label} {preview && <PreviewBadge />}
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
