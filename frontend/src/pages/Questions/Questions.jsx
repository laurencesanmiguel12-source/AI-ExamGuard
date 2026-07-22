import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { getQuestions, createQuestion, updateQuestion, deleteQuestion } from "../../api/questions";
import { getExams } from "../../api/exams";
import SectionTag from "../../components/ui/SectionTag";
import DataTable from "../../components/DataTable";
import Modal from "../../components/Modal";
import ConfirmDialog from "../../components/ConfirmDialog";
import { TextField, SelectField } from "../../components/ui/FormField";

const QUESTION_TYPES = [
  { value: "Multiple Choice", label: "Multiple Choice" },
  { value: "True/False", label: "True / False" },
  { value: "Identification", label: "Identification" },
];

const EMPTY_FORM = { question_text: "", question_type: "Multiple Choice", points: 5, order_number: 1, exam_id: "" };

export default function Questions() {
  const [questions, setQuestions] = useState([]);
  const [exams, setExams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState(null);

  function refresh() {
    setLoading(true);
    Promise.all([getQuestions(), getExams()])
      .then(([q, e]) => {
        setQuestions(q);
        setExams(e);
      })
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  const examTitle = (id) => exams.find((e) => e.id === id)?.title ?? `#${id}`;

  const columns = [
    { key: "question_text", label: "Question" },
    { key: "question_type", label: "Type" },
    { key: "points", label: "Points" },
    { key: "exam_id", label: "Exam", render: (row) => examTitle(row.exam_id) },
  ];

  function openCreate() {
    setForm({ ...EMPTY_FORM, exam_id: exams[0]?.id ?? "" });
    setError("");
    setEditing({});
  }

  function openEdit(question) {
    setForm({
      question_text: question.question_text,
      question_type: question.question_type,
      points: question.points,
      order_number: question.order_number,
      exam_id: question.exam_id,
    });
    setError("");
    setEditing(question);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    const payload = {
      ...form,
      points: Number(form.points),
      order_number: Number(form.order_number),
      exam_id: Number(form.exam_id),
    };
    try {
      if (editing.id) {
        await updateQuestion(editing.id, payload);
      } else {
        await createQuestion(payload);
      }
      setEditing(null);
      refresh();
    } catch {
      setError("Couldn't save this question.");
    }
  }

  async function confirmDelete() {
    await deleteQuestion(deleting.id);
    setDeleting(null);
    refresh();
  }

  return (
    <div>
      <div className="flex items-start justify-between mb-8">
        <div>
          <SectionTag text="Exam Content" />
          <h2 className="font-display font-black text-foreground text-4xl">Questions</h2>
        </div>
        <button
          onClick={openCreate}
          disabled={exams.length === 0}
          className="flex items-center gap-2 bg-primary hover:bg-primary/90 disabled:opacity-40 text-white px-4 py-2.5 rounded-xl text-[12px] font-mono uppercase tracking-wider transition-colors"
        >
          <Plus className="w-4 h-4" /> Add Question
        </button>
      </div>

      {exams.length === 0 && !loading && (
        <div className="mb-4 text-sm text-muted-foreground">Create an exam first before adding questions.</div>
      )}

      <DataTable columns={columns} rows={questions} loading={loading} onEdit={openEdit} onDelete={setDeleting} emptyLabel="No questions yet." />

      {editing && (
        <Modal title={editing.id ? "Edit Question" : "Add Question"} onClose={() => setEditing(null)}>
          <form onSubmit={handleSubmit}>
            {error && <div className="mb-4 rounded-xl bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-600">{error}</div>}
            <TextField
              label="Question Text"
              required
              value={form.question_text}
              onChange={(e) => setForm({ ...form, question_text: e.target.value })}
              placeholder="What is Python?"
            />
            <SelectField
              label="Type"
              value={form.question_type}
              onChange={(e) => setForm({ ...form, question_type: e.target.value })}
            >
              {QUESTION_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </SelectField>
            <div className="grid grid-cols-2 gap-3">
              <TextField
                label="Points"
                type="number"
                required
                value={form.points}
                onChange={(e) => setForm({ ...form, points: e.target.value })}
              />
              <TextField
                label="Order Number"
                type="number"
                required
                value={form.order_number}
                onChange={(e) => setForm({ ...form, order_number: e.target.value })}
              />
            </div>
            <SelectField
              label="Exam"
              required
              value={form.exam_id}
              onChange={(e) => setForm({ ...form, exam_id: e.target.value })}
            >
              {exams.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.title}
                </option>
              ))}
            </SelectField>
            <button
              type="submit"
              className="w-full bg-primary hover:bg-primary/90 text-white py-2.5 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors"
            >
              {editing.id ? "Save Changes" : "Create Question"}
            </button>
          </form>
        </Modal>
      )}

      {deleting && (
        <ConfirmDialog
          title="Delete Question"
          message="Delete this question? This cannot be undone."
          onConfirm={confirmDelete}
          onCancel={() => setDeleting(null)}
        />
      )}
    </div>
  );
}
