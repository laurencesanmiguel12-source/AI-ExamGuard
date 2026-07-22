import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { getExams, createExam, updateExam, deleteExam } from "../../api/exams";
import { getSubjects } from "../../api/subjects";
import { getInstructors } from "../../api/instructors";
import SectionTag from "../../components/ui/SectionTag";
import DataTable from "../../components/DataTable";
import Modal from "../../components/Modal";
import ConfirmDialog from "../../components/ConfirmDialog";
import { TextField, SelectField, CheckboxField } from "../../components/ui/FormField";

const EMPTY_FORM = {
  title: "",
  description: "",
  duration_minutes: 60,
  total_points: 100,
  passing_score: 60,
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
  const [exams, setExams] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [instructors, setInstructors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState(null);

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

  const columns = [
    { key: "title", label: "Title" },
    { key: "subject_id", label: "Subject", render: (row) => subjectName(row.subject_id) },
    { key: "instructor_id", label: "Instructor", render: (row) => instructorName(row.instructor_id) },
    { key: "is_active", label: "Status", render: (row) => (row.is_active ? "Active" : "Inactive") },
  ];

  function openCreate() {
    setForm({ ...EMPTY_FORM, subject_id: subjects[0]?.id ?? "", instructor_id: instructors[0]?.id ?? "" });
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
    const payload = {
      ...form,
      duration_minutes: Number(form.duration_minutes),
      total_points: Number(form.total_points),
      passing_score: Number(form.passing_score),
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
    } catch {
      setError("Couldn't save this exam.");
    }
  }

  async function confirmDelete() {
    await deleteExam(deleting.id);
    setDeleting(null);
    refresh();
  }

  const canCreate = subjects.length > 0 && instructors.length > 0;

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
        <div className="mb-4 text-sm text-muted-foreground">Create a subject and an instructor first before adding exams.</div>
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
            <SelectField
              label="Instructor"
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
            <CheckboxField
              label="Active"
              checked={form.is_active}
              onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
            />
            <button
              type="submit"
              className="w-full bg-primary hover:bg-primary/90 text-white py-2.5 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors"
            >
              {editing.id ? "Save Changes" : "Create Exam"}
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
