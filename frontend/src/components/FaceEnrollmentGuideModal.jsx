import { useState } from "react";
import { Sun, Glasses, Smile, Move3d, ShieldCheck } from "lucide-react";
import Modal from "./Modal";

const TIPS = [
  { icon: Sun, title: "Good, even lighting", body: "Face a light source (a window or lamp) - avoid strong backlight or deep shadows across your face." },
  { icon: Glasses, title: "Clear view of your face", body: "Remove glasses, masks, or anything covering your face for the capture." },
  { icon: Smile, title: "Neutral expression", body: "Look straight at the camera with a relaxed expression - no smiling, talking, or tilted head." },
  { icon: Move3d, title: "Vary the angle slightly", body: "Turn your head a little between captures (straight, slight left, slight right) for a more reliable model." },
];

// Gates the camera/capture UI on FaceEnrollment.jsx - useCamera isn't activated until this modal
// is dismissed via the consent checkbox, so the webcam isn't even turned on until the student has
// actually seen what's collected and agreed to it, not just informational after the fact.
export default function FaceEnrollmentGuideModal({ onContinue }) {
  const [consented, setConsented] = useState(false);

  return (
    <Modal title="Before You Enroll">
      <div className="space-y-3 mb-5">
        {TIPS.map(({ icon: Icon, title, body }) => (
          <div key={title} className="flex gap-3">
            <div className="w-9 h-9 rounded-lg bg-secondary border border-border flex items-center justify-center flex-shrink-0">
              <Icon className="w-4 h-4 text-primary" />
            </div>
            <div>
              <div className="text-sm font-medium text-foreground">{title}</div>
              <div className="text-xs text-muted-foreground leading-relaxed">{body}</div>
            </div>
          </div>
        ))}
      </div>

      <div className="rounded-xl bg-secondary border border-border p-4 mb-4">
        <div className="flex items-center gap-2 mb-2">
          <ShieldCheck className="w-4 h-4 text-primary flex-shrink-0" />
          <span className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest">
            Your Privacy
          </span>
        </div>
        <p className="text-xs text-foreground/80 leading-relaxed mb-2">
          We store only a derived mathematical recognition model built from your photos - never
          the raw photos themselves. This model is used only to verify your identity during
          proctored exams.
        </p>
        <a
          href="/privacy-policy"
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-primary underline"
        >
          Read the full Privacy Policy
        </a>
      </div>

      <label className="flex items-start gap-2.5 mb-5 cursor-pointer">
        <input
          type="checkbox"
          checked={consented}
          onChange={(e) => setConsented(e.target.checked)}
          className="mt-0.5 w-4 h-4 rounded border-border accent-primary flex-shrink-0"
        />
        <span className="text-xs text-foreground/80 leading-relaxed">
          I have read and agree to the Privacy Policy, and I consent to my facial photos being
          used to create a biometric recognition model for exam identity verification.
        </span>
      </label>

      <button
        onClick={onContinue}
        disabled={!consented}
        className="w-full bg-primary hover:bg-primary/90 disabled:opacity-40 text-white py-2.5 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors"
      >
        I Understand, Continue
      </button>
    </Modal>
  );
}
