import { useEffect, useState } from "react";
import { GraduationCap, Users, ClipboardList, BookOpen, RefreshCw, Trash2, Building2 } from "lucide-react";
import { getStudents } from "../../api/students";
import { getInstructors } from "../../api/instructors";
import { getCourses } from "../../api/courses";
import { getSubjects } from "../../api/subjects";
import { getExams } from "../../api/exams";
import { getSystemStatus } from "../../api/system";
import { getAuditLog } from "../../api/auditLog";
import { getSchoolAnalytics } from "../../api/analytics";
import { getSchoolsForReview } from "../../api/schools";
import SetupChecklist from "../../components/SetupChecklist";
import { previewPurge, purgeExpiredEvidence } from "../../api/retention";
import {
  getPendingTrainingCandidates,
  reviewTrainingCandidate,
  getPendingNearMisses,
  reviewNearMiss,
  getNearMissEvidenceBlobUrl,
} from "../../api/trainingReview";
import { getEvidenceBlobUrl } from "../../api/violations";
import { useAuth } from "../../context/AuthContext";
import { Link } from "react-router-dom";
import { useSchoolSlug } from "../../hooks/useSchoolNav";
import Card from "../../components/ui/Card";
import SectionTag from "../../components/ui/SectionTag";
import RiskPill from "../../components/ui/RiskPill";
import ConfirmDialog from "../../components/ConfirmDialog";
import ViolationBreakdownChart from "../../components/ViolationBreakdownChart";

function accuracyColor(percentage) {
  return percentage >= 75 ? "#10b981" : percentage >= 50 ? "#f97316" : "#ef4444";
}

const AUDIT_ACTION_LABELS = {
  VIEW_VIOLATIONS: "Viewed violations",
  VIEW_EVIDENCE: "Viewed evidence photo",
  UPDATE_ACCOMMODATION: "Updated accommodation",
  PURGE_EVIDENCE: "Purged evidence (retention)",
};

