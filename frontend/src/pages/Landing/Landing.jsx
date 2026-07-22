import { useNavigate } from "react-router-dom";
import {
  Eye, GraduationCap, Users, Settings, Lock, ClipboardList,
  BarChart3, FileText, Database, Wifi,
} from "lucide-react";
import PublicTopbar from "../../components/PublicTopbar";
import Card from "../../components/ui/Card";
import SectionTag from "../../components/ui/SectionTag";

const PHASES = [
  { n: "01", title: "Planning & Design", desc: "Functional/non-functional requirements, ERD, use cases, UI mockups, sprint backlog." },
  { n: "02", title: "Project Setup", desc: "FastAPI backend, React frontend, PostgreSQL schema with 18 tables." },
  { n: "03", title: "Authentication", desc: "JWT-secured registration & login with Admin, Instructor, and Student roles." },
  { n: "04", title: "Student Management", desc: "Admin CRUD, CSV import, instructor views, student profile updates." },
  { n: "05", title: "Face Enrollment", desc: "Webcam capture of 20 images → FaceNet encoding → secure biometric profile." },
  { n: "06", title: "Exam Module", desc: "Create/publish exams with MCQ, True/False, and Identification question types." },
  { n: "07", title: "Face Verification", desc: "Pre-exam identity match: live encoding vs. stored profile before session start." },
  { n: "08", title: "Live AI Monitoring", desc: "Frame-by-frame: FaceNet + YOLOv8 + browser JS events feeding the risk engine." },
  { n: "09", title: "LSTM Prediction", desc: "30-second feature window fed into LSTM → cheating probability score." },
  { n: "10", title: "Risk Engine", desc: "Weighted formula across all AI modules → 0–100 composite live risk score." },
  { n: "11", title: "Evidence Collection", desc: "Auto screenshot + timestamp + reason saved when risk ≥ 70." },
  { n: "12", title: "Email Notifications", desc: "Instructor alert email with student details, screenshot, and risk reason." },
  { n: "13", title: "Instructor Dashboard", desc: "Real-time WebSocket feed of all live session risk scores and alerts." },
  { n: "14", title: "Report Generator", desc: "Post-exam PDF: risk timeline, violations, screenshots, recommendation." },
  { n: "15", title: "Analytics Dashboard", desc: "Charts: avg risk, top violations, detection rates, exam scores by course." },
];

const MODULES = [
  { icon: GraduationCap, title: "Student Module", color: "#1a4fa8" },
  { icon: Users, title: "Instructor Module", color: "#059669" },
  { icon: Settings, title: "Administrator Module", color: "#7c3aed" },
  { icon: Lock, title: "Authentication Module", color: "#c8192e" },
  { icon: ClipboardList, title: "Exam Module", color: "#ea580c" },
  { icon: Eye, title: "AI Monitoring Module", color: "#c8192e" },
  { icon: BarChart3, title: "Dashboard Module", color: "#1a4fa8" },
  { icon: FileText, title: "Reports Module", color: "#059669" },
];

const TECH_STACK = [
  { cat: "Backend", items: ["FastAPI", "Python 3.11", "JWT Auth", "PostgreSQL"] },
  { cat: "AI / CV", items: ["YOLOv8", "FaceNet", "face_recognition", "OpenCV"] },
  { cat: "ML", items: ["LSTM (Keras)", "Scikit-learn", "NumPy", "Pandas"] },
  { cat: "Frontend", items: ["React", "Recharts", "WebSocket", "HTML/CSS/JS"] },
];

