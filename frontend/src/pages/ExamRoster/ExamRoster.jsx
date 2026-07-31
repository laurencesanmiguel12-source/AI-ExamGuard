import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Plus } from "lucide-react";
import { getExam } from "../../api/exams";
import {
  getExamRoster,
  getAvailableRosterStudents,
  addExamRosterStudent,
  removeExamRosterStudent,
} from "../../api/examRoster";
import SectionTag from "../../components/ui/SectionTag";
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
  const navigate = useNavigate();

  const [phase, setPhase] = useState("loading");
  const [exam, setExam] = useState(null);
  const [roster, setRoster] = useState([]);
  const [available, setAvailable] = useState([]);
  const [pageError, setPageError] = useState("");
  const [addError, setAddError] = useState("");
  const [deleting, setDeleting] = useState(null);

  function refresh() {
    return Promise.all([getExam(examId), getExamRoster(examId), getAvailableRosterStudents(examId)])
      .then(([examData, rosterData, availableData]) => {
        setExam(examData);
        setRoster(rosterData);
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

  const isRestricted = roster.length > 0;

  return (
    <div>
      <button
        onClick={() => navigate("/exams")}
        className="flex items-center gap-1.5 text-[11px] font-mono uppercase tracking-widest text-muted-foreground hover:text-foreground transition-colors mb-6"
      >
        <ArrowLeft className="w-3.5 h-3.5" /> Back to Exams
      </button>

      <div className="mb-8">
        <SectionTag text="Exam Roster" />
        <h2 className="font-display font-black text-foreground text-4xl">{exam.title}</h2>
      </div>

      {pageError && (
        <div className="mb-6 rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-600">
          {pageError}
        </div>
      )}

      <div
        className={`mb-8 rounded-xl border px-4 py-3 text-sm ${
          isRestricted
            ? "bg-orange-50 border-orange-200 text-orange-700"
            : "bg-emerald-50 border-emerald-200 text-emerald-700"
        }`}
      >
        {isRestricted
          ? `Restricted — visible only to the ${roster.length} assigned student${roster.length === 1 ? "" : "s"} below.`
          : "Course-wide — visible to every student in this exam's course. Add a student below to restrict it."}
      </div>

      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-foreground">Assigned Students</h3>
      </div>

      <DataTable
        columns={rosterColumns}
        rows={roster}
        loading={false}
        onDelete={setDeleting}
        emptyLabel="No students assigned yet — this exam is course-wide."
      />

      <div className="mt-8 mb-3">
        <h3 className="text-sm font-semibold text-foreground">Add Students</h3>
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