export default function AdminDashboard() {
  const { user } = useAuth();
  const schoolSlug = useSchoolSlug();
  const [pendingSchools, setPendingSchools] = useState(0);

  // Super-admin-only: GET /schools/review 403s for a regular school admin, and this dashboard is
  // shared by both (isAdmin() covers admin and super_admin alike).
  const isSuperAdmin = user?.role_name === "super_admin";
  useEffect(() => {
    if (!isSuperAdmin) return;
    let active = true;
    getSchoolsForReview("pending")
      .then((rows) => active && setPendingSchools(rows.length))
      .catch(() => active && setPendingSchools(0));
    return () => {
      active = false;
    };
  }, [isSuperAdmin]);
  const [tab, setTab] = useState("overview");
  const [data, setData] = useState({ students: [], instructors: [], courses: [], exams: [], subjects: [] });
  const [loading, setLoading] = useState(true);
  const [systemStatus, setSystemStatus] = useState(null);
  const [systemLoading, setSystemLoading] = useState(false);
  const [systemError, setSystemError] = useState(false);
  const [auditLog, setAuditLog] = useState(null);
  const [auditLoading, setAuditLoading] = useState(false);
  const [auditError, setAuditError] = useState(false);
  const [schoolAnalytics, setSchoolAnalytics] = useState(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [analyticsError, setAnalyticsError] = useState(false);
  const [retentionPreview, setRetentionPreview] = useState(null);
  const [retentionLoading, setRetentionLoading] = useState(false);
  const [retentionError, setRetentionError] = useState(false);
  const [confirmingPurge, setConfirmingPurge] = useState(false);
  const [purgeResult, setPurgeResult] = useState(null);
  const [trainingCandidates, setTrainingCandidates] = useState(null);
  const [trainingLoading, setTrainingLoading] = useState(false);
  const [trainingError, setTrainingError] = useState(false);
  const [trainingPreviewUrls, setTrainingPreviewUrls] = useState({});
  const [nearMisses, setNearMisses] = useState(null);
  const [nearMissPreviewUrls, setNearMissPreviewUrls] = useState({});

  useEffect(() => {
    Promise.all([getStudents(), getInstructors(), getCourses(user.school_id), getExams(), getSubjects()])
      .then(([students, instructors, courses, exams, subjects]) =>
        setData({ students, instructors, courses, exams, subjects }))
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

  function loadAuditLog() {
    setAuditLoading(true);
    setAuditError(false);
    getAuditLog()
      .then(setAuditLog)
      .catch(() => setAuditError(true))
      .finally(() => setAuditLoading(false));
  }

  useEffect(() => {
    if (tab === "audit" && auditLog === null && !auditLoading) {
      loadAuditLog();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  function loadSchoolAnalytics() {
    setAnalyticsLoading(true);
    setAnalyticsError(false);
    getSchoolAnalytics()
      .then(setSchoolAnalytics)
      .catch(() => setAnalyticsError(true))
      .finally(() => setAnalyticsLoading(false));
  }

  useEffect(() => {
    if (tab === "analytics" && schoolAnalytics === null && !analyticsLoading) {
      loadSchoolAnalytics();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  function loadRetentionPreview() {
    setRetentionLoading(true);
    setRetentionError(false);
    previewPurge()
      .then(setRetentionPreview)
      .catch(() => setRetentionError(true))
      .finally(() => setRetentionLoading(false));
  }

  useEffect(() => {
    if (tab === "retention" && retentionPreview === null && !retentionLoading) {
      loadRetentionPreview();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  function loadTrainingCandidates() {
    setTrainingLoading(true);
    setTrainingError(false);
    getPendingTrainingCandidates()
      .then(setTrainingCandidates)
      .catch(() => setTrainingError(true))
      .finally(() => setTrainingLoading(false));
  }

  function loadNearMisses() {
    getPendingNearMisses().then(setNearMisses).catch(() => setNearMisses([]));
  }

  function loadNearMissPreview(captureId) {
    if (nearMissPreviewUrls[captureId]) return;
    getNearMissEvidenceBlobUrl(captureId).then((url) =>
      setNearMissPreviewUrls((prev) => ({ ...prev, [captureId]: url }))
    );
  }

  function handleNearMissDecision(captureId, decision) {
    reviewNearMiss(captureId, decision).then(() => {
      setNearMisses((prev) => prev.filter((c) => c.id !== captureId));
    });
  }

  useEffect(() => {
    if (tab === "training" && trainingCandidates === null && !trainingLoading) {
      loadTrainingCandidates();
      loadNearMisses();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  function loadTrainingPreview(violationId) {
    if (trainingPreviewUrls[violationId]) return;
    getEvidenceBlobUrl(violationId).then((url) =>
      setTrainingPreviewUrls((prev) => ({ ...prev, [violationId]: url }))
    );
  }

  function handleTrainingDecision(violationId, decision) {
    reviewTrainingCandidate(violationId, decision).then(() => {
      setTrainingCandidates((prev) => prev.filter((c) => c.id !== violationId));
    });
  }

  async function handlePurge() {
    // Don't close the confirm dialog until the purge actually succeeds - it's the one thing that
    // can show a failure (ConfirmDialog catches a thrown error and displays it inline); closing
    // eagerly, as this used to, would unmount the dialog before a failed purge ever surfaced.
    const result = await purgeExpiredEvidence();
    setConfirmingPurge(false);
    setPurgeResult(result.purged_count);
    loadRetentionPreview();
  }

  const activeExams = data.exams.filter((e) => e.is_active).length;

  return (
    <div>
      <div className="flex items-start justify-between mb-8">
        <div>
          <SectionTag text="Administrator" />
          <h2 className="font-display font-black text-foreground text-4xl">Admin Dashboard</h2>
          <p className="text-muted-foreground text-sm mt-2 max-w-2xl">
            An overview of your school. Use the sidebar to set up Course, Subject, Instructor and
            Student Management — courses first, since everything else is built on them.
          </p>
        </div>
      </div>

      {/* Super admin only. Email notification is optional (SMTP may not be configured at all), so
          the platform operator must be able to discover a waiting signup just by logging in. */}
      {pendingSchools > 0 && (
        <Card className="p-5 mb-6 border-amber-200 bg-amber-50">
          <div className="flex items-center gap-3">
            <Building2 className="w-5 h-5 text-amber-700 shrink-0" />
            <div className="flex-1">
              <p className="text-sm font-medium text-foreground">
                {pendingSchools} school registration{pendingSchools === 1 ? "" : "s"} awaiting review
              </p>
              <p className="text-sm text-muted-foreground">
                Nobody at {pendingSchools === 1 ? "that school" : "those schools"} can sign in until
                you approve {pendingSchools === 1 ? "it" : "them"}.
              </p>
            </div>
            <Link
              to={`/${schoolSlug}/school-approvals`}
              className="bg-amber-600 hover:bg-amber-700 text-white px-4 py-2 rounded-xl text-[12px] font-mono uppercase tracking-wider transition-colors"
            >
              Review
            </Link>
          </div>
        </Card>
      )}

      <SetupChecklist
        counts={{
          courses: data.courses.length,
          subjects: data.subjects.length,
          instructors: data.instructors.length,
          exams: data.exams.length,
        }}
      />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {[
          { val: data.students.length, label: "Total Students", icon: GraduationCap, color: "text-blue-600" },
          { val: data.instructors.length, label: "Instructors", icon: Users, color: "text-emerald-700" },
          { val: activeExams, label: "Active Exams", icon: ClipboardList, color: "text-orange-700" },
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
          ["analytics", "Analytics"],
          ["system", "System"],
          ["audit", "Audit"],
          ["retention", "Retention"],
          ["training", "Training Review"],
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
              <div className="text-[10px] font-mono text-emerald-700 uppercase tracking-widest mb-1">Instructors</div>
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

      {tab === "analytics" && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <p className="text-xs text-muted-foreground">
              School-wide exam performance and integrity signals, aggregated across every instructor and exam.
            </p>
            <button
              onClick={loadSchoolAnalytics}
              disabled={analyticsLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-[11px] font-mono uppercase tracking-wider text-muted-foreground hover:text-foreground hover:border-foreground/20 disabled:opacity-50 transition-colors flex-shrink-0"
            >
              <RefreshCw className={`w-3 h-3 ${analyticsLoading ? "animate-spin" : ""}`} />
              Refresh
            </button>
          </div>

          {analyticsError && (
            <Card className="p-5 text-sm text-red-600">Couldn't load analytics. Try refreshing.</Card>
          )}

          {!analyticsError && !schoolAnalytics && (
            <Card className="p-5 text-sm text-muted-foreground">Loading analytics…</Card>
          )}

          {schoolAnalytics && (
            <>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                <Card className="p-5">
                  <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest mb-2">Total Exams</div>
                  <div className="font-display text-3xl font-black text-foreground">{schoolAnalytics.total_exams}</div>
                </Card>
                <Card className="p-5">
                  <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest mb-2">Aggregate Pass Rate</div>
                  <div className="font-display text-3xl font-black text-emerald-700">
                    {schoolAnalytics.aggregate_pass_rate.toFixed(1)}%
                  </div>
                </Card>
                <Card className="p-5">
                  <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest mb-2">Avg Risk Score</div>
                  <div className="font-display text-3xl font-black text-foreground">
                    {schoolAnalytics.aggregate_average_risk_score.toFixed(0)}
                  </div>
                </Card>
                <Card className="p-5">
                  <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest mb-2">Total Violations</div>
                  <div className="font-display text-3xl font-black text-orange-700">{schoolAnalytics.total_violations}</div>
                </Card>
              </div>

              {/* Three columns only at 2xl: with the 224px sidebar and 48px padding, an xl window (1280)
          leaves ~1008px here, which is ~320px per column - too tight for these cards. 2xl
          (1536) leaves ~1264px, so ~405px each. Two columns cover everything in between. */}
        <div className="grid grid-cols-1 lg:grid-cols-2 2xl:grid-cols-3 gap-6">
                <Card className="xl:col-span-2">
                  <div className="px-6 py-4 border-b border-border text-[11px] font-mono text-muted-foreground uppercase tracking-widest">
                    Instructors
                  </div>
                  <div className="divide-y divide-border">
                    {schoolAnalytics.instructors.length === 0 && (
                      <div className="px-6 py-6 text-sm text-muted-foreground">No instructors yet.</div>
                    )}
                    {schoolAnalytics.instructors.map((i) => {
                      // Flags an instructor whose exams may need a closer look - unusually low
                      // pass rate or unusually high proctoring risk, same red-highlight treatment
                      // InstructorDashboard.jsx already uses for individual high-risk sessions.
                      const flagged = i.exam_count > 0 && (i.avg_pass_rate < 50 || i.avg_risk_score >= 75);
                      return (
                        <div
                          key={i.instructor_id}
                          className={`px-6 py-3 flex items-center gap-4 ${flagged ? "bg-red-50/60" : ""}`}
                        >
                          <span className="text-sm text-foreground flex-1 truncate">{i.instructor_name}</span>
                          <span className="text-[11px] font-mono text-muted-foreground w-24 flex-shrink-0">
                            {i.exam_count} exam{i.exam_count === 1 ? "" : "s"}
                          </span>
                          <span
                            className="font-mono text-xs font-bold w-14 text-right flex-shrink-0"
                            style={{ color: accuracyColor(i.avg_pass_rate) }}
                          >
                            {i.avg_pass_rate.toFixed(0)}%
                          </span>
                          <RiskPill value={Math.round(i.avg_risk_score)} />
                        </div>
                      );
                    })}
                  </div>
                </Card>

                <Card>
                  <div className="px-6 py-4 border-b border-border text-[11px] font-mono text-muted-foreground uppercase tracking-widest">
                    Violation Breakdown
                  </div>
                  <div className="p-6">
                    <ViolationBreakdownChart violationCounts={schoolAnalytics.violation_breakdown} />
                  </div>
                </Card>
              </div>
            </>
          )}
        </div>
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

      {tab === "audit" && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <p className="text-xs text-muted-foreground">
              Staff access to sensitive student data - viewing another student's violations or
              evidence photos, and accommodation changes. Most recent 200 entries. Students viewing
              their own data aren't logged here.
            </p>
            <button
              onClick={loadAuditLog}
              disabled={auditLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-[11px] font-mono uppercase tracking-wider text-muted-foreground hover:text-foreground hover:border-foreground/20 disabled:opacity-50 transition-colors flex-shrink-0"
            >
              <RefreshCw className={`w-3 h-3 ${auditLoading ? "animate-spin" : ""}`} />
              Refresh
            </button>
          </div>

          {auditError && (
            <Card className="p-5 text-sm text-red-600">Couldn't load the audit log. Try refreshing.</Card>
          )}

          {!auditError && !auditLog && (
            <Card className="p-5 text-sm text-muted-foreground">Loading audit log…</Card>
          )}

          {auditLog && (
            <Card>
              <div className="divide-y divide-border">
                {auditLog.length === 0 && (
                  <div className="px-6 py-6 text-sm text-muted-foreground">No audit entries yet.</div>
                )}
                {auditLog.map((entry) => (
                  <div key={entry.id} className="px-6 py-3 flex items-center gap-4">
                    <span className="text-[11px] font-mono text-muted-foreground w-40 flex-shrink-0">
                      {new Date(entry.created_at).toLocaleString()}
                    </span>
                    <span className="text-sm text-foreground w-56 flex-shrink-0 truncate">{entry.actor_email}</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded border border-blue-200 bg-blue-50 text-blue-700 uppercase tracking-wider flex-shrink-0">
                      {AUDIT_ACTION_LABELS[entry.action] ?? entry.action}
                    </span>
                    <span className="text-[11px] font-mono text-muted-foreground truncate">
                      {entry.resource_type} #{entry.resource_id}
                      {entry.detail ? ` · ${entry.detail}` : ""}
                    </span>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      )}

      {tab === "retention" && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <p className="text-xs text-muted-foreground">
              Violation evidence photos older than the retention window are permanently deleted
              from disk (the violation record itself is kept - only the image is removed).
              Evidence for a violation with a PENDING appeal is never purged, regardless of age.
            </p>
            <button
              onClick={loadRetentionPreview}
              disabled={retentionLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-[11px] font-mono uppercase tracking-wider text-muted-foreground hover:text-foreground hover:border-foreground/20 disabled:opacity-50 transition-colors flex-shrink-0"
            >
              <RefreshCw className={`w-3 h-3 ${retentionLoading ? "animate-spin" : ""}`} />
              Refresh
            </button>
          </div>

          {retentionError && (
            <Card className="p-5 text-sm text-red-600">Couldn't load the retention preview. Try refreshing.</Card>
          )}

          {!retentionError && !retentionPreview && (
            <Card className="p-5 text-sm text-muted-foreground">Loading retention preview…</Card>
          )}

          {retentionPreview && (
            <>
              <div className="grid grid-cols-2 gap-4 mb-4">
                <Card className="p-5">
                  <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest mb-2">Retention Window</div>
                  <div className="font-display text-3xl font-black text-foreground">{retentionPreview.retention_days} days</div>
                </Card>
                <Card className="p-5">
                  <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest mb-2">Eligible for Purge</div>
                  <div className="font-display text-3xl font-black text-orange-700">{retentionPreview.eligible_count}</div>
                </Card>
              </div>

              {purgeResult !== null && (
                <div className="mb-4 rounded-xl bg-emerald-50 border border-emerald-200 px-4 py-3 text-sm text-emerald-700">
                  Purged {purgeResult} evidence file{purgeResult === 1 ? "" : "s"}.
                </div>
              )}

              <Card className="mb-4">
                <div className="px-6 py-4 border-b border-border text-[11px] font-mono text-muted-foreground uppercase tracking-widest">
                  Eligible Violations
                </div>
                <div className="divide-y divide-border">
                  {retentionPreview.violations.length === 0 && (
                    <div className="px-6 py-6 text-sm text-muted-foreground">Nothing is old enough to purge right now.</div>
                  )}
                  {retentionPreview.violations.map((v) => (
                    <div key={v.id} className="px-6 py-3 flex items-center gap-4">
                      <span className="text-[11px] font-mono text-muted-foreground w-16 flex-shrink-0">#{v.id}</span>
                      <span className="text-sm text-foreground flex-1">{v.event_type}</span>
                      <span className="text-[11px] font-mono text-muted-foreground">{new Date(v.created_at).toLocaleDateString()}</span>
                      {v.appeal_status && (
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded border border-border bg-secondary text-muted-foreground uppercase tracking-wider">
                          {v.appeal_status}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </Card>

              <button
                onClick={() => setConfirmingPurge(true)}
                disabled={retentionPreview.eligible_count === 0}
                className="flex items-center gap-2 bg-red-600 hover:bg-red-500 disabled:opacity-40 text-white px-4 py-2.5 rounded-xl text-[12px] font-mono uppercase tracking-wider transition-colors"
              >
                <Trash2 className="w-4 h-4" /> Purge {retentionPreview.eligible_count} Expired Evidence File{retentionPreview.eligible_count === 1 ? "" : "s"}
              </button>
            </>
          )}

          {confirmingPurge && (
            <ConfirmDialog
              title="Purge Expired Evidence"
              message={`This will permanently delete ${retentionPreview?.eligible_count ?? 0} evidence photo(s) from disk. The violation records themselves are kept. This cannot be undone.`}
              onConfirm={handlePurge}
              onCancel={() => setConfirmingPurge(false)}
            />
          )}
        </div>
      )}

      {tab === "training" && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <p className="text-xs text-muted-foreground">
              Phone-detection and multiple-people evidence, awaiting your review before it's ever
              used to improve detection models. Approving copies the image into the training set;
              rejecting discards it from this queue only (see the{" "}
              <a href="/privacy-policy" target="_blank" rel="noopener noreferrer" className="underline">
                privacy policy
              </a>). Face-verification evidence never appears here.
            </p>
            <button
              onClick={loadTrainingCandidates}
              disabled={trainingLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-[11px] font-mono uppercase tracking-wider text-muted-foreground hover:text-foreground hover:border-foreground/20 disabled:opacity-50 transition-colors flex-shrink-0"
            >
              <RefreshCw className={`w-3 h-3 ${trainingLoading ? "animate-spin" : ""}`} />
              Refresh
            </button>
          </div>

          {trainingError && (
            <Card className="p-5 text-sm text-red-600">Couldn't load the training review queue. Try refreshing.</Card>
          )}

          {!trainingError && !trainingCandidates && (
            <Card className="p-5 text-sm text-muted-foreground">Loading training review queue…</Card>
          )}

          {trainingCandidates && (
            <Card>
              <div className="divide-y divide-border">
                {trainingCandidates.length === 0 && (
                  <div className="px-6 py-6 text-sm text-muted-foreground">Nothing awaiting review right now.</div>
                )}
                {trainingCandidates.map((c) => (
                  <div key={c.id} className="px-6 py-4 flex items-center gap-4">
                    {trainingPreviewUrls[c.id] ? (
                      <img src={trainingPreviewUrls[c.id]} alt="" className="w-16 h-16 rounded-lg object-cover border border-border flex-shrink-0" />
                    ) : (
                      <button
                        onClick={() => loadTrainingPreview(c.id)}
                        className="w-16 h-16 rounded-lg border border-border bg-secondary text-[10px] font-mono text-muted-foreground hover:text-foreground transition-colors flex-shrink-0"
                      >
                        View
                      </button>
                    )}
                    <div className="flex-1">
                      <div className="text-sm text-foreground font-medium">{c.event_type}</div>
                      <div className="text-[11px] font-mono text-muted-foreground">{new Date(c.created_at).toLocaleString()}</div>
                    </div>
                    <button
                      onClick={() => handleTrainingDecision(c.id, "REJECTED")}
                      className="px-3 py-1.5 rounded-lg border border-border text-[11px] font-mono uppercase tracking-wider text-muted-foreground hover:text-foreground hover:border-foreground/20 transition-colors"
                    >
                      Reject
                    </button>
                    <button
                      onClick={() => handleTrainingDecision(c.id, "APPROVED")}
                      className="px-3 py-1.5 rounded-lg bg-primary text-white text-[11px] font-mono uppercase tracking-wider hover:bg-primary/90 transition-colors"
                    >
                      Approve
                    </button>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* The detector's near misses. The queue above can only ever show frames it got RIGHT -
              measured on the 2026-09-04 batch, every approved phone frame was already detected at
              0.80-0.88 confidence, so approving them taught the model nothing. These are the
              frames it nearly missed, which is where the training value actually is. */}
          <div className="mt-8">
            <div className="mb-3">
              <h3 className="text-sm font-semibold text-foreground">Near misses</h3>
              <p className="text-xs text-muted-foreground mt-1 max-w-3xl">
                Frames where the detector saw something phone-like but wasn't confident enough to
                flag it — no violation was recorded and nothing appears on the student's record.
                Approve the ones that really do show a phone: those are the examples the model got
                wrong, and the most useful thing you can give it. The percentage is how close it
                came to flagging.
              </p>
            </div>

            {nearMisses === null && (
              <Card className="p-5 text-sm text-muted-foreground">Loading near misses…</Card>
            )}

            {nearMisses && nearMisses.length === 0 && (
              <Card className="p-5 text-sm text-muted-foreground">
                None captured yet. These appear as students sit proctored exams.
              </Card>
            )}

            {nearMisses && nearMisses.length > 0 && (
              <Card>
                <div className="divide-y divide-border">
                  {nearMisses.map((c) => (
                    <div key={c.id} className="px-6 py-4 flex items-center gap-4">
                      {nearMissPreviewUrls[c.id] ? (
                        <img
                          src={nearMissPreviewUrls[c.id]}
                          alt=""
                          className="w-16 h-16 rounded-lg object-cover border border-border flex-shrink-0"
                        />
                      ) : (
                        <button
                          onClick={() => loadNearMissPreview(c.id)}
                          className="w-16 h-16 rounded-lg border border-border bg-secondary text-[10px] font-mono text-muted-foreground hover:text-foreground transition-colors flex-shrink-0"
                        >
                          View
                        </button>
                      )}
                      <div className="flex-1 min-w-0">
                        <div className="text-sm text-foreground font-medium">
                          {c.detector === "PHONE" ? "Possible phone" : c.detector}
                        </div>
                        <div className="text-[11px] font-mono text-muted-foreground">
                          {(c.confidence * 100).toFixed(0)}% confident ·{" "}
                          {new Date(c.created_at).toLocaleString()}
                        </div>
                      </div>
                      <button
                        onClick={() => handleNearMissDecision(c.id, "REJECTED")}
                        className="px-3 py-1.5 rounded-lg border border-border text-[11px] font-mono uppercase tracking-wider text-muted-foreground hover:text-foreground hover:border-foreground/20 transition-colors"
                      >
                        No phone
                      </button>
                      <button
                        onClick={() => handleNearMissDecision(c.id, "APPROVED")}
                        className="px-3 py-1.5 rounded-lg bg-primary text-white text-[11px] font-mono uppercase tracking-wider hover:bg-primary/90 transition-colors"
                      >
                        Phone present
                      </button>
                    </div>
                  ))}
                </div>
              </Card>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
