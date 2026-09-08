import { useState } from "react";
import { Shield, Camera, Monitor, Brain, AlertTriangle, Eye, ScanEye, CheckCircle, ArrowRight } from "lucide-react";
import Card from "../../components/ui/Card";

function SectionTag({ text }) {
  return (
    <div className="inline-flex items-center gap-2 mb-4">
      <div className="w-4 h-px bg-primary" />
      <span className="text-primary text-[11px] font-mono uppercase tracking-[0.2em]">{text}</span>
    </div>
  );
}

const EXAM_RULES = [
  {
    icon: Camera,
    color: "#1a4fa8",
    bg: "#eff6ff",
    border: "#bfdbfe",
    title: "Keep Your Face Visible",
    desc: "Your webcam must stay on throughout the exam. Face detection runs periodically in the background — losing your face from frame or poor lighting adds to your risk score.",
  },
  {
    icon: Shield,
    color: "#7c3aed",
    bg: "#f5f3ff",
    border: "#ddd6fe",
    title: "No Impersonation",
    desc: "Your identity is periodically checked against the face profile you enrolled beforehand. A mismatch is logged as a violation and raises your risk score. The system also checks for natural signs of a live person on camera — holding up a photo instead of your actual face may also be flagged.",
  },
  {
    icon: Monitor,
    color: "#ea580c",
    bg: "#fff7ed",
    border: "#fed7aa",
    title: "No Tab Switching",
    desc: "Leaving the exam tab, switching windows, or minimizing the browser is detected as you do it. Each tab-switch event is logged and adds to your risk score.",
  },
  {
    icon: Brain,
    color: "#c8192e",
    bg: "#fff1f2",
    border: "#fecdd3",
    title: "No AI or Search Tools",
    desc: "Visiting ChatGPT, Google Search, Bing, or similar tools in another tab is detected by the AI ExamGuard browser extension and logged as a violation.",
  },
  {
    icon: AlertTriangle,
    color: "#b45309",
    bg: "#fffbeb",
    border: "#fde68a",
    title: "Phone Usage Prohibited",
    desc: "Periodic webcam checks run object detection on your feed. Any mobile phone visible in frame is flagged and logged as a high-severity violation.",
  },
  {
    icon: Eye,
    color: "#059669",
    bg: "#f0fdf4",
    border: "#bbf7d0",
    title: "Browser Extension Required",
    desc: "This exam requires the AI ExamGuard Tab Monitor extension. It detects AI-tool/search-engine tab activity; exiting fullscreen and copy/paste/right-click are also detected separately.",
  },
  {
    icon: ScanEye,
    color: "#0d9488",
    bg: "#f0fdfa",
    border: "#99f6e4",
    title: "Prolonged Downward Gaze Monitored",
    desc: "If your head stays angled down for an extended period — longer than a normal glance while typing — it's flagged for instructor review, along with the question you were on at the time. This isn't eye-tracking — it's a coarse signal meant to catch phones held out of camera view, and it's always human-reviewed and appealable, not an automatic penalty.",
  },
];

// One statement rather than a checklist.
//
// The eight items this replaces were rendered as checkboxes with no checked/onChange binding at
// all - a student could tick none of them and still enter, and ticking every one changed nothing.
// In a consent screen that is worse than clutter: it looks like a gate, so it reads as though the
// student affirmed each point individually, when nothing was ever recorded. A single statement
// the student actually agrees to is both simpler to read and honest about what is being agreed.
const AGREEMENT = [
  "I have installed the AI ExamGuard browser extension, my webcam is on with my face clearly visible, and I am alone in a well-lit, quiet room with my phone switched off and out of camera range.",
  "I will stay on the exam tab for the whole exam, and will not use AI assistants, search engines, notes, or any other help.",
  "I understand my session is monitored by periodic camera and behaviour checks, and that leaving the tab, another person appearing, a phone coming into view, holding a photo up to the camera, or looking away for long stretches are all recorded, raise my risk score, and are reviewed by my instructor afterwards.",
];


