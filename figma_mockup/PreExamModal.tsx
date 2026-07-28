import { useState } from "react";
import {
  Shield, Camera, Monitor, Brain, AlertTriangle, Eye,
  X, ArrowRight, Download, CheckCircle,
} from "lucide-react";

// ─── Shared sub-components (self-contained within this file) ─────────────────

function SectionTag({ text }: { text: string }) {
  return (
    <div className="inline-flex items-center gap-2 mb-4">
      <div className="w-4 h-px bg-primary" />
      <span className="text-primary text-[11px] font-mono uppercase tracking-[0.2em]">{text}</span>
    </div>
  );
}

// ─── Rule definitions ─────────────────────────────────────────────────────────

const EXAM_RULES = [
  {
    icon: Camera,
    color: "#1a4fa8",
    bg: "#eff6ff",
    border: "#bfdbfe",
    title: "Keep Your Face Visible",
    desc: "Your webcam must be active throughout the exam. Ensure your face is clearly visible and well-lit at all times. Face loss or obstruction will immediately raise your risk score.",
  },
  {
    icon: Shield,
    color: "#7c3aed",
    bg: "#f5f3ff",
    border: "#ddd6fe",
    title: "No Impersonation",
    desc: "AI ExamGuard uses FaceNet biometric verification. Your identity is matched against your enrolled face profile before and during the exam. Any mismatch triggers an alert.",
  },
  {
    icon: Monitor,
    color: "#ea580c",
    bg: "#fff7ed",
    border: "#fed7aa",
    title: "No Tab Switching",
    desc: "Leaving the exam tab, switching windows, or minimizing the browser is detected in real time. Each tab-switch event is logged and adds to your risk score.",
  },
  {
    icon: Brain,
    color: "#c8192e",
    bg: "#fff1f2",
    border: "#fecdd3",
    title: "No AI or Search Tools",
    desc: "Using ChatGPT, Google Search, Bing, or any AI-powered tool during the exam is prohibited. The browser extension detects clipboard activity and unauthorized browsing.",
  },
  {
    icon: AlertTriangle,
    color: "#b45309",
    bg: "#fffbeb",
    border: "#fde68a",
    title: "Phone Usage Prohibited",
    desc: "YOLOv8 object detection monitors your webcam feed. Any mobile phone visible in frame is flagged immediately and classified as a high-severity violation.",
  },
  {
    icon: Eye,
    color: "#059669",
    bg: "#f0fdf4",
    border: "#bbf7d0",
    title: "Browser Extension Required",
    desc: "Install the AI ExamGuard browser extension before starting. It enforces fullscreen lockdown, blocks copy-paste, and monitors for unauthorized tab activity.",
  },
];

const CHECKLIST_ITEMS = [
  "I have installed the AI ExamGuard browser extension.",
  "My webcam is active and my face is clearly visible.",
  "I am in a well-lit, quiet environment.",
  "My phone is turned off or placed out of camera range.",
  "I will not switch tabs or use any AI / search tools.",
  "I understand that violations raise my risk score and will be reviewed by my instructor.",
];

const EXTENSION_STEPS = [
  {
    n: "1",
    title: "Download the Extension",
    desc: "Click the button below to open the Chrome Web Store and install AI ExamGuard Proctor.",
    action: true,
  },
  {
    n: "2",
    title: "Pin to Toolbar",
    desc: "After installation, click the puzzle icon in Chrome and pin AI ExamGuard so it's always visible.",
  },
  {
    n: "3",
    title: "Grant Permissions",
    desc: "Allow camera, tab monitoring, and fullscreen permissions when prompted by the extension.",
  },
  {
    n: "4",
    title: "Verify & Continue",
    desc: 'Click "Extension Installed" below to confirm. The system will verify connectivity before your exam begins.',
  },
];

// ─── Props ────────────────────────────────────────────────────────────────────

