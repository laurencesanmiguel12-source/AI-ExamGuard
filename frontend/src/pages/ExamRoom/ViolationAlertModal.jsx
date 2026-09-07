import { AlertTriangle } from "lucide-react";
import Modal from "../../components/Modal";

// What each flag means to the student, and what they can do about it. Written to inform, not to
// accuse: most of these fire on things that are often innocent (someone walking behind you, a
// notification stealing focus), the detector is not always right, and an instructor reviews the
// session afterwards either way. Telling a student mid-exam that they have been caught cheating
// would be both unpleasant and, some of the time, simply wrong.
const MESSAGES = {
  TAB_SWITCH: {
    title: "You left the exam tab",
    body: "Switching tabs or windows during the exam is recorded. Stay on this tab until you submit.",
  },
  FULLSCREEN_EXIT: {
    title: "You left full screen",
    body: "The exam is meant to run in full screen. Press the button below and it will return.",
    action: "fullscreen",
  },
  COPY_PASTE: {
    title: "Copy or paste detected",
    body: "Copying from or pasting into the exam is recorded. Type your answers directly.",
  },
  RIGHT_CLICK: {
    title: "Right-click detected",
    body: "The right-click menu is disabled during the exam and the attempt has been recorded.",
  },
  PHONE_DETECTED: {
    title: "Possible phone in view",
    body: "Your camera picked up something that looks like a phone. If a phone is visible, please move it out of frame. If this is a mistake, carry on — your instructor reviews every flag before it counts.",
  },
  MULTIPLE_PEOPLE: {
    title: "More than one person in view",
    body: "Your camera has picked up another person. Please make sure you are alone in frame for the rest of the exam.",
  },
  FACE_LOST: {
    title: "We can't see your face",
    body: "Your face has gone out of view of the camera. Please sit back in frame so verification can continue.",
  },
  IDENTITY_MISMATCH: {
    title: "We couldn't verify it's you",
    body: "The camera didn't match you to your enrolment photos. Face the camera directly, in good light. Your instructor will review this.",
  },
  PROLONGED_HEAD_DOWN: {
    title: "You've been looking down for a while",
    body: "Looking away from the screen for a long stretch is recorded. If you are reading scratch paper, that is fine — your instructor sees the context.",
  },
};

const FALLBACK = {
  title: "Something was flagged",
  body: "An event was recorded during your exam. Your instructor will review it.",
};

/**
 * Tells a student, at the moment it happens, that something has been flagged.
 *
 * Students previously had only a passive OK/ALERT strip they had to notice on their own, so the
 * first they knew of a flag was usually after the exam. Being told at the time is both fairer and
 * more useful: most of these are correctable in the moment - move the phone, sit back in frame,
 * return to full screen - and a student who does not know cannot correct anything.
 *
 * The exam clock keeps running while this is open, which is why it is a single dismiss and why
 * the caller applies a per-type cooldown rather than raising it on every detection poll.
 */
export default function ViolationAlertModal({ eventType, count, onDismiss }) {
  const message = MESSAGES[eventType] ?? FALLBACK;

  function dismiss() {
    if (message.action === "fullscreen" && !document.fullscreenElement) {
      // Re-entering full screen needs a user gesture; dismissing the alert is one, so the fix
      // happens on the same click rather than leaving the student to work it out.
      document.documentElement.requestFullscreen?.().catch(() => {});
    }
    onDismiss();
  }

  return (
    <Modal title={message.title} onClose={dismiss}>
      <div className="flex gap-3">
        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-700" aria-hidden="true" />
        <div className="min-w-0">
          <p className="text-sm text-foreground">{message.body}</p>
          {count > 1 && (
            <p className="mt-2 text-sm text-muted-foreground">
              This has now happened {count} times during this exam.
            </p>
          )}
          <p className="mt-3 text-xs text-muted-foreground">
            Your exam is still running and your answers are saved. The timer has not been paused.
          </p>
        </div>
      </div>

      <button
        onClick={dismiss}
        autoFocus
        className="mt-5 w-full rounded-xl bg-primary py-2.5 text-sm font-mono uppercase tracking-widest text-white transition-colors hover:bg-primary/90"
      >
        {message.action === "fullscreen" ? "Return to full screen" : "Continue exam"}
      </button>
    </Modal>
  );
}
