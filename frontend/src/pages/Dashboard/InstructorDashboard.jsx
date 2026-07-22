import { useEffect, useState } from "react";
import { PieChart as RPie, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import { Eye, FileText, BarChart3 } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { getExams } from "../../api/exams";
import { getInstructors } from "../../api/instructors";
import Card from "../../components/ui/Card";
import RiskPill from "../../components/ui/RiskPill";
import RiskBar from "../../components/ui/RiskBar";
import PreviewBadge from "../../components/ui/PreviewBadge";

const liveStudents = [
  { id: "AU-2025-001", name: "Maria Santos", risk: 12, status: "safe", face: true, phone: false, tab: false, lstm: 8 },
  { id: "AU-2025-002", name: "Juan dela Cruz", risk: 74, status: "high", face: true, phone: true, tab: true, lstm: 86 },
  { id: "AU-2025-003", name: "Ana Reyes", risk: 5, status: "safe", face: true, phone: false, tab: false, lstm: 4 },
  { id: "AU-2025-004", name: "Carlo Mendoza", risk: 91, status: "critical", face: false, phone: true, tab: false, lstm: 94 },
  { id: "AU-2025-005", name: "Liza Garcia", risk: 38, status: "medium", face: true, phone: false, tab: true, lstm: 42 },
];

const violationBreakdown = [
  { name: "Phone Detected", value: 34, fill: "#c8192e" },
  { name: "Tab Switch", value: 28, fill: "#1a4fa8" },
  { name: "Face Loss", value: 20, fill: "#e86e1e" },
  { name: "Unknown Face", value: 12, fill: "#8b1ec4" },
  { name: "Multiple People", value: 6, fill: "#1ec47a" },
];

const sessionAlerts = [
  { t: "09:34:53", msg: "Identity mismatch · Carlos Mendoza", type: "critical" },
  { t: "09:30:17", msg: "Face loss · Carlos Mendoza", type: "high" },
  { t: "09:21:33", msg: "Tab switch · Jenny Flores", type: "warn" },
  { t: "09:15:08", msg: "Phone detected · Juan dela Cruz", type: "high" },
  { t: "09:01:00", msg: "All identities verified", type: "ok" },
];

const TT = { background: "#fff", border: "1px solid rgba(0,0,0,0.1)", borderRadius: 8, fontSize: 11, fontFamily: "JetBrains Mono", color: "#0f172a" };
const TT_LABEL = { color: "#64748b" };

export default function InstructorDashboard() {
  const { user } = useAuth();
  const [myExams, setMyExams] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getInstructors(), getExams()])
      .then(([instructors, exams]) => {
        const me = instructors.find((i) => i.user_id === user.id);
        setMyExams(me ? exams.filter((e) => e.instructor_id === me.id) : []);
      })
      .catch(() => setMyExams([]))
      .finally(() => setLoading(false));
  }, [user]);

  const activeCount = myExams.filter((e) => e.is_active).length;

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
          { val: liveStudents.length, label: "Live Sessions", color: "text-orange-600", preview: true },
          { val: liveStudents.filter((s) => s.status === "critical").length, label: "Critical", color: "text-red-600", preview: true },
        ].map(({ val, label, color, preview }) => (
          <Card key={label} className="p-5">
            <div className="flex items-center gap-2 mb-2">
              <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest">{label}</div>
              {preview && <PreviewBadge />}
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
              <PreviewBadge />
            </div>
            <div className="divide-y divide-border">
              {liveStudents.map((s) => (
                <div
                  key={s.id}
                  className={`px-6 py-4 flex items-center gap-4 hover:bg-secondary/50 transition-colors ${
                    s.status === "critical" ? "bg-red-50/60" : ""
                  }`}
                >
                  <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-100 to-red-100 flex items-center justify-center text-foreground font-display font-black text-sm flex-shrink-0 border border-border">
                    {s.name[0]}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-foreground text-sm font-medium">{s.name}</span>
                      <RiskPill value={s.risk} />
                    </div>
                    <div className="flex items-center gap-3 text-[10px] font-mono text-muted-foreground">
                      <span>{s.id}</span>
                      <span className={s.face ? "text-emerald-600" : "text-red-600"}>Face:{s.face ? "✓" : "✗"}</span>
                      <span className={s.phone ? "text-red-600" : "text-muted-foreground"}>Phone:{s.phone ? "!" : "–"}</span>
                      <span className={s.tab ? "text-orange-600" : "text-muted-foreground"}>Tab:{s.tab ? "!" : "–"}</span>
                    </div>
                  </div>
                  <div className="w-24"><RiskBar value={s.risk} /></div>
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
              <PreviewBadge />
            </div>
            <div className="space-y-2">
              {sessionAlerts.map((a, i) => (
                <div key={i} className="flex items-start gap-2.5 py-1.5 border-b border-border last:border-0">
                  <div
                    className={`w-1.5 h-1.5 rounded-full flex-shrink-0 mt-1.5 ${
                      a.type === "critical" ? "bg-red-500" : a.type === "high" ? "bg-orange-400" : a.type === "warn" ? "bg-blue-400" : "bg-emerald-500"
                    }`}
                  />
                  <div className="flex-1">
                    <div className="text-xs text-foreground/80">{a.msg}</div>
                    <div className="font-mono text-[10px] text-muted-foreground">{a.t}</div>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          <Card className="p-5">
            <div className="flex items-center gap-2 mb-4">
              <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest">Violation Breakdown</div>
              <PreviewBadge />
            </div>
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
                  <span className="font-mono text-[11px] text-foreground/70">{v.value}%</span>
                </div>
              ))}
            </div>
          </Card>

          <div className="grid grid-cols-2 gap-3">
            <button className="flex flex-col items-center gap-1.5 p-4 bg-card border border-border hover:border-foreground/15 rounded-xl transition-colors">
              <FileText className="w-5 h-5 text-blue-500" />
              <span className="text-[11px] font-mono text-muted-foreground">Reports</span>
            </button>
            <button className="flex flex-col items-center gap-1.5 p-4 bg-card border border-border hover:border-foreground/15 rounded-xl transition-colors">
              <BarChart3 className="w-5 h-5 text-primary" />
              <span className="text-[11px] font-mono text-muted-foreground">Analytics</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
