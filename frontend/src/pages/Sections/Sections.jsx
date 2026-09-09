import { useEffect, useState } from "react";
import { Plus, AlertTriangle } from "lucide-react";
import { getSections, createSection, getAcademicYears, getTerms } from "../../api/academic";
import { getSubjects } from "../../api/subjects";
import { getInstructors } from "../../api/instructors";
import { useAuth } from "../../context/AuthContext";
import { useSchoolNav } from "../../hooks/useSchoolNav";
import { isAdmin } from "../../utils/roles";
import PageHeader from "../../components/PageHeader";
import DataTable from "../../components/DataTable";
import Modal from "../../components/Modal";
import Card from "../../components/ui/Card";
import { TextField, SelectField } from "../../components/ui/FormField";

const EMPTY_FORM = { subject_id: "", term_id: "", instructor_id: "", code: "", capacity: "", schedule: "" };

function detail(err, fallback) {
  return err?.response?.data?.detail ?? fallback;
}

export default function Sections() {
  const { user } = useAuth();
  const navigate = useSchoolNav();
  const canManage = isAdmin(user);

  const [sections, setSections] = useState([]);
  const [terms, setTerms] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [instructors, setInstructors] = useState([]);
  const [termFilter, setTermFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState("");

  const [form, setForm] = useState(null);
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let active = true;
    // Terms come from every year, not just the current one: a section is often built for next
    // term while this one is still running, and filtering to the current year would hide exactly
    // the term someone came here to set up.
    Promise.all([getAcademicYears(), getSubjects(), getInstructors()])
      .then(async ([years, subjectRows, instructorRows]) => {
        const termLists = await Promise.all(years.map((y) => getTerms(y.id)));
        if (!active) return;
        const withYear = termLists.flatMap((rows, i) =>
          rows.map((t) => ({ ...t, year_label: years[i].label }))
        );
        setTerms(withYear);
        setSubjects(subjectRows);
        setInstructors(instructorRows);
      })
      .catch(() => active && setPageError("Couldn't load the terms, subjects and instructors."));
    return () => {
      active = false;
    };
  }, []);

  function refresh() {
    setLoading(true);
    return getSections(termFilter ? { termId: Number(termFilter) } : {})
      .then(setSections)
      .catch(() => setPageError("Couldn't load sections."))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [termFilter]);

  const columns = [
    { key: "code", label: "Section" },
    {
      key: "subject",
      label: "Subject",
      render: (row) => `${row.subject_code ?? "—"} ${row.subject_name ?? ""}`.trim(),
      search: (row) => `${row.subject_code ?? ""} ${row.subject_name ?? ""}`,
    },
    {
      key: "term",
      label: "Term",
      render: (row) => `${row.term_name ?? "—"} ${row.academic_year_label ?? ""}`.trim(),
      search: (row) => `${row.term_name ?? ""} ${row.academic_year_label ?? ""}`,
    },
    { key: "instructor_name", label: "Instructor", render: (row) => row.instructor_name ?? "—" },
    {
      key: "enrolled_count",
      label: "Enrolled",
      // An empty class list is the thing worth spotting from the list: an exam inheriting this
      // section admits nobody, and that looks exactly like a correctly configured exam until
      // somebody tries to start it.
      render: (row) =>
        row.enrolled_count === 0 ? (
          <span className="flex items-center gap-1.5 text-amber-700">
            <AlertTriangle className="h-3.5 w-3.5" /> Nobody enrolled
          </span>
        ) : (
          row.enrolled_count
        ),
      search: (row) => String(row.enrolled_count),
    },
  ];

  async function handleSubmit(event) {
    event.preventDefault();
    setFormError("");
    setSubmitting(true);
    try {
      await createSection({
        subject_id: Number(form.subject_id),
        term_id: Number(form.term_id),
        instructor_id: Number(form.instructor_id),
        code: form.code,
        capacity: form.capacity === "" ? null : Number(form.capacity),
        schedule: form.schedule === "" ? null : form.schedule,
      });
      setForm(null);
      await refresh();
    } catch (err) {
      setFormError(detail(err, "Couldn't create this section."));
    } finally {
      setSubmitting(false);
    }
  }

  const canCreate = canManage && terms.length > 0 && subjects.length > 0 && instructors.length > 0;

  function missingPrerequisite() {
    if (terms.length === 0) return "Add a term on the Academic Calendar first — a section belongs to one.";
    if (subjects.length === 0) return "Add a subject first — a section is one offering of one subject.";
    if (instructors.length === 0) return "Add an instructor first — a section is taught by one.";
    return null;
  }

  return (
    <div>
      <PageHeader
        eyebrow="Academic Management"
        title="Sections & Class Lists"
        description="A section is one offering of one subject, in one term, taught by one instructor, to one enrolled class. Its class list is what an exam admits when no roster is set for the exam itself."
        actions={
          canManage && (
            <button
              onClick={() => {
                setForm({
                  ...EMPTY_FORM,
                  subject_id: subjects[0]?.id ?? "",
                  term_id: termFilter || terms[0]?.id || "",
                  instructor_id: instructors[0]?.id ?? "",
                });
                setFormError("");
              }}
              disabled={!canCreate}
              className="flex items-center gap-2 bg-primary hover:bg-primary/90 disabled:opacity-40 text-white px-4 py-2.5 rounded-xl text-[12px] font-mono uppercase tracking-wider transition-colors"
            >
              <Plus className="w-4 h-4" /> Add Section
            </button>
          )
        }
      />

      {pageError && (
        <div
          role="alert"
          className="mb-6 rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-600"
        >
          {pageError}
        </div>
      )}

      {canManage && !canCreate && !loading && (
        <div className="mb-4 text-sm text-muted-foreground">{missingPrerequisite()}</div>
      )}

      {terms.length > 0 && (
        <div className="mb-4 max-w-sm">
          <SelectField
            label="Term"
            value={termFilter}
            onChange={(e) => setTermFilter(e.target.value)}
          >
            <option value="">All terms</option>
            {terms.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name} — {t.year_label}
                {t.status === "ACTIVE" ? " (active)" : ""}
              </option>
            ))}
          </SelectField>
        </div>
      )}

      <DataTable
        columns={columns}
        rows={sections}
        loading={loading}
        onRowClick={(row) => navigate(`/sections/${row.id}`)}
        emptyLabel="No sections yet"
        searchable
        searchPlaceholder="Search by section code, subject, term or instructor…"
        emptyHint="A section is what makes a class a real thing: two instructors teaching the same subject are two sections, and each one carries its own class list for an exam to admit."
      />

      {sections.length > 0 && (
        <Card className="mt-4 p-4 text-xs text-muted-foreground">
          Open a section to manage who is enrolled in it.
        </Card>
      )}

      {form && (
        <Modal title="Add Section" onClose={() => setForm(null)}>
          <form onSubmit={handleSubmit}>
            {formError && (
              <div className="mb-4 rounded-xl bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-600">
                {formError}
              </div>
            )}
            <SelectField
              label="Subject"
              required
              value={form.subject_id}
              onChange={(e) => setForm({ ...form, subject_id: e.target.value })}
            >
              {subjects.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.code} — {s.name}
                </option>
              ))}
            </SelectField>
            <SelectField
              label="Term"
              required
              value={form.term_id}
              onChange={(e) => setForm({ ...form, term_id: e.target.value })}
            >
              {terms.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name} — {t.year_label}
                </option>
              ))}
            </SelectField>
            <SelectField
              label="Instructor"
              hint="Who teaches this particular offering. Two instructors on the same subject are two sections, which is what tells their classes apart."
              required
              value={form.instructor_id}
              onChange={(e) => setForm({ ...form, instructor_id: e.target.value })}
            >
              {instructors.map((i) => (
                <option key={i.id} value={i.id}>
                  {i.instructor_name ?? i.employee_number}
                </option>
              ))}
            </SelectField>
            <TextField
              label="Section Code"
              hint="How the class is named on a schedule — BSCS-3A, Section 2, and so on."
              required
              value={form.code}
              onChange={(e) => setForm({ ...form, code: e.target.value })}
              placeholder="BSCS-3A"
            />
            <TextField
              label="Capacity"
              type="number"
              min="1"
              hint="Optional. For reference only — it does not block enrolment."
              value={form.capacity}
              onChange={(e) => setForm({ ...form, capacity: e.target.value })}
              placeholder="40"
            />
            <TextField
              label="Schedule"
              hint="Optional, free text."
              value={form.schedule}
              onChange={(e) => setForm({ ...form, schedule: e.target.value })}
              placeholder="MWF 9:00-10:30"
            />
            <button
              type="submit"
              disabled={submitting}
              className="w-full bg-primary hover:bg-primary/90 disabled:opacity-50 text-white py-2.5 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors"
            >
              {submitting ? "Saving…" : "Create Section"}
            </button>
          </form>
        </Modal>
      )}
    </div>
  );
}
