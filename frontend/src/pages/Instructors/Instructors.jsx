import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { getInstructors, createInstructor, updateInstructor, deleteInstructor } from "../../api/instructors";
import SectionTag from "../../components/ui/SectionTag";
import DataTable from "../../components/DataTable";
import Modal from "../../components/Modal";
import ConfirmDialog from "../../components/ConfirmDialog";
import { TextField } from "../../components/ui/FormField";

const EMPTY_FORM = { employee_number: "", user_id: "" };

const COLUMNS = [
  { key: "employee_number", label: "Employee No." },
  { key: "user_id", label: "User ID", render: (row) => `#${row.user_id}` },
];

export default function Instructors() {
  const [instructors, setInstructors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState(null);

  function refresh() {
    setLoading(true);
    getInstructors()
      .then(setInstructors)
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  function openCreate() {
    setForm(EMPTY_FORM);
    setError("");
    setEditing({});
  }

  function openEdit(instructor) {
    setForm({ employee_number: instructor.employee_number, user_id: instructor.user_id });
    setError("");
    setEditing(instructor);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    try {
      if (editing.id) {
        await updateInstructor(editing.id, { employee_number: form.employee_number });
      } else {
        await createInstructor({ employee_number: form.employee_number, user_id: Number(form.user_id) });
      }
      setEditing(null);
      refresh();
    } catch {
      setError("Couldn't save this instructor. Check that the User ID exists and isn't already linked.");
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

      <DataTable columns={COLUMNS} rows={instructors} loading={loading} onEdit={openEdit} onDelete={setDeleting} emptyLabel="No instructors yet." />

      {editing && (
        <Modal title={editing.id ? "Edit Instructor" : "Add Instructor"} onClose={() => setEditing(null)}>
          <form onSubmit={handleSubmit}>
            {error && <div className="mb-4 rounded-xl bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-600">{error}</div>}
            {!editing.id && (
              <p className="text-xs text-muted-foreground mb-4">
                This links an existing user account to an instructor record. Register the account
                first (e.g. via <code>/auth/register</code>) and enter its numeric User ID below.
              </p>
            )}
            <TextField
              label="Employee Number"
              required
              value={form.employee_number}
              onChange={(e) => setForm({ ...form, employee_number: e.target.value })}
              placeholder="EMP-2025-001"
            />
            {!editing.id && (
              <TextField
                label="User ID"
                type="number"
                required
                value={form.user_id}
                onChange={(e) => setForm({ ...form, user_id: e.target.value })}
                placeholder="8"
              />
            )}
            <button
              type="submit"
              className="w-full bg-primary hover:bg-primary/90 text-white py-2.5 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors"
            >
              {editing.id ? "Save Changes" : "Create Instructor"}
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
    </div>
  );
}
