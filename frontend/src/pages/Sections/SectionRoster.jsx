import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { ArrowLeft, Plus, AlertTriangle, Users } from "lucide-react";
import {
  getSection,
  getSectionRoster,
  getTerms,
  enrollStudents,
  setEnrollmentStatus,
} from "../../api/academic";
import { getStudents } from "../../api/students";
import { useAuth } from "../../context/AuthContext";
import { useSchoolNav } from "../../hooks/useSchoolNav";
import { isAdmin } from "../../utils/roles";
import PageHeader from "../../components/PageHeader";
import Card from "../../components/ui/Card";
import DataTable from "../../components/DataTable";

const STATUS_STYLE = {
  ENROLLED: "bg-emerald-50 text-emerald-800 border-emerald-200",
  DROPPED: "bg-secondary text-muted-foreground border-border",
  COMPLETED: "bg-secondary text-muted-foreground border-border",
};

function detail(err, fallback) {
  return err?.response?.data?.detail ?? fallback;
}

// What the server actually did, said in full. Enrolment is deliberately re-runnable - re-uploading
// an edited class list must be safe - so "nothing happened" and "everything happened" both need to
// be distinguishable from each other and from a partial success.
function enrolmentSummary({ enrolled, reinstated, skipped_already_enrolled: skipped }) {
  const parts = [];
  if (enrolled) parts.push(`${enrolled} enrolled`);
  if (reinstated) parts.push(`${reinstated} reinstated`);
  if (skipped) parts.push(`${skipped} already enrolled`);
  return parts.length ? parts.join(", ") : "Nothing changed.";
}

