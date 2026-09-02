import { useEffect, useState } from "react";
import { Building2, Check, X, Clock } from "lucide-react";
import { getSchoolsForReview, reviewSchool } from "../../api/schools";
import SectionTag from "../../components/ui/SectionTag";
import Card from "../../components/ui/Card";
import Modal from "../../components/Modal";
import { TextField } from "../../components/ui/FormField";

const STATUS_STYLES = {
  pending: "bg-amber-50 text-amber-700 border-amber-200",
  approved: "bg-emerald-50 text-emerald-700 border-emerald-200",
  rejected: "bg-red-50 text-red-700 border-red-200",
};

function StatusBadge({ status }) {
  return (
    <span
      className={`px-2 py-0.5 rounded-lg border text-[11px] font-mono uppercase tracking-wider ${
        STATUS_STYLES[status] ?? "bg-secondary text-muted-foreground border-border"
      }`}
    >
      {status}
    </span>
  );
}

export default function SchoolApprovals() {
  const [schools, setSchools] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  // { school, decision } - the note is optional on approve, and the main reason to have this
  // dialog at all on reject, since the applicant is shown it at their login screen.
  const [deciding, setDeciding] = useState(null);
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function refresh() {
    setLoading(true);
    getSchoolsForReview()
      .then(setSchools)
      .catch(() => setError("Couldn't load schools."))
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  async function submitDecision() {
    setSubmitting(true);
    setError("");
    try {
      await reviewSchool(deciding.school.id, {
        status: deciding.decision,
        review_note: note.trim() || null,
      });
      setDeciding(null);
      setNote("");
      refresh();
    } catch (err) {
      setError(err.response?.data?.detail ?? "Couldn't save that decision.");
    } finally {
      setSubmitting(false);
    }
  }

  const pending = schools.filter((s) => s.status === "pending");
  const reviewed = schools.filter((s) => s.status !== "pending");

  return (
    <div>
      <div className="mb-8">
        <SectionTag text="Platform Administration" />
        <h2 className="font-display font-black text-foreground text-4xl">School Approvals</h2>
        <p className="text-muted-foreground text-sm mt-1">
          Self-service school registrations wait here until you approve them. Until then, nobody at
          that school can sign in.
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-xl bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-600">
          {error}
        </div>
      )}

      <Card className="mb-6">
        <div className="px-6 py-4 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-amber-600" />
            <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest">
              Awaiting review
            </div>
          </div>
          <span className="font-mono text-xs text-foreground/70">{pending.length} pending</span>
        </div>

        <div className="divide-y divide-border">
          {loading && <div className="px-6 py-6 text-sm text-muted-foreground">Loading…</div>}
          {!loading && pending.length === 0 && (
            <div className="px-6 py-6 text-sm text-muted-foreground">
              Nothing waiting — new school registrations will appear here.
            </div>
          )}
          {pending.map((school) => (
            <div key={school.id} className="px-6 py-4 flex items-center gap-4">
              <div className="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center shrink-0">
                <Building2 className="w-4 h-4 text-primary" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm text-foreground truncate">{school.name}</div>
                <div className="font-mono text-[11px] text-muted-foreground">
                  {school.code} · /{school.slug}/login
                </div>
              </div>
              <button
                onClick={() => {
                  setNote("");
                  setDeciding({ school, decision: "approved" });
                }}
                className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-2 rounded-xl text-[12px] font-mono uppercase tracking-wider transition-colors"
              >
                <Check className="w-3.5 h-3.5" /> Approve
              </button>
              <button
                onClick={() => {
                  setNote("");
                  setDeciding({ school, decision: "rejected" });
                }}
                className="flex items-center gap-1.5 border border-border hover:bg-secondary text-foreground px-3 py-2 rounded-xl text-[12px] font-mono uppercase tracking-wider transition-colors"
              >
                <X className="w-3.5 h-3.5" /> Reject
              </button>
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <div className="px-6 py-4 border-b border-border">
          <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest">
            All schools
          </div>
        </div>
        <div className="divide-y divide-border">
          {reviewed.map((school) => (
            <div key={school.id} className="px-6 py-3 flex items-center gap-4">
              <div className="flex-1 min-w-0">
                <div className="text-sm text-foreground truncate">{school.name}</div>
                <div className="font-mono text-[11px] text-muted-foreground">
                  {school.code} · /{school.slug}/login
                  {school.review_note ? ` · ${school.review_note}` : ""}
                </div>
              </div>
              <StatusBadge status={school.status} />
            </div>
          ))}
          {!loading && reviewed.length === 0 && (
            <div className="px-6 py-6 text-sm text-muted-foreground">No schools yet.</div>
          )}
        </div>
      </Card>

      {deciding && (
        <Modal
          title={
            deciding.decision === "approved"
              ? `Approve ${deciding.school.name}?`
              : `Reject ${deciding.school.name}?`
          }
          onClose={() => setDeciding(null)}
        >
          <p className="text-sm text-muted-foreground mb-4">
            {deciding.decision === "approved"
              ? "Their admin account starts working immediately — they sign in with the credentials they registered with."
              : "They'll see this reason on their login page, so make it something they can act on."}
          </p>
          <TextField
            label={deciding.decision === "approved" ? "Note (optional)" : "Reason"}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder={
              deciding.decision === "approved"
                ? "Verified by phone"
                : "Couldn't verify this institution"
            }
          />
          <button
            onClick={submitDecision}
            disabled={submitting}
            className={`w-full text-white py-2.5 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors disabled:opacity-50 ${
              deciding.decision === "approved"
                ? "bg-emerald-600 hover:bg-emerald-700"
                : "bg-red-600 hover:bg-red-700"
            }`}
          >
            {submitting
              ? "Saving…"
              : deciding.decision === "approved"
              ? "Approve school"
              : "Reject school"}
          </button>
        </Modal>
      )}
    </div>
  );
}
