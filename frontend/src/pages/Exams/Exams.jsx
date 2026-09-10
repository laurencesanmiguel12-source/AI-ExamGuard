import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Plus, ListChecks, Users } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { useSchoolSlug } from "../../hooks/useSchoolNav";
import { getExams, createExam, updateExam, deleteExam } from "../../api/exams";
import { getSubjects } from "../../api/subjects";
import { getInstructors } from "../../api/instructors";
import { getSections } from "../../api/academic";
import PageHeader from "../../components/PageHeader";
import DataTable from "../../components/DataTable";
import DetailModal from "../../components/DetailModal";
import Modal from "../../components/Modal";
import ConfirmDialog from "../../components/ConfirmDialog";
import { TextField, SelectField, CheckboxField } from "../../components/ui/FormField";
import { isAdmin } from "../../utils/roles";

function ownershipMessage(err) {
  if (err?.response?.status === 403) {
    return "You don't have permission to manage this exam — only its assigned instructor can.";
  }
  return null;
}

const EMPTY_FORM = {
  title: "",
  description: "",
  duration_minutes: 60,
  total_points: 100,
  passing_score: 60,
  max_risk_score: "",
  start_time: "",
  end_time: "",
  is_active: false,
  // The only thing an exam is filed under. Subject and instructor come from the section, so they
  // are not on this form at all - a field that cannot be filled in cannot disagree with the class
  // the exam belongs to.
  section_id: "",
};

