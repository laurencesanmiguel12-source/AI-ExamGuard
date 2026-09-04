import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { getSubjects, createSubject, updateSubject, deleteSubject } from "../../api/subjects";
import { getCourses } from "../../api/courses";
import { useAuth } from "../../context/AuthContext";
import PageHeader from "../../components/PageHeader";
import DataTable from "../../components/DataTable";
import Modal from "../../components/Modal";
import ConfirmDialog from "../../components/ConfirmDialog";
import { TextField, SelectField } from "../../components/ui/FormField";

const EMPTY_FORM = { code: "", name: "", course_id: "" };

export default function Subjects() {
  const { user } = useAuth();
  const [subjects, setSubjects] = useState([]);
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  function refresh() {
    setLoading(true);
    Promise.all([getSubjects(), getCourses(user.school_id)])
      .then(([s, c]) => {
        setSubjects(s);
        setCourses(c);
      })
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  const courseName = (id) => courses.find((c) => c.id === id)?.code ?? `#${id}`;

  const columns = [
    { key: "code", label: "Code" },
    { key: "name", label: "Name" },
    { key: "course_id", label: "Course", render: (row) => courseName(row.course_id) },
  ];

  function openCreate() {
    setForm({ ...EMPTY_FORM, course_id: courses[0]?.id ?? "" });
    setError("");
    setEditing({});
  }

  function openEdit(subject) {
    setForm({ code: subject.code, name: subject.name, course_id: subject.course_id });
    setError("");
    setEditing(subject);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    const payload = { ...form, course_id: Number(form.course_id) };
    setSubmitting(true);
    try {
      if (editing.id) {
        await updateSubject(editing.id, payload);
      } else {
        await createSubject(payload);
      }
      setEditing(null);
      refresh();
    } catch {
      setError("Couldn't save this subject.");
    } finally {
      setSubmitting(false);
    }
  }

  async function confirmDelete() {
    await deleteSubject(deleting.id);
    setDeleting(null);
    refresh();
  }

  return (
    <div>
      <PageHeader
        eyebrow="Academic Management"
        title="Subject Management"
        description="The individual subjects taught within each course. Exams are created against a subject, and instructors must be assigned to one before they can set an exam for it."
        actions={
        <button
          onClick={openCreate}
          disabled={courses.length === 0}
          className="flex items-center gap-2 bg-primary hover:bg-primary/90 disabled:opacity-40 text-white px-4 py-2.5 rounded-xl text-[12px] font-mono uppercase tracking-wider transition-colors"
        >
          <Plus className="w-4 h-4" /> Add Subject
        </button>
        }
      />

      {courses.length === 0 && !loading && (
        <div className="mb-4 text-sm text-muted-foreground">Create a course first before adding subjects.</div>
      )}

      <DataTable columns={columns} rows={subjects} loading={loading} onEdit={openEdit} onDelete={setDeleting} emptyLabel="No subjects yet"
        emptyHint="Subjects are the individual classes inside a course, like CS-101. Exams are created against a subject, so you need at least one before any exam can exist."
      />

      {editing && (
        <Modal title={editing.id ? "Edit Subject" : "Add Subject"} onClose={() => setEditing(null)}>
          <form onSubmit={handleSubmit}>
            {error && <div className="mb-4 rounded-xl bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-600">{error}</div>}
            <TextField
              label="Code"
              hint="The subject code as it appears on a schedule, e.g. CS-101."
              required
              value={form.code}
              onChange={(e) => setForm({ ...form, code: e.target.value })}
              placeholder="CS411"
            />
            <TextField
              label="Name"
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Computer Vision Fundamentals"
            />
            <SelectField
              label="Course"
              required
              value={form.course_id}
              onChange={(e) => setForm({ ...form, course_id: e.target.value })}
            >
              {courses.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.code} — {c.name}
                </option>
              ))}
            </SelectField>
            <button
              type="submit"
              disabled={submitting}
              className="w-full bg-primary hover:bg-primary/90 disabled:opacity-50 text-white py-2.5 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors"
            >
              {submitting ? "Saving…" : editing.id ? "Save Changes" : "Create Subject"}
            </button>
          </form>
        </Modal>
      )}

      {deleting && (
        <ConfirmDialog
          title="Delete Subject"
          message={`Delete subject "${deleting.name}"? This cannot be undone.`}
          onConfirm={confirmDelete}
          onCancel={() => setDeleting(null)}
        />
      )}
    </div>
  );
}
