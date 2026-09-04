import { useEffect, useState } from "react";
import { Plus, BookOpen, AlertTriangle } from "lucide-react";
import { getInstructors, createInstructor, updateInstructor, deleteInstructor } from "../../api/instructors";
import { getSubjects } from "../../api/subjects";
import {
  getInstructorSubjects,
  assignInstructorSubject,
  unassignInstructorSubject,
} from "../../api/instructorSubjects";
import PageHeader from "../../components/PageHeader";
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
  subject_ids: [],
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

function buildColumns(onManageSubjects, subjectCounts) {
  return [
    { key: "employee_number", label: "Employee No." },
    { key: "user_id", label: "User ID", render: (row) => `#${row.user_id}` },
    {
      key: "subjects",
      label: "Subjects",
      render: (row) => {
        const count = subjectCounts[row.id];
        return (
          <div className="flex items-center gap-3">
            <button
              onClick={() => onManageSubjects(row)}
              className="flex items-center gap-1.5 text-[11px] font-mono uppercase tracking-wider text-primary hover:underline"
            >
              <BookOpen className="w-3.5 h-3.5" /> Manage
            </button>
            {/* An instructor with no subject cannot create an exam, and with no exam of their own
                every roster stays closed to them - the account looks fine until they try to use
                it. Called out here because assigning a subject is a separate step an admin can
                easily miss. */}
            {count === 0 && (
              <span
                className="flex items-center gap-1 text-[11px] text-amber-700"
                title="Assign a subject before this instructor can create exams"
              >
                <AlertTriangle className="w-3.5 h-3.5" /> No subjects
              </span>
            )}
          </div>
        );
      },
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
  const [subjectCounts, setSubjectCounts] = useState({});

  function refresh() {
    setLoading(true);
    Promise.all([getInstructors(), getSubjects()])
      .then(([i, s]) => {
        setInstructors(i);
        setAllSubjects(s);
        // One request per instructor - the same shape the instructor dashboard already uses for
        // per-exam rosters, and this list is short. A failure here only costs the warning badge,
        // so it must not blank out the table.
        return Promise.all(
          i.map((row) =>
            getInstructorSubjects(row.id)
              .then((assigned) => [row.id, assigned.length])
              .catch(() => [row.id, null])
          )
        ).then((entries) => setSubjectCounts(Object.fromEntries(entries)));
      })
      .catch(() => setSubjectCounts({}))
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
      <PageHeader
        eyebrow="Academic Management"
        title="Instructor Management"
        description="Teaching staff accounts for your school. Assign each instructor at least one subject — without one they cannot create any exam."
        actions={
        <button
          onClick={openCreate}
          className="flex items-center gap-2 bg-primary hover:bg-primary/90 text-white px-4 py-2.5 rounded-xl text-[12px] font-mono uppercase tracking-wider transition-colors"
        >
          <Plus className="w-4 h-4" /> Add Instructor
        </button>
        }
      />

      <DataTable
        columns={buildColumns(setManagingSubjects, subjectCounts)}
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
                {/* Assigned here rather than only through the separate Manage dialog: without at
                    least one subject the new account cannot create an exam, so it arrives unable
                    to do the main thing an instructor does. */}
                <div className="mb-4">
                  <label className="block text-[11px] font-mono uppercase tracking-wider text-muted-foreground mb-2">
                    Subjects
                  </label>
                  {allSubjects.length === 0 ? (
                    <p className="text-sm text-muted-foreground">
                      No subjects exist yet — create one first, or assign later from the list.
                    </p>
                  ) : (
                    <div className="space-y-2 max-h-40 overflow-y-auto">
                      {allSubjects.map((s) => (
                        <label key={s.id} className="flex items-center gap-2.5 cursor-pointer">
                          <input
                            type="checkbox"
                            className="w-4 h-4 accent-primary"
                            checked={form.subject_ids.includes(s.id)}
                            onChange={(e) =>
                              setForm({
                                ...form,
                                subject_ids: e.target.checked
                                  ? [...form.subject_ids, s.id]
                                  : form.subject_ids.filter((id) => id !== s.id),
                              })
                            }
                          />
                          <span className="text-sm text-foreground">
                            {s.code} — {s.name}
                          </span>
                        </label>
                      ))}
                    </div>
                  )}
                  {allSubjects.length > 0 && form.subject_ids.length === 0 && (
                    <p className="mt-2 flex items-center gap-1.5 text-[12px] text-amber-700">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      Without a subject this instructor won't be able to create exams.
                    </p>
                  )}
                </div>
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
