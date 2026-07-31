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
    desc: "Your identity is periodically checked against the face profile you enrolled beforehand. A mismatch is logged as a violation and raises your risk score.",
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
    desc: "If your head stays angled down for an extended period — longer than a normal glance while typing — it's flagged for instructor review. This isn't eye-tracking — it's a coarse signal meant to catch phones held out of camera view, and it's always human-reviewed and appealable, not an automatic penalty.",
  },
];

const CHECKLIST_ITEMS = [
  "I have installed the AI ExamGuard browser extension.",
  "My webcam is active and my face is clearly visible.",
  "I am in a well-lit, quiet environment.",
  "My phone is turned off or placed out of camera range.",
  "I will not switch tabs or use any AI / search tools.",
  "I understand that keeping my head angled down for an extended period may be flagged for review.",
  "I understand that violations raise my risk score and will be reviewed by my instructor.",
];

export default function PreExamModal({ examTitle, onConfirm, onCancel }) {
  const [step, setStep] = useState("guide");
  const [checked, setChecked] = useState(false);

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
                <SectionTag text="Pre-Exam Checklist" />
                <p className="text-sm text-muted-foreground leading-relaxed">
                  Complete the checklist below and confirm that you have read and understood all
                  proctoring rules before entering the exam room. Your browser extension and camera
                  will be checked for real right after this.
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
                  violation will be recorded and my instructor can review my session on the live
                  risk dashboard.
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
                  <CheckCircle className="w-3.5 h-3.5" /> Enter Exam Room
                </button>
              </div>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
