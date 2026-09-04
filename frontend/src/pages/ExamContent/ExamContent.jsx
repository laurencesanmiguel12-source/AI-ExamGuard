import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useSchoolNav } from "../../hooks/useSchoolNav";
import { ArrowLeft, Plus, Upload, Download, ChevronDown, ChevronRight } from "lucide-react";
import { getExam } from "../../api/exams";
import {
  getExamQuestions,
  createExamQuestion,
  updateExamQuestion,
  deleteExamQuestion,
  importExamQuestionsCsv,
} from "../../api/questions";
import {
  createExamChoice,
  updateExamChoice,
  deleteExamChoice,
} from "../../api/choices";
import PageHeader from "../../components/PageHeader";
import Card from "../../components/ui/Card";
import DataTable from "../../components/DataTable";
import Modal from "../../components/Modal";
import ConfirmDialog from "../../components/ConfirmDialog";
import { TextField, SelectField, CheckboxField } from "../../components/ui/FormField";

const QUESTION_TYPES = [
  { value: "Multiple Choice", label: "Multiple Choice" },
  { value: "True/False", label: "True / False" },
  { value: "Identification", label: "Identification" },
];

const EMPTY_QUESTION_FORM = { question_text: "", question_type: "Multiple Choice", points: 5, order_number: 1 };
const EMPTY_CHOICE_FORM = { choice_text: "", is_correct: false };

function ownershipMessage(err) {
  if (err?.response?.status === 403) {
    return "You don't have permission to manage this exam's content — only its assigned instructor can.";
  }
  return null;
}

