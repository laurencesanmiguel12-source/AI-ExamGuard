import { useEffect, useState } from "react";
import { useSchoolNav } from "../../hooks/useSchoolNav";
import { PieChart as RPie, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import { Eye, FileText, BarChart3 } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { getExams } from "../../api/exams";
import { getInstructors } from "../../api/instructors";
import { getLiveSessions } from "../../api/violations";
import Card from "../../components/ui/Card";
import RiskPill from "../../components/ui/RiskPill";
import RiskBar from "../../components/ui/RiskBar";

const VIOLATION_META = {
  TAB_SWITCH: { label: "Tab Switch", fill: "#1a4fa8" },
  FULLSCREEN_EXIT: { label: "Fullscreen Exit", fill: "#c8192e" },
  COPY_PASTE: { label: "Copy/Paste", fill: "#e86e1e" },
  RIGHT_CLICK: { label: "Right Click", fill: "#8b1ec4" },
  FACE_LOST: { label: "Face Lost", fill: "#1ec47a" },
  IDENTITY_MISMATCH: { label: "Identity Mismatch", fill: "#f43f5e" },
  PHONE_DETECTED: { label: "Phone Detected", fill: "#eab308" },
  MULTIPLE_PEOPLE: { label: "Multiple People", fill: "#0ea5e9" },
  AI_TOOL_DETECTED: { label: "AI Tool Detected", fill: "#dc2626" },
  SEARCH_ENGINE_DETECTED: { label: "Search Engine Detected", fill: "#f97316" },
  // Head pose, not eye gaze - a coarse proxy, not a certain detection, so it reads as "needs
  // review" rather than a hard accusation.
  PROLONGED_HEAD_DOWN: { label: "Prolonged Downward Gaze", fill: "#0d9488" },
  // Sustained near-identical webcam frames - a suspected static photo held up to the camera,
  // not just a single bad-angle mismatch. See risk_service.py's weighting note.
  STATIC_IMAGE_SUSPECTED: { label: "Static Image Suspected", fill: "#9333ea" },
};

const ALERT_SEVERITY = {
  FULLSCREEN_EXIT: "critical",
  IDENTITY_MISMATCH: "critical",
  PHONE_DETECTED: "critical",
  AI_TOOL_DETECTED: "critical",
  SEARCH_ENGINE_DETECTED: "critical",
  STATIC_IMAGE_SUSPECTED: "critical",
  FACE_LOST: "high",
  COPY_PASTE: "high",
  MULTIPLE_PEOPLE: "high",
  PROLONGED_HEAD_DOWN: "high",
  TAB_SWITCH: "warn",
  RIGHT_CLICK: "warn",
};

const TT = { background: "#fff", border: "1px solid rgba(0,0,0,0.1)", borderRadius: 8, fontSize: 11, fontFamily: "JetBrains Mono", color: "#0f172a" };
const TT_LABEL = { color: "#64748b" };

export default function InstructorDashboard() {
  const { user } = useAuth();
  const navigate = useSchoolNav();
  const [myExams, setMyExams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [liveSessions, setLiveSessions] = useState([]);
  const [recentEvents, setRecentEvents] = useState([]);

  useEffect(() => {
    Promise.all([getInstructors(), getExams()])
      .then(([instructors, exams]) => {
        const me = instructors.find((i) => i.user_id === user.id);
        setMyExams(me ? exams.filter((e) => e.instructor_id === me.id) : []);
      })
      .catch(() => setMyExams([]))
      .finally(() => setLoading(false));
  }, [user]);

  useEffect(() => {
    let cancelled = false;

    function poll() {
      getLiveSessions()
        .then((data) => {
          if (cancelled) return;
          setLiveSessions(data.sessions);
          setRecentEvents(data.recent_events);
        })
        .catch(() => {});
    }

    poll();
    const id = setInterval(poll, 5000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const activeCount = myExams.filter((e) => e.is_active).length;
  const myExamIds = new Set(myExams.map((e) => e.id));
  const mySessions = liveSessions.filter((s) => myExamIds.has(s.exam_id));
  const myRecentEvents = recentEvents.filter((e) => myExamIds.has(e.exam_id));
  const criticalCount = mySessions.filter((s) => s.risk_score >= 75).length;

  const violationBreakdown = Object.entries(VIOLATION_META)
    .map(([type, meta]) => ({
      name: meta.label,
      fill: meta.fill,
      value: mySessions.reduce((sum, s) => sum + (s.violation_counts[type] ?? 0), 0),
    }))
    .filter((v) => v.value > 0);

  return (
    <div>
      <div className="flex items-start justify-between mb-8">
        <div>
          <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest mb-1">
            Instructor Dashboard
          </div>
          <h2 className="font-display font-black text-foreground text-4xl">
            Welcome, {user?.first_name}
          </h2>
          <p className="text-muted-foreground text-sm mt-1">
            {loading
              ? "Loading your exams…"
              : myExams.length === 0
              ? "No exams assigned to your instructor profile yet."
              : `${myExams.length} exam${myExams.length === 1 ? "" : "s"} · ${activeCount} active`}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {[
          { val: myExams.length, label: "My Exams", color: "text-blue-600" },
          { val: activeCount, label: "Active", color: "text-emerald-600" },
          { val: mySessions.length, label: "Live Sessions", color: "text-orange-600" },
          { val: criticalCount, label: "Critical", color: "text-red-600" },
        ].map(({ val, label, color }) => (
          <Card key={label} className="p-5">
            <div className="flex items-center gap-2 mb-2">
              <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest">{label}</div>
            </div>
            <div className={`font-display text-4xl font-black ${color}`}>{val}</div>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2">
          <Card>
            <div className="px-6 py-4 border-b border-border flex items-center gap-2">
              <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest">
                Examinee Risk Monitor
              </div>
            </div>
            <div className="divide-y divide-border">
              {mySessions.length === 0 && (
                <div className="px-6 py-6 text-sm text-muted-foreground">No active exam sessions right now.</div>
              )}
              {mySessions.map((s) => (
                <div
                  key={s.session_id}
                  className={`px-6 py-4 flex items-center gap-4 hover:bg-secondary/50 transition-colors ${
                    s.risk_score >= 75 ? "bg-red-50/60" : ""
                  }`}
                >
                  <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-100 to-red-100 flex items-center justify-center text-foreground font-display font-black text-sm flex-shrink-0 border border-border">
                    {s.student_name?.[0] ?? "?"}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-foreground text-sm font-medium">{s.student_name}</span>
                      <span className="text-[10px] font-mono text-muted-foreground">{s.student_number}</span>
                      <RiskPill value={Math.round(s.risk_score)} />
                    </div>
                    <div className="flex items-center gap-3 text-[10px] font-mono text-muted-foreground truncate">
                      <span>{s.exam_title}</span>
                      {Object.entries(VIOLATION_META).map(([type, meta]) => {
                        const count = s.violation_counts[type] ?? 0;
                        return (
                          <span key={type} className={count > 0 ? "text-orange-600" : "text-muted-foreground"}>
                            {meta.label}:{count > 0 ? count : "–"}
                          </span>
                        );
                      })}
                    </div>
                  </div>
                  <div className="w-24"><RiskBar value={Math.round(s.risk_score)} /></div>
                  <Eye className="w-4 h-4 text-muted-foreground" />
                </div>
              ))}
            </div>
          </Card>
        </div>

        <div className="space-y-4">
          <Card className="p-5">
            <div className="flex items-center gap-2 mb-4">
              <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest">Session Alerts</div>
            </div>
            <div className="space-y-2">
              {myRecentEvents.length === 0 && (
                <div className="text-xs text-muted-foreground">No recent activity.</div>
              )}
              {myRecentEvents.map((e, i) => (
                <div key={i} className="flex items-start gap-2.5 py-1.5 border-b border-border last:border-0">
                  <div
                    className={`w-1.5 h-1.5 rounded-full flex-shrink-0 mt-1.5 ${
                      ALERT_SEVERITY[e.event_type] === "critical"
                        ? "bg-red-500"
                        : ALERT_SEVERITY[e.event_type] === "high"
                        ? "bg-orange-400"
                        : "bg-blue-400"
                    }`}
                  />
                  <div className="flex-1">
                    <div className="text-xs text-foreground/80">
                      {VIOLATION_META[e.event_type]?.label ?? e.event_type}
                      {e.detail ? ` · ${e.detail}` : ""} · {e.student_name} ({e.student_number})
                    </div>
                    <div className="font-mono text-[10px] text-muted-foreground">
                      {new Date(e.created_at).toLocaleTimeString()}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          <Card className="p-5">
            <div className="flex items-center gap-2 mb-4">
              <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest">Violation Breakdown</div>
            </div>
            {violationBreakdown.length === 0 ? (
              <p className="text-sm text-muted-foreground">No violations logged yet.</p>
            ) : (
              <>
                <ResponsiveContainer width="100%" height={160}>
                  <RPie>
                    <Pie data={violationBreakdown} cx="50%" cy="50%" innerRadius={40} outerRadius={70} dataKey="value" paddingAngle={3}>
                      {violationBreakdown.map((e, i) => <Cell key={i} fill={e.fill} />)}
                    </Pie>
                    <Tooltip contentStyle={TT} labelStyle={TT_LABEL} />
                  </RPie>
                </ResponsiveContainer>
                <div className="space-y-1.5 mt-1">
                  {violationBreakdown.map((v) => (
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
          </Card>

          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={() => navigate("/reports")}
              className="flex flex-col items-center gap-1.5 p-4 bg-card border border-border hover:border-foreground/15 rounded-xl transition-colors"
            >
              <FileText className="w-5 h-5 text-blue-500" />
              <span className="text-[11px] font-mono text-muted-foreground">Reports</span>
            </button>
            <button
              onClick={() => navigate("/reports")}
              className="flex flex-col items-center gap-1.5 p-4 bg-card border border-border hover:border-foreground/15 rounded-xl transition-colors"
            >
              <BarChart3 className="w-5 h-5 text-primary" />
              <span className="text-[11px] font-mono text-muted-foreground">Analytics</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
