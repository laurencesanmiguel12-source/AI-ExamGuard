import { useEffect, useState } from "react";
import { Plus, BookOpen } from "lucide-react";
import { getInstructors, createInstructor, updateInstructor, deleteInstructor } from "../../api/instructors";
import { getSubjects } from "../../api/subjects";
import {
  getInstructorSubjects,
  assignInstructorSubject,
  unassignInstructorSubject,
} from "../../api/instructorSubjects";
import SectionTag from "../../components/ui/SectionTag";
import DataTable from "../../components/DataTable";
import Modal from "../../components/Modal";
import ConfirmDialog from "../../components/ConfirmDialog";
import { TextField } from "../../components/ui/FormField";

const EMPTY_FORM = {
  employee_number: "",
  email: "",
  password: "",
  first_name: "",
  last_name: "",
};

function SubjectsModal({ instructor, allSubjects, onClose }) {
  const [assignedIds, setAssignedIds] = useState(new Set());
  const [loading, setLoading] = useState(true);
  const [pendingId, setPendingId] = useState(null);
  const [error, setError] = useState("");

  function refresh() {
    setLoading(true);
    getInstructorSubjects(instructor.id)
      .then((rows) => setAssignedIds(new Set(rows.map((r) => r.subject_id))))
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  async function toggle(subjectId, checked) {
    setError("");
    setPendingId(subjectId);
    try {
      if (checked) {
        await assignInstructorSubject(instructor.id, subjectId);
      } else {
        await unassignInstructorSubject(instructor.id, subjectId);
      }
      refresh();
    } catch {
      setError("Couldn't update that assignment. Please try again.");
    } finally {
      setPendingId(null);
    }
  }

  return (
    <Modal title={`Subjects — ${instructor.employee_number}`} onClose={onClose}>
      {error && (
        <div className="mb-4 rounded-xl bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-600">{error}</div>
      )}
      {loading ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : allSubjects.length === 0 ? (
        <p className="text-sm text-muted-foreground">No subjects exist yet.</p>
      ) : (
        <div className="space-y-2 max-h-80 overflow-y-auto">
          {allSubjects.map((s) => (
            <label key={s.id} className="flex items-center gap-2.5 cursor-pointer">
              <input
                type="checkbox"
                className="w-4 h-4 accent-primary"
                checked={assignedIds.has(s.id)}
                disabled={pendingId === s.id}
                onChange={(e) => toggle(s.id, e.target.checked)}
              />
              <span className="text-sm text-foreground">
                {s.code} — {s.name}
              </span>
            </label>
          ))}
        </div>
      )}
    </Modal>
  );
}

function buildColumns(onManageSubjects) {
  return [
    { key: "employee_number", label: "Employee No." },
    { key: "user_id", label: "User ID", render: (row) => `#${row.user_id}` },
    {
      key: "subjects",
      label: "Subjects",
      render: (row) => (
        <button
          onClick={() => onManageSubjects(row)}
          className="flex items-center gap-1.5 text-[11px] font-mono uppercase tracking-wider text-primary hover:underline"
        >
          <BookOpen className="w-3.5 h-3.5" /> Manage
        </button>
      ),
    },
  ];
}

export default function Instructors() {
  const [instructors, setInstructors] = useState([]);
  const [allSubjects, setAllSubjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState(null);
  const [managingSubjects, setManagingSubjects] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  function refresh() {
    setLoading(true);
    Promise.all([getInstructors(), getSubjects()])
      .then(([i, s]) => {
        setInstructors(i);
        setAllSubjects(s);
      })
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  function openCreate() {
    setForm(EMPTY_FORM);
    setError("");
    setEditing({});
  }

  function openEdit(instructor) {
    setForm({ ...EMPTY_FORM, employee_number: instructor.employee_number });
    setError("");
    setEditing(instructor);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      if (editing.id) {
        await updateInstructor(editing.id, { employee_number: form.employee_number });
      } else {
        await createInstructor(form);
      }
      setEditing(null);
      refresh();
    } catch (err) {
      setError(err.response?.data?.detail ?? "Couldn't save this instructor.");
    } finally {
      setSubmitting(false);
    }
  }

  async function confirmDelete() {
    await deleteInstructor(deleting.id);
    setDeleting(null);
    refresh();
  }

  return (
    <div>
      <div className="flex items-start justify-between mb-8">
        <div>
          <SectionTag text="Academic Management" />
          <h2 className="font-display font-black text-foreground text-4xl">Instructors</h2>
        </div>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 bg-primary hover:bg-primary/90 text-white px-4 py-2.5 rounded-xl text-[12px] font-mono uppercase tracking-wider transition-colors"
        >
          <Plus className="w-4 h-4" /> Add Instructor
        </button>
      </div>

      <DataTable
        columns={buildColumns(setManagingSubjects)}
        rows={instructors}
        loading={loading}
        onEdit={openEdit}
        onDelete={setDeleting}
        emptyLabel="No instructors yet."
      />

      {editing && (
        <Modal title={editing.id ? "Edit Instructor" : "Add Instructor"} onClose={() => setEditing(null)}>
          <form onSubmit={handleSubmit}>
            {error && <div className="mb-4 rounded-xl bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-600">{error}</div>}
            <TextField
              label="Employee Number"
              required
              value={form.employee_number}
              onChange={(e) => setForm({ ...form, employee_number: e.target.value })}
              placeholder="EMP-2025-001"
            />
            {!editing.id && (
              <>
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
                  type="email"
                  required
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                />
                <TextField
                  label="Password"
                  type="password"
                  required
                  minLength={8}
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                />
              </>
            )}
            <button
              type="submit"
              disabled={submitting}
              className="w-full bg-primary hover:bg-primary/90 disabled:opacity-50 text-white py-2.5 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors"
            >
              {submitting ? "Saving…" : editing.id ? "Save Changes" : "Create Instructor"}
            </button>
          </form>
        </Modal>
      )}

      {deleting && (
        <ConfirmDialog
          title="Delete Instructor"
          message={`Delete instructor "${deleting.employee_number}"? This cannot be undone.`}
          onConfirm={confirmDelete}
          onCancel={() => setDeleting(null)}
        />
      )}

      {managingSubjects && (
        <SubjectsModal
          instructor={managingSubjects}
          allSubjects={allSubjects}
          onClose={() => setManagingSubjects(null)}
        />
      )}
    </div>
  );
}
