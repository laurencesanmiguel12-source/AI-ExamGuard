import { useEffect, useState } from "react";
import { ShieldCheck } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { useSchoolNav } from "../../hooks/useSchoolNav";
import { getExamSessions } from "../../api/examSessions";
import { getStudents } from "../../api/students";
import { getExams } from "../../api/exams";
import { getSessionViolations } from "../../api/violations";
import Card from "../../components/ui/Card";
import PageHeader from "../../components/PageHeader";
import ViolationsPanel from "../../components/ViolationsPanel";

// The defense panel asked for this - "Should already see the list of violations commited and
// option to appeal" - and it turned out to be a discoverability problem, not a missing feature.
// ResultDetail has rendered ViolationsPanel in appeal mode for a long time, and the appeal
// endpoints have always been live. But it sat three clicks deep, on ONE attempt at a time, and
// nothing anywhere told a student they had been flagged at all: you had to already suspect it,
// open My Results, and pick the right attempt.
//
// So this page adds no new capability. It aggregates what already existed into the one view the
// question implies - everything flagged against you, newest first, each still appealable through
// the same component and the same endpoint ResultDetail uses.
export default function MyViolations() {
  const { user } = useAuth();
  const navigate = useSchoolNav();
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errored, setErrored] = useState(false);
  const [noProfile, setNoProfile] = useState(false);

  async function load() {
    setErrored(false);
    try {
      const [sessions, students, exams] = await Promise.all([
        getExamSessions(),
        getStudents(),
        getExams().catch(() => []),
      ]);
      const me = students.find((s) => s.user_id === user.id);
      if (!me) {
        setNoProfile(true);
        return;
      }

      const examTitle = Object.fromEntries(exams.map((e) => [e.id, e.title]));
      const mine = sessions
        .filter((s) => s.student_id === me.id)
        .sort((a, b) => new Date(b.started_at) - new Date(a.started_at));

      const withViolations = await Promise.all(
        mine.map(async (s) => ({
          session: s,
          title: examTitle[s.exam_id] ?? `Exam #${s.exam_id}`,
          violations: await getSessionViolations(s.id).catch(() => []),
        }))
      );

      // Attempts with a clean record are omitted rather than listed as empty - this page answers
      // "what was flagged against me", and a wall of "no violations" buries the ones that matter.
      setGroups(withViolations.filter((g) => g.violations.length > 0));
    } catch {
      setErrored(true);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user.id]);

  const total = groups.reduce((sum, g) => sum + g.violations.length, 0);

  return (
    <div>
      <PageHeader
        eyebrow="Exam History"
        title="Violations & Appeals"
        description="Everything AI ExamGuard flagged during your exams. If you think something was recorded in error — a family member walking past, a reflection mistaken for a phone — you can appeal it here and your instructor will review it."
      />

      {loading && <Card className="p-6 text-sm text-muted-foreground">Loading…</Card>}

      {errored && !loading && (
        <Card className="p-6">
          <p className="text-sm text-red-600">Couldn't load your violations.</p>
          <button
            onClick={() => { setLoading(true); load(); }}
            className="mt-3 rounded-xl border border-border px-4 py-2 text-[11px] font-mono uppercase tracking-wider text-muted-foreground transition-colors hover:text-foreground"
          >
            Try again
          </button>
        </Card>
      )}

      {noProfile && !loading && (
        <Card className="p-6 text-sm text-muted-foreground">
          Your account isn't linked to a student record yet. Ask an admin to provision one.
        </Card>
      )}

      {!loading && !errored && !noProfile && groups.length === 0 && (
        <Card className="p-10 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl border border-emerald-200 bg-emerald-50">
            <ShieldCheck className="h-6 w-6 text-emerald-700" />
          </div>
          <p className="text-sm font-medium text-foreground">Nothing has been flagged</p>
          <p className="mx-auto mt-1.5 max-w-md text-sm text-muted-foreground">
            No proctoring violations have been recorded against any of your exams. There is nothing
            to appeal.
          </p>
        </Card>
      )}

      {!loading && groups.length > 0 && (
        <>
          <p className="mb-4 text-sm text-muted-foreground">
            {total} violation{total === 1 ? "" : "s"} across {groups.length} attempt
            {groups.length === 1 ? "" : "s"}.
          </p>
          <div className="space-y-6">
            {groups.map((g) => (
              <Card key={g.session.id}>
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-6 py-4">
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-foreground">{g.title}</div>
                    <div className="mt-0.5 text-[11px] font-mono text-muted-foreground">
                      {new Date(g.session.started_at).toLocaleString()} ·{" "}
                      {g.violations.length} flagged
                    </div>
                  </div>
                  <button
                    onClick={() => navigate(`/results/${g.session.id}`)}
                    className="shrink-0 rounded-xl border border-border px-3 py-1.5 text-[11px] font-mono uppercase tracking-wider text-muted-foreground transition-colors hover:text-foreground"
                  >
                    View full result
                  </button>
                </div>
                <div className="p-6">
                  {/* Same component and same endpoint ResultDetail uses - a student appealing from
                      here and from there is doing the identical thing. */}
                  <ViolationsPanel violations={g.violations} mode="appeal" onAppealed={load} />
                </div>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
