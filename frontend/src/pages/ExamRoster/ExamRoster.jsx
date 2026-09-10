import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useSchoolNav } from "../../hooks/useSchoolNav";
import { ArrowLeft, Plus, Users, AlertTriangle } from "lucide-react";
import { getExam } from "../../api/exams";
import {
  getExamRoster,
  getExamRosterSource,
  getAvailableRosterStudents,
  addExamRosterStudent,
  removeExamRosterStudent,
  bulkAddExamRosterStudents,
} from "../../api/examRoster";
import PageHeader from "../../components/PageHeader";
import Card from "../../components/ui/Card";
import DataTable from "../../components/DataTable";
import ConfirmDialog from "../../components/ConfirmDialog";

function ownershipMessage(err) {
  if (err?.response?.status === 403) {
    return "You don't have permission to manage this exam's roster — only its assigned instructor can.";
  }
  return null;
}

export default function ExamRoster() {
  const { examId } = useParams();
  const navigate = useSchoolNav();

  const [phase, setPhase] = useState("loading");
  const [exam, setExam] = useState(null);
  const [roster, setRoster] = useState([]);
  const [source, setSource] = useState(null);
  const [available, setAvailable] = useState([]);
  const [pageError, setPageError] = useState("");
  const [addError, setAddError] = useState("");
  const [deleting, setDeleting] = useState(null);
  const [bulkAdding, setBulkAdding] = useState(false);

  function refresh() {
    return Promise.all([
      getExam(examId),
      getExamRoster(examId),
      getExamRosterSource(examId),
      getAvailableRosterStudents(examId),
    ])
      .then(([examData, rosterData, sourceData, availableData]) => {
        setExam(examData);
        setRoster(rosterData);
        setSource(sourceData);
        setAvailable(availableData);
        setPhase("ready");
      })
      .catch(() => setPhase("error"));
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [examId]);

  const rosterColumns = [
    { key: "student_name", label: "Name", render: (row) => row.student.student_name ?? row.student.student_number },
    { key: "student_number", label: "Student Number", render: (row) => row.student.student_number },
  ];

  async function handleAdd(student) {
    setAddError("");
    try {
      await addExamRosterStudent(examId, student.id);
      refresh();
    } catch (err) {
      setAddError(ownershipMessage(err) ?? err?.response?.data?.detail ?? "Couldn't add this student.");
    }
  }

  async function handleBulkAdd() {
    setAddError("");
    setBulkAdding(true);
    try {
      await bulkAddExamRosterStudents(examId);
      await refresh();
    } catch (err) {
      setAddError(ownershipMessage(err) ?? err?.response?.data?.detail ?? "Couldn't add these students.");
    } finally {
      setBulkAdding(false);
    }
  }

  async function confirmRemove() {
    try {
      await removeExamRosterStudent(examId, deleting.student.id);
      setDeleting(null);
      refresh();
    } catch (err) {
      setPageError(ownershipMessage(err) ?? "Couldn't remove this student.");
      setDeleting(null);
    }
  }

  if (phase === "loading") {
    return (
      <div className="text-sm text-muted-foreground font-mono uppercase tracking-widest">Loading…</div>
    );
  }

  if (phase === "error") {
    return <div className="text-sm text-red-600">Couldn't load this exam.</div>;
  }

  // Since roster inheritance landed, "the table below is empty" and "nobody can sit this exam"
  // stopped being the same statement: an exam with no explicit rows admits its section's enrolled
  // class instead. Only the server knows which source is actually in force, so this reads
  // roster/source rather than re-deriving it from roster.length - deriving it locally is exactly
  // what made a healthy inherited exam announce that nobody could open it.
  const inherited = source?.source === "SECTION";
  const admits = source?.count ?? roster.length;
  const admitsNobody = source?.admits_nobody ?? roster.length === 0;

  return (
    <div>
      <button
        onClick={() => navigate("/exams")}
        className="flex items-center gap-1.5 text-[11px] font-mono uppercase tracking-widest text-muted-foreground hover:text-foreground transition-colors mb-6"
      >
        <ArrowLeft className="w-3.5 h-3.5" /> Back to Exams
      </button>

      <PageHeader
        eyebrow="Exam Roster"
        title={exam.title}
        description="Who sits this exam. Leave it empty to admit the section's enrolled class; add anyone here to restrict it to exactly the students you list."
      />

      {pageError && (
        <div className="mb-6 rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-600">
          {pageError}
        </div>
      )}

      <div
        role={admitsNobody ? "alert" : "status"}
        className={`mb-4 rounded-xl border px-4 py-3 text-sm ${
          admitsNobody
            ? "bg-red-50 border-red-200 text-red-700"
            : inherited
              ? "bg-emerald-50 border-emerald-200 text-emerald-800"
              : "bg-orange-50 border-orange-200 text-orange-700"
        }`}
      >
        {admitsNobody
          ? inherited
            ? "Nobody can open this exam. It has no roster of its own, so it admits its section's class list — and that section has nobody enrolled. Enrol students in the section, or add them below to roster them for this exam alone."
            : "Nobody can open this exam. It has no roster of its own and isn't linked to a section, so there is no class list for it to fall back on. Add students below."
          : inherited
            ? `Admitting the ${admits} student${admits === 1 ? "" : "s"} enrolled in this exam's section. Nothing is rostered here, so the class list is inherited and stays in step with the section.`
            : `Restricted to the ${admits} student${admits === 1 ? "" : "s"} listed below. This exam has its own roster, so its section's class list does not apply.`}
      </div>

      {inherited && !admitsNobody && available.length > 0 && (
        <div
          role="status"
          className="mb-4 flex gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3"
        >
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" />
          <p className="text-sm text-foreground">
            Adding anyone below <strong>replaces</strong> the inherited class list rather than
            adding to it — the moment one student is rostered here, this exam admits only the
            students you have listed. To sit the whole class plus one extra, add everybody.
          </p>
        </div>
      )}

      {/* Only meaningful for an exam that actually keeps its own roster. On an inherited one
          "not on the roster yet" is the normal, correct state, and nudging someone to add them
          would quietly convert the exam to an explicit roster - the opposite of what they want. */}
      {available.length > 0 && !inherited && (
        <div className="mb-8 rounded-xl border bg-blue-50 border-blue-200 text-blue-700 px-4 py-3 text-sm">
          {available.length} student{available.length === 1 ? "" : "s"} in this course{" "}
          {available.length === 1 ? "isn't" : "aren't"} on the roster yet, including anyone who
          registered recently — see "Add Students" below.
        </div>
      )}

      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-foreground">Assigned Students</h3>
      </div>

      {exam.is_active && admitsNobody && (
        <div
          role="status"
          className="mb-4 flex gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3"
        >
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" />
          <p className="text-sm text-foreground">
            This exam is active but admits nobody, so no student can open it. Fix this before it
            is due to start.
          </p>
        </div>
      )}

      <DataTable
        columns={rosterColumns}
        rows={roster}
        loading={false}
        onDelete={setDeleting}
        emptyLabel={inherited ? "Inheriting the section's class list" : "Nobody can sit this exam yet"}
        emptyHint={
          inherited
            ? "Nothing is rostered for this exam specifically, so it admits whoever is enrolled in its section. Add students here only to restrict it to a smaller group — a makeup or a deferred sitting."
            : "This exam has no class list to fall back on. Pick students from the list below."
        }
      />

      <div className="mt-8 mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">
          Add Students {available.length > 0 && <span className="text-muted-foreground font-normal">({available.length} waiting)</span>}
        </h3>
        {/* Rosters the SECTION's class, which is why the count comes from the roster source and
            not from the available list below. "Add All" over that list would have admitted people
            who are not in this class AND dropped the inherited roster in the same click - two
            wrongs from one button. Offered only while the class is what is actually in force. */}
        {inherited && admits > 0 && (
          <button
            onClick={handleBulkAdd}
            disabled={bulkAdding}
            className="flex items-center gap-1.5 bg-primary hover:bg-primary/90 disabled:opacity-40 text-white px-3 py-1.5 rounded-lg text-[11px] font-mono uppercase tracking-wider transition-colors"
          >
            <Users className="w-3.5 h-3.5" />
            {bulkAdding ? "Rostering…" : `Roster the class (${admits})`}
          </button>
        )}
      </div>

      {addError && (
        <div className="mb-4 rounded-xl bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-600">
          {addError}
        </div>
      )}

      {available.length === 0 ? (
        <Card className="p-6 text-sm text-muted-foreground">
          No available students to add — either everyone in this exam's course is already assigned, or the
          course has no students.
        </Card>
      ) : (
        <Card>
          <div className="divide-y divide-border">
            {available.map((student) => (
              <div key={student.id} className="px-6 py-3 flex items-center justify-between">
                <span className="text-sm text-foreground/80">
                  {student.student_name ?? student.student_number}
                  <span className="text-xs text-muted-foreground ml-2">{student.student_number}</span>
                </span>
                <button
                  onClick={() => handleAdd(student)}
                  className="flex items-center gap-1.5 bg-primary/10 hover:bg-primary/20 text-primary px-2.5 py-1 rounded-lg text-[11px] font-mono uppercase tracking-wider transition-colors"
                >
                  <Plus className="w-3.5 h-3.5" /> Add
                </button>
              </div>
            ))}
          </div>
        </Card>
      )}

      {deleting && (
        <ConfirmDialog
          title="Remove Student"
          message={`Remove ${deleting.student.student_name ?? deleting.student.student_number} (${deleting.student.student_number}) from this exam's roster?`}
          onConfirm={confirmRemove}
          onCancel={() => setDeleting(null)}
        />
      )}
    </div>
  );
}
