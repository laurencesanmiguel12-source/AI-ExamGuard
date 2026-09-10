import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { getStudents, createStudent, updateStudent, deleteStudent } from "../../api/students";
import { getCourses } from "../../api/courses";
import { getSubjects } from "../../api/subjects";
import { useAuth } from "../../context/AuthContext";
import PageHeader from "../../components/PageHeader";
import DataTable from "../../components/DataTable";
import Modal from "../../components/Modal";
import DetailModal from "../../components/DetailModal";
import ConfirmDialog from "../../components/ConfirmDialog";
import { TextField, SelectField, CheckboxField } from "../../components/ui/FormField";
import { isAdmin } from "../../utils/roles";

const EMPTY_FORM = {
  student_number: "",
  course_id: "",
  email: "",
  password: "",
  first_name: "",
  last_name: "",
  accommodation_notes: "",
  skip_face_check: false,
  skip_object_check: false,
  extra_time_minutes: 0,
};

export default function Students() {
  const { user } = useAuth();
  const [students, setStudents] = useState([]);
  const [courses, setCourses] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [viewing, setViewing] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  function refresh() {
    setLoading(true);
    Promise.all([getStudents(), getCourses(user.school_id), getSubjects().catch(() => [])])
      .then(([s, c, sub]) => {
        setStudents(s);
        setCourses(c);
        setSubjects(sub);
      })
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  const courseName = (id) => courses.find((c) => c.id === id)?.code ?? `#${id}`;

  // Instructors can read this list but every mutation behind it is require_admin - show them the
  // roster without buttons that would only ever come back 403.
  const canManage = isAdmin(user);

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
    // Name and email as well as the record fields - the same QA finding as Instructors: the form
    // could change a student's course and their accommodations but not the spelling of their name.
    setForm({
      ...EMPTY_FORM,
      first_name: student.first_name ?? "",
      last_name: student.last_name ?? "",
      email: student.email ?? "",
      student_number: student.student_number,
      course_id: student.course_id,
      accommodation_notes: student.accommodation_notes ?? "",
      skip_face_check: student.skip_face_check ?? false,
      skip_object_check: student.skip_object_check ?? false,
      extra_time_minutes: student.extra_time_minutes ?? 0,
    });
    setError("");
    setViewing(null);
    setEditing(student);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      if (editing.id) {
        const payload = {
          student_number: form.student_number,
          course_id: Number(form.course_id),
          accommodation_notes: form.accommodation_notes,
          skip_face_check: form.skip_face_check,
          skip_object_check: form.skip_object_check,
          extra_time_minutes: Number(form.extra_time_minutes) || 0,
          first_name: form.first_name,
          last_name: form.last_name,
          email: form.email,
        };
        await updateStudent(editing.id, payload);
      } else {
        const payload = {
          course_id: Number(form.course_id),
          email: form.email,
          password: form.password,
          first_name: form.first_name,
          last_name: form.last_name,
        };
        await createStudent(payload);
      }
      setEditing(null);
      refresh();
    } catch (err) {
      setError(err.response?.data?.detail ?? "Couldn't save this student.");
    } finally {
      setSubmitting(false);
    }
  }

  async function confirmDelete() {
    await deleteStudent(deleting.id);
    setDeleting(null);
    refresh();
  }

  return (
    <div>
      {/* Two audiences on one page: an admin manages these records, an instructor can only look
          them up. Saying which of those you are is the whole point of the description here. */}
      <PageHeader
        eyebrow="Academic Management"
        title="Student Management"
        description={
          canManage
            ? "Every student enrolled at your school. Students can also create their own account from the sign-up page — those appear here automatically."
            : "Every student enrolled at your school, read-only. To put a student into one of your exams, use Manage Roster on the exam itself."
        }
        actions={
          canManage && (
            <button
              onClick={openCreate}
              disabled={courses.length === 0}
              className="flex items-center gap-2 bg-primary hover:bg-primary/90 disabled:opacity-40 text-white px-4 py-2.5 rounded-xl text-[12px] font-mono uppercase tracking-wider transition-colors"
            >
              <Plus className="w-4 h-4" /> Add Student
            </button>
          )
        }
      />

      {canManage && courses.length === 0 && !loading && (
        <div className="mb-4 text-sm text-muted-foreground">Create a course first before adding students.</div>
      )}

      <DataTable
        columns={columns}
        rows={students}
        loading={loading}
        onEdit={canManage ? openEdit : undefined}
        onDelete={canManage ? setDeleting : undefined}
        onRowClick={setViewing}
        searchable
        searchPlaceholder="Search students by name, number or course…"
        emptyLabel="No students yet"
        emptyHint={
          canManage
            ? "Add students here, or share your school's sign-up link and let them register themselves — either way they appear in this list."
            : "No students have registered at your school yet. Once they do, they will appear here."
        }
      />

      {/* Read-only "who is this", opened by clicking the row. The panel asked for the student's
          subjects and course specifically - a student belongs to one course, and their subjects
          are that course's subjects, which nothing in the UI previously spelled out. */}
      {viewing && (
        <DetailModal
          title={viewing.student_name ?? `Student #${viewing.user_id}`}
          subtitle={`${viewing.student_number} · ${courseName(viewing.course_id)}`}
          stats={[
            { label: "Subjects", value: subjects.filter((sub) => sub.course_id === viewing.course_id).length },
            { label: "Face model", value: viewing.face_model_path ? "Yes" : "No" },
            { label: "Accommodations", value: (viewing.skip_face_check ? 1 : 0) + (viewing.skip_object_check ? 1 : 0) },
          ]}
          sections={[
            {
              label: "Record",
              rows: [
                ["Student number", viewing.student_number],
                ["Course", courses.find((c) => c.id === viewing.course_id)?.name ?? courseName(viewing.course_id)],
                ["Face enrolled", viewing.face_model_path ? "Yes" : "Not yet"],
                ["Skip face check", viewing.skip_face_check ? "Yes" : "No"],
                ["Skip object check", viewing.skip_object_check ? "Yes" : "No"],
                ["Extra time", viewing.extra_time_minutes ? `${viewing.extra_time_minutes} min` : "None"],
              ],
            },
            {
              label: "Subjects in their course",
              emptyLabel: "This course has no subjects yet, so there is nothing for them to sit.",
              items: subjects
                .filter((sub) => sub.course_id === viewing.course_id)
                .map((sub) => ({ key: sub.id, primary: sub.name, secondary: sub.code })),
            },
          ]}
          onEdit={canManage ? () => openEdit(viewing) : undefined}
          editLabel="Edit student"
          onClose={() => setViewing(null)}
        />
      )}

      {editing && (
        <Modal title={editing.id ? "Edit Student" : "Add Student"} onClose={() => setEditing(null)}>
          <form onSubmit={handleSubmit}>
            {error && <div className="mb-4 rounded-xl bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-600">{error}</div>}
            {editing.id && (
              <TextField
                label="Student Number"
                hint="Generated when the account was created. Change it only to match your registrar's own numbering."
                required
                value={form.student_number}
                onChange={(e) => setForm({ ...form, student_number: e.target.value })}
              />
            )}
            {/* Always shown. These are the fields an edit form exists to correct; only the
                password is create-only, because setting somebody else's password is a different
                act from fixing their name. */}
            <div className="grid grid-cols-2 gap-3">
              <TextField
                label="First Name"
                required
                value={form.first_name}
                onChange={(e) => setForm({ ...form, first_name: e.target.value })}
              />
              <TextField
                label="Last Name"
                required
                value={form.last_name}
                onChange={(e) => setForm({ ...form, last_name: e.target.value })}
              />
            </div>
            <TextField
              label="Email Address"
              hint="Their sign-in address. Changing it changes how they log in."
              type="email"
              required
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
            {!editing.id && (
              <TextField
                label="Password"
                type="password"
                required
                minLength={8}
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
              />
            )}
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
              disabled={submitting}
              className="w-full bg-primary hover:bg-primary/90 disabled:opacity-50 text-white py-2.5 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors"
            >
              {submitting ? "Saving…" : editing.id ? "Save Changes" : "Create Student"}
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