export default function SectionRoster() {
  const { sectionId } = useParams();
  const navigate = useSchoolNav();
  const { user } = useAuth();
  const canManage = isAdmin(user);

  const [phase, setPhase] = useState("loading");
  const [section, setSection] = useState(null);
  const [term, setTerm] = useState(null);
  const [roster, setRoster] = useState([]);
  const [students, setStudents] = useState([]);
  const [selected, setSelected] = useState([]);
  const [pageError, setPageError] = useState("");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);

  function load() {
    return Promise.all([
      getSection(sectionId),
      // active_only=false: a class list that silently hides a dropped student looks like the
      // student was never enrolled, which is the state someone comes here to correct.
      getSectionRoster(sectionId, { activeOnly: false }),
      getStudents(),
      getTerms(),
    ])
      .then(([sectionData, rosterData, studentRows, termRows]) => {
        setSection(sectionData);
        setRoster(rosterData);
        setStudents(studentRows);
        setTerm(termRows.find((t) => t.id === sectionData.term_id) ?? null);
        setPhase("ready");
      })
      .catch(() => setPhase("error"));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sectionId]);

  function refresh() {
    return getSectionRoster(sectionId, { activeOnly: false }).then(setRoster);
  }

  const enrolledIds = useMemo(
    () => new Set(roster.filter((r) => r.status === "ENROLLED").map((r) => r.student_id)),
    [roster]
  );
  const available = useMemo(
    () => students.filter((s) => !enrolledIds.has(s.id)),
    [students, enrolledIds]
  );

  const termClosed = term?.status === "CLOSED";
  const activeCount = enrolledIds.size;

  async function handleEnrol() {
    setPageError("");
    setResult(null);
    setBusy(true);
    try {
      const response = await enrollStudents(sectionId, selected.map(Number));
      setResult(response);
      setSelected([]);
      await refresh();
    } catch (err) {
      setPageError(detail(err, "Couldn't enrol these students."));
    } finally {
      setBusy(false);
    }
  }

  async function changeStatus(row, status) {
    setPageError("");
    setResult(null);
    try {
      await setEnrollmentStatus(sectionId, row.student_id, status);
      await refresh();
    } catch (err) {
      setPageError(detail(err, "Couldn't change this enrolment."));
    }
  }

  if (phase === "loading") {
    return (
      <div className="text-sm text-muted-foreground font-mono uppercase tracking-widest">
        Loading…
      </div>
    );
  }

  if (phase === "error") {
    return <div className="text-sm text-red-600">Couldn't load this section.</div>;
  }

  const columns = [
    {
      key: "student_name",
      label: "Name",
      render: (row) => row.student_name ?? row.student_number ?? `#${row.student_id}`,
    },
    { key: "student_number", label: "Student Number", render: (row) => row.student_number ?? "—" },
    {
      key: "status",
      label: "Status",
      render: (row) => (
        <span
          className={`rounded-lg border px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider ${
            STATUS_STYLE[row.status] ?? STATUS_STYLE.DROPPED
          }`}
        >
          {row.status}
        </span>
      ),
      search: (row) => row.status,
    },
  ];

  if (canManage) {
    columns.push({
      // Named rather than blank: DataTable always renders its own trailing "Actions" header for
      // the edit/delete slot, and a second unlabelled column beside it reads as a broken header.
      key: "enrolment",
      label: "Enrolment",
      render: (row) => (
        <button
          onClick={(e) => {
            e.stopPropagation();
            changeStatus(row, row.status === "ENROLLED" ? "DROPPED" : "ENROLLED");
          }}
          className="rounded-lg bg-primary/10 px-2.5 py-1 text-[11px] font-mono uppercase tracking-wider text-primary transition-colors hover:bg-primary/20"
        >
          {row.status === "ENROLLED" ? "Drop" : "Reinstate"}
        </button>
      ),
    });
  }

  return (
    <div>
      <button
        onClick={() => navigate("/sections")}
        className="flex items-center gap-1.5 text-[11px] font-mono uppercase tracking-widest text-muted-foreground hover:text-foreground transition-colors mb-6"
      >
        <ArrowLeft className="w-3.5 h-3.5" /> Back to Sections
      </button>

      <PageHeader
        eyebrow="Academic Management"
        title={section.label ?? section.code}
        description={`${section.subject_code ?? ""} ${section.subject_name ?? ""} · ${
          section.term_name ?? ""
        } ${section.academic_year_label ?? ""} · ${section.instructor_name ?? "No instructor"}`}
      />

      {pageError && (
        <div
          role="alert"
          className="mb-6 rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-600"
        >
          {pageError}
        </div>
      )}

      {/* The lockout warning, said where it can still be fixed. An exam pointing at this section
          with no roster of its own admits exactly these students - so an empty class list is an
          exam nobody can open, and it looks correctly configured right up until exam day. */}
      <div
        role={activeCount === 0 ? "alert" : "status"}
        className={`mb-4 rounded-xl border px-4 py-3 text-sm ${
          activeCount === 0
            ? "bg-amber-50 border-amber-200 text-amber-800"
            : "bg-emerald-50 border-emerald-200 text-emerald-800"
        }`}
      >
        {activeCount === 0
          ? "Nobody is enrolled in this section. Any exam that inherits this class list will admit no students at all — and will look correctly set up until someone tries to start it."
          : `${activeCount} student${activeCount === 1 ? "" : "s"} enrolled. An exam in this section with no roster of its own admits exactly these students.`}
      </div>

      {termClosed && (
        <div
          role="status"
          className="mb-4 flex gap-3 rounded-xl border border-border bg-secondary px-4 py-3"
        >
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            {term.name} is closed, so enrolment is locked and everyone in it has been marked
            completed. Reopen the term on the Academic Calendar to change this class list.
          </p>
        </div>
      )}

      <h3 className="mb-3 text-sm font-semibold text-foreground">Class List</h3>
      <DataTable
        columns={columns}
        rows={roster}
        loading={false}
        searchable
        searchPlaceholder="Search this class list by name, number or status…"
        emptyLabel="Nobody enrolled yet"
        emptyHint="Enrol students below. This is the class list an exam inherits when no roster is set on the exam itself."
      />

      {canManage && !termClosed && (
        <>
          <div className="mt-8 mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-foreground">
              Enrol Students{" "}
              {available.length > 0 && (
                <span className="font-normal text-muted-foreground">
                  ({available.length} not enrolled)
                </span>
              )}
            </h3>
            {selected.length > 0 && (
              <button
                onClick={handleEnrol}
                disabled={busy}
                className="flex items-center gap-1.5 bg-primary hover:bg-primary/90 disabled:opacity-40 text-white px-3 py-1.5 rounded-lg text-[11px] font-mono uppercase tracking-wider transition-colors"
              >
                <Users className="w-3.5 h-3.5" />
                {busy ? "Enrolling…" : `Enrol ${selected.length} Selected`}
              </button>
            )}
          </div>

          {result && (
            <div
              role="status"
              className="mb-4 rounded-xl border border-border bg-secondary px-4 py-3 text-sm text-foreground"
            >
              {enrolmentSummary(result)}
              {result.errors?.length > 0 && (
                <ul className="mt-2 list-disc pl-5 text-red-600">
                  {result.errors.map((e) => (
                    <li key={e}>{e}</li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {available.length === 0 ? (
            <Card className="p-6 text-sm text-muted-foreground">
              Every student in the school is already enrolled in this section.
            </Card>
          ) : (
            <Card>
              <div className="max-h-96 divide-y divide-border overflow-y-auto">
                {available.map((student) => {
                  const checked = selected.includes(student.id);
                  return (
                    <label
                      key={student.id}
                      className="flex cursor-pointer items-center gap-3 px-6 py-3 hover:bg-black/5"
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() =>
                          setSelected((prev) =>
                            checked ? prev.filter((id) => id !== student.id) : [...prev, student.id]
                          )
                        }
                        className="h-4 w-4 accent-primary"
                      />
                      <span className="text-sm text-foreground/80">
                        {student.student_name ?? student.student_number}
                        <span className="ml-2 text-xs text-muted-foreground">
                          {student.student_number}
                        </span>
                      </span>
                    </label>
                  );
                })}
              </div>
              <div className="border-t border-border px-6 py-3">
                <button
                  onClick={() => setSelected(available.map((s) => s.id))}
                  className="flex items-center gap-1.5 text-[11px] font-mono uppercase tracking-wider text-primary transition-colors hover:text-primary/80"
                >
                  <Plus className="h-3.5 w-3.5" /> Select all {available.length}
                </button>
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
