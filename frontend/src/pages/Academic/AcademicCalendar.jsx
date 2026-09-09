import { useEffect, useState } from "react";
import { Plus, CalendarDays, Check } from "lucide-react";
import {
  getAcademicYears,
  createAcademicYear,
  setCurrentAcademicYear,
  getTerms,
  createTerm,
  setTermStatus,
} from "../../api/academic";
import PageHeader from "../../components/PageHeader";
import Card from "../../components/ui/Card";
import Modal from "../../components/Modal";
import ConfirmDialog from "../../components/ConfirmDialog";
import { TextField, CheckboxField } from "../../components/ui/FormField";

const EMPTY_YEAR = { label: "", starts_on: "", ends_on: "", make_current: false };
const EMPTY_TERM = { name: "", sequence: 1, starts_on: "", ends_on: "" };

// The three states a term can be in, and what each one means for the people using it. A term is a
// deliberate administrative state machine rather than a date comparison, so the UI has to say what
// the state IS - "is this term over" is a decision somebody makes, not something the calendar
// answers on its own.
const TERM_STATE = {
  PLANNED: {
    label: "Planned",
    className: "bg-secondary text-muted-foreground border-border",
  },
  ACTIVE: {
    label: "Active",
    className: "bg-emerald-50 text-emerald-800 border-emerald-200",
  },
  CLOSED: {
    label: "Closed",
    className: "bg-secondary text-muted-foreground border-border",
  },
};

function detail(err, fallback) {
  return err?.response?.data?.detail ?? fallback;
}

function StatusBadge({ status }) {
  const state = TERM_STATE[status] ?? {
    label: status,
    className: "bg-secondary text-muted-foreground border-border",
  };
  return (
    <span
      className={`rounded-lg border px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider ${state.className}`}
    >
      {state.label}
    </span>
  );
}

