import { useState } from "react";
import Modal from "./Modal";

// Every list page (Courses/Subjects/Students/Instructors/Exams) routes its delete confirmation
// through here - catching a failed onConfirm (e.g. a backend FK-constraint 400) in this one place
// means every caller gets a visible error + a re-enabled dialog instead of a silently-stuck
// confirm button, without having to remember to wrap their own confirmDelete in try/catch.
export default function ConfirmDialog({ title = "Confirm", message, onConfirm, onCancel }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function handleConfirm() {
    setBusy(true);
    setError("");
    try {
      await onConfirm();
    } catch {
      setError("That didn't work. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal title={title} onClose={onCancel}>
      <p className="text-sm text-foreground/80 mb-5">{message}</p>
      {error && (
        <div className="mb-4 rounded-xl bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-600">{error}</div>
      )}
      <div className="flex gap-3">
        <button
          onClick={onCancel}
          disabled={busy}
          className="flex-1 border border-border hover:border-foreground/20 disabled:opacity-50 text-muted-foreground hover:text-foreground py-2.5 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors"
        >
          Cancel
        </button>
        <button
          onClick={handleConfirm}
          disabled={busy}
          className="flex-1 bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white py-2.5 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors"
        >
          {busy ? "Deleting…" : "Delete"}
        </button>
      </div>
    </Modal>
  );
}
