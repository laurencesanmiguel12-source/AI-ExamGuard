import { ScanFace } from "lucide-react";
import Modal from "./Modal";

// Shown once per browser session (not on every dashboard visit - sessionStorage, not
// localStorage, so a fresh login prompts again but re-navigating within the same session
// doesn't nag repeatedly) to a student with no enrolled face model. Dismissible, not a hard
// block - the real enforcement is server-side (ExamSessionService.start_exam rejects starting
// a proctored exam without an enrolled model or the skip_face_check accommodation), this is
// just surfacing that requirement immediately instead of only at the moment they try to start
// an exam.
export default function EnrollmentPromptModal({ onEnrollNow, onDismiss }) {
  return (
    <Modal title="Face Enrollment Needed" onClose={onDismiss}>
      <div className="flex flex-col items-center text-center">
        <div className="w-14 h-14 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center mb-4">
          <ScanFace className="w-7 h-7 text-primary" />
        </div>
        <p className="text-sm text-foreground/80 mb-5">
          Your account isn't enrolled for face verification yet. You'll need to complete a quick
          one-time enrollment before you can start any proctored exam.
        </p>
      </div>
      <div className="flex gap-3">
        <button
          onClick={onDismiss}
          className="flex-1 border border-border hover:border-foreground/20 text-muted-foreground hover:text-foreground py-2.5 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors"
        >
          Later
        </button>
        <button
          onClick={onEnrollNow}
          className="flex-1 bg-primary hover:bg-primary/90 text-white py-2.5 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors"
        >
          Enroll Now
        </button>
      </div>
    </Modal>
  );
}