const DB_TABLES = [
  "users", "students", "instructors", "courses", "subjects",
  "exams", "questions", "choices", "student_answers",
  "exam_sessions", "face_profiles", "monitoring_events",
  "risk_scores", "screenshots", "notifications", "reports",
];

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-background">
      <PublicTopbar />

      <section className="relative min-h-screen flex items-center pt-14 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-white via-blue-50/40 to-red-50/20" />
        <div
          className="absolute inset-0 opacity-[0.04]"
          style={{
            backgroundImage:
              "linear-gradient(rgba(0,0,0,1) 1px,transparent 1px),linear-gradient(90deg,rgba(0,0,0,1) 1px,transparent 1px)",
            backgroundSize: "48px 48px",
          }}
        />
        <div
          className="absolute top-1/3 right-0 w-[600px] h-[600px] rounded-full opacity-[0.07]"
          style={{ background: "radial-gradient(circle, #c8192e 0%, transparent 70%)" }}
        />
        <div
          className="absolute bottom-0 left-0 w-[400px] h-[400px] rounded-full opacity-[0.05]"
          style={{ background: "radial-gradient(circle, #1a4fa8 0%, transparent 70%)" }}
        />

        <div className="relative max-w-screen-xl mx-auto px-6 py-24 grid grid-cols-1 lg:grid-cols-5 gap-16 items-center">
          <div className="lg:col-span-3">
            <div className="inline-flex items-center gap-2 bg-primary/8 border border-primary/20 rounded-full px-4 py-1.5 mb-8">
              <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
              <span className="text-primary text-[11px] font-mono uppercase tracking-[0.2em]">
                BSCS · Arellano University · 2025
              </span>
            </div>

            <h1
              className="font-display font-black text-foreground leading-[0.92] tracking-tight mb-6"
              style={{ fontSize: "clamp(3.5rem,8vw,6.5rem)" }}
            >
              AI<br />
              <span className="text-primary">EXAM</span><br />
              GUARD
            </h1>

            <p className="text-muted-foreground text-sm font-mono uppercase tracking-[0.15em] mb-4">
              AI-Driven Online Academic Integrity &amp; Computer Vision-Based Proctoring
            </p>
            <p className="text-foreground/70 text-base leading-relaxed max-w-lg mb-10">
              A web-based multi-modal automated proctoring system featuring real-time YOLOv8 object
              detection, FaceNet biometric verification, LSTM behavioral prediction, and a live
              0–100 risk classification dashboard for Philippine higher education.
            </p>

            <div className="flex flex-wrap gap-3 mb-14">
              <button
                onClick={() => navigate("/login")}
                className="inline-flex items-center gap-2 border border-border hover:border-foreground/20 hover:bg-black/[0.03] text-foreground/70 hover:text-foreground px-5 py-2.5 rounded-xl text-[12px] font-mono uppercase tracking-wider transition-all"
              >
                <Lock className="w-3.5 h-3.5" /> Sign In
              </button>
            </div>

            <div className="grid grid-cols-3 gap-6 pt-6 border-t border-border">
              {[
                { val: "96.4%", sub: "Detection Accuracy" },
                { val: "30 FPS", sub: "Processing Speed" },
                { val: "15", sub: "Dev Phases" },
              ].map(({ val, sub }) => (
                <div key={sub}>
                  <div className="font-display text-4xl font-black text-foreground">{val}</div>
                  <div className="text-muted-foreground text-[11px] font-mono uppercase tracking-widest mt-1">
                    {sub}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="lg:col-span-2 space-y-3">
            <Card className="overflow-hidden">
              <div className="flex items-center gap-2 px-4 py-2.5 border-b border-border bg-secondary">
                <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest">
                  Live Session · AU-2025-003 · Ana Reyes
                </span>
                <div className="ml-auto flex items-center gap-1">
                  <Wifi className="w-3 h-3 text-emerald-500" />
                  <span className="text-[10px] font-mono text-emerald-600">30fps</span>
                </div>
              </div>
              <div className="relative aspect-video bg-secondary overflow-hidden">
                <img
                  src="https://images.unsplash.com/photo-1434030216411-0b793f4b4173?w=480&h=270&fit=crop&auto=format"
                  alt="Student taking exam"
                  className="w-full h-full object-cover opacity-60"
                />
                <div className="absolute inset-0 flex items-center justify-center">
                  <div
                    className="relative w-24 h-32 border-2 border-emerald-500"
                    style={{ boxShadow: "0 0 20px rgba(16,185,129,0.4)" }}
                  >
                    {[
                      ["top-0 left-0", "border-t-2 border-l-2"],
                      ["top-0 right-0", "border-t-2 border-r-2"],
                      ["bottom-0 left-0", "border-b-2 border-l-2"],
                      ["bottom-0 right-0", "border-b-2 border-r-2"],
                    ].map(([pos, cls], i) => (
                      <div key={i} className={`absolute w-3 h-3 ${pos} ${cls} border-emerald-500`} />
                    ))}
                    <div className="absolute -top-6 left-0 right-0 text-center">
                      <span className="bg-emerald-50 border border-emerald-200 text-emerald-700 text-[9px] font-mono px-2 py-0.5 rounded-full">
                        VERIFIED ✓
                      </span>
                    </div>
                  </div>
                </div>
                <div className="absolute top-3 right-3 space-y-1.5">
                  {["YOLO", "FACE", "LSTM"].map((label) => (
                    <div key={label} className="flex items-center gap-1.5 bg-white/80 backdrop-blur px-2 py-1 rounded shadow-sm">
                      <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                      <span className="text-[9px] font-mono text-foreground">{label}</span>
                    </div>
                  ))}
                </div>
                <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent px-3 py-2.5 flex items-end justify-between">
                  <div>
                    <div className="text-[9px] font-mono text-white/70 uppercase">Risk Score</div>
                    <div className="font-display text-4xl font-black text-emerald-400">05</div>
                  </div>
                  <span className="text-[10px] font-mono text-emerald-400 bg-emerald-400/20 border border-emerald-400/30 px-2 py-1 rounded">
                    ● SAFE
                  </span>
                </div>
              </div>
            </Card>

            <Card className="p-4">
              <div className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest mb-3">
                Live Alerts
              </div>
              {[
                { color: "bg-red-500", msg: "Identity mismatch — AU-2025-004", t: "09:34:53" },
                { color: "bg-orange-400", msg: "Phone detected — AU-2025-002", t: "09:15:08" },
                { color: "bg-blue-400", msg: "Tab switch — AU-2025-007", t: "09:12:44" },
              ].map((a, i) => (
                <div
                  key={i}
                  className="flex items-center gap-3 py-1.5 border-b border-border last:border-0"
                  style={{ opacity: 1 - i * 0.25 }}
                >
                  <div className={`w-1.5 h-1.5 rounded-full ${a.color} flex-shrink-0`} />
                  <span className="text-xs text-foreground/80 flex-1">{a.msg}</span>
                  <span className="font-mono text-[10px] text-muted-foreground">{a.t}</span>
                </div>
              ))}
            </Card>
          </div>
        </div>
      </section>

      <section className="py-24 bg-secondary">
        <div className="max-w-screen-xl mx-auto px-6">
          <SectionTag text="Development Roadmap" />
          <h2 className="font-display font-black text-foreground text-5xl mb-3">15 Development Phases</h2>
          <p className="text-muted-foreground text-sm mb-14 max-w-xl">
            From system design through analytics — a 9-week agile implementation roadmap.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
            {PHASES.map((p) => (
              <div
                key={p.n}
                className="group bg-card border border-border rounded-xl p-4 hover:border-primary/40 hover:shadow-md transition-all duration-300"
              >
                <div className="font-mono text-[11px] text-primary mb-2">Phase {p.n}</div>
                <div className="text-foreground text-sm font-semibold mb-1.5">{p.title}</div>
                <p className="text-muted-foreground text-[11px] leading-relaxed">{p.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="py-24 bg-background">
        <div className="max-w-screen-xl mx-auto px-6 grid grid-cols-1 lg:grid-cols-3 gap-12">
          <div>
            <SectionTag text="System Modules" />
            <h3 className="font-display font-black text-foreground text-3xl mb-8">8 Core Modules</h3>
            <div className="space-y-2">
              {MODULES.map(({ icon: Icon, title, color }) => (
                <div key={title} className="flex items-center gap-3 p-3 bg-card border border-border rounded-xl hover:border-foreground/15 transition-colors">
                  <div
                    className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                    style={{ backgroundColor: `${color}14`, border: `1px solid ${color}28` }}
                  >
                    <Icon className="w-4 h-4" style={{ color }} />
                  </div>
                  <span className="text-foreground/80 text-sm">{title}</span>
                </div>
              ))}
            </div>
          </div>

          <div>
            <SectionTag text="Database Design" />
            <h3 className="font-display font-black text-foreground text-3xl mb-8">PostgreSQL Schema</h3>
            <div className="grid grid-cols-2 gap-2">
              {DB_TABLES.map((t) => (
                <div key={t} className="flex items-center gap-2 px-3 py-2 bg-card border border-border rounded-lg">
                  <Database className="w-3 h-3 text-blue-500 flex-shrink-0" />
                  <span className="font-mono text-[11px] text-foreground/70">{t}</span>
                </div>
              ))}
            </div>
          </div>

          <div>
            <SectionTag text="Technology Stack" />
            <h3 className="font-display font-black text-foreground text-3xl mb-8">Full-Stack Setup</h3>
            <div className="space-y-3">
              {TECH_STACK.map(({ cat, items }) => (
                <div key={cat} className="p-4 bg-card border border-border rounded-xl">
                  <div className="text-[10px] font-mono text-primary uppercase tracking-widest mb-3">{cat}</div>
                  <div className="flex flex-wrap gap-2">
                    {items.map((item) => (
                      <span key={item} className="bg-secondary border border-border text-foreground/70 text-[11px] font-mono px-2.5 py-1 rounded-lg">
                        {item}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-4 p-4 bg-red-50 border border-red-100 rounded-xl">
              <div className="text-[10px] font-mono text-primary uppercase tracking-widest mb-3">Risk Formula</div>
              <div className="font-mono text-xs text-foreground/80 space-y-1">
                <div>Phone Detected · · · · +80</div>
                <div>Multiple People · · · +60</div>
                <div>Unknown Face · · · · +90</div>
                <div>Tab Switch · · · · · +20</div>
                <div className="pt-2 border-t border-red-200 text-foreground font-bold">Total → 0–100 → Risk Level</div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
