import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { getChoices, createChoice, updateChoice, deleteChoice } from "../../api/choices";
import { getQuestions } from "../../api/questions";
import SectionTag from "../../components/ui/SectionTag";
import DataTable from "../../components/DataTable";
import Modal from "../../components/Modal";
import ConfirmDialog from "../../components/ConfirmDialog";
import { TextField, SelectField, CheckboxField } from "../../components/ui/FormField";

const EMPTY_FORM = { choice_text: "", is_correct: false, question_id: "" };

export default function Choices() {
  const [choices, setChoices] = useState([]);
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState(null);

  function refresh() {
    setLoading(true);
    Promise.all([getChoices(), getQuestions()])
      .then(([c, q]) => {
        setChoices(c);
        setQuestions(q);
      })
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  const questionText = (id) => {
    const q = questions.find((q) => q.id === id);
    return q ? q.question_text.slice(0, 40) : `#${id}`;
  };

  const columns = [
    { key: "choice_text", label: "Choice" },
    { key: "is_correct", label: "Correct", render: (row) => (row.is_correct ? "✓" : "") },
    { key: "question_id", label: "Question", render: (row) => questionText(row.question_id) },
  ];

  function openCreate() {
    setForm({ ...EMPTY_FORM, question_id: questions[0]?.id ?? "" });
    setError("");
    setEditing({});
  }

  function openEdit(choice) {
    setForm({ choice_text: choice.choice_text, is_correct: choice.is_correct, question_id: choice.question_id });
    setError("");
    setEditing(choice);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    const payload = { ...form, question_id: Number(form.question_id) };
    try {
      if (editing.id) {
        await updateChoice(editing.id, payload);
      } else {
        await createChoice(payload);
      }
      setEditing(null);
      refresh();
    } catch {
      setError("Couldn't save this choice.");
    }
  }

  async function confirmDelete() {
    await deleteChoice(deleting.id);
    setDeleting(null);
    refresh();
  }

  return (
    <div>
      <div className="flex items-start justify-between mb-8">
        <div>
          <SectionTag text="Exam Content" />
          <h2 className="font-display font-black text-foreground text-4xl">Choices</h2>
        </div>
        <button
          onClick={openCreate}
          disabled={questions.length === 0}
          className="flex items-center gap-2 bg-primary hover:bg-primary/90 disabled:opacity-40 text-white px-4 py-2.5 rounded-xl text-[12px] font-mono uppercase tracking-wider transition-colors"
        >
          <Plus className="w-4 h-4" /> Add Choice
        </button>
      </div>

      {questions.length === 0 && !loading && (
        <div className="mb-4 text-sm text-muted-foreground">Create a question first before adding choices.</div>
      )}

      <DataTable columns={columns} rows={choices} loading={loading} onEdit={openEdit} onDelete={setDeleting} emptyLabel="No choices yet." />

      {editing && (
        <Modal title={editing.id ? "Edit Choice" : "Add Choice"} onClose={() => setEditing(null)}>
          <form onSubmit={handleSubmit}>
            {error && <div className="mb-4 rounded-xl bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-600">{error}</div>}
            <TextField
              label="Choice Text"
              required
              value={form.choice_text}
              onChange={(e) => setForm({ ...form, choice_text: e.target.value })}
              placeholder="A programming language"
            />
            <SelectField
              label="Question"
              required
              value={form.question_id}
              onChange={(e) => setForm({ ...form, question_id: e.target.value })}
            >
              {questions.map((q) => (
                <option key={q.id} value={q.id}>
                  {q.question_text.slice(0, 60)}
                </option>
              ))}
            </SelectField>
            <CheckboxField
              label="Correct answer"
              checked={form.is_correct}
              onChange={(e) => setForm({ ...form, is_correct: e.target.checked })}
            />
            <button
              type="submit"
              className="w-full bg-primary hover:bg-primary/90 text-white py-2.5 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors"
            >
              {editing.id ? "Save Changes" : "Create Choice"}
            </button>
          </form>
        </Modal>
      )}

      {deleting && (
        <ConfirmDialog
          title="Delete Choice"
          message="Delete this choice? This cannot be undone."
          onConfirm={confirmDelete}
          onCancel={() => setDeleting(null)}
        />
      )}
    </div>
  );
}