export default function AcademicCalendar() {
  const [years, setYears] = useState([]);
  const [terms, setTerms] = useState([]);
  const [selectedYearId, setSelectedYearId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState("");

  const [yearForm, setYearForm] = useState(null);
  const [termForm, setTermForm] = useState(null);
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [closing, setClosing] = useState(null);

  function loadYears() {
    setLoading(true);
    return getAcademicYears()
      .then((rows) => {
        setYears(rows);
        // Land on the year that is actually in force rather than whichever sorted first - the
        // current year is what almost every visit here is about.
        setSelectedYearId((prev) =>
          prev && rows.some((y) => y.id === prev)
            ? prev
            : ((rows.find((y) => y.is_current) ?? rows[0])?.id ?? null)
        );
      })
      .catch(() => setPageError("Couldn't load the academic calendar."))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    loadYears();
  }, []);

  useEffect(() => {
    if (!selectedYearId) {
      setTerms([]);
      return;
    }
    let active = true;
    getTerms(selectedYearId)
      .then((rows) => active && setTerms(rows))
      .catch(() => active && setPageError("Couldn't load this year's terms."));
    return () => {
      active = false;
    };
  }, [selectedYearId]);

  function refreshTerms() {
    return getTerms(selectedYearId).then(setTerms);
  }

  async function submitYear(event) {
    event.preventDefault();
    setFormError("");
    setSubmitting(true);
    try {
      const created = await createAcademicYear(yearForm);
      setYearForm(null);
      await loadYears();
      setSelectedYearId(created.id);
    } catch (err) {
      setFormError(detail(err, "Couldn't create this academic year."));
    } finally {
      setSubmitting(false);
    }
  }

  async function submitTerm(event) {
    event.preventDefault();
    setFormError("");
    setSubmitting(true);
    try {
      await createTerm({
        ...termForm,
        sequence: Number(termForm.sequence),
        academic_year_id: selectedYearId,
      });
      setTermForm(null);
      await refreshTerms();
    } catch (err) {
      setFormError(detail(err, "Couldn't create this term."));
    } finally {
      setSubmitting(false);
    }
  }

  async function makeCurrent(year) {
    setPageError("");
    try {
      await setCurrentAcademicYear(year.id);
      await loadYears();
    } catch (err) {
      setPageError(detail(err, "Couldn't make this the current year."));
    }
  }

  async function changeStatus(term, status) {
    setPageError("");
    try {
      await setTermStatus(term.id, status);
      await refreshTerms();
    } catch (err) {
      // The server-side refusals are the interesting ones here - "'1st Semester' is still active.
      // Close it before activating another term." already says exactly what to do, so it is shown
      // as written rather than flattened into a generic failure.
      setPageError(detail(err, "Couldn't change this term's status."));
    }
  }

  async function confirmClose() {
    const term = closing;
    setClosing(null);
    await changeStatus(term, "CLOSED");
  }

  const selectedYear = years.find((y) => y.id === selectedYearId) ?? null;

  return (
    <div>
      <PageHeader
        eyebrow="Academic Management"
        title="Academic Calendar"
        description="The school years and terms everything else hangs off. A section is one subject taught in one term, so a term has to exist before any class can be built against it."
        actions={
          <button
            onClick={() => {
              setYearForm(EMPTY_YEAR);
              setFormError("");
            }}
            className="flex items-center gap-2 bg-primary hover:bg-primary/90 text-white px-4 py-2.5 rounded-xl text-[12px] font-mono uppercase tracking-wider transition-colors"
          >
            <Plus className="w-4 h-4" /> Add School Year
          </button>
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

      {loading ? (
        <div className="text-sm text-muted-foreground font-mono uppercase tracking-widest">
          Loading…
        </div>
      ) : years.length === 0 ? (
        <Card className="p-8 text-center">
          <CalendarDays className="mx-auto mb-3 h-6 w-6 text-muted-foreground" />
          <p className="text-sm font-semibold text-foreground">No school year yet</p>
          <p className="mx-auto mt-1.5 max-w-md text-sm text-muted-foreground">
            A school year holds the terms, a term holds the sections, and a section holds the class
            list an exam admits. Nothing below can be set up until one exists.
          </p>
        </Card>
      ) : (
        <>
          <h3 className="mb-3 text-sm font-semibold text-foreground">School Years</h3>
          <Card>
            <div className="divide-y divide-border">
              {years.map((year) => (
                <div key={year.id} className="flex flex-wrap items-center gap-3 px-6 py-3">
                  <button
                    onClick={() => setSelectedYearId(year.id)}
                    aria-pressed={year.id === selectedYearId}
                    className={`text-sm transition-colors ${
                      year.id === selectedYearId
                        ? "font-semibold text-foreground"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {year.label}
                  </button>
                  <span className="text-xs text-muted-foreground">
                    {year.starts_on} → {year.ends_on}
                  </span>
                  {year.is_current ? (
                    <span className="flex items-center gap-1 rounded-lg border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider text-emerald-800">
                      <Check className="h-3 w-3" /> Current
                    </span>
                  ) : (
                    <button
                      onClick={() => makeCurrent(year)}
                      className="rounded-lg bg-primary/10 px-2.5 py-1 text-[11px] font-mono uppercase tracking-wider text-primary transition-colors hover:bg-primary/20"
                    >
                      Make current
                    </button>
                  )}
                </div>
              ))}
            </div>
          </Card>

          <div className="mt-8 mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-foreground">
              Terms in {selectedYear?.label ?? "—"}
            </h3>
            <button
              onClick={() => {
                setTermForm({ ...EMPTY_TERM, sequence: terms.length + 1 });
                setFormError("");
              }}
              disabled={!selectedYearId}
              className="flex items-center gap-1.5 bg-primary hover:bg-primary/90 disabled:opacity-40 text-white px-3 py-1.5 rounded-lg text-[11px] font-mono uppercase tracking-wider transition-colors"
            >
              <Plus className="w-3.5 h-3.5" /> Add Term
            </button>
          </div>

          {terms.length === 0 ? (
            <Card className="p-6 text-sm text-muted-foreground">
              No terms in this year yet. Add one — a section belongs to a term, so this is what a
              class list is eventually attached to.
            </Card>
          ) : (
            <Card>
              <div className="divide-y divide-border">
                {terms.map((term) => (
                  <div key={term.id} className="flex flex-wrap items-center gap-3 px-6 py-3">
                    <span className="text-sm text-foreground">
                      <span className="text-muted-foreground font-mono text-xs mr-2">
                        #{term.sequence}
                      </span>
                      {term.name}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {term.starts_on} → {term.ends_on}
                    </span>
                    <StatusBadge status={term.status} />
                    <span className="flex-1" />
                    {term.status === "PLANNED" && (
                      <button
                        onClick={() => changeStatus(term, "ACTIVE")}
                        className="rounded-lg bg-primary/10 px-2.5 py-1 text-[11px] font-mono uppercase tracking-wider text-primary transition-colors hover:bg-primary/20"
                      >
                        Activate
                      </button>
                    )}
                    {term.status === "ACTIVE" && (
                      <button
                        onClick={() => setClosing(term)}
                        className="rounded-lg bg-primary/10 px-2.5 py-1 text-[11px] font-mono uppercase tracking-wider text-primary transition-colors hover:bg-primary/20"
                      >
                        Close
                      </button>
                    )}
                    {term.status === "CLOSED" && (
                      <button
                        onClick={() => changeStatus(term, "ACTIVE")}
                        className="rounded-lg bg-primary/10 px-2.5 py-1 text-[11px] font-mono uppercase tracking-wider text-primary transition-colors hover:bg-primary/20"
                      >
                        Reopen
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          )}

          {terms.length > 0 && (
            <p className="mt-3 max-w-2xl text-xs text-muted-foreground">
              Only one term runs at a time — activating another is refused rather than quietly
              ending the one someone is still teaching. Closing a term completes its class lists so
              they stop reading as current.
            </p>
          )}
        </>
      )}

      {yearForm && (
        <Modal title="Add School Year" onClose={() => setYearForm(null)}>
          <form onSubmit={submitYear}>
            {formError && (
              <div className="mb-4 rounded-xl bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-600">
                {formError}
              </div>
            )}
            <TextField
              label="Label"
              hint="However your school writes it — 2026-2027, AY 2026-27, SY 2026-2027. It is a label, not something the system computes on."
              required
              value={yearForm.label}
              onChange={(e) => setYearForm({ ...yearForm, label: e.target.value })}
              placeholder="2026-2027"
            />
            <TextField
              label="Starts On"
              type="date"
              required
              value={yearForm.starts_on}
              onChange={(e) => setYearForm({ ...yearForm, starts_on: e.target.value })}
            />
            <TextField
              label="Ends On"
              type="date"
              required
              value={yearForm.ends_on}
              onChange={(e) => setYearForm({ ...yearForm, ends_on: e.target.value })}
            />
            <CheckboxField
              label="Make this the current school year"
              checked={yearForm.make_current}
              onChange={(e) => setYearForm({ ...yearForm, make_current: e.target.checked })}
            />
            <button
              type="submit"
              disabled={submitting}
              className="w-full bg-primary hover:bg-primary/90 disabled:opacity-50 text-white py-2.5 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors"
            >
              {submitting ? "Saving…" : "Create School Year"}
            </button>
          </form>
        </Modal>
      )}

      {termForm && (
        <Modal title={`Add Term to ${selectedYear?.label ?? ""}`} onClose={() => setTermForm(null)}>
          <form onSubmit={submitTerm}>
            {formError && (
              <div className="mb-4 rounded-xl bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-600">
                {formError}
              </div>
            )}
            <TextField
              label="Name"
              required
              value={termForm.name}
              onChange={(e) => setTermForm({ ...termForm, name: e.target.value })}
              placeholder="1st Semester"
            />
            <TextField
              label="Sequence"
              type="number"
              min="1"
              max="12"
              required
              hint="Order within the year, stated rather than worked out from the dates — a summer term may overlap or abut the semesters around it."
              value={termForm.sequence}
              onChange={(e) => setTermForm({ ...termForm, sequence: e.target.value })}
            />
            <TextField
              label="Starts On"
              type="date"
              required
              value={termForm.starts_on}
              onChange={(e) => setTermForm({ ...termForm, starts_on: e.target.value })}
            />
            <TextField
              label="Ends On"
              type="date"
              required
              value={termForm.ends_on}
              onChange={(e) => setTermForm({ ...termForm, ends_on: e.target.value })}
            />
            <button
              type="submit"
              disabled={submitting}
              className="w-full bg-primary hover:bg-primary/90 disabled:opacity-50 text-white py-2.5 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors"
            >
              {submitting ? "Saving…" : "Create Term"}
            </button>
          </form>
        </Modal>
      )}

      {closing && (
        <ConfirmDialog
          title="Close Term"
          message={`Close "${closing.name}"? Everyone still enrolled in its sections is marked as having completed it, so those class lists stop reading as current. The term can be reopened afterwards, but that does not put the enrolments back to enrolled.`}
          onConfirm={confirmClose}
          onCancel={() => setClosing(null)}
        />
      )}
    </div>
  );
}