interface PreExamModalProps {
  examTitle: string;
  onConfirm: () => void;
  onCancel: () => void;
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function PreExamModal({ examTitle, onConfirm, onCancel }: PreExamModalProps) {
  const [step, setStep] = useState<"guide" | "extension" | "ready">("guide");
  const [checked, setChecked] = useState(false);
  const [extInstalled, setExtInstalled] = useState(false);

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4"
      style={{ background: "rgba(15,23,42,0.55)", backdropFilter: "blur(6px)" }}
    >
      <div
        className="bg-card border border-border rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col"
        style={{ animation: "modalIn 0.2s ease" }}
      >
        <style>{`@keyframes modalIn{from{opacity:0;transform:scale(0.97) translateY(8px)}to{opacity:1;transform:none}}`}</style>

        {/* ── Header ── */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-secondary/50 flex-shrink-0">
          <div className="flex items-center gap-3">
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
          <button
            onClick={onCancel}
            className="text-muted-foreground hover:text-foreground transition-colors p-1.5 rounded-lg hover:bg-black/5"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* ── Step tabs ── */}
        <div className="flex border-b border-border flex-shrink-0">
          {[
            { id: "guide",     label: "01 · Rules"    },
            { id: "extension", label: "02 · Extension" },
            { id: "ready",     label: "03 · Confirm"   },
          ].map(({ id, label }) => (
            <button
              key={id}
              onClick={() => setStep(id as typeof step)}
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

        {/* ── Body ── */}
        <div className="overflow-y-auto flex-1 px-6 py-5">

          {/* Step 1 — Rules */}
          {step === "guide" && (
            <div>
              <div className="mb-5">
                <SectionTag text="Proctoring Rules" />
                <p className="text-sm text-muted-foreground leading-relaxed">
                  AI ExamGuard actively monitors your session using computer vision, biometric
                  verification, and behavioral analysis. Violations are scored in real time and
                  reviewed by your instructor or proctor.
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
                    Any detected violation automatically raises your composite risk score (0–100).
                    Sessions with a score above <span className="font-semibold">70</span> trigger
                    screenshot evidence collection. Scores above{" "}
                    <span className="font-semibold">90</span> send an immediate email alert to your
                    instructor or proctor for manual review.
                  </p>
                </div>
              </div>

              <button
                onClick={() => setStep("extension")}
                className="mt-5 w-full flex items-center justify-center gap-2 bg-primary hover:bg-primary/90 text-white font-mono text-[12px] uppercase tracking-widest py-3 rounded-xl transition-colors"
              >
                Next: Install Extension <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          {/* Step 2 — Extension */}
          {step === "extension" && (
            <div>
              <div className="mb-5">
                <SectionTag text="Browser Extension" />
                <p className="text-sm text-muted-foreground leading-relaxed">
                  The AI ExamGuard extension is required before you can start. It enforces fullscreen
                  mode, blocks clipboard access, and prevents navigation to unauthorized tabs or AI
                  tools during the exam.
                </p>
              </div>

              <div className="flex flex-col gap-3">
                {EXTENSION_STEPS.map(({ n, title, desc, action }) => (
                  <div key={n} className="flex gap-4 p-4 rounded-xl border border-border bg-secondary/40">
                    <div className="w-7 h-7 rounded-full bg-primary text-white flex items-center justify-center text-[11px] font-mono font-bold flex-shrink-0">
                      {n}
                    </div>
                    <div className="flex-1">
                      <div className="text-sm font-medium text-foreground mb-1">{title}</div>
                      <p className="text-[11px] text-muted-foreground leading-relaxed">{desc}</p>
                      {action && (
                        <button className="mt-2 inline-flex items-center gap-2 border border-blue-200 bg-blue-50 hover:bg-blue-100 text-blue-700 text-[11px] font-mono uppercase tracking-wider px-3 py-1.5 rounded-lg transition-colors">
                          <Download className="w-3 h-3" /> Install from Chrome Store
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              <button
                onClick={() => { setExtInstalled(true); setStep("ready"); }}
                className={`mt-5 w-full flex items-center justify-center gap-2 font-mono text-[12px] uppercase tracking-widest py-3 rounded-xl transition-colors ${
                  extInstalled
                    ? "bg-emerald-600 hover:bg-emerald-700 text-white"
                    : "bg-primary hover:bg-primary/90 text-white"
                }`}
              >
                <CheckCircle className="w-3.5 h-3.5" /> Extension Installed — Continue
              </button>
            </div>
          )}

          {/* Step 3 — Confirm */}
          {step === "ready" && (
            <div>
              <div className="mb-5">
                <SectionTag text="Pre-Exam Checklist" />
                <p className="text-sm text-muted-foreground leading-relaxed">
                  Complete the checklist below and confirm that you have read and understood all
                  proctoring rules before entering the exam room.
                </p>
              </div>

              <div className="flex flex-col gap-2.5 mb-5">
                {CHECKLIST_ITEMS.map((item, i) => (
                  <label
                    key={i}
                    className="flex items-start gap-3 p-3.5 rounded-xl border border-border bg-secondary/30 cursor-pointer hover:bg-secondary/60 transition-colors group"
                  >
                    <input
                      type="checkbox"
                      className="mt-0.5 accent-[#c8192e] w-4 h-4 flex-shrink-0 cursor-pointer"
                    />
                    <span className="text-[12px] text-muted-foreground group-hover:text-foreground transition-colors leading-relaxed">
                      {item}
                    </span>
                  </label>
                ))}
              </div>

              <label className="flex items-start gap-3 p-4 rounded-xl border border-primary/25 bg-primary/5 cursor-pointer mb-5">
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={(e) => setChecked(e.target.checked)}
                  className="mt-0.5 accent-[#c8192e] w-4 h-4 flex-shrink-0 cursor-pointer"
                />
                <span className="text-[12px] text-foreground leading-relaxed font-medium">
                  I have read and understood all AI ExamGuard proctoring rules. I agree that any
                  violation will be recorded, evidence will be collected, and my instructor will be
                  notified automatically.
                </span>
              </label>

              <div className="flex gap-3">
                <button
                  onClick={onCancel}
                  className="flex-1 py-3 rounded-xl border border-border text-muted-foreground hover:text-foreground hover:border-foreground/20 font-mono text-[12px] uppercase tracking-widest transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={onConfirm}
                  disabled={!checked}
                  className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-xl font-mono text-[12px] uppercase tracking-widest transition-all ${
                    checked
                      ? "bg-primary hover:bg-primary/90 text-white shadow-sm"
                      : "bg-secondary text-muted-foreground cursor-not-allowed"
                  }`}
                >
                  <Shield className="w-3.5 h-3.5" /> Enter Exam Room
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
