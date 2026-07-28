import { useEffect, useState } from "react";
import { GraduationCap, Users, ClipboardList, BookOpen, RefreshCw } from "lucide-react";
import { getStudents } from "../../api/students";
import { getInstructors } from "../../api/instructors";
import { getCourses } from "../../api/courses";
import { getExams } from "../../api/exams";
import { getSystemStatus } from "../../api/system";
import Card from "../../components/ui/Card";
import SectionTag from "../../components/ui/SectionTag";

export default function AdminDashboard() {
  const [tab, setTab] = useState("overview");
  const [data, setData] = useState({ students: [], instructors: [], courses: [], exams: [] });
  const [loading, setLoading] = useState(true);
  const [systemStatus, setSystemStatus] = useState(null);
  const [systemLoading, setSystemLoading] = useState(false);
  const [systemError, setSystemError] = useState(false);

  useEffect(() => {
    Promise.all([getStudents(), getInstructors(), getCourses(), getExams()])
      .then(([students, instructors, courses, exams]) => setData({ students, instructors, courses, exams }))
      .finally(() => setLoading(false));
  }, []);

  function loadSystemStatus() {
    setSystemLoading(true);
    setSystemError(false);
    getSystemStatus()
      .then(setSystemStatus)
      .catch(() => setSystemError(true))
      .finally(() => setSystemLoading(false));
  }

  useEffect(() => {
    if (tab === "system" && systemStatus === null && !systemLoading) {
      loadSystemStatus();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  const activeExams = data.exams.filter((e) => e.is_active).length;

  return (
    <div>
      <div className="flex items-start justify-between mb-8">
        <div>
          <SectionTag text="Administrator" />
          <h2 className="font-display font-black text-foreground text-4xl">Admin Dashboard</h2>
          <p className="text-muted-foreground text-sm mt-1">System management · Arellano University AI ExamGuard</p>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {[
          { val: data.students.length, label: "Total Students", icon: GraduationCap, color: "text-blue-600" },
          { val: data.instructors.length, label: "Instructors", icon: Users, color: "text-emerald-600" },
          { val: activeExams, label: "Active Exams", icon: ClipboardList, color: "text-orange-600" },
          { val: data.courses.length, label: "Courses", icon: BookOpen, color: "text-primary" },
        ].map(({ val, label, icon: Icon, color }) => (
          <Card key={label} className="p-5 flex items-center gap-4">
            <div className="w-10 h-10 rounded-xl bg-secondary border border-border flex items-center justify-center flex-shrink-0">
              <Icon className={`w-5 h-5 ${color}`} />
            </div>
            <div>
              <div className={`font-display text-3xl font-black ${color}`}>{loading ? "…" : val}</div>
              <div className="text-[11px] font-mono text-muted-foreground">{label}</div>
            </div>
          </Card>
        ))}
      </div>

      <div className="flex gap-1 bg-secondary border border-border rounded-xl p-1 mb-6 w-fit">
        {[
          ["overview", "Overview"],
          ["exams", "Exams"],
          ["system", "System"],
        ].map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`px-5 py-2 rounded-lg text-[12px] font-mono uppercase tracking-wider transition-all ${
              tab === key ? "bg-primary text-white" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "overview" && (
        <Card>
          <div className="px-6 py-4 border-b border-border">
            <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest">User Summary</div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 divide-y sm:divide-y-0 sm:divide-x divide-border">
            <div className="px-6 py-6">
              <div className="text-[10px] font-mono text-blue-600 uppercase tracking-widest mb-1">Students</div>
              <div className="font-display text-3xl font-black text-foreground">{data.students.length}</div>
              <p className="text-xs text-muted-foreground mt-2">
                Enrolled across {new Set(data.students.map((s) => s.course_id)).size} course(s).
              </p>
            </div>
            <div className="px-6 py-6">
              <div className="text-[10px] font-mono text-emerald-600 uppercase tracking-widest mb-1">Instructors</div>
              <div className="font-display text-3xl font-black text-foreground">{data.instructors.length}</div>
              <p className="text-xs text-muted-foreground mt-2">Provisioned instructor profiles.</p>
            </div>
          </div>
          <div className="px-6 py-4 border-t border-border text-xs text-muted-foreground">
            Per-user directory (names, emails, biometric status) will land once the Students/Instructors
            management pages are built — the backend doesn't join user details onto these list
            endpoints yet.
          </div>
        </Card>
      )}

      {tab === "exams" && (
        <Card>
          <div className="px-6 py-4 border-b border-border">
            <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest">Published Examinations</div>
          </div>
          <div className="divide-y divide-border">
            {data.exams.length === 0 && (
              <div className="px-6 py-6 text-sm text-muted-foreground">No exams yet.</div>
            )}
            {data.exams.map((e) => (
              <div key={e.id} className="px-6 py-4 flex items-center gap-4 hover:bg-secondary/50 transition-colors">
                <div className="w-10 h-10 rounded-xl bg-secondary border border-border flex items-center justify-center flex-shrink-0">
                  <BookOpen className="w-5 h-5 text-blue-500" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-foreground text-sm font-medium">{e.title}</span>
                    <span
                      className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                        e.is_active
                          ? "text-primary border-primary/25 bg-primary/8"
                          : "text-muted-foreground border-border bg-secondary"
                      }`}
                    >
                      {e.is_active ? "active" : "inactive"}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-[11px] font-mono text-muted-foreground">
                    <span>{new Date(e.start_time).toLocaleDateString()}</span>
                    <span>·</span>
                    <span>{e.duration_minutes} min</span>
                    <span>·</span>
                    <span>{e.total_points} pts</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {tab === "system" && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <p className="text-xs text-muted-foreground">
              Live status pulled from the running backend - model versions, real hardware, and a
              measured latency for each pipeline stage.
            </p>
            <button
              onClick={loadSystemStatus}
              disabled={systemLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-[11px] font-mono uppercase tracking-wider text-muted-foreground hover:text-foreground hover:border-foreground/20 disabled:opacity-50 transition-colors"
            >
              <RefreshCw className={`w-3 h-3 ${systemLoading ? "animate-spin" : ""}`} />
              Refresh
            </button>
          </div>

          {systemError && (
            <Card className="p-5 text-sm text-red-600">Couldn't load system status. Try refreshing.</Card>
          )}

          {!systemError && !systemStatus && (
            <Card className="p-5 text-sm text-muted-foreground">Loading system status…</Card>
          )}

          {systemStatus && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card className="p-5 flex items-center gap-4">
                <div className="w-10 h-10 rounded-xl bg-secondary border border-border flex items-center justify-center flex-shrink-0">
                  <div className={`w-3 h-3 rounded-full ${systemStatus.face.recognizer_available ? "bg-emerald-500" : "bg-red-500"}`} />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-foreground text-sm font-medium">Face Detection &amp; Recognition</span>
                    <span className="text-[10px] font-mono text-muted-foreground">
                      {systemStatus.face.recognizer_available ? "● loaded" : "● unavailable"}
                    </span>
                  </div>
                  <div className="text-[11px] font-mono text-muted-foreground">
                    {systemStatus.face.detector} · {systemStatus.face.recognizer} · OpenCV {systemStatus.face.opencv_version}
                  </div>
                  <div className="text-[11px] font-mono text-muted-foreground mt-0.5">
                    {systemStatus.face.enrolled_profiles} enrolled profile{systemStatus.face.enrolled_profiles === 1 ? "" : "s"}
                  </div>
                </div>
                <div className="font-mono text-sm text-foreground font-bold">{systemStatus.face.latency_ms}ms</div>
              </Card>

              <Card className="p-5 flex items-center gap-4">
                <div className="w-10 h-10 rounded-xl bg-secondary border border-border flex items-center justify-center flex-shrink-0">
                  <div className="w-3 h-3 rounded-full bg-emerald-500" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-foreground text-sm font-medium">Object Detection</span>
                    <span className="text-[10px] font-mono text-muted-foreground">● loaded</span>
                  </div>
                  <div className="text-[11px] font-mono text-muted-foreground">
                    {systemStatus.object_detection.base_model}
                  </div>
                  <div className="text-[11px] font-mono text-muted-foreground">
                    {systemStatus.object_detection.phone_model}
                  </div>
                  <div className="text-[11px] font-mono text-muted-foreground mt-0.5">
                    Ultralytics {systemStatus.object_detection.ultralytics_version} · Torch {systemStatus.object_detection.torch_version}
                  </div>
                </div>
                <div className="font-mono text-sm text-foreground font-bold">{systemStatus.object_detection.latency_ms}ms</div>
              </Card>

              <Card className="p-5 flex items-center gap-4">
                <div className="w-10 h-10 rounded-xl bg-secondary border border-border flex items-center justify-center flex-shrink-0">
                  <div className="w-3 h-3 rounded-full bg-emerald-500" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-foreground text-sm font-medium">Risk Engine</span>
                    <span className="text-[10px] font-mono text-muted-foreground">● loaded</span>
                  </div>
                  <div className="text-[11px] font-mono text-muted-foreground">
                    {systemStatus.risk_engine.vision_model}
                  </div>
                  <div className="text-[11px] font-mono text-muted-foreground mt-0.5">
                    scikit-learn {systemStatus.risk_engine.sklearn_version} · {systemStatus.risk_engine.behavioral_signal_count} hand-weighted behavioral signals
                  </div>
                </div>
                <div className="font-mono text-sm text-foreground font-bold">{systemStatus.risk_engine.latency_ms}ms</div>
              </Card>

              <Card className="p-5 flex items-center gap-4">
                <div className="w-10 h-10 rounded-xl bg-secondary border border-border flex items-center justify-center flex-shrink-0">
                  <div className="w-3 h-3 rounded-full bg-emerald-500" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-foreground text-sm font-medium">Tab Monitor Extension</span>
                    <span className="text-[10px] font-mono text-muted-foreground">● active</span>
                  </div>
                  <div className="text-[11px] font-mono text-muted-foreground">
                    {systemStatus.tab_monitor.extension_type}
                  </div>
                </div>
                <div className="font-mono text-sm text-foreground font-bold">
                  {systemStatus.tab_monitor.violations_logged} logged
                </div>
              </Card>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
