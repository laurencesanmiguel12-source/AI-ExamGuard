import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CheckCircle2, ArrowRight, RefreshCw } from "lucide-react";
import Card from "../../components/ui/Card";
import { useSchoolSlug } from "../../hooks/useSchoolNav";
import { getSetupReadiness } from "../../api/setupImport";

// Each group names where it gets fixed. The panel asked for a workflow to connect rows that
// arrived floating; a list that says "these are unlinked" without a route to the screen that
// links them is a report, not a workflow.
const GROUPS = [
  {
    key: "instructors_without_subjects",
    title: "Instructors teaching nothing",
    why: "Imported without a subject_codes cell, or added by hand and never assigned.",
    to: "/instructors",
    action: "Assign subjects",
  },
  {
    key: "subjects_without_instructor",
    title: "Subjects nobody teaches",
    why: "No instructor is assigned to these, so no one can open a class for them.",
    to: "/instructors",
    action: "Assign an instructor",
  },
  {
    key: "subjects_without_section",
    title: "Not opened as a class this term",
    why: "Somebody teaches these, but no section exists for them in the running term.",
    to: "/sections",
    action: "Open a section",
  },
  {
    key: "sections_without_enrollment",
    title: "Classes with nobody enrolled",
    why: "An exam on one of these admits no students at all, and looks correctly set up until somebody tries to start it.",
    to: "/sections",
    action: "Enrol students",
  },
];

export default function SetupReadinessPanel() {
  const schoolSlug = useSchoolSlug();
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  function load() {
    setLoading(true);
    setError("");
    return getSetupReadiness()
      .then(setReport)
      .catch(() => setError("Couldn't check what's left to set up."))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
  }, []);

  if (loading && !report) {
    return (
      <Card className="p-6 text-sm text-muted-foreground font-mono uppercase tracking-widest">
        Checking…
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="p-6">
        <p role="alert" className="text-sm text-red-600">{error}</p>
      </Card>
    );
  }

  const groups = GROUPS.map((g) => ({ ...g, items: report[g.key] ?? [] })).filter(
    (g) => g.items.length > 0
  );

  return (
    <Card className="p-6">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-foreground">What's left to set up</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            {report.current_year ? (
              <>
                {report.current_year}
                {report.active_term ? ` · ${report.active_term}` : " · no term running"}
              </>
            ) : (
              "No school year opened yet"
            )}
          </p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="flex items-center gap-1.5 text-[11px] font-mono uppercase tracking-wider text-muted-foreground transition-colors hover:text-foreground disabled:opacity-40"
        >
          <RefreshCw className="h-3.5 w-3.5" /> {loading ? "Checking…" : "Re-check"}
        </button>
      </div>

      {/* The first unmet step in flow order, said as one sentence. Six lists to choose between
          is not an answer to "what do I do next"; one is. */}
      {report.blocking_step ? (
        <div
          role="status"
          className="mb-5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
        >
          <span className="font-semibold">Next: </span>
          {report.blocking_step}
        </div>
      ) : (
        <div
          role="status"
          className="mb-5 flex items-start gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800"
        >
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
          <span>
            Ready to run exams — at least one class is enrolled and could sit one today.
            {groups.length > 0 && " The loose ends below are worth tidying, but nothing is blocked."}
          </span>
        </div>
      )}

      {groups.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          Nothing is left unconnected. Every instructor has a subject, every subject has a class,
          and every class has students in it.
        </p>
      ) : (
        <div className="divide-y divide-border">
          {groups.map((group) => (
            <div key={group.key} className="py-3.5 first:pt-0 last:pb-0">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h4 className="text-sm font-semibold text-foreground">
                  {group.title}{" "}
                  <span className="font-normal text-muted-foreground">({group.items.length})</span>
                </h4>
                <Link
                  to={`/${schoolSlug}${group.to}`}
                  className="flex items-center gap-1 text-[11px] font-mono uppercase tracking-wider text-primary transition-colors hover:text-primary/80"
                >
                  {group.action} <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </div>
              <p className="mt-0.5 text-sm text-muted-foreground">{group.why}</p>
              <ul className="mt-2 flex flex-wrap gap-1.5">
                {group.items.slice(0, 12).map((item) => (
                  <li
                    key={item.id}
                    className="rounded-lg border border-border bg-secondary px-2 py-0.5 text-xs text-foreground/80"
                    title={item.detail ?? undefined}
                  >
                    {item.label}
                  </li>
                ))}
                {group.items.length > 12 && (
                  <li className="px-1 py-0.5 text-xs text-muted-foreground">
                    +{group.items.length - 12} more
                  </li>
                )}
              </ul>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