export default function ExamContent() {
  const { examId } = useParams();
  const navigate = useSchoolNav();

  const [phase, setPhase] = useState("loading");
  const [exam, setExam] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [selectedQuestionId, setSelectedQuestionId] = useState(null);
  const [pageError, setPageError] = useState("");

  const [editingQuestion, setEditingQuestion] = useState(null);
  const [questionForm, setQuestionForm] = useState(EMPTY_QUESTION_FORM);
  const [questionError, setQuestionError] = useState("");
  const [deletingQuestion, setDeletingQuestion] = useState(null);

  const [editingChoice, setEditingChoice] = useState(null);
  const [choiceForm, setChoiceForm] = useState(EMPTY_CHOICE_FORM);
  const [choiceError, setChoiceError] = useState("");
  const [deletingChoice, setDeletingChoice] = useState(null);

  const [csvFile, setCsvFile] = useState(null);
  const [csvPreview, setCsvPreview] = useState([]);
  const [csvResult, setCsvResult] = useState(null);
  const [csvError, setCsvError] = useState("");
  const [showCsvGuide, setShowCsvGuide] = useState(false);
  const [importing, setImporting] = useState(false);

  function refresh() {
    return Promise.all([getExam(examId), getExamQuestions(examId)])
      .then(([examData, questionData]) => {
        setExam(examData);
        setQuestions([...questionData].sort((a, b) => a.order_number - b.order_number));
        setPhase("ready");
      })
      .catch(() => setPhase("error"));
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [examId]);

  const selectedQuestion = questions.find((q) => q.id === selectedQuestionId) ?? null;

  const questionColumns = [
    {
      key: "question_text",
      label: "Question",
      render: (row) => (
        <button
          onClick={() => setSelectedQuestionId(row.id)}
          className={`text-left hover:text-primary hover:underline underline-offset-2 transition-colors ${
            row.id === selectedQuestionId ? "text-primary font-semibold" : ""
          }`}
        >
          {row.question_text}
        </button>
      ),
    },
    { key: "question_type", label: "Type" },
    { key: "points", label: "Points" },
    { key: "choices", label: "Choices", render: (row) => row.choices.length },
  ];

  const choiceColumns = [
    { key: "choice_text", label: "Choice" },
    { key: "is_correct", label: "Correct", render: (row) => (row.is_correct ? "✓" : "") },
  ];

  function openCreateQuestion() {
    setQuestionForm({ ...EMPTY_QUESTION_FORM, order_number: questions.length + 1 });
    setQuestionError("");
    setEditingQuestion({});
  }

  function openEditQuestion(question) {
    setQuestionForm({
      question_text: question.question_text,
      question_type: question.question_type,
      points: question.points,
      order_number: question.order_number,
    });
    setQuestionError("");
    setEditingQuestion(question);
  }

  async function handleQuestionSubmit(event) {
    event.preventDefault();
    setQuestionError("");
    const payload = {
      ...questionForm,
      points: Number(questionForm.points),
      order_number: Number(questionForm.order_number),
    };
    try {
      if (editingQuestion.id) {
        await updateExamQuestion(examId, editingQuestion.id, payload);
      } else {
        await createExamQuestion(examId, payload);
      }
      setEditingQuestion(null);
      refresh();
    } catch (err) {
      setQuestionError(ownershipMessage(err) ?? "Couldn't save this question.");
    }
  }

  async function confirmDeleteQuestion() {
    try {
      await deleteExamQuestion(examId, deletingQuestion.id);
      if (deletingQuestion.id === selectedQuestionId) setSelectedQuestionId(null);
      setDeletingQuestion(null);
      refresh();
    } catch (err) {
      setPageError(ownershipMessage(err) ?? "Couldn't delete this question.");
      setDeletingQuestion(null);
    }
  }

  function openCreateChoice() {
    setChoiceForm(EMPTY_CHOICE_FORM);
    setChoiceError("");
    setEditingChoice({});
  }

  function openEditChoice(choice) {
    setChoiceForm({ choice_text: choice.choice_text, is_correct: choice.is_correct });
    setChoiceError("");
    setEditingChoice(choice);
  }

  async function handleChoiceSubmit(event) {
    event.preventDefault();
    setChoiceError("");
    try {
      if (editingChoice.id) {
        await updateExamChoice(examId, selectedQuestionId, editingChoice.id, choiceForm);
      } else {
        await createExamChoice(examId, selectedQuestionId, choiceForm);
      }
      setEditingChoice(null);
      refresh();
    } catch (err) {
      setChoiceError(ownershipMessage(err) ?? "Couldn't save this choice.");
    }
  }

  async function confirmDeleteChoice() {
    try {
      await deleteExamChoice(examId, selectedQuestionId, deletingChoice.id);
      setDeletingChoice(null);
      refresh();
    } catch (err) {
      setPageError(ownershipMessage(err) ?? "Couldn't delete this choice.");
      setDeletingChoice(null);
    }
  }

  // Real, valid, importable rows - not placeholder text - one example per accepted
  // question_type so an instructor can see the exact shape (including that Identification rows
  // have no choice columns filled in) rather than guessing from the prose description alone.
  const CSV_TEMPLATE =
    "question_text,question_type,points,order_number,choice_1,choice_1_correct,choice_2,choice_2_correct,choice_3,choice_3_correct,choice_4,choice_4_correct\n" +
    "What is the capital of France?,Multiple Choice,5,1,Paris,true,London,false,Berlin,false,Madrid,false\n" +
    "The Earth revolves around the Sun.,True/False,5,2,True,true,False,false,,,,\n" +
    // Third row deliberately contains a comma inside the question, wrapped in quotes. This is the
    // single most common way an import goes wrong: an unquoted comma shifts every later value one
    // column left, so the row fails with a confusing "question_type must be one of ..." naming a
    // fragment of the question. Shipping a correct example is cheaper than explaining the symptom.
    "\"In programming, what is a variable used for?\",Multiple Choice,5,3,Storing a value,true," +
    "Printing output,false,Ending a loop,false,Declaring a class,false\n" +
    "Name the process by which plants convert sunlight into energy.,Identification,10,4,,,,,,,,\n";

  const CSV_RULES = [
    ["question_text", "Required. If it contains a comma, wrap the whole cell in \"double quotes\" — otherwise the row shifts and fails."],
    ["question_type", "Required, spelled exactly: Multiple Choice, True/False, or Identification."],
    ["points", "Required. A whole number greater than 0."],
    ["order_number", "Optional. Leave blank and questions keep the order of the rows."],
    ["choice_1 … choice_6", "Up to 6 choices. Multiple Choice and True/False need at least 2 filled in; Identification takes none — leave them blank."],
    ["choice_N_correct", "true / yes / 1 to mark the answer, false / no / 0 otherwise. At least one choice must be correct."],
  ];

  function handleDownloadTemplate() {
    const blob = new Blob([CSV_TEMPLATE], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "exam_questions_template.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  function handleCsvFileChange(event) {
    const file = event.target.files?.[0] ?? null;
    setCsvFile(file);
    setCsvResult(null);
    setCsvError("");
    setCsvPreview([]);
    if (!file) return;

    file.text().then((text) => {
      const lines = text.split(/\r?\n/).filter((l) => l.trim().length > 0);
      if (lines.length < 2) return;
      const header = lines[0].split(",").map((h) => h.trim());
      const qtIdx = header.indexOf("question_type");
      const qtextIdx = header.indexOf("question_text");
      const preview = lines.slice(1, 11).map((line) => {
        const cells = line.split(",");
        const choiceCount = header.filter((h, i) => h.startsWith("choice_") && !h.endsWith("_correct") && cells[i]?.trim()).length;
        return {
          question_text: qtextIdx >= 0 ? cells[qtextIdx] : "",
          question_type: qtIdx >= 0 ? cells[qtIdx] : "",
          choiceCount,
        };
      });
      setCsvPreview(preview);
    });
  }

  async function handleCsvImport() {
    if (!csvFile) return;
    setImporting(true);
    setCsvError("");
    try {
      const result = await importExamQuestionsCsv(examId, csvFile);
      setCsvResult(result);
      setCsvFile(null);
      setCsvPreview([]);
      refresh();
    } catch (err) {
      setCsvError(ownershipMessage(err) ?? "Couldn't import this file.");
    } finally {
      setImporting(false);
    }
  }

  if (phase === "loading") {
    return (
      <div className="text-sm text-muted-foreground font-mono uppercase tracking-widest">Loading…</div>
    );
  }

  if (phase === "error") {
    return <div className="text-sm text-red-600">Couldn't load this exam.</div>;
  }

  return (
    <div>
      <button
        onClick={() => navigate("/exams")}
        className="flex items-center gap-1.5 text-[11px] font-mono uppercase tracking-widest text-muted-foreground hover:text-foreground transition-colors mb-6"
      >
        <ArrowLeft className="w-3.5 h-3.5" /> Back to Exams
      </button>

      <PageHeader
        eyebrow="Exam Content"
        title={exam.title}
        description="Write the questions for this exam and mark the correct answers. Add them one at a time, or import many at once from a spreadsheet using the CSV panel below."
      />

      {pageError && (
        <div className="mb-6 rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-600">
          {pageError}
        </div>
      )}

      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-foreground">Questions</h3>
        <button
          onClick={openCreateQuestion}
          className="flex items-center gap-2 bg-primary hover:bg-primary/90 text-white px-4 py-2.5 rounded-xl text-[12px] font-mono uppercase tracking-wider transition-colors"
        >
          <Plus className="w-4 h-4" /> Add Question
        </button>
      </div>

      <DataTable
        columns={questionColumns}
        rows={questions}
        loading={false}
        onEdit={openEditQuestion}
        onDelete={setDeletingQuestion}
        emptyLabel="No questions yet. Add one manually or import a CSV below."
      />

      <div className="flex items-center justify-between mt-8 mb-3">
        <h3 className="text-sm font-semibold text-foreground">
          Choices {selectedQuestion && <span className="text-muted-foreground font-normal">— {selectedQuestion.question_text.slice(0, 60)}</span>}
        </h3>
        <button
          onClick={openCreateChoice}
          disabled={!selectedQuestion}
          className="flex items-center gap-2 bg-primary hover:bg-primary/90 disabled:opacity-40 text-white px-4 py-2.5 rounded-xl text-[12px] font-mono uppercase tracking-wider transition-colors"
        >
          <Plus className="w-4 h-4" /> Add Choice
        </button>
      </div>

      {selectedQuestion ? (
        <DataTable
          columns={choiceColumns}
          rows={selectedQuestion.choices}
          loading={false}
          onEdit={openEditChoice}
          onDelete={setDeletingChoice}
          emptyLabel="No choices yet."
        />
      ) : (
        <Card className="p-6 text-sm text-muted-foreground">Click a question above to manage its choices.</Card>
      )}

      <div className="mt-8">
        <h3 className="text-sm font-semibold text-foreground mb-3">Bulk Import via CSV</h3>
        <Card className="p-6">
          <p className="text-sm text-muted-foreground mb-1">
            Add many questions at once from a spreadsheet. One row per question.
          </p>
          <p className="text-sm text-muted-foreground mb-4">
            The quickest route: download the template, open it in Excel or Google Sheets, replace
            the example rows with your own, then save as CSV and upload it below. Nothing is saved
            until you press Confirm Import, and you'll see a preview first.
          </p>

          <div className="flex flex-wrap items-center gap-4 mb-4">
            <button
              onClick={handleDownloadTemplate}
              className="flex items-center gap-1.5 text-[11px] font-mono uppercase tracking-wider text-primary hover:text-primary/80 transition-colors"
            >
              <Download className="w-3.5 h-3.5" /> Download CSV Template
            </button>
            <button
              onClick={() => setShowCsvGuide((v) => !v)}
              aria-expanded={showCsvGuide}
              className="flex items-center gap-1 text-[11px] font-mono uppercase tracking-wider text-muted-foreground hover:text-foreground transition-colors"
            >
              {showCsvGuide ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
              Column guide
            </button>
          </div>

          {showCsvGuide && (
            <div className="mb-4 rounded-xl border border-border bg-secondary/40 p-4">
              <dl className="space-y-2.5">
                {CSV_RULES.map(([column, rule]) => (
                  <div key={column} className="grid grid-cols-1 sm:grid-cols-[170px_1fr] gap-1 sm:gap-3">
                    <dt className="font-mono text-[11px] text-foreground/80 pt-0.5">{column}</dt>
                    <dd className="text-sm text-muted-foreground">{rule}</dd>
                  </div>
                ))}
              </dl>
              <p className="text-sm text-muted-foreground mt-4 pt-3 border-t border-border">
                Save the file as <span className="font-mono text-foreground/80">CSV UTF-8</span> so
                accents and special characters survive. Rows with problems are skipped and listed
                individually after import — the rest still import, so you can fix just those and
                upload again.
              </p>
            </div>
          )}
          <input
            type="file"
            accept=".csv"
            onChange={handleCsvFileChange}
            className="text-sm text-foreground mb-4 block"
          />

          {csvPreview.length > 0 && (
            <div className="mb-4 border border-border rounded-xl overflow-hidden">
              <div className="grid grid-cols-3 gap-4 px-4 py-2 text-[10px] font-mono text-muted-foreground uppercase tracking-widest bg-secondary">
                <span>Question</span>
                <span>Type</span>
                <span>Choices</span>
              </div>
              <div className="divide-y divide-border">
                {csvPreview.map((row, i) => (
                  <div key={i} className="grid grid-cols-3 gap-4 px-4 py-2 text-sm text-foreground/80">
                    <span className="truncate">{row.question_text || "(blank)"}</span>
                    <span>{row.question_type || "(blank)"}</span>
                    <span>{row.choiceCount}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {csvError && (
            <div className="mb-4 rounded-xl bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-600">{csvError}</div>
          )}

          <button
            onClick={handleCsvImport}
            disabled={!csvFile || importing}
            className="flex items-center gap-2 bg-primary hover:bg-primary/90 disabled:opacity-40 text-white px-4 py-2.5 rounded-xl text-[12px] font-mono uppercase tracking-wider transition-colors"
          >
            <Upload className="w-4 h-4" /> {importing ? "Importing…" : "Confirm Import"}
          </button>

          {csvResult && (
            <div className="mt-4">
              <div className="rounded-xl bg-emerald-50 border border-emerald-200 px-3 py-2 text-sm text-emerald-700 mb-2">
                Created {csvResult.created} question{csvResult.created === 1 ? "" : "s"}.
              </div>
              {csvResult.errors.length > 0 && (
                <div className="rounded-xl bg-orange-50 border border-orange-200 px-3 py-2 text-sm text-orange-700">
                  <div className="font-semibold mb-1">{csvResult.errors.length} row(s) skipped:</div>
                  <ul className="list-disc list-inside space-y-0.5">
                    {csvResult.errors.map((e, i) => (
                      <li key={i}>Row {e.row}: {e.message}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </Card>
      </div>

      {editingQuestion && (
        <Modal title={editingQuestion.id ? "Edit Question" : "Add Question"} onClose={() => setEditingQuestion(null)}>
          <form onSubmit={handleQuestionSubmit}>
            {questionError && <div className="mb-4 rounded-xl bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-600">{questionError}</div>}
            <TextField
              label="Question Text"
              required
              value={questionForm.question_text}
              onChange={(e) => setQuestionForm({ ...questionForm, question_text: e.target.value })}
              placeholder="What is Python?"
            />
            <SelectField
              label="Type"
              value={questionForm.question_type}
              onChange={(e) => setQuestionForm({ ...questionForm, question_type: e.target.value })}
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
                hint="What this single question is worth towards the exam total."
                type="number"
                required
                value={questionForm.points}
                onChange={(e) => setQuestionForm({ ...questionForm, points: e.target.value })}
              />
              <TextField
                label="Order Number"
                hint="Where this question appears in the exam. Lower numbers come first."
                type="number"
                required
                value={questionForm.order_number}
                onChange={(e) => setQuestionForm({ ...questionForm, order_number: e.target.value })}
              />
            </div>
            <button
              type="submit"
              className="w-full bg-primary hover:bg-primary/90 text-white py-2.5 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors"
            >
              {editingQuestion.id ? "Save Changes" : "Create Question"}
            </button>
          </form>
        </Modal>
      )}

      {deletingQuestion && (
        <ConfirmDialog
          title="Delete Question"
          message="Delete this question and all of its choices? This cannot be undone."
          onConfirm={confirmDeleteQuestion}
          onCancel={() => setDeletingQuestion(null)}
        />
      )}

      {editingChoice && (
        <Modal title={editingChoice.id ? "Edit Choice" : "Add Choice"} onClose={() => setEditingChoice(null)}>
          <form onSubmit={handleChoiceSubmit}>
            {choiceError && <div className="mb-4 rounded-xl bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-600">{choiceError}</div>}
            <TextField
              label="Choice Text"
              required
              value={choiceForm.choice_text}
              onChange={(e) => setChoiceForm({ ...choiceForm, choice_text: e.target.value })}
              placeholder="A programming language"
            />
            <CheckboxField
              label="Correct answer"
              checked={choiceForm.is_correct}
              onChange={(e) => setChoiceForm({ ...choiceForm, is_correct: e.target.checked })}
            />
            <button
              type="submit"
              className="w-full bg-primary hover:bg-primary/90 text-white py-2.5 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors"
            >
              {editingChoice.id ? "Save Changes" : "Create Choice"}
            </button>
          </form>
        </Modal>
      )}

      {deletingChoice && (
        <ConfirmDialog
          title="Delete Choice"
          message="Delete this choice? This cannot be undone."
          onConfirm={confirmDeleteChoice}
          onCancel={() => setDeletingChoice(null)}
        />
      )}
    </div>
  );
}
