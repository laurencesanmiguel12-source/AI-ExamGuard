import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { getStudents, createStudent, updateStudent, deleteStudent } from "../../api/students";
import { getCourses } from "../../api/courses";
import SectionTag from "../../components/ui/SectionTag";
import DataTable from "../../components/DataTable";
import Modal from "../../components/Modal";
import ConfirmDialog from "../../components/ConfirmDialog";
import { TextField, SelectField, CheckboxField } from "../../components/ui/FormField";

const EMPTY_FORM = {
  student_number: "",
  user_id: "",
  course_id: "",
  accommodation_notes: "",
  skip_face_check: false,
  skip_object_check: false,
  extra_time_minutes: 0,
};

export default function Students() {
  const [students, setStudents] = useState([]);
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState(null);

  function refresh() {
    setLoading(true);
    Promise.all([getStudents(), getCourses()])
      .then(([s, c]) => {
        setStudents(s);
        setCourses(c);
      })
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  const courseName = (id) => courses.find((c) => c.id === id)?.code ?? `#${id}`;

  const columns = [
    { key: "student_name", label: "Name", render: (row) => row.student_name ?? `#${row.user_id}` },
    { key: "student_number", label: "Student No." },
    { key: "user_id", label: "User ID", render: (row) => `#${row.user_id}` },
    { key: "course_id", label: "Course", render: (row) => courseName(row.course_id) },
    {
      key: "accommodation",
      label: "Accommodation",
      render: (row) =>
        row.skip_face_check || row.skip_object_check || row.extra_time_minutes > 0 ? (
          <span className="text-[10px] font-mono px-2 py-0.5 rounded border border-blue-200 bg-blue-50 text-blue-700 uppercase tracking-wider">
            Active
          </span>
        ) : (
          <span className="text-xs text-muted-foreground">—</span>
        ),
    },
  ];

  function openCreate() {
    setForm({ ...EMPTY_FORM, course_id: courses[0]?.id ?? "" });
    setError("");
    setEditing({});
  }

  function openEdit(student) {
    setForm({
      student_number: student.student_number,
      user_id: student.user_id,
      course_id: student.course_id,
      accommodation_notes: student.accommodation_notes ?? "",
      skip_face_check: student.skip_face_check ?? false,
      skip_object_check: student.skip_object_check ?? false,
      extra_time_minutes: student.extra_time_minutes ?? 0,
    });
    setError("");
    setEditing(student);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    const payload = {
      ...form,
      user_id: Number(form.user_id),
      course_id: Number(form.course_id),
      extra_time_minutes: Number(form.extra_time_minutes) || 0,
    };
    try {
      if (editing.id) {
        await updateStudent(editing.id, payload);
      } else {
        await createStudent(payload);
      }
      setEditing(null);
      refresh();
    } catch {
      setError("Couldn't save this student. Check that the User ID exists and isn't already linked.");
    }
  }

  async function confirmDelete() {
    await deleteStudent(deleting.id);
    setDeleting(null);
    refresh();
  }

  return (
    <div>
      <div className="flex items-start justify-between mb-8">
        <div>
          <SectionTag text="Academic Management" />
          <h2 className="font-display font-black text-foreground text-4xl">Students</h2>
        </div>
        <button
          onClick={openCreate}
          disabled={courses.length === 0}
          className="flex items-center gap-2 bg-primary hover:bg-primary/90 disabled:opacity-40 text-white px-4 py-2.5 rounded-xl text-[12px] font-mono uppercase tracking-wider transition-colors"
        >
          <Plus className="w-4 h-4" /> Add Student
        </button>
      </div>

      {courses.length === 0 && !loading && (
        <div className="mb-4 text-sm text-muted-foreground">Create a course first before adding students.</div>
      )}

      <DataTable columns={columns} rows={students} loading={loading} onEdit={openEdit} onDelete={setDeleting} emptyLabel="No students yet." />

      {editing && (
        <Modal title={editing.id ? "Edit Student" : "Add Student"} onClose={() => setEditing(null)}>
          <form onSubmit={handleSubmit}>
            {error && <div className="mb-4 rounded-xl bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-600">{error}</div>}
            <p className="text-xs text-muted-foreground mb-4">
              This links an existing user account to a student record. Register the account first
              (e.g. via <code>/auth/register</code>) and enter its numeric User ID below — there's no
              user directory to pick from yet.
            </p>
            <TextField
              label="Student Number"
              required
              value={form.student_number}
              onChange={(e) => setForm({ ...form, student_number: e.target.value })}
              placeholder="AU-2025-001"
            />
            <TextField
              label="User ID"
              type="number"
              required
              value={form.user_id}
              onChange={(e) => setForm({ ...form, user_id: e.target.value })}
              placeholder="7"
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
            {editing.id && (
              <>
                <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest mb-3 mt-2 pt-4 border-t border-border">
                  Accessibility Accommodation
                </div>
                <TextField
                  label="Accommodation Notes"
                  value={form.accommodation_notes}
                  onChange={(e) => setForm({ ...form, accommodation_notes: e.target.value })}
                  placeholder="e.g. Extended time and no camera monitoring — visual impairment, on file with the registrar"
                />
                <CheckboxField
                  label="Skip face detection/verification checks"
                  checked={form.skip_face_check}
                  onChange={(e) => setForm({ ...form, skip_face_check: e.target.checked })}
                />
                <CheckboxField
                  label="Skip phone/object detection checks"
                  checked={form.skip_object_check}
                  onChange={(e) => setForm({ ...form, skip_object_check: e.target.checked })}
                />
                <TextField
                  label="Extra Time (minutes)"
                  type="number"
                  min="0"
                  value={form.extra_time_minutes}
                  onChange={(e) => setForm({ ...form, extra_time_minutes: e.target.value })}
                  placeholder="0"
                />
              </>
            )}
            <button
              type="submit"
              className="w-full bg-primary hover:bg-primary/90 text-white py-2.5 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors"
            >
              {editing.id ? "Save Changes" : "Create Student"}
            </button>
          </form>
        </Modal>
      )}

      {deleting && (
        <ConfirmDialog
          title="Delete Student"
          message={`Delete student "${deleting.student_name ?? deleting.student_number}" (${deleting.student_number})? This cannot be undone.`}
          onConfirm={confirmDelete}
          onCancel={() => setDeleting(null)}
        />
      )}
    </div>
  );
}
