import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle, XCircle } from "lucide-react";
import { fileAppeal, getEvidenceBlobUrl, reviewAppeal } from "../api/violations";

const EVENT_LABELS = {
  TAB_SWITCH: "Tab Switch",
  FULLSCREEN_EXIT: "Fullscreen Exit",
  COPY_PASTE: "Copy/Paste",
  RIGHT_CLICK: "Right Click",
  FACE_LOST: "Face Lost",
  IDENTITY_MISMATCH: "Identity Mismatch",
  PHONE_DETECTED: "Phone Detected",
  MULTIPLE_PEOPLE: "Multiple People",
  AI_TOOL_DETECTED: "AI Tool Detected",
  SEARCH_ENGINE_DETECTED: "Search Engine Detected",
  PROLONGED_HEAD_DOWN: "Prolonged Downward Gaze",
};

const STATUS_STYLE = {
  PENDING: "text-orange-700 border-orange-200 bg-orange-50",
  UPHELD: "text-red-700 border-red-200 bg-red-50",
  OVERTURNED: "text-emerald-700 border-emerald-200 bg-emerald-50",
};

function EvidenceThumbnail({ violationId }) {
  const [url, setUrl] = useState(null);

  useEffect(() => {
    let objectUrl;
    let cancelled = false;
    getEvidenceBlobUrl(violationId).then((u) => {
      if (cancelled) return;
      objectUrl = u;
      setUrl(u);
    });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [violationId]);

  if (!url) {
    return <div className="w-20 h-20 rounded-lg bg-secondary border border-border flex-shrink-0" />;
  }

  return (
    <img
      src={url}
      alt="Evidence frame"
      className="w-20 h-20 rounded-lg border border-border object-cover flex-shrink-0"
    />
  );
}

function AppealForm({ onSubmit }) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="text-[11px] font-mono uppercase tracking-wider text-primary hover:underline"
      >
        Contest this violation
      </button>
    );
  }

  return (
    <div className="mt-2 space-y-2">
      <textarea
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        placeholder="Explain why you believe this violation was flagged in error…"
        rows={2}
        className="w-full text-sm rounded-lg border border-border bg-background px-3 py-2 focus:outline-none focus:ring-1 focus:ring-primary"
      />
      <div className="flex gap-2">
        <button
          disabled={!reason.trim() || submitting}
          onClick={async () => {
            setSubmitting(true);
            try {
              await onSubmit(reason.trim());
            } finally {
              setSubmitting(false);
            }
          }}
          className="px-3 py-1.5 bg-primary hover:bg-primary/90 disabled:opacity-50 text-white rounded-lg text-[11px] font-mono uppercase tracking-wider transition-colors"
        >
          {submitting ? "Submitting…" : "Submit Appeal"}
        </button>
        <button
          onClick={() => setOpen(false)}
          className="px-3 py-1.5 border border-border text-muted-foreground hover:text-foreground rounded-lg text-[11px] font-mono uppercase tracking-wider transition-colors"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

function ReviewForm({ onSubmit }) {
  const [response, setResponse] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(status) {
    if (!response.trim()) return;
    setSubmitting(true);
    try {
      await onSubmit(status, response.trim());
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mt-2 space-y-2">
      <textarea
        value={response}
        onChange={(e) => setResponse(e.target.value)}
        placeholder="Explain your decision…"
        rows={2}
        className="w-full text-sm rounded-lg border border-border bg-background px-3 py-2 focus:outline-none focus:ring-1 focus:ring-primary"
      />
      <div className="flex gap-2">
        <button
          disabled={!response.trim() || submitting}
          onClick={() => submit("OVERTURNED")}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg text-[11px] font-mono uppercase tracking-wider transition-colors"
        >
          <CheckCircle className="w-3 h-3" /> Overturn
        </button>
        <button
          disabled={!response.trim() || submitting}
          onClick={() => submit("UPHELD")}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white rounded-lg text-[11px] font-mono uppercase tracking-wider transition-colors"
        >
          <XCircle className="w-3 h-3" /> Uphold
        </button>
      </div>
    </div>
  );
}

// mode="appeal" (student, on their own submitted session) lets the student contest a violation
// that has no appeal yet. mode="review" (instructor/admin) lets them decide a PENDING appeal.
// Neither mode lets the viewer edit a violation that's already been decided - shown read-only.
export default function ViolationsPanel({ violations, mode, onAppealed, onReviewed }) {
  if (violations.length === 0) {
    return <p className="text-sm text-muted-foreground">No proctoring violations logged for this session.</p>;
  }

  return (
    <div className="space-y-3">
      {violations.map((v) => (
        <div key={v.id} className="flex gap-3 p-3.5 rounded-xl border border-border bg-secondary/30">
          {v.has_evidence && <EvidenceThumbnail violationId={v.id} />}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <AlertTriangle className="w-3.5 h-3.5 text-orange-500 flex-shrink-0" />
              <span className="text-sm font-medium text-foreground">
                {EVENT_LABELS[v.event_type] ?? v.event_type}
              </span>
              {v.detail && <span className="text-[11px] font-mono text-muted-foreground">· {v.detail}</span>}
              <span className="text-[10px] font-mono text-muted-foreground ml-auto">
                {new Date(v.created_at).toLocaleString()}
              </span>
            </div>

            {v.appeal_status && (
              <div className="mt-1.5 space-y-1">
                <span
                  className={`inline-block text-[10px] font-mono px-2 py-0.5 rounded border uppercase tracking-wider ${STATUS_STYLE[v.appeal_status]}`}
                >
                  Appeal {v.appeal_status}
                </span>
                <p className="text-[12px] text-muted-foreground">
                  <span className="font-medium text-foreground/80">Reason: </span>
                  {v.appeal_reason}
                </p>
                {v.appeal_response && (
                  <p className="text-[12px] text-muted-foreground">
                    <span className="font-medium text-foreground/80">Response: </span>
                    {v.appeal_response}
                  </p>
                )}
              </div>
            )}

            {mode === "appeal" && !v.appeal_status && (
              <AppealForm onSubmit={(reason) => fileAppeal(v.id, reason).then(onAppealed)} />
            )}

            {mode === "review" && v.appeal_status === "PENDING" && (
              <ReviewForm
                onSubmit={(status, response) => reviewAppeal(v.id, status, response).then(onReviewed)}
              />
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