export default function PreExamModal({ examTitle, onConfirm, onCancel }) {
  const [step, setStep] = useState("guide");

  return (
    <div className="flex h-screen items-center justify-center px-6 py-8">
      <Card className="w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
        <div className="flex items-center gap-3 px-6 py-4 border-b border-border bg-secondary/50 flex-shrink-0">
          <div className="w-9 h-9 rounded-xl bg-primary flex items-center justify-center flex-shrink-0">
            <Shield style={{ width: 18, height: 18 }} className="text-white" />
          </div>
          <div>
            <div className="text-foreground font-semibold text-sm leading-tight">
              AI ExamGuard — Exam Guidelines
            </div>
            <div className="text-muted-foreground text-[11px] font-mono mt-0.5 truncate max-w-xs">
              {examTitle}
            </div>
          </div>
        </div>

        <div className="flex border-b border-border flex-shrink-0">
          {[
            { id: "guide", label: "01 · Rules" },
            { id: "ready", label: "02 · Confirm" },
          ].map(({ id, label }) => (
            <button
              key={id}
              onClick={() => setStep(id)}
              className={`flex-1 py-3 text-[11px] font-mono uppercase tracking-wider transition-colors border-b-2 ${
                step === id
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="overflow-y-auto flex-1 px-6 py-5">
          {step === "guide" && (
            <div>
              <div className="mb-5">
                <SectionTag text="Proctoring Rules" />
                <p className="text-sm text-muted-foreground leading-relaxed">
                  AI ExamGuard monitors your session using periodic camera checks, biometric
                  verification, and behavioral signals. Violations are scored in real time and
                  visible to your instructor's live dashboard.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {EXAM_RULES.map(({ icon: Icon, color, bg, border, title, desc }) => (
                  <div
                    key={title}
                    className="flex gap-3 p-3.5 rounded-xl border"
                    style={{ background: bg, borderColor: border }}
                  >
                    <div
                      className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5"
                      style={{ background: `${color}18`, border: `1px solid ${color}30` }}
                    >
                      <Icon style={{ width: 15, height: 15, color }} />
                    </div>
                    <div>
                      <div className="text-[12px] font-semibold mb-1" style={{ color }}>{title}</div>
                      <p className="text-[11px] text-muted-foreground leading-relaxed">{desc}</p>
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-4 p-4 rounded-xl bg-red-50 border border-red-200">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
                  <p className="text-[12px] text-red-700 leading-relaxed">
                    <span className="font-semibold">Violation Impact: </span>
                    Any detected violation raises your composite risk score (0–100) in real time.
                    A score of <span className="font-semibold">75</span> or higher is flagged{" "}
                    <span className="font-semibold">CRITICAL</span> and appears immediately on your
                    instructor's live monitoring dashboard.
                  </p>
                </div>
              </div>

              <button
                onClick={() => setStep("ready")}
                className="mt-5 w-full flex items-center justify-center gap-2 bg-primary hover:bg-primary/90 text-white font-mono text-[12px] uppercase tracking-widest py-3 rounded-xl transition-colors"
              >
                Next: Confirm <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          {step === "ready" && (
            <div>
              <div className="mb-5">
                <SectionTag text="Before You Start" />
                <p className="text-sm text-muted-foreground leading-relaxed">
                  Read this through. Choosing to enter the exam room is your agreement to it. Your
                  browser extension and camera are checked for real straight afterwards, so make
                  sure you are set up before you continue.
                </p>
              </div>

              <div className="mb-5 rounded-xl border border-primary/25 bg-primary/5 p-4">
                {AGREEMENT.map((line, i) => (
                  <p
                    key={i}
                    className={`text-[12px] leading-relaxed text-foreground ${i > 0 ? "mt-3" : ""}`}
                  >
                    {line}
                  </p>
                ))}
              </div>

              <div className="flex gap-3">
                <button
                  onClick={onCancel}
                  className="flex-1 py-3 rounded-xl border border-border text-muted-foreground hover:text-foreground hover:border-foreground/20 font-mono text-[12px] uppercase tracking-widest transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={onConfirm}
                  className="flex-[1.6] flex items-center justify-center gap-2 py-3 rounded-xl bg-primary hover:bg-primary/90 text-white shadow-sm font-mono text-[12px] uppercase tracking-widest transition-all"
                >
                  <CheckCircle className="w-3.5 h-3.5" /> I agree — enter exam room
                </button>
              </div>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
