import { useEffect, useState } from "react";
import { Plus, AlertTriangle } from "lucide-react";
import {
  getSections,
  createSection,
  updateSection,
  deleteSection,
  getAcademicYears,
  getTerms,
} from "../../api/academic";
import { getSubjects } from "../../api/subjects";
import { getInstructors } from "../../api/instructors";
import { useAuth } from "../../context/AuthContext";
import { useSchoolNav } from "../../hooks/useSchoolNav";
import { isAdmin } from "../../utils/roles";
import PageHeader from "../../components/PageHeader";
import DataTable from "../../components/DataTable";
import Modal from "../../components/Modal";
import ConfirmDialog from "../../components/ConfirmDialog";
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
  // null = closed, {} = creating, a section = editing that one. Same shape the other list pages
  // use, so the form below can serve both without a second copy of it.
  const [editing, setEditing] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let active = true;
    // Terms come from every year, not just the current one: a section is often built for next
    // term while this one is still running, and filtering to the current year would hide exactly
    // the term someone came here to set up.
    // One terms request, not one per year. GET /academic/terms with no academic_year_id already
    // returns every term in the school, and the year label is joined on here from the years we
    // are fetching anyway - a school with eight years of history was making nine round trips to
    // populate one dropdown.
    Promise.all([getAcademicYears(), getSubjects(), getInstructors(), getTerms()])
      .then(([years, subjectRows, instructorRows, termRows]) => {
        if (!active) return;
        const labelByYear = new Map(years.map((y) => [y.id, y.label]));
        const withYear = termRows.map((t) => ({
          ...t,
          year_label: labelByYear.get(t.academic_year_id) ?? "",
        }));
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

  function openCreate() {
    setForm({
      ...EMPTY_FORM,
      subject_id: subjects[0]?.id ?? "",
      term_id: termFilter || terms[0]?.id || "",
      instructor_id: instructors[0]?.id ?? "",
    });
    setFormError("");
    setEditing({});
  }

  function openEdit(section) {
    setForm({
      subject_id: section.subject_id,
      term_id: section.term_id,
      instructor_id: section.instructor_id,
      code: section.code,
      capacity: section.capacity ?? "",
      schedule: section.schedule ?? "",
    });
    setFormError("");
    setEditing(section);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setFormError("");
    setSubmitting(true);
    try {
      if (editing.id) {
        // Subject and term are not sent: they are what makes this section this class, and the
        // server does not accept them on an edit.
        await updateSection(editing.id, {
          code: form.code,
          instructor_id: Number(form.instructor_id),
          capacity: form.capacity === "" ? null : Number(form.capacity),
          schedule: form.schedule === "" ? null : form.schedule,
        });
      } else {
        await createSection({
          subject_id: Number(form.subject_id),
          term_id: Number(form.term_id),
          instructor_id: Number(form.instructor_id),
          code: form.code,
          capacity: form.capacity === "" ? null : Number(form.capacity),
          schedule: form.schedule === "" ? null : form.schedule,
        });
      }
      setEditing(null);
      await refresh();
    } catch (err) {
      setFormError(detail(err, "Couldn't save this section."));
    } finally {
      setSubmitting(false);
    }
  }

  async function confirmDelete() {
    // Deliberately not caught here - ConfirmDialog surfaces the server's refusal, and that
    // refusal ("1 exam is set on this section") is the useful part.
    await deleteSection(deleting.id);
    setDeleting(null);
    await refresh();
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
              onClick={openCreate}
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
        onEdit={canManage ? openEdit : undefined}
        onDelete={canManage ? setDeleting : undefined}
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

      {editing && (
        <Modal
          title={editing.id ? `Edit ${editing.subject_code ?? ""} ${editing.code}`.trim() : "Add Section"}
          onClose={() => setEditing(null)}
        >
          <form onSubmit={handleSubmit}>
            {formError && (
              <div className="mb-4 rounded-xl bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-600">
                {formError}
              </div>
            )}
            {/* Subject and term are settled at creation and shown read-only afterwards. They are
                what makes this section this class - changing either gives you a different class,
                not a corrected one - and an unused section can simply be deleted and remade. */}
            {editing.id ? (
              <div className="mb-4 rounded-xl border border-border bg-secondary px-4 py-3 text-sm">
                <span className="text-muted-foreground">
                  {editing.subject_code} {editing.subject_name} · {editing.term_name}{" "}
                  {editing.academic_year_label}
                </span>
                <p className="mt-1 text-xs text-muted-foreground">
                  A section's subject and term cannot be changed. Delete it and make another if
                  either is wrong.
                </p>
              </div>
            ) : (
              <>
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
              </>
            )}
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
            {editing.id && Number(form.instructor_id) !== editing.instructor_id && (
              <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
                This hands the class to a different instructor, and every exam set on it goes with
                them — they become the owner and {editing.instructor_name ?? "the current instructor"}{" "}
                loses access.
              </div>
            )}
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
              {submitting ? "Saving…" : editing.id ? "Save Changes" : "Create Section"}
            </button>
          </form>
        </Modal>
      )}

      {deleting && (
        <ConfirmDialog
          title="Delete Section"
          message={`Delete ${deleting.subject_code ?? ""} ${deleting.code}? This is refused if any exam is set on it or anyone is still enrolled.`}
          onConfirm={confirmDelete}
          onCancel={() => setDeleting(null)}
        />
      )}
    </div>
  );
}
