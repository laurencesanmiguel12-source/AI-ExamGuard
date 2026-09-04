import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Plus, ListChecks, Users } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { useSchoolSlug } from "../../hooks/useSchoolNav";
import { getExams, createExam, updateExam, deleteExam } from "../../api/exams";
import { getSubjects } from "../../api/subjects";
import { getInstructors } from "../../api/instructors";
import SectionTag from "../../components/ui/SectionTag";
import DataTable from "../../components/DataTable";
import Modal from "../../components/Modal";
import ConfirmDialog from "../../components/ConfirmDialog";
import { TextField, SelectField, CheckboxField } from "../../components/ui/FormField";
import { isAdmin } from "../../utils/roles";

function ownershipMessage(err) {
  if (err?.response?.status === 403) {
    return "You don't have permission to manage this exam — only its assigned instructor can.";
  }
  return null;
}

const EMPTY_FORM = {
  title: "",
  description: "",
  duration_minutes: 60,
  total_points: 100,
  passing_score: 60,
  max_risk_score: "",
  start_time: "",
  end_time: "",
  is_active: false,
  subject_id: "",
  instructor_id: "",
};

function toLocalInput(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export default function Exams() {
  const { user } = useAuth();
  const schoolSlug = useSchoolSlug();
  const [exams, setExams] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [instructors, setInstructors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState(null);
  const [deleteError, setDeleteError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function refresh() {
    setLoading(true);
    Promise.all([getExams(), getSubjects(), getInstructors()])
      .then(([e, s, i]) => {
        setExams(e);
        setSubjects(s);
        setInstructors(i);
      })
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  const subjectName = (id) => subjects.find((s) => s.id === id)?.code ?? `#${id}`;
  const instructorName = (id) => instructors.find((i) => i.id === id)?.employee_number ?? `#${id}`;
  const myInstructor = instructors.find((i) => i.user_id === user.id) ?? null;

  const columns = [
    { key: "title", label: "Title" },
    { key: "subject_id", label: "Subject", render: (row) => subjectName(row.subject_id) },
    { key: "instructor_id", label: "Instructor", render: (row) => instructorName(row.instructor_id) },
    { key: "is_active", label: "Status", render: (row) => (row.is_active ? "Active" : "Inactive") },
    {
      key: "content",
      label: "Content",
      render: (row) => (
        <Link
          to={`/${schoolSlug}/exams/${row.id}/content`}
          className="inline-flex items-center gap-1.5 bg-primary/10 hover:bg-primary/20 text-primary-ink px-2.5 py-1.5 rounded-lg text-[11px] font-mono uppercase tracking-wider transition-colors"
        >
          <ListChecks className="w-3.5 h-3.5" /> Manage Content
        </Link>
      ),
    },
    {
      key: "roster",
      label: "Roster",
      render: (row) => (
        <Link
          to={`/${schoolSlug}/exams/${row.id}/roster`}
          className="inline-flex items-center gap-1.5 bg-primary/10 hover:bg-primary/20 text-primary-ink px-2.5 py-1.5 rounded-lg text-[11px] font-mono uppercase tracking-wider transition-colors"
        >
          <Users className="w-3.5 h-3.5" /> Manage Roster
        </Link>
      ),
    },
  ];

  function openCreate() {
    setForm({
      ...EMPTY_FORM,
      subject_id: subjects[0]?.id ?? "",
      instructor_id: myInstructor?.id ?? instructors[0]?.id ?? "",
    });
    setError("");
    setEditing({});
  }

  function openEdit(exam) {
    setForm({
      title: exam.title,
      description: exam.description ?? "",
      duration_minutes: exam.duration_minutes,
      total_points: exam.total_points,
      passing_score: exam.passing_score,
      max_risk_score: exam.max_risk_score ?? "",
      start_time: toLocalInput(exam.start_time),
      end_time: toLocalInput(exam.end_time),
      is_active: exam.is_active,
      subject_id: exam.subject_id,
      instructor_id: exam.instructor_id,
    });
    setError("");
    setEditing(exam);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    const payload = {
      ...form,
      duration_minutes: Number(form.duration_minutes),
      total_points: Number(form.total_points),
      passing_score: Number(form.passing_score),
      max_risk_score: form.max_risk_score === "" ? null : Number(form.max_risk_score),
      subject_id: Number(form.subject_id),
      instructor_id: Number(form.instructor_id),
      start_time: new Date(form.start_time).toISOString(),
      end_time: new Date(form.end_time).toISOString(),
    };
    try {
      if (editing.id) {
        await updateExam(editing.id, payload);
      } else {
        await createExam(payload);
      }
      setEditing(null);
      refresh();
    } catch (err) {
      setError(ownershipMessage(err) ?? "Couldn't save this exam.");
    } finally {
      setSubmitting(false);
    }
  }

  async function confirmDelete() {
    try {
      await deleteExam(deleting.id);
      setDeleting(null);
      refresh();
    } catch (err) {
      setDeleteError(ownershipMessage(err) ?? "Couldn't delete this exam.");
      setDeleting(null);
    }
  }

  const canCreate = subjects.length > 0 && (isAdmin(user) ? instructors.length > 0 : !!myInstructor);

  return (
    <div>
      <div className="flex items-start justify-between mb-8">
        <div>
          <SectionTag text="Academic Management" />
          <h2 className="font-display font-black text-foreground text-4xl">Exams</h2>
        </div>
        <button
          onClick={openCreate}
          disabled={!canCreate}
          className="flex items-center gap-2 bg-primary hover:bg-primary/90 disabled:opacity-40 text-white px-4 py-2.5 rounded-xl text-[12px] font-mono uppercase tracking-wider transition-colors"
        >
          <Plus className="w-4 h-4" /> Add Exam
        </button>
      </div>

      {!canCreate && !loading && (
        <div className="mb-4 text-sm text-muted-foreground">
          {subjects.length === 0
            ? "Create a subject first before adding exams."
            : isAdmin(user) && instructors.length === 0
            ? "Create an instructor first before adding exams."
            : "Your account has no linked instructor profile yet — contact an admin before adding exams."}
        </div>
      )}

      {deleteError && (
        <div className="mb-4 rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-600">
          {deleteError}
        </div>
      )}

      <DataTable columns={columns} rows={exams} loading={loading} onEdit={openEdit} onDelete={setDeleting} emptyLabel="No exams yet." />

      {editing && (
        <Modal title={editing.id ? "Edit Exam" : "Add Exam"} onClose={() => setEditing(null)}>
          <form onSubmit={handleSubmit}>
            {error && <div className="mb-4 rounded-xl bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-600">{error}</div>}
            <TextField
              label="Title"
              required
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              placeholder="Python Midterm Examination"
            />
            <TextField
              label="Description"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="Optional"
            />
            <div className="grid grid-cols-2 gap-3">
              <TextField
                label="Duration (min)"
                type="number"
                required
                value={form.duration_minutes}
                onChange={(e) => setForm({ ...form, duration_minutes: e.target.value })}
              />
              <TextField
                label="Total Points"
                type="number"
                required
                value={form.total_points}
                onChange={(e) => setForm({ ...form, total_points: e.target.value })}
              />
            </div>
            <TextField
              label="Passing Score"
              type="number"
              required
              value={form.passing_score}
              onChange={(e) => setForm({ ...form, passing_score: e.target.value })}
            />
            <TextField
              label="Max Risk Score (retake threshold, optional)"
              type="number"
              min="0"
              max="100"
              value={form.max_risk_score}
              onChange={(e) => setForm({ ...form, max_risk_score: e.target.value })}
              placeholder="Leave blank to disable retake flagging"
            />
            <div className="grid grid-cols-2 gap-3">
              <TextField
                label="Start Time"
                type="datetime-local"
                required
                value={form.start_time}
                onChange={(e) => setForm({ ...form, start_time: e.target.value })}
              />
              <TextField
                label="End Time"
                type="datetime-local"
                required
                value={form.end_time}
                onChange={(e) => setForm({ ...form, end_time: e.target.value })}
              />
            </div>
            <SelectField
              label="Subject"
              required
              value={form.subject_id}
              onChange={(e) => setForm({ ...form, subject_id: e.target.value })}
            >
              {subjects.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.code} — {s.name}
                </option>
              ))}
            </SelectField>
            {editing?.id && (
              <SelectField
                label="Instructor (reassign)"
                required
                value={form.instructor_id}
                onChange={(e) => setForm({ ...form, instructor_id: e.target.value })}
              >
                {instructors.map((i) => (
                  <option key={i.id} value={i.id}>
                    {i.employee_number}
                  </option>
                ))}
              </SelectField>
            )}
            <CheckboxField
              label="Active"
              checked={form.is_active}
              onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
            />
            <button
              type="submit"
              disabled={submitting}
              className="w-full bg-primary hover:bg-primary/90 disabled:opacity-50 text-white py-2.5 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors"
            >
              {submitting ? "Saving…" : editing.id ? "Save Changes" : "Create Exam"}
            </button>
          </form>
        </Modal>
      )}

      {deleting && (
        <ConfirmDialog
          title="Delete Exam"
          message={`Delete exam "${deleting.title}"? This cannot be undone.`}
          onConfirm={confirmDelete}
          onCancel={() => setDeleting(null)}
        />
      )}
    </div>
  );
}
