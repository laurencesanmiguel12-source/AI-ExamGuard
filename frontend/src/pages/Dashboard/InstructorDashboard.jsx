import { useEffect, useRef, useState } from "react";
import { useSchoolNav } from "../../hooks/useSchoolNav";
import { Eye, FileText, BarChart3, Download, Bell, BellOff, Users } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { getExams } from "../../api/exams";
import { getInstructors } from "../../api/instructors";
import { getStudents } from "../../api/students";
import { getExamRoster } from "../../api/examRoster";
import { getLiveSessions } from "../../api/violations";
import { playNotificationChime } from "../../utils/notificationSound";
import Card from "../../components/ui/Card";
import RiskPill from "../../components/ui/RiskPill";
import RiskBar from "../../components/ui/RiskBar";
import ViolationBreakdownChart, { VIOLATION_META } from "../../components/ViolationBreakdownChart";

const SOUND_PREF_KEY = "liveMonitorSoundEnabled";

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

export default function InstructorDashboard() {
  const { user } = useAuth();
  const navigate = useSchoolNav();
  const [myExams, setMyExams] = useState([]);
  const [students, setStudents] = useState([]);
  const [enrolledByExam, setEnrolledByExam] = useState({});
  const [loading, setLoading] = useState(true);
  const [liveSessions, setLiveSessions] = useState([]);
  const [recentEvents, setRecentEvents] = useState([]);
  const [soundEnabled, setSoundEnabled] = useState(
    () => localStorage.getItem(SOUND_PREF_KEY) !== "off"
  );
  // Most-recent event timestamp seen across all polls so far, scoped to MY exams (not every
  // instructor's) - compared against on each new poll to detect genuinely new arrivals. null
  // means "haven't completed a first poll yet", which matters below: the first poll establishes
  // the baseline silently, it doesn't chime for every pre-existing recent event on page load.
  const lastSeenEventTimeRef = useRef(null);

  useEffect(() => {
    Promise.all([getInstructors(), getExams()])
      .then(([instructors, exams]) => {
        const me = instructors.find((i) => i.user_id === user.id);
        setMyExams(me ? exams.filter((e) => e.instructor_id === me.id) : []);
      })
      .catch(() => setMyExams([]))
      .finally(() => setLoading(false));
    getStudents().then(setStudents).catch(() => setStudents([]));
  }, [user]);

  useEffect(() => {
    let cancelled = false;
    if (myExams.length === 0) {
      setEnrolledByExam({});
      return undefined;
    }
    Promise.all(
      myExams.map((exam) => getExamRoster(exam.id).then((roster) => [exam.id, roster]))
    ).then((entries) => {
      if (!cancelled) setEnrolledByExam(Object.fromEntries(entries));
    }).catch(() => {
      if (!cancelled) setEnrolledByExam({});
    });
    return () => {
      cancelled = true;
    };
  }, [myExams]);

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

  useEffect(() => {
    if (myRecentEvents.length === 0) return;
    const latest = Math.max(...myRecentEvents.map((e) => new Date(e.created_at).getTime()));
    const previous = lastSeenEventTimeRef.current;
    lastSeenEventTimeRef.current = latest;
    if (previous !== null && latest > previous && soundEnabled) {
      playNotificationChime();
    }
  }, [myRecentEvents, soundEnabled]);

  function toggleSound() {
    setSoundEnabled((prev) => {
      const next = !prev;
      localStorage.setItem(SOUND_PREF_KEY, next ? "on" : "off");
      return next;
    });
  }

  const myViolationCounts = {};
  for (const s of mySessions) {
    for (const [type, count] of Object.entries(s.violation_counts)) {
      myViolationCounts[type] = (myViolationCounts[type] ?? 0) + count;
    }
  }

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

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
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

      {/* Breakpoints here are chosen against the CONTENT width, not the viewport. Tailwind's
          `lg`/`xl` match the window, but this grid sits beside a fixed 224px sidebar inside 48px
          of padding, so it always has ~272px less to work with than the breakpoint name suggests.
          Splitting at lg (1024 window ≈ 750px of content) rather than xl is what stops a laptop
          sitting in the 1024-1279 band from rendering one full-width stretched column. */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <Card>
          <div className="px-6 py-4 border-b border-border flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Users className="w-4 h-4 text-blue-600" />
              <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest">
                Students
              </div>
            </div>
            {/* Every student registered at this school (GET /students/ is school-scoped), not a
                count of exam enrollments - most of these are on no roster at all. Said "enrolled"
                until 2026-09-02, which read as an enrollment count next to the per-exam roster
                counts in the card beside it. */}
            <span className="font-mono text-xs text-foreground/70">{students.length} registered</span>
          </div>
          <div className="divide-y divide-border max-h-64 overflow-y-auto">
            {students.length === 0 && (
              <div className="px-6 py-6 text-sm text-muted-foreground">No students registered yet.</div>
            )}
            {students.map((student) => (
              <div key={student.id} className="px-6 py-2.5 flex items-center gap-3">
                <div className="w-7 h-7 rounded-lg bg-blue-50 text-blue-700 flex items-center justify-center text-xs font-bold">
                  {student.student_name?.[0] ?? "?"}
                </div>
                <span className="text-sm text-foreground/80 flex-1 truncate">
                  {student.student_name ?? student.student_number}
                </span>
                <span className="font-mono text-[10px] text-muted-foreground">{student.student_number}</span>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <div className="px-6 py-4 border-b border-border flex items-center gap-2">
            <Users className="w-4 h-4 text-emerald-600" />
            <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest">
              Current Exam Enrollment
            </div>
          </div>
          <div className="divide-y divide-border">
            {myExams.length === 0 && (
              <div className="px-6 py-6 text-sm text-muted-foreground">No exams assigned yet.</div>
            )}
            {myExams.map((exam) => {
              const roster = enrolledByExam[exam.id] ?? [];
              return (
                <div key={exam.id} className="px-6 py-3">
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-foreground flex-1 truncate">{exam.title}</span>
                    <span className="font-mono text-xs text-foreground/70">{roster.length} students</span>
                    <button
                      onClick={() => navigate(`/exams/${exam.id}/roster`)}
                      className="text-[10px] font-mono uppercase tracking-wider text-primary hover:underline"
                    >
                      View roster
                    </button>
                  </div>
                  {roster.length > 0 && (
                    <div className="mt-1 text-[11px] text-muted-foreground truncate">
                      {roster.map((entry) => entry.student.student_name ?? entry.student.student_number).join(", ")}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </Card>
      </div>

      {/* Three columns only at 2xl: with the 224px sidebar and 48px padding, an xl window (1280)
          leaves ~1008px here, which is ~320px per column - too tight for these cards. 2xl
          (1536) leaves ~1264px, so ~405px each. Two columns cover everything in between. */}
      <div className="grid grid-cols-1 lg:grid-cols-2 2xl:grid-cols-3 gap-6">
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
            <div className="flex items-center justify-between gap-2 mb-4">
              <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest">Session Alerts</div>
              <button
                onClick={toggleSound}
                title={soundEnabled ? "Mute alert sound" : "Unmute alert sound"}
                aria-label={soundEnabled ? "Mute alert sound" : "Unmute alert sound"}
                className={`flex-shrink-0 p-1.5 rounded-lg border transition-colors ${
                  soundEnabled
                    ? "border-primary/30 bg-primary/8 text-primary"
                    : "border-border text-muted-foreground hover:text-foreground"
                }`}
              >
                {soundEnabled ? <Bell className="w-3.5 h-3.5" /> : <BellOff className="w-3.5 h-3.5" />}
              </button>
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
            <ViolationBreakdownChart violationCounts={myViolationCounts} />
          </Card>

          <div className="grid grid-cols-3 gap-3">
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
            <a
              href="https://chromewebstore.google.com/detail/ai-examguard-tab-monitor/gbkbkbcbbehpcoifmkenkjafkfbphmkf"
              target="_blank"
              rel="noopener noreferrer"
              className="flex flex-col items-center gap-1.5 p-4 bg-card border border-border hover:border-foreground/15 rounded-xl transition-colors"
            >
              <Download className="w-5 h-5 text-emerald-600" />
              <span className="text-[11px] font-mono text-muted-foreground">Extension</span>
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