function toLocalInput(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export default function Exams() {
  const { user } = useAuth();
  const schoolSlug = useSchoolSlug();
  const [exams, setExams] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [instructors, setInstructors] = useState([]);
  const [sections, setSections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState(null);
  const [deleteError, setDeleteError] = useState("");
  const [viewing, setViewing] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  function refresh() {
    setLoading(true);
    Promise.all([getExams(), getSubjects(), getInstructors(), getSections()])
      .then(([e, s, i, sec]) => {
        setExams(e);
        setSubjects(s);
        setInstructors(i);
        setSections(sec);
      })
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  const subjectName = (id) => subjects.find((s) => s.id === id)?.code ?? `#${id}`;
  // Name first, employee number only as a fallback. The defense panel asked for names -
  // InstructorResponse has carried instructor_name since that was fixed on the Instructors page,
  // and this list was still rendering the payroll id at them.
  const instructorName = (id) => {
    const found = instructors.find((i) => i.id === id);
    return found?.instructor_name ?? found?.employee_number ?? `#${id}`;
  };
  const myInstructor = instructors.find((i) => i.user_id === user.id) ?? null;
  const sectionById = (id) => sections.find((sec) => sec.id === id) ?? null;
  // The sections this account may actually set an exam on. An instructor owns their own; an admin
  // manages the whole school. Offering the rest would put choices in the list that the server
  // answers with a 403 - the form should not invite a click it knows will fail.
  const creatableSections = isAdmin(user)
    ? sections
    : sections.filter((sec) => sec.instructor_id === myInstructor?.id);

  const columns = [
    { key: "title", label: "Title" },
    { key: "subject_id", label: "Subject", render: (row) => subjectName(row.subject_id) },
    {
      // The class and the term it ran in, which is what tells two exams on the same subject apart
      // - the whole reason the hierarchy exists.
      key: "section_id",
      label: "Section",
      render: (row) => {
        const sec = sectionById(row.section_id);
        return sec ? `${sec.code} · ${sec.term_name ?? ""}`.trim() : `#${row.section_id}`;
      },
      search: (row) => {
        const sec = sectionById(row.section_id);
        return sec ? `${sec.code} ${sec.term_name ?? ""} ${sec.academic_year_label ?? ""}` : "";
      },
    },
    { key: "instructor_id", label: "Instructor", render: (row) => instructorName(row.instructor_id) },
    { key: "is_active", label: "Status", render: (row) => (row.is_active ? "Active" : "Inactive") },
    {
      key: "content",
      label: "Content",
      render: (row) => (
        <Link
          to={`/${schoolSlug}/exams/${row.id}/content`}
          className="inline-flex items-center gap-1.5 bg-primary/10 hover:bg-primary/20 text-primary-ink px-2.5 py-1.5 rounded-lg text-[11px] font-mono uppercase tracking-wider transition-colors"
        >
          <ListChecks className="w-3.5 h-3.5" /> Manage Content
        </Link>
      ),
    },
    {
      key: "roster",
      label: "Roster",
      render: (row) => (
        <Link
          to={`/${schoolSlug}/exams/${row.id}/roster`}
          className="inline-flex items-center gap-1.5 bg-primary/10 hover:bg-primary/20 text-primary-ink px-2.5 py-1.5 rounded-lg text-[11px] font-mono uppercase tracking-wider transition-colors"
        >
          <Users className="w-3.5 h-3.5" /> Manage Roster
        </Link>
      ),
    },
  ];

  function openCreate() {
    setForm({ ...EMPTY_FORM, section_id: creatableSections[0]?.id ?? "" });
    setError("");
    setEditing({});
  }

  function openEdit(exam) {
    setForm({
      title: exam.title,
      description: exam.description ?? "",
      duration_minutes: exam.duration_minutes,
      total_points: exam.total_points,
      passing_score: exam.passing_score,
      max_risk_score: exam.max_risk_score ?? "",
      start_time: toLocalInput(exam.start_time),
      end_time: toLocalInput(exam.end_time),
      is_active: exam.is_active,
      section_id: exam.section_id ?? "",
    });
    setError("");
    setEditing(exam);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    const payload = {
      ...form,
      duration_minutes: Number(form.duration_minutes),
      total_points: Number(form.total_points),
      passing_score: Number(form.passing_score),
      max_risk_score: form.max_risk_score === "" ? null : Number(form.max_risk_score),
      section_id: Number(form.section_id),
      start_time: new Date(form.start_time).toISOString(),
      end_time: new Date(form.end_time).toISOString(),
    };
    try {
      if (editing.id) {
        await updateExam(editing.id, payload);
      } else {
        await createExam(payload);
      }
      setEditing(null);
      refresh();
    } catch (err) {
      setError(ownershipMessage(err) ?? "Couldn't save this exam.");
    } finally {
      setSubmitting(false);
    }
  }

  async function confirmDelete() {
    try {
      await deleteExam(deleting.id);
      setDeleting(null);
      refresh();
    } catch (err) {
      setDeleteError(ownershipMessage(err) ?? "Couldn't delete this exam.");
      setDeleting(null);
    }
  }

  const canCreate = creatableSections.length > 0;

  return (
    <div>
      <PageHeader
        eyebrow="Assessment"
        title="Exam Management"
        description="Every exam at your school. Open one to write its questions, choose who sits it, and set the window it stays open for."
        actions={
        <button
          onClick={openCreate}
          disabled={!canCreate}
          className="flex items-center gap-2 bg-primary hover:bg-primary/90 disabled:opacity-40 text-white px-4 py-2.5 rounded-xl text-[12px] font-mono uppercase tracking-wider transition-colors"
        >
          <Plus className="w-4 h-4" /> Add Exam
        </button>
        }
      />

      {!canCreate && !loading && (
        <div className="mb-4 text-sm text-muted-foreground">
          {sections.length === 0
            ? "Set up a section first — an exam belongs to one class, and that is where its students come from. Sections & Class Lists."
            : isAdmin(user)
            ? "No sections in this school yet."
            : "You aren't teaching any section yet, so there is no class to set an exam for. An admin assigns sections on Sections & Class Lists."}
        </div>
      )}

      {deleteError && (
        <div className="mb-4 rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-600">
          {deleteError}
        </div>
      )}

      <DataTable columns={columns} rows={exams} loading={loading} onEdit={openEdit} onDelete={setDeleting} onRowClick={setViewing} emptyLabel="No exams yet"
        searchable searchPlaceholder="Search exams by title or subject…"
        emptyHint="An exam belongs to one section — one class, in one term, taught by one instructor — and admits that class unless you roster students on the exam itself."
      />

      {viewing && (() => {
        const sec = sectionById(viewing.section_id);
        const when = (iso) => (iso ? new Date(iso).toLocaleString() : null);
        return (
          <DetailModal
            title={viewing.title}
            subtitle={viewing.description || undefined}
            stats={[
              { label: "Minutes", value: viewing.duration_minutes },
              { label: "Points", value: viewing.total_points },
              { label: "Pass %", value: viewing.passing_score },
            ]}
            sections={[
              {
                label: "Class",
                rows: [
                  ["Course", sec?.course_code],
                  ["Subject", subjectName(viewing.subject_id)],
                  ["Section", sec ? sec.code : `#${viewing.section_id}`],
                  ["Term", viewing.term_label],
                  ["Instructor", instructorName(viewing.instructor_id)],
                  [
                    "Enrolled in section",
                    sec ? sec.enrolled_count : null,
                  ],
                ],
              },
              {
                label: "Window",
                rows: [
                  ["Opens", when(viewing.start_time)],
                  ["Closes", when(viewing.end_time)],
                  ["Status", viewing.is_active ? "Active" : "Inactive"],
                  [
                    "Retake flagging",
                    viewing.max_risk_score === null || viewing.max_risk_score === undefined
                      ? "Off"
                      : `Above risk ${viewing.max_risk_score}`,
                  ],
                ],
              },
            ]}
            onEdit={() => {
              setViewing(null);
              openEdit(viewing);
            }}
            editLabel="Edit exam"
            onClose={() => setViewing(null)}
          />
        );
      })()}

      {editing && (
        <Modal title={editing.id ? "Edit Exam" : "Add Exam"} onClose={() => setEditing(null)}>
          <form onSubmit={handleSubmit}>
            {error && <div className="mb-4 rounded-xl bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-600">{error}</div>}
            <TextField
              label="Title"
              required
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              placeholder="Python Midterm Examination"
            />
            <TextField
              label="Description"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="Optional"
            />
            <div className="grid grid-cols-2 gap-3">
              <TextField
                label="Duration (min)"
                hint="How long a student gets once they start, in minutes."
                type="number"
                required
                value={form.duration_minutes}
                onChange={(e) => setForm({ ...form, duration_minutes: e.target.value })}
              />
              <TextField
                label="Total Points"
                hint="The exam total. Keep it equal to the sum of your question points."
                type="number"
                required
                value={form.total_points}
                onChange={(e) => setForm({ ...form, total_points: e.target.value })}
              />
            </div>
            <TextField
              label="Passing Score (%)"
              hint="The percentage needed to pass, 0–100 — not a number of points. A student passes when their score as a percentage of Total Points reaches this."
              type="number"
              min="0"
              max="100"
              required
              value={form.passing_score}
              onChange={(e) => setForm({ ...form, passing_score: e.target.value })}
            />
            <TextField
              label="Max Risk Score"
              hint="Optional. If proctoring flags a student above this score (0–100), their attempt is marked for review and they may be offered a retake. Leave blank to never auto-flag."
              type="number"
              min="0"
              max="100"
              value={form.max_risk_score}
              onChange={(e) => setForm({ ...form, max_risk_score: e.target.value })}
              placeholder="Leave blank to disable retake flagging"
            />
            <div className="grid grid-cols-2 gap-3">
              <TextField
                label="Start Time"
                hint="The exam cannot be opened before this."
                type="datetime-local"
                required
                value={form.start_time}
                onChange={(e) => setForm({ ...form, start_time: e.target.value })}
              />
              <TextField
                label="End Time"
                hint="The exam closes at this time."
                type="datetime-local"
                required
                value={form.end_time}
                onChange={(e) => setForm({ ...form, end_time: e.target.value })}
              />
            </div>
            {/* One field where there used to be two. Picking the class settles the subject, the
                instructor, the term and the school year at once, and picking a section whose
                enrolment is empty is the one thing worth warning about before the exam day. */}
            <SelectField
              label="Section"
              hint="The class sitting this exam. Its enrolled students are admitted automatically unless you set a roster on the exam itself."
              required
              value={form.section_id}
              onChange={(e) => setForm({ ...form, section_id: e.target.value })}
            >
              {creatableSections.map((sec) => (
                <option key={sec.id} value={sec.id}>
                  {sec.subject_code} {sec.code} — {sec.term_name} {sec.academic_year_label}
                  {sec.enrolled_count === 0 ? " (nobody enrolled)" : ` (${sec.enrolled_count})`}
                </option>
              ))}
            </SelectField>
            {sectionById(Number(form.section_id))?.enrolled_count === 0 && (
              <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
                Nobody is enrolled in this section, so this exam will admit no students unless you
                roster them on the exam itself.
              </div>
            )}
            <CheckboxField
              label="Active"
              checked={form.is_active}
              onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
            />
            <button
              type="submit"
              disabled={submitting}
              className="w-full bg-primary hover:bg-primary/90 disabled:opacity-50 text-white py-2.5 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors"
            >
              {submitting ? "Saving…" : editing.id ? "Save Changes" : "Create Exam"}
            </button>
          </form>
        </Modal>
      )}

      {deleting && (
        <ConfirmDialog
          title="Delete Exam"
          message={`Delete exam "${deleting.title}"? This cannot be undone.`}
          onConfirm={confirmDelete}
          onCancel={() => setDeleting(null)}
        />
      )}
    </div>
  );
}
