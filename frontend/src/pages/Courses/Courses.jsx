import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { getCourses, createCourse, updateCourse, deleteCourse } from "../../api/courses";
import { useAuth } from "../../context/AuthContext";
import SectionTag from "../../components/ui/SectionTag";
import DataTable from "../../components/DataTable";
import Modal from "../../components/Modal";
import ConfirmDialog from "../../components/ConfirmDialog";
import { TextField } from "../../components/ui/FormField";

const COLUMNS = [
  { key: "code", label: "Code" },
  { key: "name", label: "Name" },
];

const EMPTY_FORM = { code: "", name: "" };

export default function Courses() {
  const { user } = useAuth();
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  function refresh() {
    setLoading(true);
    getCourses(user.school_id)
      .then(setCourses)
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  function openCreate() {
    setForm(EMPTY_FORM);
    setError("");
    setEditing({});
  }

  function openEdit(course) {
    setForm({ code: course.code, name: course.name });
    setError("");
    setEditing(course);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      if (editing.id) {
        await updateCourse(editing.id, form);
      } else {
        await createCourse(form);
      }
      setEditing(null);
      refresh();
    } catch {
      setError("Couldn't save this course.");
    } finally {
      setSubmitting(false);
    }
  }

  async function confirmDelete() {
    await deleteCourse(deleting.id);
    setDeleting(null);
    refresh();
  }

  return (
    <div>
      <div className="flex items-start justify-between mb-8">
        <div>
          <SectionTag text="Academic Management" />
          <h2 className="font-display font-black text-foreground text-4xl">Courses</h2>
        </div>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 bg-primary hover:bg-primary/90 text-white px-4 py-2.5 rounded-xl text-[12px] font-mono uppercase tracking-wider transition-colors"
        >
          <Plus className="w-4 h-4" /> Add Course
        </button>
      </div>

      <DataTable columns={COLUMNS} rows={courses} loading={loading} onEdit={openEdit} onDelete={setDeleting} emptyLabel="No courses yet." />

      {editing && (
        <Modal title={editing.id ? "Edit Course" : "Add Course"} onClose={() => setEditing(null)}>
          <form onSubmit={handleSubmit}>
            {error && <div className="mb-4 rounded-xl bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-600">{error}</div>}
            <TextField
              label="Code"
              required
              value={form.code}
              onChange={(e) => setForm({ ...form, code: e.target.value })}
              placeholder="BSCS"
            />
            <TextField
              label="Name"
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="BS Computer Science"
            />
            <button
              type="submit"
              disabled={submitting}
              className="w-full bg-primary hover:bg-primary/90 disabled:opacity-50 text-white py-2.5 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors"
            >
              {submitting ? "Saving…" : editing.id ? "Save Changes" : "Create Course"}
            </button>
          </form>
        </Modal>
      )}

      {deleting && (
        <ConfirmDialog
          title="Delete Course"
          message={`Delete course "${deleting.name}"? This cannot be undone.`}
          onConfirm={confirmDelete}
          onCancel={() => setDeleting(null)}
        />
      )}
    </div>
  );
}
