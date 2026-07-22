import { useEffect, useState } from "react";
import { GraduationCap, Users, ClipboardList, BookOpen } from "lucide-react";
import { getStudents } from "../../api/students";
import { getInstructors } from "../../api/instructors";
import { getCourses } from "../../api/courses";
import { getExams } from "../../api/exams";
import Card from "../../components/ui/Card";
import SectionTag from "../../components/ui/SectionTag";
import PreviewBadge from "../../components/ui/PreviewBadge";

export default function AdminDashboard() {
  const [tab, setTab] = useState("overview");
  const [data, setData] = useState({ students: [], instructors: [], courses: [], exams: [] });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getStudents(), getInstructors(), getCourses(), getExams()])
      .then(([students, instructors, courses, exams]) => setData({ students, instructors, courses, exams }))
      .finally(() => setLoading(false));
  }, []);

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
          <div className="mb-4"><PreviewBadge label="PREVIEW — PHASE 9" /></div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[
              { label: "YOLOv8 Engine", metric: "28–30 FPS", detail: "v8.0.196 · COCO weights" },
              { label: "FaceNet Service", metric: "< 80ms", detail: "face_recognition 1.3.0" },
              { label: "LSTM Predictor", metric: "94.2% Acc", detail: "Keras 2.x · 30s window" },
              { label: "Risk Engine", metric: "< 10ms", detail: "Scikit-learn 1.4" },
            ].map(({ label, metric, detail }) => (
              <Card key={label} className="p-5 flex items-center gap-4 opacity-70">
                <div className="w-10 h-10 rounded-xl bg-secondary border border-border flex items-center justify-center flex-shrink-0">
                  <div className="w-3 h-3 rounded-full bg-muted-foreground" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-foreground text-sm font-medium">{label}</span>
                    <span className="text-[10px] font-mono text-muted-foreground">● not deployed</span>
                  </div>
                  <div className="text-[11px] font-mono text-muted-foreground">{detail}</div>
                </div>
                <div className="font-mono text-sm text-muted-foreground font-bold">{metric}</div>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
