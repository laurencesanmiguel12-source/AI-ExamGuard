import { useState, useEffect } from "react";
import PreExamModal from "./PreExamModal";
import {
  Shield, Eye, Camera, Brain, AlertTriangle, CheckCircle,
  Users, Database, Monitor, Activity, Lock, ChevronRight,
  Menu, X, BarChart3, Clock, BookOpen, Award, TrendingUp,
  Zap, Bell, FileText, Settings, UserCheck,
  GraduationCap, ClipboardList, Radio, Search,
  Upload, Download, Plus, Edit2, Trash2,
  AlertCircle, Circle, ArrowRight, Wifi,
  Filter, Star, Target,
} from "lucide-react";
import {
  AreaChart, Area, LineChart, Line, BarChart, Bar,
  XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart as RPie, Pie, Cell,
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
} from "recharts";

// ─── Types ────────────────────────────────────────────────────────────────────

type View =
  | "landing" | "login" | "student" | "instructor" | "admin"
  | "exam" | "enroll" | "monitor" | "reports" | "analytics";

type Role = "student" | "instructor" | "admin";

// ─── Mock Data ────────────────────────────────────────────────────────────────

const riskTimeline = [
  { time: "09:00", risk: 5 }, { time: "09:05", risk: 8 },
  { time: "09:10", risk: 12 }, { time: "09:15", risk: 55 },
  { time: "09:20", risk: 48 }, { time: "09:25", risk: 20 },
  { time: "09:30", risk: 72 }, { time: "09:35", risk: 88 },
  { time: "09:40", risk: 61 }, { time: "09:45", risk: 30 },
  { time: "09:50", risk: 18 },
];

const liveStudents = [
  { id: "AU-2025-001", name: "Maria Santos",   risk: 12, status: "safe",     face: true,  phone: false, tab: false, lstm: 8  },
  { id: "AU-2025-002", name: "Juan dela Cruz", risk: 74, status: "high",     face: true,  phone: true,  tab: true,  lstm: 86 },
  { id: "AU-2025-003", name: "Ana Reyes",      risk: 5,  status: "safe",     face: true,  phone: false, tab: false, lstm: 4  },
  { id: "AU-2025-004", name: "Carlo Mendoza",  risk: 91, status: "critical", face: false, phone: true,  tab: false, lstm: 94 },
  { id: "AU-2025-005", name: "Liza Garcia",    risk: 38, status: "medium",   face: true,  phone: false, tab: true,  lstm: 42 },
  { id: "AU-2025-006", name: "Rico Bautista",  risk: 7,  status: "safe",     face: true,  phone: false, tab: false, lstm: 5  },
  { id: "AU-2025-007", name: "Jenny Flores",   risk: 55, status: "medium",   face: true,  phone: false, tab: true,  lstm: 61 },
];

const violationBreakdown = [
  { name: "Phone Detected",  value: 34, fill: "#c8192e" },
  { name: "Tab Switch",      value: 28, fill: "#1a4fa8" },
  { name: "Face Loss",       value: 20, fill: "#e86e1e" },
  { name: "Unknown Face",    value: 12, fill: "#8b1ec4" },
  { name: "Multiple People", value: 6,  fill: "#1ec47a" },
];

const analyticsWeekly = [
  { day: "Mon", avgRisk: 28, exams: 4, violations: 12 },
  { day: "Tue", avgRisk: 34, exams: 6, violations: 19 },
  { day: "Wed", avgRisk: 22, exams: 3, violations: 8  },
  { day: "Thu", avgRisk: 48, exams: 8, violations: 31 },
  { day: "Fri", avgRisk: 41, exams: 7, violations: 24 },
  { day: "Sat", avgRisk: 15, exams: 2, violations: 5  },
];

const radarData = [
  { metric: "Accuracy",   value: 96 }, { metric: "FPS",       value: 88 },
  { metric: "Face Match", value: 94 }, { metric: "YOLO Speed",value: 91 },
  { metric: "LSTM",       value: 82 }, { metric: "Usability", value: 87 },
];

const examQuestions = [
  { no: 1, type: "mcq",            question: "Which computer vision technique is used to detect facial landmarks in real-time?",     choices: ["Histogram of Oriented Gradients","Dlib shape predictor","SIFT feature extraction","Canny edge detection"], answer: 1 },
  { no: 2, type: "tf",             question: "YOLOv8 can only detect one object class per image frame.",                             choices: ["True","False"],                                                                                         answer: 1 },
  { no: 3, type: "identification", question: "What does LSTM stand for in the context of sequential behavioral prediction?",         choices: [],                                                                                                       answer: -1 },
  { no: 4, type: "mcq",            question: "Which library is used in AI ExamGuard for biometric face encoding and matching?",      choices: ["TensorFlow Face API","FaceNet / face_recognition","DeepFace","MediaPipe"],                             answer: 1 },
  { no: 5, type: "mcq",            question: "What is the risk score threshold that triggers automatic evidence collection?",         choices: ["50","60","70","90"],                                                                                    answer: 2 },
];

const reportTimeline = [
  { time: "09:01:00", event: "Identity Verified",              risk: 5,  type: "ok"       },
  { time: "09:12:44", event: "Tab Switch Detected",            risk: 22, type: "warn"     },
  { time: "09:15:08", event: "Mobile Phone Detected",          risk: 58, type: "high"     },
  { time: "09:15:10", event: "Screenshot Captured",            risk: 58, type: "evidence" },
  { time: "09:21:33", event: "Tab Switch Detected",            risk: 31, type: "warn"     },
  { time: "09:30:17", event: "Face Loss Detected",             risk: 74, type: "high"     },
  { time: "09:30:18", event: "Screenshot Captured",            risk: 74, type: "evidence" },
  { time: "09:34:52", event: "Unknown Face Detected",          risk: 91, type: "critical" },
  { time: "09:34:53", event: "Screenshot Captured — Email Sent", risk: 91, type: "evidence" },
  { time: "09:50:00", event: "Exam Submitted",                 risk: 91, type: "end"      },
];

const adminUsers = [
  { id: 1, name: "Maria Santos",    role: "student",    email: "m.santos@arellano.edu",    status: "active",    enrolled: true  },
  { id: 2, name: "Juan dela Cruz",  role: "student",    email: "j.delacruz@arellano.edu",  status: "active",    enrolled: true  },
  { id: 3, name: "Ana Reyes",       role: "student",    email: "a.reyes@arellano.edu",     status: "active",    enrolled: false },
  { id: 4, name: "Dr. Roberto Lim", role: "instructor", email: "r.lim@arellano.edu",       status: "active",    enrolled: false },
  { id: 5, name: "Prof. Clara Diaz",role: "instructor", email: "c.diaz@arellano.edu",      status: "active",    enrolled: false },
  { id: 6, name: "Carlo Mendoza",   role: "student",    email: "c.mendoza@arellano.edu",   status: "suspended", enrolled: true  },
];

// ─── Tooltip style (light) ────────────────────────────────────────────────────
const TT = { background: "#fff", border: "1px solid rgba(0,0,0,0.1)", borderRadius: 8, fontSize: 11, fontFamily: "JetBrains Mono", color: "#0f172a" };
const TT_LABEL = { color: "#64748b" };
const TICK = { fill: "#94a3b8", fontSize: 11, fontFamily: "JetBrains Mono" };

// ─── Shared UI ────────────────────────────────────────────────────────────────

function RiskPill({ value }: { value: number }) {
  const cfg =
    value < 25  ? { cls: "bg-emerald-50 text-emerald-700 border-emerald-200", label: "LOW"      }
  : value < 50  ? { cls: "bg-blue-50 text-blue-700 border-blue-200",          label: "MEDIUM"   }
  : value < 75  ? { cls: "bg-orange-50 text-orange-700 border-orange-200",    label: "HIGH"     }
  :               { cls: "bg-red-50 text-red-700 border-red-200",             label: "CRITICAL" };
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded border text-[10px] font-mono font-bold tracking-widest ${cfg.cls}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {cfg.label} · {value}
    </span>
  );
}

function RiskBar({ value, showLabel = true }: { value: number; showLabel?: boolean }) {
  const color = value < 25 ? "#10b981" : value < 50 ? "#3b82f6" : value < 75 ? "#f97316" : "#ef4444";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-black/8 rounded-full overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${value}%`, backgroundColor: color, transition: "width 0.8s ease" }} />
      </div>
      {showLabel && <span className="font-mono text-[11px] text-muted-foreground w-7 text-right">{value}</span>}
    </div>
  );
}

function StatusDot({ on, label }: { on: boolean; label: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <div className={`w-2 h-2 rounded-full ${on ? "bg-emerald-500" : "bg-red-500"}`} />
      <span className="text-[11px] font-mono text-muted-foreground">{label}</span>
    </div>
  );
}

function SectionTag({ text }: { text: string }) {
  return (
    <div className="inline-flex items-center gap-2 mb-4">
      <div className="w-4 h-px bg-primary" />
      <span className="text-primary text-[11px] font-mono uppercase tracking-[0.2em]">{text}</span>
    </div>
  );
}

function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-card border border-border rounded-xl shadow-sm ${className}`}>
      {children}
    </div>
  );
}

// ─── Topbar ───────────────────────────────────────────────────────────────────

const NAV_LINKS: { label: string; view: View }[] = [
  { label: "Home",        view: "landing"    },
  { label: "Student",     view: "student"    },
  { label: "Instructor",  view: "instructor" },
  { label: "Admin",       view: "admin"      },
  { label: "Exam Room",   view: "exam"       },
  { label: "Face Enroll", view: "enroll"     },
  { label: "AI Monitor",  view: "monitor"    },
  { label: "Reports",     view: "reports"    },
  { label: "Analytics",   view: "analytics"  },
];

function Topbar({ view, setView }: { view: View; setView: (v: View) => void }) {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", fn);
    return () => window.removeEventListener("scroll", fn);
  }, []);

  const scrolledOrInner = scrolled || view !== "landing";

  return (
    <header className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${scrolledOrInner ? "bg-white/95 backdrop-blur border-b border-border shadow-sm" : "bg-white/80 backdrop-blur"}`}>
      <div className="max-w-screen-xl mx-auto px-6 h-14 flex items-center justify-between">
        <button onClick={() => setView("landing")} className="flex items-center gap-2.5 group">
          <div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center group-hover:scale-105 transition-transform">
            <Shield className="w-3.5 h-3.5 text-white" />
          </div>
          <div>
            <div className="text-foreground font-display font-bold text-sm leading-none">AI ExamGuard</div>
            <div className="text-muted-foreground text-[9px] font-mono uppercase tracking-[0.2em]">Arellano University</div>
          </div>
        </button>

        <nav className="hidden xl:flex items-center gap-1">
          {NAV_LINKS.map(({ label, view: v }) => (
            <button key={v} onClick={() => setView(v)}
              className={`px-3 py-1.5 rounded-lg text-[11px] font-mono uppercase tracking-wider transition-all ${view === v ? "bg-primary text-white" : "text-muted-foreground hover:text-foreground hover:bg-black/5"}`}>
              {label}
            </button>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          <button onClick={() => setView("login")}
            className="hidden sm:flex items-center gap-2 bg-primary hover:bg-primary/90 text-white text-[11px] font-mono uppercase tracking-widest px-4 py-2 rounded-lg transition-colors">
            <Lock className="w-3.5 h-3.5" /> Login
          </button>
          <button className="xl:hidden text-muted-foreground hover:text-foreground" onClick={() => setOpen(!open)}>
            {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {open && (
        <div className="xl:hidden bg-white border-t border-border px-6 py-4 grid grid-cols-2 gap-2">
          {NAV_LINKS.map(({ label, view: v }) => (
            <button key={v} onClick={() => { setView(v); setOpen(false); }}
              className={`px-3 py-2 rounded-lg text-[11px] font-mono uppercase tracking-wider text-left transition-all ${view === v ? "bg-primary text-white" : "text-muted-foreground hover:text-foreground hover:bg-black/5"}`}>
              {label}
            </button>
          ))}
        </div>
      )}
    </header>
  );
}

// ─── Landing ──────────────────────────────────────────────────────────────────

const PHASES = [
  { n: "01", title: "Planning & Design",       desc: "Functional/non-functional requirements, ERD, use cases, UI mockups, sprint backlog." },
  { n: "02", title: "Project Setup",           desc: "FastAPI backend, React frontend, PostgreSQL schema with 18 tables." },
  { n: "03", title: "Authentication",          desc: "JWT-secured registration & login with Admin, Instructor, and Student roles." },
  { n: "04", title: "Student Management",      desc: "Admin CRUD, CSV import, instructor views, student profile updates." },
  { n: "05", title: "Face Enrollment",         desc: "Webcam capture of 20 images → FaceNet encoding → secure biometric profile." },
  { n: "06", title: "Exam Module",             desc: "Create/publish exams with MCQ, True/False, and Identification question types." },
  { n: "07", title: "Face Verification",       desc: "Pre-exam identity match: live encoding vs. stored profile before session start." },
  { n: "08", title: "Live AI Monitoring",      desc: "Frame-by-frame: FaceNet + YOLOv8 + browser JS events feeding the risk engine." },
  { n: "09", title: "LSTM Prediction",         desc: "30-second feature window fed into LSTM → cheating probability score." },
  { n: "10", title: "Risk Engine",             desc: "Weighted formula across all AI modules → 0–100 composite live risk score." },
  { n: "11", title: "Evidence Collection",     desc: "Auto screenshot + timestamp + reason saved when risk ≥ 70." },
  { n: "12", title: "Email Notifications",     desc: "Instructor alert email with student details, screenshot, and risk reason." },
  { n: "13", title: "Instructor Dashboard",    desc: "Real-time WebSocket feed of all live session risk scores and alerts." },
  { n: "14", title: "Report Generator",        desc: "Post-exam PDF: risk timeline, violations, screenshots, recommendation." },
  { n: "15", title: "Analytics Dashboard",     desc: "Charts: avg risk, top violations, detection rates, exam scores by course." },
];

const MODULES = [
  { icon: GraduationCap, title: "Student Module",         color: "#1a4fa8" },
  { icon: Users,         title: "Instructor Module",      color: "#059669" },
  { icon: Settings,      title: "Administrator Module",   color: "#7c3aed" },
  { icon: Lock,          title: "Authentication Module",  color: "#c8192e" },
  { icon: ClipboardList, title: "Exam Module",            color: "#ea580c" },
  { icon: Eye,           title: "AI Monitoring Module",   color: "#c8192e" },
  { icon: BarChart3,     title: "Dashboard Module",       color: "#1a4fa8" },
  { icon: FileText,      title: "Reports Module",         color: "#059669" },
];

const TECH_STACK = [
  { cat: "Backend",   items: ["FastAPI", "Python 3.11", "JWT Auth", "PostgreSQL"]       },
  { cat: "AI / CV",   items: ["YOLOv8", "FaceNet", "face_recognition", "OpenCV"]        },
  { cat: "ML",        items: ["LSTM (Keras)", "Scikit-learn", "NumPy", "Pandas"]         },
  { cat: "Frontend",  items: ["React", "Recharts", "WebSocket", "HTML/CSS/JS"]           },
];

const DB_TABLES = [
  "users","students","instructors","courses","subjects",
  "exams","questions","choices","student_answers",
  "exam_sessions","face_profiles","monitoring_events",
  "risk_scores","screenshots","notifications","reports",
];

// ── SVG Artwork: Proctoring Canvas ───────────────────────────────────────────

function ProctorCanvas() {
  return (
    <svg viewBox="0 0 520 400" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full" aria-hidden="true">
      <defs>
        <style>{`
          @keyframes scanPulse { 0%{transform:translateY(0px);opacity:.9} 85%{opacity:.9} 100%{transform:translateY(164px);opacity:0} }
          @keyframes blinkDot  { 0%,100%{opacity:1} 50%{opacity:.2} }
          @keyframes floatA    { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-7px)} }
          @keyframes floatB    { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-5px)} }
          @keyframes riskFill  { from{stroke-dashoffset:220} to{stroke-dashoffset:184} }
          .scan { animation: scanPulse 2.8s ease-in-out infinite; }
          .blink{ animation: blinkDot  1.8s ease-in-out infinite; }
          .fa   { animation: floatA    3.2s ease-in-out infinite; }
          .fb   { animation: floatB    2.6s ease-in-out infinite 0.7s; }
          .fc   { animation: floatA    3.8s ease-in-out infinite 1.3s; }
          .riskArc { stroke-dasharray: 220; animation: riskFill 1.5s ease-out 0.3s forwards; stroke-dashoffset: 220; }
        `}</style>
        <pattern id="heroDots" x="0" y="0" width="20" height="20" patternUnits="userSpaceOnUse">
          <circle cx="1" cy="1" r="1" fill="#94a3b8" opacity="0.25"/>
        </pattern>
        <linearGradient id="screenBg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#0d1829"/>
          <stop offset="100%" stopColor="#162035"/>
        </linearGradient>
        <linearGradient id="redBlue" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#c8192e"/>
          <stop offset="100%" stopColor="#1a4fa8"/>
        </linearGradient>
        <linearGradient id="riskGradient" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%"   stopColor="#10b981"/>
          <stop offset="55%"  stopColor="#f97316"/>
          <stop offset="100%" stopColor="#ef4444"/>
        </linearGradient>
        <clipPath id="screenClip">
          <rect x="96" y="52" width="310" height="226" rx="4"/>
        </clipPath>
        <filter id="glow">
          <feGaussianBlur stdDeviation="3" result="blur"/>
          <feComposite in="SourceGraphic" in2="blur" operator="over"/>
        </filter>
      </defs>

      {/* ─ Background canvas ─ */}
      <rect width="520" height="400" fill="#f8fafc"/>
      <rect width="520" height="400" fill="url(#heroDots)"/>

      {/* Decorative geometric accents */}
      <circle cx="480" cy="40" r="60" fill="#eff6ff" opacity="0.6"/>
      <circle cx="40"  cy="350" r="50" fill="#fff1f2" opacity="0.5"/>
      <circle cx="480" cy="370" r="35" fill="#f0fdf4" opacity="0.5"/>

      {/* ─ Laptop stand ─ */}
      <rect x="168" y="284" width="184" height="12" rx="3" fill="#e2e8f0"/>
      <rect x="148" y="294" width="224" height="7" rx="3.5" fill="#cbd5e1"/>

      {/* ─ Monitor outer shell ─ */}
      <rect x="88" y="34" width="326" height="256" rx="14" fill="#ffffff" stroke="#e2e8f0" strokeWidth="2"/>

      {/* ─ Titlebar ─ */}
      <rect x="88" y="34" width="326" height="30" rx="14" fill="#f1f5f9"/>
      <rect x="88" y="48" width="326" height="16" fill="#f1f5f9"/>
      <circle cx="108" cy="49" r="5" fill="#fca5a5"/>
      <circle cx="124" cy="49" r="5" fill="#fde68a"/>
      <circle cx="140" cy="49" r="5" fill="#86efac"/>
      <text x="251" y="53" textAnchor="middle" fontFamily="JetBrains Mono,monospace" fontSize="8" fill="#64748b">AI ExamGuard · CS411 · Ana Reyes</text>
      <circle cx="388" cy="49" r="3" fill="#f97316" opacity="0.7"/>
      <text x="384" y="52" fontFamily="JetBrains Mono,monospace" fontSize="5.5" fill="#fff">30</text>

      {/* ─ Screen content (dark) ─ */}
      <rect x="96" y="64" width="310" height="218" fill="url(#screenBg)" clipPath="url(#screenClip)"/>

      {/* Fine grid overlay on screen */}
      <g clipPath="url(#screenClip)" opacity="0.06">
        {[...Array(10)].map((_,i) => <line key={`vg${i}`} x1={96+i*31} y1="64" x2={96+i*31} y2="282" stroke="#60a5fa" strokeWidth="0.5"/>)}
        {[...Array(8)].map((_,i) => <line key={`hg${i}`} x1="96" y1={64+i*28} x2="406" y2={64+i*28} stroke="#60a5fa" strokeWidth="0.5"/>)}
      </g>

      {/* ─ Abstract student silhouette ─ */}
      <g clipPath="url(#screenClip)">
        {/* Torso/shoulders fill */}
        <path d="M200 282 Q251 228 302 282 Z" fill="#1e3a5f" opacity="0.4"/>
        {/* Head shape */}
        <ellipse cx="251" cy="168" rx="36" ry="42" fill="#1e3a5f" opacity="0.35"/>
        {/* Collar/neck */}
        <rect x="237" y="207" width="28" height="22" rx="4" fill="#1e3a5f" opacity="0.3"/>
      </g>

      {/* ─ Face detection overlay ─ */}
      <g clipPath="url(#screenClip)">
        {/* Detection bracket — corners */}
        <g stroke="#10b981" strokeWidth="2.5" fill="none" filter="url(#glow)">
          <path d="M207 122 h-18 v18"/>
          <path d="M295 122 h18 v18"/>
          <path d="M207 214 h-18 v-18"/>
          <path d="M295 214 h18 v-18"/>
        </g>
        {/* Dot-grid face mapping */}
        {[...Array(5)].map((_,row) =>
          [...Array(6)].map((_,col) => (
            <circle key={`fd${row}${col}`}
              cx={215 + col * 15} cy={132 + row * 16}
              r="1.8" fill="#10b981" opacity={0.3 + row*0.08}/>
          ))
        )}
        {/* Scan sweep line */}
        <rect x="189" y="122" width="124" height="2.5" fill="#10b981" opacity="0.85" className="scan"/>

        {/* Verified badge */}
        <rect x="215" y="104" width="72" height="15" rx="7.5" fill="rgba(16,185,129,0.18)"/>
        <rect x="215" y="104" width="72" height="15" rx="7.5" stroke="#10b981" strokeWidth="1" fill="none"/>
        <text x="251" y="115" textAnchor="middle" fontFamily="JetBrains Mono,monospace" fontSize="7" fill="#10b981">● VERIFIED</text>

        {/* Module badges top-right */}
        {[{l:"YOLO",y:74,c:"#fb923c"},{l:"FACE",y:88,c:"#10b981"},{l:"LSTM",y:102,c:"#60a5fa"}].map(({l,y,c}) => (
          <g key={l}>
            <rect x="366" y={y} width="32" height="11" rx="3" fill="rgba(255,255,255,0.07)"/>
            <circle cx="371" cy={y+5.5} r="2.2" fill={c} className="blink"/>
            <text x="375" y={y+8.5} fontFamily="JetBrains Mono,monospace" fontSize="6.5" fill="rgba(255,255,255,0.75)">{l}</text>
          </g>
        ))}
      </g>

      {/* ─ Bottom status bar on screen ─ */}
      <g clipPath="url(#screenClip)">
        <rect x="96" y="248" width="310" height="34" fill="rgba(0,0,0,0.55)"/>
        <text x="112" y="261" fontFamily="JetBrains Mono,monospace" fontSize="6.5" fill="rgba(255,255,255,0.45)" letterSpacing="1">RISK SCORE</text>
        <text x="112" y="275" fontFamily="Barlow Condensed,sans-serif" fontSize="20" fontWeight="900" fill="#34d399">07</text>
        {/* Mini risk bar */}
        <rect x="152" y="263" width="100" height="5" rx="2.5" fill="rgba(255,255,255,0.1)"/>
        <rect x="152" y="263" width="7" height="5" rx="2.5" fill="#10b981"/>
        <text x="259" y="269" fontFamily="JetBrains Mono,monospace" fontSize="7" fill="#34d399">LOW</text>
        {/* Right side timestamp */}
        <text x="360" y="269" fontFamily="JetBrains Mono,monospace" fontSize="6.5" fill="rgba(255,255,255,0.35)">09:14:22</text>
      </g>

      {/* ═══════════════════════════════════════════════════════════ */}
      {/*  Floating UI artwork elements around the monitor           */}
      {/* ═══════════════════════════════════════════════════════════ */}

      {/* ─ LEFT FLOAT: Risk Gauge card ─ */}
      <g className="fa">
        <rect x="8" y="84" width="76" height="100" rx="12" fill="#fff" stroke="#e2e8f0" strokeWidth="1.5"/>
        <text x="46" y="100" textAnchor="middle" fontFamily="JetBrains Mono,monospace" fontSize="7" fill="#64748b" letterSpacing="1">RISK</text>
        {/* Arc track */}
        <path d="M18 160 A28 28 0 0 1 74 160" stroke="#e2e8f0" strokeWidth="5" strokeLinecap="round" fill="none"/>
        {/* Arc fill — risk 7% of range */}
        <path d="M18 160 A28 28 0 0 1 74 160" stroke="url(#riskGradient)" strokeWidth="5" strokeLinecap="round" fill="none"
          strokeDasharray="88" strokeDashoffset="80" className="riskArc"/>
        <text x="46" y="156" textAnchor="middle" fontFamily="Barlow Condensed,sans-serif" fontSize="22" fontWeight="900" fill="#0f172a">07</text>
        <text x="46" y="167" textAnchor="middle" fontFamily="JetBrains Mono,monospace" fontSize="6.5" fill="#10b981">LOW</text>
        <rect x="14" y="174" width="48" height="5" rx="2.5" fill="#f1f5f9"/>
        <rect x="14" y="174" width="4" height="5" rx="2.5" fill="#10b981"/>
      </g>

      {/* ─ TOP-RIGHT FLOAT: Alert card ─ */}
      <g className="fb">
        <rect x="436" y="54" width="76" height="72" rx="12" fill="#fff" stroke="#fecdd3" strokeWidth="1.5"/>
        {/* Red header strip */}
        <rect x="436" y="54" width="76" height="24" rx="12" fill="#fff1f2"/>
        <rect x="436" y="66" width="76" height="12" fill="#fff1f2"/>
        <circle cx="450" cy="66" r="5" fill="#ef4444" opacity="0.8"/>
        <text x="460" y="69.5" fontFamily="JetBrains Mono,monospace" fontSize="7" fill="#c8192e" fontWeight="bold">ALERT</text>
        <text x="446" y="87" fontFamily="JetBrains Mono,monospace" fontSize="6.5" fill="#64748b">Phone</text>
        <text x="446" y="97" fontFamily="JetBrains Mono,monospace" fontSize="6.5" fill="#64748b">Detected</text>
        <text x="446" y="113" fontFamily="JetBrains Mono,monospace" fontSize="5.5" fill="#94a3b8">09:15:08</text>
        {/* Exclamation icon */}
        <circle cx="494" cy="107" r="8" fill="#fff1f2" stroke="#fecdd3" strokeWidth="1"/>
        <text x="494" y="111" textAnchor="middle" fontFamily="sans-serif" fontSize="11" fill="#c8192e">!</text>
      </g>

      {/* ─ RIGHT FLOAT: Face match card ─ */}
      <g className="fc">
        <rect x="436" y="158" width="76" height="56" rx="12" fill="#eff6ff" stroke="#bfdbfe" strokeWidth="1.5"/>
        <text x="448" y="172" fontFamily="JetBrains Mono,monospace" fontSize="6" fill="#1a4fa8" letterSpacing="0.5">FACE MATCH</text>
        <text x="448" y="186" fontFamily="Barlow Condensed,sans-serif" fontSize="18" fontWeight="900" fill="#1a4fa8">98.4%</text>
        {/* Check badge */}
        <circle cx="494" cy="185" r="9" fill="#dbeafe" stroke="#93c5fd" strokeWidth="1"/>
        <text x="494" y="189" textAnchor="middle" fontSize="11" fill="#1d4ed8">✓</text>
        <text x="448" y="200" fontFamily="JetBrains Mono,monospace" fontSize="5.5" fill="#3b82f6">FaceNet · 1:1</text>
      </g>

      {/* ─ BOTTOM FLOAT: LSTM prediction card ─ */}
      <g className="fb">
        <rect x="436" y="244" width="76" height="60" rx="12" fill="#f5f3ff" stroke="#ddd6fe" strokeWidth="1.5"/>
        <text x="448" y="258" fontFamily="JetBrains Mono,monospace" fontSize="6" fill="#7c3aed" letterSpacing="0.5">LSTM PRED.</text>
        <text x="448" y="272" fontFamily="Barlow Condensed,sans-serif" fontSize="18" fontWeight="900" fill="#7c3aed">5.2%</text>
        <text x="448" y="283" fontFamily="JetBrains Mono,monospace" fontSize="5.5" fill="#8b5cf6">cheat prob.</text>
        {/* Mini bar */}
        <rect x="448" y="289" width="52" height="4" rx="2" fill="#ede9fe"/>
        <rect x="448" y="289" width="3" height="4" rx="2" fill="#7c3aed"/>
      </g>

      {/* ─ Neural net art (bottom-left decorative) ─ */}
      <g opacity="0.5">
        {/* Nodes */}
        {([[24,310],[24,340],[24,370],[56,295],[56,325],[56,355],[56,385],[88,310],[88,340],[88,370]] as [number,number][]).map(([x,y],i) => (
          <circle key={`n${i}`} cx={x} cy={y} r={i<3?5:i<7?5:5}
            fill={i<3?"#c8192e":i<7?"#1a4fa8":"#10b981"} opacity={0.18+i*0.03}/>
        ))}
        {/* Edges */}
        {([[24,310,56,295],[24,310,56,325],[24,340,56,325],[24,340,56,355],[24,370,56,355],[24,370,56,385],[56,295,88,310],[56,325,88,310],[56,325,88,340],[56,355,88,340],[56,355,88,370],[56,385,88,370]] as [number,number,number,number][]).map(([x1,y1,x2,y2],i) => (
          <line key={`e${i}`} x1={x1} y1={y1} x2={x2} y2={y2} stroke="#1a4fa8" strokeWidth="0.8" opacity="0.18"/>
        ))}
      </g>

      {/* ─ Live indicator badge ─ */}
      <g className="fa">
        <rect x="8" y="54" width="74" height="22" rx="11" fill="#fff" stroke="#e2e8f0" strokeWidth="1.5"/>
        <circle cx="22" cy="65" r="4" fill="#c8192e" className="blink"/>
        <text x="30" y="69" fontFamily="JetBrains Mono,monospace" fontSize="7.5" fill="#0f172a" fontWeight="bold">LIVE</text>
        <text x="52" y="69" fontFamily="JetBrains Mono,monospace" fontSize="6" fill="#64748b">30 FPS</text>
      </g>
    </svg>
  );
}

// ── Marketing feature data (from one-pager) ───────────────────────────────────

const MARKETING_FEATURES = [
  {
    icon: Eye,
    color: "#c8192e",
    bg: "#fff1f2",
    border: "#fecdd3",
    title: "Real-Time AI Monitoring",
    desc: "Webcam-based face verification, YOLO-based object & phone detection trained on real exam footage, and tab/window-switch tracking — all running live during the exam, not reviewed after the fact.",
  },
  {
    icon: BarChart3,
    color: "#1a4fa8",
    bg: "#eff6ff",
    border: "#bfdbfe",
    title: "A Risk Score You Can Actually Read",
    desc: "Every session gets a transparent 0–100 risk score instructors can watch live, combining a trained model with clear, auditable rules — never a black box.",
  },
  {
    icon: CheckCircle,
    color: "#059669",
    bg: "#f0fdf4",
    border: "#bbf7d0",
    title: "Fair by Design",
    desc: "Built-in accommodations for students who need checks disabled, a full student appeal workflow on every flagged violation, and instructor review before any consequence.",
  },
  {
    icon: Lock,
    color: "#7c3aed",
    bg: "#f5f3ff",
    border: "#ddd6fe",
    title: "Privacy-Conscious by Default",
    desc: "Evidence auto-expires on a fixed retention window, every access is audit-logged, and admins have direct purge controls — proctoring without a permanent surveillance archive.",
  },
  {
    icon: Star,
    color: "#b45309",
    bg: "#fffbeb",
    border: "#fde68a",
    title: "Your Own Branded Space, Instantly",
    desc: "Register your school and get a fully isolated environment — your own login page, your own courses, students, and exams, completely separate from every other school.",
  },
  {
    icon: ClipboardList,
    color: "#0891b2",
    bg: "#ecfeff",
    border: "#a5f3fc",
    title: "Built for the Whole Exam Lifecycle",
    desc: "Exam creation with bulk CSV question import, subject-scoped instructor assignment, rosters, live monitoring, and per-question analytics — not just the proctoring moment.",
  },
];

const ONBOARDING_STEPS = [
  {
    n: "01",
    title: "Register your school",
    desc: "Enter your school name and set up your admin account. Your school gets its own login URL immediately — no waiting, no sales call.",
    icon: GraduationCap,
    color: "#c8192e",
  },
  {
    n: "02",
    title: "Add your people",
    desc: "Bring in instructors and assign them to subjects, add your courses, and either add students directly or share your course list so they can self-register.",
    icon: Users,
    color: "#1a4fa8",
  },
  {
    n: "03",
    title: "Create your first exam",
    desc: "Build a question bank (or bulk-import via CSV), scope it to a course or a specific roster, and set a passing score — AI monitoring runs automatically once it's live.",
    icon: ClipboardList,
    color: "#7c3aed",
  },
  {
    n: "04",
    title: "Watch it happen, live",
    desc: "Instructors see a live risk feed as students take the exam, then get a full report: score distribution, pass rate, and per-question accuracy the moment it ends.",
    icon: Activity,
    color: "#059669",
  },
];

function Landing({ setView }: { setView: (v: View) => void }) {
  return (
    <div className="min-h-screen bg-background">

      {/* ══════════════════════════════════════════════════════════ */}
      {/*  HERO                                                      */}
      {/* ══════════════════════════════════════════════════════════ */}
      <section className="relative min-h-screen flex items-center pt-14 overflow-hidden">
        {/* Background layers */}
        <div className="absolute inset-0 bg-gradient-to-br from-white via-blue-50/30 to-red-50/15"/>
        <div className="absolute inset-0 opacity-[0.035]"
          style={{ backgroundImage: "linear-gradient(rgba(0,0,0,1) 1px,transparent 1px),linear-gradient(90deg,rgba(0,0,0,1) 1px,transparent 1px)", backgroundSize: "56px 56px" }}/>
        {/* Glow orbs */}
        <div className="absolute top-1/4 right-0 w-[700px] h-[700px] rounded-full opacity-[0.06]"
          style={{ background: "radial-gradient(circle, #c8192e 0%, transparent 70%)" }}/>
        <div className="absolute -bottom-24 -left-24 w-[500px] h-[500px] rounded-full opacity-[0.05]"
          style={{ background: "radial-gradient(circle, #1a4fa8 0%, transparent 70%)" }}/>

        <div className="relative max-w-screen-xl mx-auto px-6 py-20 grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">

          {/* ── Left: Copy ── */}
          <div>
            {/* Eyebrow badge */}
            <div className="inline-flex items-center gap-2 bg-primary/8 border border-primary/20 rounded-full px-4 py-1.5 mb-8">
              <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse"/>
              <span className="text-primary text-[11px] font-mono uppercase tracking-[0.2em]">
                AI-Driven Academic Integrity · Built for Philippine Higher Ed
              </span>
            </div>

            <h1 className="font-display font-black text-foreground leading-[0.9] tracking-tight mb-6"
              style={{ fontSize: "clamp(3.5rem,7vw,6rem)" }}>
              AI<br/>
              <span className="text-primary">EXAM</span><br/>
              GUARD
            </h1>

            <p className="text-foreground/70 text-base leading-relaxed max-w-xl mb-3">
              Real-time, AI-assisted proctoring for online exams — face verification, device
              detection, and behavior monitoring, with a transparent risk score instructors can
              actually see and audit.
            </p>
            <p className="text-muted-foreground text-sm leading-relaxed max-w-xl mb-10">
              Free to register. Any school can bring its instructors, courses, and students onto
              its own fully isolated space in minutes — no IT department, no procurement process.
            </p>

            {/* CTA buttons */}
            <div className="flex flex-wrap gap-3 mb-12">
              <button onClick={() => setView("login")}
                className="inline-flex items-center gap-2 bg-primary hover:bg-primary/90 text-white px-6 py-3 rounded-xl text-[12px] font-mono uppercase tracking-widest transition-all shadow-sm">
                <Shield className="w-4 h-4"/> Register Free
              </button>
            </div>

            {/* Stats row */}
            <div className="grid grid-cols-3 gap-6 pt-6 border-t border-border">
              {[
                { val: "96.4%", sub: "Detection Accuracy" },
                { val: "30 FPS", sub: "Processing Speed"  },
                { val: "0–100",  sub: "Auditable Risk Score"},
              ].map(({ val, sub }) => (
                <div key={sub}>
                  <div className="font-display text-[2.2rem] font-black text-foreground leading-none">{val}</div>
                  <div className="text-muted-foreground text-[11px] font-mono uppercase tracking-widest mt-1">{sub}</div>
                </div>
              ))}
            </div>
          </div>

          {/* ── Right: SVG Artwork ── */}
          <div className="relative w-full aspect-[4/3] max-w-[560px] mx-auto lg:mx-0">
            <ProctorCanvas/>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════ */}
      {/*  TECH BELT                                                */}
      {/* ══════════════════════════════════════════════════════════ */}
      <div className="border-y border-border bg-white overflow-hidden">
        <div className="max-w-screen-xl mx-auto px-6 py-5 flex items-center gap-0">
          <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-[0.2em] whitespace-nowrap pr-8 border-r border-border mr-8 flex-shrink-0">
            Powered by
          </span>
          <div className="flex items-center gap-8 flex-wrap">
            {[
              {
                name: "YuNet",
                sub: "Face Detection",
                color: "#1a4fa8",
                bg: "#eff6ff",
                mark: (
                  <svg viewBox="0 0 28 28" fill="none" className="w-7 h-7">
                    <rect width="28" height="28" rx="6" fill="#1a4fa8" opacity="0.12"/>
                    <ellipse cx="14" cy="11" rx="5" ry="6" stroke="#1a4fa8" strokeWidth="1.8" fill="none"/>
                    <path d="M9 11 Q14 16 19 11" stroke="#1a4fa8" strokeWidth="1.5" fill="none" strokeLinecap="round"/>
                    <circle cx="11.5" cy="9.5" r="1.2" fill="#1a4fa8"/>
                    <circle cx="16.5" cy="9.5" r="1.2" fill="#1a4fa8"/>
                    <path d="M8 20 Q14 16 20 20" stroke="#1a4fa8" strokeWidth="1.5" fill="none" strokeLinecap="round"/>
                  </svg>
                ),
              },
              {
                name: "YOLOv8",
                sub: "Object Detection",
                color: "#c8192e",
                bg: "#fff1f2",
                mark: (
                  <svg viewBox="0 0 28 28" fill="none" className="w-7 h-7">
                    <rect width="28" height="28" rx="6" fill="#c8192e" opacity="0.12"/>
                    <rect x="5" y="5" width="8" height="8" rx="2" stroke="#c8192e" strokeWidth="1.8" fill="none"/>
                    <rect x="15" y="5" width="8" height="8" rx="2" stroke="#c8192e" strokeWidth="1.8" fill="none"/>
                    <rect x="5" y="15" width="8" height="8" rx="2" stroke="#c8192e" strokeWidth="1.8" fill="none"/>
                    <rect x="15" y="15" width="8" height="8" rx="2" stroke="#c8192e" strokeWidth="1" fill="none" strokeDasharray="2 1.5"/>
                    <circle cx="19" cy="19" r="2.5" fill="#c8192e" opacity="0.7"/>
                  </svg>
                ),
              },
              {
                name: "OpenCV",
                sub: "Computer Vision",
                color: "#059669",
                bg: "#f0fdf4",
                mark: (
                  <svg viewBox="0 0 28 28" fill="none" className="w-7 h-7">
                    <rect width="28" height="28" rx="6" fill="#059669" opacity="0.1"/>
                    <circle cx="14" cy="14" r="7" stroke="#059669" strokeWidth="1.8" fill="none"/>
                    <circle cx="14" cy="14" r="3.5" stroke="#059669" strokeWidth="1.4" fill="none"/>
                    <circle cx="14" cy="14" r="1.2" fill="#059669"/>
                    <line x1="14" y1="5" x2="14" y2="7.5" stroke="#059669" strokeWidth="1.5" strokeLinecap="round"/>
                    <line x1="14" y1="20.5" x2="14" y2="23" stroke="#059669" strokeWidth="1.5" strokeLinecap="round"/>
                    <line x1="5" y1="14" x2="7.5" y2="14" stroke="#059669" strokeWidth="1.5" strokeLinecap="round"/>
                    <line x1="20.5" y1="14" x2="23" y2="14" stroke="#059669" strokeWidth="1.5" strokeLinecap="round"/>
                  </svg>
                ),
              },
              {
                name: "PyTorch",
                sub: "Model Training",
                color: "#ea580c",
                bg: "#fff7ed",
                mark: (
                  <svg viewBox="0 0 28 28" fill="none" className="w-7 h-7">
                    <rect width="28" height="28" rx="6" fill="#ea580c" opacity="0.1"/>
                    <path d="M14 4 L14 15 A6 6 0 1 1 7.5 11" stroke="#ea580c" strokeWidth="1.8" fill="none" strokeLinecap="round"/>
                    <circle cx="20" cy="8" r="1.5" fill="#ea580c"/>
                    <circle cx="14" cy="21" r="3" stroke="#ea580c" strokeWidth="1.5" fill="none"/>
                    <circle cx="14" cy="21" r="1" fill="#ea580c"/>
                  </svg>
                ),
              },
            ].map(({ name, sub, color, bg, mark }) => (
              <div key={name} className="flex items-center gap-3 group">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 border"
                  style={{ background: bg, borderColor: `${color}28` }}>
                  {mark}
                </div>
                <div>
                  <div className="text-foreground font-semibold text-sm leading-none" style={{ color }}>{name}</div>
                  <div className="text-muted-foreground text-[11px] font-mono mt-0.5">{sub}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════ */}
      {/*  WHY AI EXAMGUARD — 6 features                           */}
      {/* ══════════════════════════════════════════════════════════ */}
      <section className="py-24 bg-secondary">
        <div className="max-w-screen-xl mx-auto px-6">
          <div className="max-w-2xl mb-14">
            <SectionTag text="Why AI ExamGuard"/>
            <h2 className="font-display font-black text-foreground text-5xl mb-3">Six things that make it a real proctoring system, not a mock-up.</h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {MARKETING_FEATURES.map(({ icon: Icon, color, bg, border, title, desc }) => (
              <div key={title} className="group bg-card border border-border rounded-2xl p-6 hover:shadow-md transition-all duration-300 hover:-translate-y-0.5">
                <div className="w-11 h-11 rounded-xl flex items-center justify-center mb-4"
                  style={{ background: bg, border: `1px solid ${border}` }}>
                  <Icon className="w-5 h-5" style={{ color }}/>
                </div>
                <h3 className="text-foreground font-semibold text-base mb-2 leading-snug">{title}</h3>
                <p className="text-muted-foreground text-sm leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════ */}
      {/*  GET STARTED IN MINUTES — 4 steps                        */}
      {/* ══════════════════════════════════════════════════════════ */}
      <section className="py-24 bg-background">
        <div className="max-w-screen-xl mx-auto px-6">
          <div className="max-w-xl mb-14">
            <SectionTag text="Get Started in Minutes"/>
            <h2 className="font-display font-black text-foreground text-5xl mb-3">From zero to your first proctored exam.</h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {ONBOARDING_STEPS.map(({ n, title, desc, icon: Icon, color }, i) => (
              <div key={n} className="relative">
                {/* Connector line */}
                {i < ONBOARDING_STEPS.length - 1 && (
                  <div className="hidden lg:block absolute top-8 left-full w-full h-px bg-border z-0" style={{ width: "calc(100% - 44px)", left: 44 }}/>
                )}
                <div className="relative z-10 flex flex-col gap-4">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-2xl flex items-center justify-center flex-shrink-0 border"
                      style={{ background: `${color}10`, borderColor: `${color}28` }}>
                      <Icon className="w-5 h-5" style={{ color }}/>
                    </div>
                    <span className="font-display font-black text-foreground/20 text-4xl leading-none">{n}</span>
                  </div>
                  <div>
                    <div className="text-foreground font-semibold text-sm mb-2">{title}</div>
                    <p className="text-muted-foreground text-sm leading-relaxed">{desc}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════ */}
      {/*  CTA BANNER                                               */}
      {/* ══════════════════════════════════════════════════════════ */}
      <section className="py-20 bg-foreground overflow-hidden relative">
        <div className="absolute inset-0 opacity-[0.04]"
          style={{ backgroundImage: "linear-gradient(rgba(255,255,255,1) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,1) 1px,transparent 1px)", backgroundSize: "40px 40px" }}/>
        <div className="absolute top-0 right-0 w-[500px] h-[500px] rounded-full opacity-[0.08]"
          style={{ background: "radial-gradient(circle, #c8192e 0%, transparent 70%)" }}/>
        <div className="relative max-w-screen-xl mx-auto px-6 text-center">
          <h2 className="font-display font-black text-white text-5xl mb-4">
            Ready to bring real exam integrity<br className="hidden md:block"/> to your school?
          </h2>
          <p className="text-white/60 text-base mb-10 font-mono">
            Register your school free — your own space is ready in minutes.
          </p>
          <div className="flex flex-wrap gap-3 justify-center">
            <button onClick={() => setView("login")}
              className="inline-flex items-center gap-2 bg-primary hover:bg-primary/90 text-white px-8 py-3.5 rounded-xl text-[13px] font-mono uppercase tracking-widest transition-all shadow-md">
              <Shield className="w-4 h-4"/> Register Your School Free
            </button>
            <button onClick={() => setView("student")}
              className="inline-flex items-center gap-2 border border-white/20 text-white/70 hover:text-white hover:border-white/40 px-7 py-3.5 rounded-xl text-[13px] font-mono uppercase tracking-widest transition-all">
              <GraduationCap className="w-4 h-4"/> Student Demo
            </button>
          </div>
          <p className="text-white/25 text-[11px] font-mono mt-8">
            Content source for hero-page design · every feature listed is implemented and tested in the running system, not a concept mock-up.
          </p>
        </div>
      </section>

    </div>
  );
}

// ─── Login ────────────────────────────────────────────────────────────────────

function LoginPage({ setView }: { setView: (v: View) => void }) {
  const [role, setRole] = useState<Role>("student");
  const [step, setStep] = useState<"creds" | "face">("creds");

  return (
    <div className="min-h-screen pt-14 flex items-center justify-center bg-secondary relative overflow-hidden">
      <div className="absolute top-0 right-0 w-96 h-96 rounded-full opacity-[0.06]" style={{ background: "radial-gradient(circle,#c8192e,transparent)" }} />
      <div className="absolute bottom-0 left-0 w-80 h-80 rounded-full opacity-[0.05]" style={{ background: "radial-gradient(circle,#1a4fa8,transparent)" }} />

      <div className="relative w-full max-w-md px-6">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-primary/10 border border-primary/20 mb-4">
            <Shield className="w-7 h-7 text-primary" />
          </div>
          <h1 className="font-display font-black text-foreground text-4xl">Secure Login</h1>
          <p className="text-muted-foreground text-sm mt-1">AI ExamGuard — Arellano University</p>
        </div>

        <Card className="p-6">
          <div className="flex gap-1 bg-secondary rounded-xl p-1 mb-6">
            {(["student","instructor","admin"] as Role[]).map((r) => (
              <button key={r} onClick={() => setRole(r)}
                className={`flex-1 py-2 rounded-lg text-[11px] font-mono uppercase tracking-wider transition-all ${role === r ? "bg-primary text-white shadow" : "text-muted-foreground hover:text-foreground"}`}>
                {r}
              </button>
            ))}
          </div>

          {step === "creds" ? (
            <div className="space-y-4">
              <div>
                <label className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest block mb-1.5">Email Address</label>
                <div className="flex items-center gap-2 bg-secondary border border-border rounded-xl px-4 py-3 focus-within:border-primary/40 transition-colors">
                  <Users className="w-4 h-4 text-muted-foreground" />
                  <input className="bg-transparent text-sm text-foreground placeholder:text-muted-foreground/50 flex-1 outline-none" placeholder={`${role}@arellano.edu`} />
                </div>
              </div>
              <div>
                <label className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest block mb-1.5">Password</label>
                <div className="flex items-center gap-2 bg-secondary border border-border rounded-xl px-4 py-3 focus-within:border-primary/40 transition-colors">
                  <Lock className="w-4 h-4 text-muted-foreground" />
                  <input type="password" className="bg-transparent text-sm text-foreground placeholder:text-muted-foreground/50 flex-1 outline-none" placeholder="••••••••" />
                </div>
              </div>
              <button onClick={() => setStep("face")}
                className="w-full flex items-center justify-center gap-2 bg-primary hover:bg-primary/90 text-white py-3 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors mt-2">
                <ArrowRight className="w-4 h-4" /> Continue
              </button>
              <div className="text-center text-[11px] font-mono text-muted-foreground">JWT-secured · Role-based access control</div>
            </div>
          ) : (
            <div className="space-y-4 text-center">
              <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest">Face Verification Required</div>
              <div className="relative aspect-video bg-secondary rounded-xl overflow-hidden border border-border">
                <img src="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&h=225&fit=crop&auto=format" alt="Face verification" className="w-full h-full object-cover opacity-40" />
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="w-24 h-32 border-2 border-blue-500 rounded" style={{ boxShadow: "0 0 24px rgba(59,130,246,0.4)" }}>
                    <div className="absolute -top-6 left-0 right-0 text-center text-[9px] font-mono text-blue-600 bg-blue-50 rounded px-2 py-0.5 mx-auto w-fit">SCANNING…</div>
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="w-full h-0.5 bg-blue-400/60 animate-bounce" />
                    </div>
                  </div>
                </div>
              </div>
              <p className="text-muted-foreground text-xs">Comparing live face against your enrolled biometric profile via FaceNet</p>
              <button onClick={() => setView(role === "student" ? "student" : role === "instructor" ? "instructor" : "admin")}
                className="w-full flex items-center justify-center gap-2 bg-primary hover:bg-primary/90 text-white py-3 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors">
                <CheckCircle className="w-4 h-4" /> Verified — Enter Dashboard
              </button>
            </div>
          )}
        </Card>

        <div className="flex items-center justify-center gap-3 mt-6 text-[11px] font-mono text-muted-foreground">
          <span className="flex items-center gap-1"><Lock className="w-3 h-3" /> Encrypted</span>
          <span>·</span>
          <span className="flex items-center gap-1"><Eye className="w-3 h-3" /> Biometric</span>
          <span>·</span>
          <span className="flex items-center gap-1"><Shield className="w-3 h-3" /> JWT Auth</span>
        </div>
      </div>
    </div>
  );
}

// ─── Student Dashboard ────────────────────────────────────────────────────────

const availableExams = [
  { code: "CS411", title: "Computer Vision Fundamentals", date: "Jan 28, 2025", time: "9:00 AM",  duration: 60, status: "upcoming"  },
  { code: "CS312", title: "Machine Learning Algorithms",  date: "Jan 30, 2025", time: "1:00 PM",  duration: 90, status: "upcoming"  },
  { code: "CS201", title: "Data Structures & Algorithms", date: "Jan 22, 2025", time: "9:00 AM",  duration: 60, status: "completed" },
];

function StudentDashboard({ setView }: { setView: (v: View) => void }) {
  const [examModal, setExamModal] = useState<string | null>(null);

  const startExam = (title: string) => setExamModal(title);
  const confirmExam = () => { setExamModal(null); setView("exam"); };

  return (
    <div className="min-h-screen pt-14 bg-background">
      {examModal && (
        <PreExamModal
          examTitle={examModal}
          onConfirm={confirmExam}
          onCancel={() => setExamModal(null)}
        />
      )}
      <div className="max-w-screen-xl mx-auto px-6 py-10">
        <div className="flex items-start justify-between mb-10">
          <div>
            <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest mb-1">Student Dashboard</div>
            <h2 className="font-display font-black text-foreground text-5xl">Welcome, Maria</h2>
            <p className="text-muted-foreground text-sm mt-1">AU-2025-001 · BSCS 4-A · Arellano University</p>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => setView("enroll")}
              className="flex items-center gap-2 border border-blue-200 bg-blue-50 hover:bg-blue-100 text-blue-700 px-4 py-2.5 rounded-xl text-[12px] font-mono uppercase tracking-wider transition-colors">
              <Camera className="w-4 h-4" /> Enroll Face
            </button>
            <button onClick={() => startExam("Computer Vision Fundamentals · CS411")}
              className="flex items-center gap-2 bg-primary hover:bg-primary/90 text-white px-4 py-2.5 rounded-xl text-[12px] font-mono uppercase tracking-wider transition-colors">
              <ClipboardList className="w-4 h-4" /> Take Exam
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <div className="px-6 py-4 border-b border-border flex items-center justify-between">
                <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest">Available Exams</div>
                <span className="text-[10px] font-mono text-primary bg-primary/8 border border-primary/20 px-2 py-0.5 rounded-full">2 Upcoming</span>
              </div>
              <div className="divide-y divide-border">
                {availableExams.map((e) => (
                  <div key={e.code} className="px-6 py-4 flex items-center gap-4 hover:bg-secondary/50 transition-colors">
                    <div className="w-10 h-10 rounded-xl bg-secondary border border-border flex items-center justify-center flex-shrink-0">
                      <BookOpen className="w-5 h-5 text-blue-500" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-foreground text-sm font-medium">{e.title}</span>
                        <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${e.status === "completed" ? "text-muted-foreground border-border bg-secondary" : "text-emerald-700 border-emerald-200 bg-emerald-50"}`}>
                          {e.status}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 text-[11px] font-mono text-muted-foreground">
                        <span>{e.code}</span><span>·</span><span>{e.date}</span><span>·</span><span>{e.time}</span><span>·</span><span>{e.duration} min</span>
                      </div>
                    </div>
                    {e.status === "upcoming" ? (
                      <button onClick={() => startExam(e.title)} className="flex items-center gap-1.5 bg-primary hover:bg-primary/90 text-white text-[11px] font-mono uppercase tracking-wider px-3 py-2 rounded-lg transition-colors">
                        Start <ArrowRight className="w-3 h-3" />
                      </button>
                    ) : (
                      <button onClick={() => setView("reports")} className="flex items-center gap-1.5 border border-border hover:border-foreground/20 text-muted-foreground hover:text-foreground text-[11px] font-mono uppercase tracking-wider px-3 py-2 rounded-lg transition-colors">
                        Report
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </Card>

            <Card>
              <div className="px-6 py-4 border-b border-border">
                <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest">Last Exam — Risk Timeline</div>
              </div>
              <div className="p-6">
                <ResponsiveContainer width="100%" height={180}>
                  <AreaChart data={riskTimeline}>
                    <defs>
                      <linearGradient id="rg1" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%"  stopColor="#c8192e" stopOpacity={0.15} />
                        <stop offset="95%" stopColor="#c8192e" stopOpacity={0}    />
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="time" tick={TICK} axisLine={false} tickLine={false} />
                    <YAxis domain={[0,100]} tick={TICK} axisLine={false} tickLine={false} />
                    <Tooltip contentStyle={TT} labelStyle={TT_LABEL} />
                    <Area type="monotone" dataKey="risk" stroke="#c8192e" strokeWidth={2} fill="url(#rg1)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>

          <div className="space-y-4">
            <Card className="p-5">
              <div className="flex items-center gap-4 mb-5">
                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-500 to-primary flex items-center justify-center text-white font-display font-black text-2xl flex-shrink-0">M</div>
                <div>
                  <div className="text-foreground font-semibold">Maria Santos</div>
                  <div className="text-[11px] font-mono text-muted-foreground">AU-2025-001</div>
                  <div className="flex items-center gap-1.5 mt-1">
                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                    <span className="text-[10px] font-mono text-emerald-600">Active</span>
                  </div>
                </div>
              </div>
              <div className="space-y-2">
                {[
                  { label: "Program",       val: "BSCS"                    },
                  { label: "Year/Section",   val: "4-A"                     },
                  { label: "Email",          val: "m.santos@arellano.edu"   },
                  { label: "Enrolled Since", val: "2021"                    },
                ].map(({ label, val }) => (
                  <div key={label} className="flex justify-between text-xs">
                    <span className="text-muted-foreground">{label}</span>
                    <span className="text-foreground/80 font-mono">{val}</span>
                  </div>
                ))}
              </div>
            </Card>

            <Card className="p-5">
              <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest mb-4">Biometric Status</div>
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center justify-center">
                  <UserCheck className="w-5 h-5 text-emerald-600" />
                </div>
                <div>
                  <div className="text-foreground text-sm font-medium">Face Enrolled</div>
                  <div className="text-[11px] font-mono text-emerald-600">20/20 captures · Jan 15, 2025</div>
                </div>
              </div>
              <div className="space-y-2">
                <StatusDot on={true} label="Face encoding saved"   />
                <StatusDot on={true} label="Reference images stored" />
                <StatusDot on={true} label="Identity verified"      />
              </div>
              <button onClick={() => setView("enroll")} className="w-full mt-4 border border-border hover:border-foreground/20 text-muted-foreground hover:text-foreground text-[11px] font-mono uppercase tracking-wider py-2 rounded-xl transition-colors">
                Re-enroll
              </button>
            </Card>

            <Card className="p-5">
              <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest mb-4">My Stats</div>
              <div className="grid grid-cols-2 gap-3">
                {[
                  { val: "3",    label: "Exams Taken", color: "text-blue-600"    },
                  { val: "85%",  label: "Avg Score",   color: "text-emerald-600" },
                  { val: "LOW",  label: "Avg Risk",    color: "text-emerald-600" },
                  { val: "2",    label: "Violations",  color: "text-orange-600"  },
                ].map(({ val, label, color }) => (
                  <div key={label} className="bg-secondary border border-border rounded-xl p-3 text-center">
                    <div className={`font-display text-2xl font-black ${color}`}>{val}</div>
                    <div className="text-[10px] font-mono text-muted-foreground mt-0.5">{label}</div>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Face Enrollment ──────────────────────────────────────────────────────────

function FaceEnrollment() {
  const [captures, setCaptures] = useState(0);
  const [phase, setPhase] = useState<"ready"|"capturing"|"processing"|"done">("ready");

  const startCapture = () => {
    setPhase("capturing"); setCaptures(0);
    const iv = setInterval(() => {
      setCaptures((c) => {
        if (c >= 19) { clearInterval(iv); setPhase("processing"); setTimeout(() => setPhase("done"), 2000); return 20; }
        return c + 1;
      });
    }, 300);
  };

  return (
    <div className="min-h-screen pt-14 bg-background">
      <div className="max-w-3xl mx-auto px-6 py-10">
        <div className="mb-8">
          <SectionTag text="Biometric Enrollment" />
          <h2 className="font-display font-black text-foreground text-5xl">Face Enrollment</h2>
          <p className="text-muted-foreground text-sm mt-2">We capture 20 reference images and extract your FaceNet encoding for secure identity verification.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card className="overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-2.5 border-b border-border bg-secondary">
              <div className={`w-2 h-2 rounded-full ${phase === "capturing" ? "bg-primary animate-pulse" : phase === "done" ? "bg-emerald-500" : "bg-muted-foreground"}`} />
              <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest">
                {phase === "ready" ? "Camera Ready" : phase === "capturing" ? `Capturing ${captures}/20` : phase === "processing" ? "Extracting Encoding…" : "Enrollment Complete"}
              </span>
            </div>
            <div className="relative aspect-video bg-secondary flex items-center justify-center">
              <img src="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&h=225&fit=crop&auto=format" alt="Webcam" className="w-full h-full object-cover opacity-40" />
              <div className="absolute inset-0 flex items-center justify-center">
                {phase !== "done" ? (
                  <div className={`w-28 h-36 border-2 ${phase === "capturing" ? "border-primary" : "border-blue-500"} rounded`}
                    style={{ boxShadow: phase === "capturing" ? "0 0 24px rgba(200,25,46,0.35)" : "0 0 24px rgba(59,130,246,0.3)" }}>
                    {phase === "capturing" && <div className="absolute inset-0 overflow-hidden"><div className="w-full h-0.5 bg-primary/60 animate-bounce" /></div>}
                  </div>
                ) : (
                  <div className="w-28 h-36 border-2 border-emerald-500 rounded flex items-center justify-center" style={{ boxShadow: "0 0 24px rgba(16,185,129,0.35)" }}>
                    <CheckCircle className="w-10 h-10 text-emerald-500" />
                  </div>
                )}
              </div>
              {captures > 0 && (
                <div className="absolute bottom-2 right-2 grid grid-cols-5 gap-0.5">
                  {Array.from({ length: 20 }).map((_, i) => (
                    <div key={i} className={`w-4 h-4 rounded-sm ${i < captures ? "bg-primary" : "bg-black/10"}`} />
                  ))}
                </div>
              )}
            </div>
            {phase !== "done" && (
              <div className="p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[11px] font-mono text-muted-foreground">Progress</span>
                  <span className="text-[11px] font-mono text-foreground">{captures}/20</span>
                </div>
                <div className="h-1.5 bg-black/8 rounded-full overflow-hidden">
                  <div className="h-full bg-primary rounded-full transition-all duration-300" style={{ width: `${(captures/20)*100}%` }} />
                </div>
              </div>
            )}
          </Card>

          <div className="space-y-4">
            <Card className="p-5">
              <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest mb-4">Enrollment Process</div>
              <div className="space-y-3">
                {[
                  { step: "Open Webcam",                done: phase !== "ready"  },
                  { step: "Capture 20 Reference Images", done: captures === 20    },
                  { step: "Extract FaceNet Encoding",    done: phase === "done"   },
                  { step: "Link to Student ID",          done: phase === "done"   },
                  { step: "Save Reference Images",       done: phase === "done"   },
                  { step: "Enrollment Complete",         done: phase === "done"   },
                ].map(({ step, done }, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <div className={`w-5 h-5 rounded-full border flex items-center justify-center flex-shrink-0 ${done ? "bg-emerald-50 border-emerald-200" : "border-border"}`}>
                      {done ? <CheckCircle className="w-3 h-3 text-emerald-600" /> : <Circle className="w-3 h-3 text-muted-foreground/30" />}
                    </div>
                    <span className={`text-sm ${done ? "text-foreground" : "text-muted-foreground/50"}`}>{step}</span>
                  </div>
                ))}
              </div>
            </Card>

            <Card className="p-5">
              <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest mb-3">What We Store</div>
              <div className="space-y-2">
                {[
                  { icon: Brain,  label: "Face Encoding (128-dim vector)", ok: true  },
                  { icon: Users,  label: "Student ID reference link",      ok: true  },
                  { icon: Camera, label: "20 reference images",            ok: true  },
                  { icon: X,      label: "Raw video footage — not stored", ok: false },
                ].map(({ icon: Icon, label, ok }) => (
                  <div key={label} className="flex items-center gap-2.5">
                    <Icon className={`w-4 h-4 flex-shrink-0 ${ok ? "text-blue-500" : "text-muted-foreground/30"}`} />
                    <span className={`text-xs ${ok ? "text-foreground/80" : "text-muted-foreground/40 line-through"}`}>{label}</span>
                  </div>
                ))}
              </div>
            </Card>

            {phase === "done" ? (
              <div className="flex items-center gap-3 p-4 bg-emerald-50 border border-emerald-200 rounded-xl">
                <CheckCircle className="w-5 h-5 text-emerald-600" />
                <div>
                  <div className="text-foreground text-sm font-medium">Enrollment Successful</div>
                  <div className="text-[11px] font-mono text-emerald-600">20 captures · FaceNet encoding saved</div>
                </div>
              </div>
            ) : (
              <button onClick={startCapture} disabled={phase === "capturing" || phase === "processing"}
                className="w-full flex items-center justify-center gap-2 bg-primary hover:bg-primary/90 disabled:opacity-50 text-white py-3 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors">
                <Camera className="w-4 h-4" />
                {phase === "ready" ? "Start Enrollment" : phase === "capturing" ? `Capturing ${captures}/20…` : "Processing…"}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Exam Room ────────────────────────────────────────────────────────────────

function ExamRoom({ setView }: { setView: (v: View) => void }) {
  const [current, setCurrent] = useState(0);
  const [answers, setAnswers] = useState<Record<number,number|string>>({});
  const [identInput, setIdentInput] = useState("");
  const [time, setTime] = useState(3417);
  const [showGuide, setShowGuide] = useState(true);
  const riskVal = 12;

  useEffect(() => {
    const id = setInterval(() => setTime((t) => Math.max(0, t - 1)), 1000);
    return () => clearInterval(id);
  }, []);

  const mm = String(Math.floor(time / 60)).padStart(2, "0");
  const ss = String(time % 60).padStart(2, "0");
  const q = examQuestions[current];

  return (
    <div className="min-h-screen pt-14 bg-background flex flex-col">
      {showGuide && (
        <PreExamModal
          examTitle="Computer Vision Fundamentals · CS411"
          onConfirm={() => setShowGuide(false)}
          onCancel={() => setView("student")}
        />
      )}
      <div className="border-b border-border bg-card px-6 py-3 flex items-center gap-4 flex-shrink-0 shadow-sm">
        <div className="flex-1">
          <div className="text-foreground text-sm font-semibold">Computer Vision Fundamentals · CS411</div>
          <div className="text-[11px] font-mono text-muted-foreground">Dr. Roberto Lim · BSCS 4-A</div>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-center">
            <div className="font-mono text-2xl font-bold text-foreground">{mm}:{ss}</div>
            <div className="text-[10px] font-mono text-muted-foreground">Remaining</div>
          </div>
          <div className="w-px h-8 bg-border" />
          <RiskPill value={riskVal} />
          <div className="w-px h-8 bg-border" />
          <StatusDot on={true} label="Face Verified" />
          <StatusDot on={true} label="Camera Active" />
        </div>
      </div>

      <div className="flex flex-1 max-w-screen-xl mx-auto w-full px-6 py-8 gap-8">
        <div className="flex-1 space-y-6">
          <div className="flex flex-wrap gap-2">
            {examQuestions.map((_, i) => (
              <button key={i} onClick={() => setCurrent(i)}
                className={`w-9 h-9 rounded-xl text-sm font-mono font-bold transition-all ${
                  i === current        ? "bg-primary text-white"
                : answers[i] !== undefined ? "bg-blue-50 border border-blue-200 text-blue-700"
                : "bg-secondary border border-border text-muted-foreground hover:border-foreground/20 hover:text-foreground"
                }`}>
                {i + 1}
              </button>
            ))}
          </div>

          <Card className="p-6">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-8 h-8 rounded-xl bg-primary/8 border border-primary/20 flex items-center justify-center">
                <span className="text-primary font-mono font-bold text-sm">{current + 1}</span>
              </div>
              <span className={`text-[10px] font-mono px-2 py-0.5 rounded border uppercase tracking-wider ${
                q.type === "mcq"            ? "text-blue-700 border-blue-200 bg-blue-50"
              : q.type === "tf"             ? "text-emerald-700 border-emerald-200 bg-emerald-50"
              :                               "text-orange-700 border-orange-200 bg-orange-50"
              }`}>
                {q.type === "mcq" ? "Multiple Choice" : q.type === "tf" ? "True / False" : "Identification"}
              </span>
            </div>

            <p className="text-foreground text-base leading-relaxed mb-6">{q.question}</p>

            {q.type === "identification" ? (
              <input
                className="w-full bg-secondary border border-border rounded-xl px-4 py-3 text-foreground text-sm placeholder:text-muted-foreground/50 outline-none focus:border-primary/40 transition-colors font-mono"
                placeholder="Type your answer here…"
                value={identInput}
                onChange={(e) => { setIdentInput(e.target.value); setAnswers((a) => ({ ...a, [current]: e.target.value })); }}
              />
            ) : (
              <div className="space-y-3">
                {q.choices.map((choice, ci) => (
                  <button key={ci} onClick={() => setAnswers((a) => ({ ...a, [current]: ci }))}
                    className={`w-full flex items-center gap-4 px-4 py-3.5 rounded-xl border text-sm text-left transition-all ${
                      answers[current] === ci
                        ? "bg-primary/8 border-primary/30 text-foreground"
                        : "bg-secondary border-border text-foreground/70 hover:border-foreground/20 hover:text-foreground"
                    }`}>
                    <div className={`w-5 h-5 rounded-full border flex-shrink-0 flex items-center justify-center ${answers[current] === ci ? "border-primary bg-primary" : "border-border"}`}>
                      {answers[current] === ci && <div className="w-2 h-2 rounded-full bg-white" />}
                    </div>
                    {choice}
                  </button>
                ))}
              </div>
            )}

            <div className="flex justify-between mt-6 pt-5 border-t border-border">
              <button onClick={() => setCurrent((c) => Math.max(0, c - 1))} disabled={current === 0}
                className="px-4 py-2 border border-border hover:border-foreground/20 disabled:opacity-30 text-muted-foreground hover:text-foreground rounded-xl text-sm font-mono uppercase tracking-wider transition-colors">
                ← Previous
              </button>
              {current < examQuestions.length - 1 ? (
                <button onClick={() => setCurrent((c) => c + 1)}
                  className="px-4 py-2 bg-primary hover:bg-primary/90 text-white rounded-xl text-sm font-mono uppercase tracking-wider transition-colors">
                  Next →
                </button>
              ) : (
                <button onClick={() => setView("reports")}
                  className="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-sm font-mono uppercase tracking-wider transition-colors">
                  Submit Exam
                </button>
              )}
            </div>
          </Card>
        </div>

        <div className="w-64 flex-shrink-0 space-y-4">
          <Card className="overflow-hidden">
            <div className="flex items-center gap-2 px-3 py-2 border-b border-border bg-secondary">
              <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
              <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest">AI Monitor</span>
            </div>
            <div className="relative aspect-[4/3] bg-secondary overflow-hidden">
              <img src="https://images.unsplash.com/photo-1434030216411-0b793f4b4173?w=256&h=192&fit=crop&auto=format" alt="Monitoring" className="w-full h-full object-cover opacity-50" />
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-16 h-20 border border-emerald-500/80 rounded" style={{ boxShadow: "0 0 12px rgba(16,185,129,0.3)" }} />
              </div>
              <div className="absolute bottom-2 left-2 right-2 bg-white/80 backdrop-blur rounded-lg px-2 py-1.5">
                <div className="text-[9px] font-mono text-muted-foreground">Risk</div>
                <div className="flex items-end gap-1">
                  <span className="font-display text-2xl font-black text-emerald-600">12</span>
                  <span className="text-[9px] font-mono text-emerald-600 mb-1">LOW</span>
                </div>
              </div>
            </div>
          </Card>

          <Card className="p-4 space-y-2.5">
            <div className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest">Detection Status</div>
            {[
              { label: "Face Detected",    ok: true  },
              { label: "Identity Match",   ok: true  },
              { label: "Phone",            ok: false },
              { label: "Multiple Persons", ok: false },
              { label: "Fullscreen Active",ok: true  },
              { label: "Tab Focus",        ok: true  },
            ].map(({ label, ok }) => (
              <div key={label} className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">{label}</span>
                <span className={`text-[10px] font-mono font-bold ${ok ? "text-emerald-600" : "text-red-600"}`}>{ok ? "OK" : "ALERT"}</span>
              </div>
            ))}
          </Card>

          <Card className="p-4">
            <div className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest mb-3">LSTM Prediction</div>
            <div className="text-center">
              <div className="font-display text-4xl font-black text-emerald-600">8%</div>
              <div className="text-[11px] font-mono text-muted-foreground mt-1">Cheating Probability</div>
            </div>
            <RiskBar value={8} showLabel={false} />
          </Card>
        </div>
      </div>
    </div>
  );
}

// ─── Instructor Dashboard ─────────────────────────────────────────────────────

function InstructorDashboard({ setView }: { setView: (v: View) => void }) {
  const [tick, setTick] = useState(0);
  useEffect(() => { const id = setInterval(() => setTick((t) => t + 1), 3000); return () => clearInterval(id); }, []);
  const crit = liveStudents.find((s) => s.status === "critical");

  return (
    <div className="min-h-screen pt-14 bg-background">
      <div className="max-w-screen-xl mx-auto px-6 py-10">
        <div className="flex items-start justify-between mb-10">
          <div>
            <SectionTag text="Instructor Dashboard" />
            <h2 className="font-display font-black text-foreground text-5xl">Live Sessions</h2>
            <p className="text-muted-foreground text-sm mt-1">Computer Vision Fundamentals · CS411 · Jan 28, 2025</p>
          </div>
          <div className="flex items-center gap-2 bg-emerald-50 border border-emerald-200 rounded-xl px-4 py-2.5">
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-emerald-700 text-[12px] font-mono uppercase tracking-widest">WebSocket · Live</span>
          </div>
        </div>

        {crit && (
          <div className="mb-6 flex items-center gap-4 bg-red-50 border border-red-200 rounded-xl px-5 py-4">
            <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0" />
            <div className="flex-1">
              <div className="text-foreground text-sm font-semibold">CRITICAL — {crit.name} ({crit.id})</div>
              <div className="text-red-600 text-[11px] font-mono mt-0.5">Identity mismatch detected · Risk Score: {crit.risk} · Email sent to instructor</div>
            </div>
            <button onClick={() => setView("reports")} className="bg-primary hover:bg-primary/90 text-white text-[11px] font-mono uppercase tracking-wider px-4 py-2 rounded-xl transition-colors">
              View Report
            </button>
          </div>
        )}

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[
            { val: liveStudents.length,                                                      label: "Active Sessions", color: "text-blue-600"    },
            { val: liveStudents.filter((s) => s.status === "safe").length,                   label: "Safe",           color: "text-emerald-600" },
            { val: liveStudents.filter((s) => ["medium","high"].includes(s.status)).length,  label: "Flagged",        color: "text-orange-600"  },
            { val: liveStudents.filter((s) => s.status === "critical").length,               label: "Critical",       color: "text-red-600"     },
          ].map(({ val, label, color }) => (
            <Card key={label} className="p-5">
              <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest mb-2">{label}</div>
              <div className={`font-display text-4xl font-black ${color}`}>{val}</div>
            </Card>
          ))}
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className="xl:col-span-2">
            <Card>
              <div className="px-6 py-4 border-b border-border flex items-center justify-between">
                <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest">Examinee Risk Monitor</div>
                <div className="text-[10px] font-mono text-muted-foreground">Updated {tick}s ago</div>
              </div>
              <div className="divide-y divide-border">
                {liveStudents.map((s) => (
                  <div key={s.id} className={`px-6 py-4 flex items-center gap-4 hover:bg-secondary/50 transition-colors ${s.status === "critical" ? "bg-red-50/60" : ""}`}>
                    <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-100 to-red-100 flex items-center justify-center text-foreground font-display font-black text-sm flex-shrink-0 border border-border">
                      {s.name[0]}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-foreground text-sm font-medium">{s.name}</span>
                        <RiskPill value={s.risk} />
                      </div>
                      <div className="flex items-center gap-3 text-[10px] font-mono text-muted-foreground">
                        <span>{s.id}</span>
                        <span className={s.face ? "text-emerald-600" : "text-red-600"}>Face:{s.face ? "✓" : "✗"}</span>
                        <span className={s.phone ? "text-red-600" : "text-muted-foreground"}>Phone:{s.phone ? "!" : "–"}</span>
                        <span className={s.tab ? "text-orange-600" : "text-muted-foreground"}>Tab:{s.tab ? "!" : "–"}</span>
                        <span className="text-blue-600">LSTM:{s.lstm}%</span>
                      </div>
                    </div>
                    <div className="w-24"><RiskBar value={s.risk} /></div>
                    <button onClick={() => setView("monitor")} className="text-muted-foreground hover:text-foreground transition-colors ml-2">
                      <Eye className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            </Card>
          </div>

          <div className="space-y-4">
            <Card className="p-5">
              <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest mb-4">Session Alerts</div>
              <div className="space-y-2">
                {[
                  { t: "09:34:53", msg: "Identity mismatch · Carlos Mendoza", type: "critical" },
                  { t: "09:30:17", msg: "Face loss · Carlos Mendoza",          type: "high"     },
                  { t: "09:21:33", msg: "Tab switch · Jenny Flores",           type: "warn"     },
                  { t: "09:15:08", msg: "Phone detected · Juan dela Cruz",     type: "high"     },
                  { t: "09:12:44", msg: "Tab switch · Juan dela Cruz",         type: "warn"     },
                  { t: "09:01:00", msg: "All identities verified",             type: "ok"       },
                ].map((a, i) => (
                  <div key={i} className="flex items-start gap-2.5 py-1.5 border-b border-border last:border-0">
                    <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 mt-1.5 ${a.type === "critical" ? "bg-red-500" : a.type === "high" ? "bg-orange-400" : a.type === "warn" ? "bg-blue-400" : "bg-emerald-500"}`} />
                    <div className="flex-1">
                      <div className="text-xs text-foreground/80">{a.msg}</div>
                      <div className="font-mono text-[10px] text-muted-foreground">{a.t}</div>
                    </div>
                  </div>
                ))}
              </div>
            </Card>

            <Card className="p-5">
              <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest mb-4">Violation Breakdown</div>
              <ResponsiveContainer width="100%" height={160}>
                <RPie>
                  <Pie data={violationBreakdown} cx="50%" cy="50%" innerRadius={40} outerRadius={70} dataKey="value" paddingAngle={3}>
                    {violationBreakdown.map((e, i) => <Cell key={i} fill={e.fill} />)}
                  </Pie>
                  <Tooltip contentStyle={TT} labelStyle={TT_LABEL} />
                </RPie>
              </ResponsiveContainer>
              <div className="space-y-1.5 mt-1">
                {violationBreakdown.map((v) => (
                  <div key={v.name} className="flex items-center justify-between">
                    <div className="flex items-center gap-2"><div className="w-2 h-2 rounded-full" style={{ backgroundColor: v.fill }} /><span className="text-[11px] text-muted-foreground">{v.name}</span></div>
                    <span className="font-mono text-[11px] text-foreground/70">{v.value}%</span>
                  </div>
                ))}
              </div>
            </Card>

            <div className="grid grid-cols-2 gap-3">
              <button onClick={() => setView("reports")} className="flex flex-col items-center gap-1.5 p-4 bg-card border border-border hover:border-foreground/15 rounded-xl transition-colors">
                <FileText className="w-5 h-5 text-blue-500" /><span className="text-[11px] font-mono text-muted-foreground">Reports</span>
              </button>
              <button onClick={() => setView("analytics")} className="flex flex-col items-center gap-1.5 p-4 bg-card border border-border hover:border-foreground/15 rounded-xl transition-colors">
                <BarChart3 className="w-5 h-5 text-primary" /><span className="text-[11px] font-mono text-muted-foreground">Analytics</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Admin Dashboard ──────────────────────────────────────────────────────────

function AdminDashboard() {
  const [tab, setTab] = useState<"users"|"exams"|"system">("users");
  const [search, setSearch] = useState("");
  const filtered = adminUsers.filter((u) => u.name.toLowerCase().includes(search.toLowerCase()) || u.role.includes(search.toLowerCase()));

  return (
    <div className="min-h-screen pt-14 bg-background">
      <div className="max-w-screen-xl mx-auto px-6 py-10">
        <div className="flex items-start justify-between mb-10">
          <div>
            <SectionTag text="Administrator" />
            <h2 className="font-display font-black text-foreground text-5xl">Admin Dashboard</h2>
            <p className="text-muted-foreground text-sm mt-1">System management · Arellano University AI ExamGuard</p>
          </div>
          <div className="flex items-center gap-2">
            <button className="flex items-center gap-2 border border-border hover:border-foreground/20 text-muted-foreground hover:text-foreground text-[12px] font-mono uppercase tracking-wider px-4 py-2.5 rounded-xl transition-colors">
              <Upload className="w-4 h-4" /> Import CSV
            </button>
            <button className="flex items-center gap-2 bg-primary hover:bg-primary/90 text-white text-[12px] font-mono uppercase tracking-wider px-4 py-2.5 rounded-xl transition-colors">
              <Plus className="w-4 h-4" /> Add User
            </button>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[
            { val: "148",   label: "Total Students", icon: GraduationCap, color: "text-blue-600"    },
            { val: "12",    label: "Instructors",    icon: Users,          color: "text-emerald-600" },
            { val: "24",    label: "Active Exams",   icon: ClipboardList,  color: "text-orange-600"  },
            { val: "98.2%", label: "System Uptime",  icon: Activity,       color: "text-primary"     },
          ].map(({ val, label, icon: Icon, color }) => (
            <Card key={label} className="p-5 flex items-center gap-4">
              <div className="w-10 h-10 rounded-xl bg-secondary border border-border flex items-center justify-center flex-shrink-0">
                <Icon className={`w-5 h-5 ${color}`} />
              </div>
              <div>
                <div className={`font-display text-3xl font-black ${color}`}>{val}</div>
                <div className="text-[11px] font-mono text-muted-foreground">{label}</div>
              </div>
            </Card>
          ))}
        </div>

        <div className="flex gap-1 bg-secondary border border-border rounded-xl p-1 mb-6 w-fit">
          {(["users","exams","system"] as const).map((t) => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-5 py-2 rounded-lg text-[12px] font-mono uppercase tracking-wider transition-all ${tab === t ? "bg-primary text-white" : "text-muted-foreground hover:text-foreground"}`}>
              {t}
            </button>
          ))}
        </div>

        {tab === "users" && (
          <Card>
            <div className="px-6 py-4 border-b border-border flex items-center gap-4">
              <div className="flex items-center gap-2 bg-secondary border border-border rounded-xl px-3 py-2 flex-1 max-w-sm">
                <Search className="w-4 h-4 text-muted-foreground" />
                <input className="bg-transparent text-sm text-foreground placeholder:text-muted-foreground/50 flex-1 outline-none font-mono" placeholder="Search users…" value={search} onChange={(e) => setSearch(e.target.value)} />
              </div>
              <button className="flex items-center gap-1.5 border border-border hover:border-foreground/20 text-muted-foreground hover:text-foreground text-[11px] font-mono px-3 py-2 rounded-xl transition-colors">
                <Filter className="w-3.5 h-3.5" /> Filter
              </button>
            </div>
            <div className="divide-y divide-border">
              <div className="grid grid-cols-6 gap-4 px-6 py-2.5 text-[10px] font-mono text-muted-foreground uppercase tracking-widest">
                <span className="col-span-2">Name</span><span>Role</span><span>Email</span><span>Biometric</span><span>Actions</span>
              </div>
              {filtered.map((u) => (
                <div key={u.id} className="grid grid-cols-6 gap-4 px-6 py-4 items-center hover:bg-secondary/50 transition-colors">
                  <div className="col-span-2 flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-100 to-red-100 flex items-center justify-center text-foreground font-display font-bold text-sm border border-border">
                      {u.name[0]}
                    </div>
                    <div>
                      <div className="text-foreground text-sm">{u.name}</div>
                      <div className={`text-[10px] font-mono ${u.status === "suspended" ? "text-red-600" : "text-emerald-600"}`}>{u.status}</div>
                    </div>
                  </div>
                  <span className={`text-[11px] font-mono px-2 py-0.5 rounded border w-fit ${u.role === "student" ? "text-blue-700 border-blue-200 bg-blue-50" : u.role === "instructor" ? "text-emerald-700 border-emerald-200 bg-emerald-50" : "text-purple-700 border-purple-200 bg-purple-50"}`}>
                    {u.role}
                  </span>
                  <span className="text-[11px] font-mono text-muted-foreground truncate">{u.email}</span>
                  <div className="flex items-center gap-1.5">
                    {u.enrolled
                      ? <span className="flex items-center gap-1 text-[10px] font-mono text-emerald-600"><CheckCircle className="w-3 h-3" /> Enrolled</span>
                      : <span className="flex items-center gap-1 text-[10px] font-mono text-muted-foreground"><AlertCircle className="w-3 h-3" /> Pending</span>}
                  </div>
                  <div className="flex items-center gap-2">
                    <button className="text-muted-foreground hover:text-foreground transition-colors"><Edit2 className="w-4 h-4" /></button>
                    <button className="text-muted-foreground hover:text-red-600 transition-colors"><Trash2 className="w-4 h-4" /></button>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}

        {tab === "exams" && (
          <Card>
            <div className="px-6 py-4 border-b border-border"><div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest">Published Examinations</div></div>
            <div className="divide-y divide-border">
              {[
                { code: "CS411", title: "Computer Vision Fundamentals", instructor: "Dr. Roberto Lim",   date: "Jan 28, 2025", enrolled: 32, sessions: 7,  status: "live"      },
                { code: "CS312", title: "Machine Learning Algorithms",  instructor: "Prof. Clara Diaz",  date: "Jan 30, 2025", enrolled: 28, sessions: 0,  status: "scheduled" },
                { code: "CS201", title: "Data Structures & Algorithms", instructor: "Dr. Roberto Lim",   date: "Jan 22, 2025", enrolled: 35, sessions: 35, status: "completed" },
              ].map((e) => (
                <div key={e.code} className="px-6 py-4 flex items-center gap-4 hover:bg-secondary/50 transition-colors">
                  <div className="w-10 h-10 rounded-xl bg-secondary border border-border flex items-center justify-center flex-shrink-0">
                    <BookOpen className="w-5 h-5 text-blue-500" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-foreground text-sm font-medium">{e.title}</span>
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${e.status === "live" ? "text-primary border-primary/25 bg-primary/8" : e.status === "scheduled" ? "text-blue-700 border-blue-200 bg-blue-50" : "text-muted-foreground border-border bg-secondary"}`}>
                        {e.status}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-[11px] font-mono text-muted-foreground">
                      <span>{e.code}</span><span>·</span><span>{e.instructor}</span><span>·</span><span>{e.date}</span><span>·</span><span>{e.enrolled} enrolled</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-display text-2xl font-black text-foreground">{e.sessions}</div>
                    <div className="text-[10px] font-mono text-muted-foreground">Sessions</div>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}

        {tab === "system" && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[
              { label: "YOLOv8 Engine",      metric: "28–30 FPS",   detail: "v8.0.196 · COCO weights"        },
              { label: "FaceNet Service",     metric: "< 80ms",      detail: "face_recognition 1.3.0"         },
              { label: "LSTM Predictor",      metric: "94.2% Acc",   detail: "Keras 2.x · 30s window"         },
              { label: "Risk Engine",         metric: "< 10ms",      detail: "Scikit-learn 1.4"               },
              { label: "PostgreSQL DB",       metric: "2.4 ms avg",  detail: "16 tables · 1.2GB"              },
              { label: "WebSocket Server",    metric: "7 active",    detail: "FastAPI WS · 100ms poll"        },
            ].map(({ label, metric, detail }) => (
              <Card key={label} className="p-5 flex items-center gap-4">
                <div className="w-10 h-10 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center justify-center flex-shrink-0">
                  <div className="w-3 h-3 rounded-full bg-emerald-500" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-foreground text-sm font-medium">{label}</span>
                    <span className="text-[10px] font-mono text-emerald-600">● online</span>
                  </div>
                  <div className="text-[11px] font-mono text-muted-foreground">{detail}</div>
                </div>
                <div className="font-mono text-sm text-foreground font-bold">{metric}</div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── AI Monitor ───────────────────────────────────────────────────────────────

function AIMonitor() {
  const [selected, setSelected] = useState(liveStudents[1]);
  const [riskAnim, setRiskAnim] = useState(selected.risk);
  useEffect(() => {
    const id = setInterval(() => setRiskAnim((r) => Math.max(0, Math.min(100, r + (Math.random() > 0.5 ? 2 : -1)))), 800);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="min-h-screen pt-14 bg-background">
      <div className="max-w-screen-xl mx-auto px-6 py-10">
        <div className="mb-8 flex items-start justify-between">
          <div>
            <SectionTag text="Live AI Monitoring" />
            <h2 className="font-display font-black text-foreground text-5xl">AI Monitor</h2>
            <p className="text-muted-foreground text-sm mt-1">Per-session real-time detection feed — Phase 8 &amp; 9</p>
          </div>
          <div className="flex items-center gap-2 bg-primary/8 border border-primary/20 rounded-xl px-4 py-2">
            <Radio className="w-4 h-4 text-primary" />
            <span className="text-primary text-[12px] font-mono uppercase tracking-widest">LIVE · Every Frame</span>
          </div>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
          <div className="xl:col-span-1 space-y-2">
            <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest mb-3">Active Sessions</div>
            {liveStudents.map((s) => (
              <button key={s.id} onClick={() => { setSelected(s); setRiskAnim(s.risk); }}
                className={`w-full flex items-center gap-3 p-3 rounded-xl border text-left transition-all ${selected.id === s.id ? "bg-primary/8 border-primary/30" : "bg-card border-border hover:border-foreground/15"}`}>
                <div className={`w-2 h-2 rounded-full flex-shrink-0 ${s.status === "safe" ? "bg-emerald-500" : s.status === "medium" ? "bg-orange-400" : s.status === "high" ? "bg-red-400" : "bg-red-500 animate-pulse"}`} />
                <div className="flex-1 min-w-0">
                  <div className="text-foreground text-xs font-medium truncate">{s.name}</div>
                  <div className="font-mono text-[10px] text-muted-foreground">{s.id}</div>
                </div>
                <span className={`font-mono text-sm font-bold ${s.risk < 25 ? "text-emerald-600" : s.risk < 50 ? "text-blue-600" : s.risk < 75 ? "text-orange-600" : "text-red-600"}`}>{s.risk}</span>
              </button>
            ))}
          </div>

          <div className="xl:col-span-2 space-y-4">
            <Card className="overflow-hidden">
              <div className="flex items-center gap-3 px-4 py-2.5 border-b border-border bg-secondary">
                <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest">{selected.name} · {selected.id}</span>
                <div className="ml-auto"><StatusDot on={true} label="30 FPS" /></div>
              </div>
              <div className="relative aspect-video bg-secondary overflow-hidden">
                <img src="https://images.unsplash.com/photo-1488190211105-8b0e65b80b4e?w=640&h=360&fit=crop&auto=format" alt="Live monitoring" className="w-full h-full object-cover opacity-50" />
                <div className="absolute top-8 left-1/2 -translate-x-1/2 w-28 h-36">
                  <div className={`absolute inset-0 border-2 ${selected.face ? "border-emerald-500" : "border-red-500"} rounded`}
                    style={{ boxShadow: selected.face ? "0 0 20px rgba(16,185,129,0.4)" : "0 0 20px rgba(239,68,68,0.4)" }}>
                    {[["top-0 left-0","border-t-2 border-l-2"],["top-0 right-0","border-t-2 border-r-2"],["bottom-0 left-0","border-b-2 border-l-2"],["bottom-0 right-0","border-b-2 border-r-2"]].map(([pos,cls],i) => (
                      <div key={i} className={`absolute w-3.5 h-3.5 ${pos} ${cls} ${selected.face ? "border-emerald-500" : "border-red-500"}`} />
                    ))}
                  </div>
                  <div className="absolute -top-6 left-0 right-0 text-center">
                    <span className={`text-[9px] font-mono px-2 py-0.5 rounded-full border ${selected.face ? "text-emerald-700 bg-emerald-50 border-emerald-200" : "text-red-700 bg-red-50 border-red-200"}`}>
                      {selected.face ? "VERIFIED ✓" : "FACE LOST ✗"}
                    </span>
                  </div>
                </div>
                {selected.phone && (
                  <div className="absolute bottom-12 right-12 w-16 h-28 border-2 border-red-500 rounded" style={{ boxShadow: "0 0 16px rgba(239,68,68,0.5)" }}>
                    <div className="absolute -top-5 left-0 right-0 text-center">
                      <span className="text-[9px] font-mono text-red-700 bg-red-50 border border-red-200 px-1.5 py-0.5 rounded">PHONE</span>
                    </div>
                  </div>
                )}
                <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent px-4 py-3 flex justify-between items-end">
                  <div>
                    <div className="text-[9px] font-mono text-white/70 uppercase">Live Risk</div>
                    <div className={`font-display text-4xl font-black ${riskAnim < 25 ? "text-emerald-400" : riskAnim < 75 ? "text-orange-300" : "text-red-400"}`}>{Math.round(riskAnim)}</div>
                  </div>
                  <RiskPill value={Math.round(riskAnim)} />
                </div>
              </div>
            </Card>

            <Card className="p-5">
              <div className="flex items-center justify-between mb-3">
                <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest">Composite Risk Score</div>
                <span className="font-display text-2xl font-black text-foreground">{Math.round(riskAnim)}</span>
              </div>
              <RiskBar value={Math.round(riskAnim)} showLabel={false} />
              <div className="flex justify-between mt-1.5 text-[10px] font-mono text-muted-foreground">
                <span>0 — SAFE</span><span>50 — MEDIUM</span><span>100 — CRITICAL</span>
              </div>
            </Card>
          </div>

          <div className="xl:col-span-1 space-y-4">
            {[
              { icon: Eye,     label: "Face Module",    color: "text-blue-600",   items: [{ l: "Face Present", v: selected.face },{ l: "Identity Match", v: selected.status !== "critical" },{ l: "Single Person", v: !selected.phone }] },
              { icon: Target,  label: "YOLOv8 Module",  color: "text-orange-600", items: [{ l: "Phone", v: !selected.phone },{ l: "Book", v: true },{ l: "Multiple People", v: true },{ l: "Laptop", v: true }] },
              { icon: Monitor, label: "Browser Monitor",color: "text-purple-600", items: [{ l: "Tab Focus", v: !selected.tab },{ l: "Fullscreen", v: true },{ l: "Copy/Paste", v: true },{ l: "Right Click", v: true }] },
            ].map(({ icon: Icon, label, color, items }) => (
              <Card key={label} className="p-4">
                <div className="flex items-center gap-2 mb-3">
                  <Icon className={`w-4 h-4 ${color}`} />
                  <span className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest">{label}</span>
                </div>
                <div className="space-y-2">
                  {items.map(({ l, v }) => (
                    <div key={l} className="flex items-center justify-between">
                      <span className="text-xs text-muted-foreground">{l}</span>
                      <span className={`text-[10px] font-mono font-bold ${v ? "text-emerald-600" : "text-red-600"}`}>{v ? "OK" : "ALERT"}</span>
                    </div>
                  ))}
                </div>
              </Card>
            ))}

            <Card className="p-4">
              <div className="flex items-center gap-2 mb-3">
                <Brain className="w-4 h-4 text-primary" />
                <span className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest">LSTM Prediction</span>
              </div>
              <div className="text-center my-2">
                <div className={`font-display text-4xl font-black ${selected.lstm < 40 ? "text-emerald-600" : selected.lstm < 70 ? "text-orange-600" : "text-red-600"}`}>{selected.lstm}%</div>
                <div className="text-[11px] font-mono text-muted-foreground mt-1">Cheating Probability</div>
              </div>
              <RiskBar value={selected.lstm} showLabel={false} />
              <div className="mt-3 text-[10px] font-mono text-muted-foreground">30-sec window · 6 signals</div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Reports ──────────────────────────────────────────────────────────────────

function Reports() {
  return (
    <div className="min-h-screen pt-14 bg-background">
      <div className="max-w-4xl mx-auto px-6 py-10">
        <div className="flex items-start justify-between mb-8">
          <div>
            <SectionTag text="Post-Exam Report" />
            <h2 className="font-display font-black text-foreground text-5xl">Exam Report</h2>
            <p className="text-muted-foreground text-sm mt-1">Auto-generated · CS411 · Jan 28, 2025</p>
          </div>
          <button className="flex items-center gap-2 border border-border hover:border-foreground/20 text-muted-foreground hover:text-foreground text-[12px] font-mono uppercase tracking-wider px-4 py-2.5 rounded-xl transition-colors">
            <Download className="w-4 h-4" /> Export PDF
          </button>
        </div>

        <Card className="p-6 mb-6">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-100 to-red-100 flex items-center justify-center text-foreground font-display font-black text-2xl border border-border">J</div>
              <div>
                <div className="text-foreground font-semibold text-lg">Juan dela Cruz</div>
                <div className="text-[11px] font-mono text-muted-foreground">AU-2025-002 · BSCS 4-A</div>
                <div className="text-[11px] font-mono text-muted-foreground">Computer Vision Fundamentals · CS411</div>
              </div>
            </div>
            <div className="text-right">
              <div className="text-[11px] font-mono text-muted-foreground mb-1">Final Risk</div>
              <RiskPill value={91} />
              <div className="text-[11px] font-mono text-muted-foreground mt-2">Duration: 49 minutes</div>
            </div>
          </div>
          <div className="grid grid-cols-4 gap-4 mt-6 pt-5 border-t border-border">
            {[
              { label: "Peak Risk",   val: "91",  color: "text-red-600"     },
              { label: "Violations",  val: "6",   color: "text-orange-600"  },
              { label: "Screenshots", val: "3",   color: "text-blue-600"    },
              { label: "LSTM Max",    val: "94%", color: "text-primary"     },
            ].map(({ label, val, color }) => (
              <div key={label} className="text-center">
                <div className={`font-display text-3xl font-black ${color}`}>{val}</div>
                <div className="text-[10px] font-mono text-muted-foreground mt-0.5">{label}</div>
              </div>
            ))}
          </div>
        </Card>

        <Card className="p-6 mb-6">
          <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest mb-5">Risk Score Timeline</div>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={riskTimeline}>
              <defs>
                <linearGradient id="rtGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#c8192e" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#c8192e" stopOpacity={0}    />
                </linearGradient>
              </defs>
              <XAxis dataKey="time" tick={TICK} axisLine={false} tickLine={false} />
              <YAxis domain={[0,100]} tick={TICK} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={TT} labelStyle={TT_LABEL} />
              <Area type="monotone" dataKey="risk" stroke="#c8192e" strokeWidth={2} fill="url(#rtGrad)" dot={{ fill: "#c8192e", r: 3 }} />
            </AreaChart>
          </ResponsiveContainer>
        </Card>

        <Card className="p-6 mb-6">
          <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest mb-5">Incident Timeline</div>
          <div className="relative">
            <div className="absolute left-4 top-0 bottom-0 w-px bg-border" />
            <div className="space-y-4">
              {reportTimeline.map((e, i) => (
                <div key={i} className="flex items-start gap-4 pl-10 relative">
                  <div className={`absolute left-2.5 w-3 h-3 rounded-full border-2 -translate-x-1/2 mt-0.5 ${
                    e.type === "ok"       ? "bg-emerald-500 border-emerald-500"
                  : e.type === "warn"     ? "bg-blue-400 border-blue-400"
                  : e.type === "high"     ? "bg-orange-400 border-orange-400"
                  : e.type === "critical" ? "bg-red-500 border-red-500"
                  : e.type === "evidence" ? "bg-primary border-primary"
                  :                         "bg-muted-foreground border-muted-foreground"
                  }`} />
                  <div className="flex-1 flex items-center justify-between">
                    <div>
                      <div className="text-foreground text-sm">{e.event}</div>
                      <div className="font-mono text-[10px] text-muted-foreground mt-0.5">{e.time}</div>
                    </div>
                    {e.risk > 0 && <RiskPill value={e.risk} />}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </Card>

        <Card className="p-6 border-red-200 bg-red-50">
          <div className="flex items-start gap-4">
            <AlertTriangle className="w-6 h-6 text-primary flex-shrink-0 mt-0.5" />
            <div>
              <div className="text-foreground font-semibold text-base mb-2">System Recommendation — HIGH RISK</div>
              <p className="text-foreground/70 text-sm leading-relaxed">
                This examination session has been flagged as HIGH RISK with a peak composite score of 91/100.
                Multiple violations were detected including mobile phone presence, facial identity mismatch, and repeated
                tab-switch events. Three screenshots have been captured as evidence and an email notification has been
                dispatched to the course instructor. Manual review by the academic integrity committee is recommended
                before releasing the examination result.
              </p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}

// ─── Analytics ────────────────────────────────────────────────────────────────

function Analytics() {
  return (
    <div className="min-h-screen pt-14 bg-background">
      <div className="max-w-screen-xl mx-auto px-6 py-10">
        <div className="mb-10">
          <SectionTag text="Analytics Dashboard" />
          <h2 className="font-display font-black text-foreground text-5xl">System Analytics</h2>
          <p className="text-muted-foreground text-sm mt-1">Phase 15 — Recharts-powered insights across all sessions</p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[
            { val: "96.4%", label: "Avg Detection Accuracy", trend: "+1.2%", up: true,  icon: Target      },
            { val: "2.1%",  label: "False Positive Rate",    trend: "-0.3%", up: false, icon: AlertCircle },
            { val: "28.4",  label: "Avg FPS",                trend: "+0.6",  up: true,  icon: Zap         },
            { val: "87%",   label: "Usability Score",        trend: "+3%",   up: true,  icon: Star        },
          ].map(({ val, label, trend, up, icon: Icon }) => (
            <Card key={label} className="p-5">
              <div className="flex items-center justify-between mb-3">
                <Icon className="w-4 h-4 text-muted-foreground" />
                <span className={`text-[10px] font-mono ${up ? "text-emerald-600" : "text-red-600"}`}>{trend}</span>
              </div>
              <div className="font-display text-3xl font-black text-foreground mb-1">{val}</div>
              <div className="text-[11px] font-mono text-muted-foreground">{label}</div>
            </Card>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          <div className="lg:col-span-2">
            <Card className="p-6">
              <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest mb-5">Weekly Avg Risk &amp; Violations</div>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={analyticsWeekly} barGap={4}>
                  <XAxis dataKey="day" tick={TICK} axisLine={false} tickLine={false} />
                  <YAxis tick={TICK} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={TT} labelStyle={TT_LABEL} />
                  <Bar dataKey="avgRisk"    name="Avg Risk"   fill="#c8192e" radius={[4,4,0,0]} />
                  <Bar dataKey="violations" name="Violations" fill="#1a4fa8" radius={[4,4,0,0]} />
                </BarChart>
              </ResponsiveContainer>
            </Card>
          </div>

          <Card className="p-6">
            <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest mb-5">Top Violations</div>
            <ResponsiveContainer width="100%" height={180}>
              <RPie>
                <Pie data={violationBreakdown} cx="50%" cy="50%" innerRadius={45} outerRadius={80} dataKey="value" paddingAngle={3}>
                  {violationBreakdown.map((e, i) => <Cell key={i} fill={e.fill} />)}
                </Pie>
                <Tooltip contentStyle={TT} labelStyle={TT_LABEL} />
              </RPie>
            </ResponsiveContainer>
            <div className="space-y-2 mt-2">
              {violationBreakdown.map((v) => (
                <div key={v.name} className="flex items-center justify-between">
                  <div className="flex items-center gap-2"><div className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: v.fill }} /><span className="text-[11px] text-muted-foreground">{v.name}</span></div>
                  <span className="font-mono text-[11px] text-foreground/70">{v.value}%</span>
                </div>
              ))}
            </div>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="p-6">
            <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest mb-5">Daily Exams vs Avg Risk</div>
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={analyticsWeekly}>
                <XAxis dataKey="day" tick={TICK} axisLine={false} tickLine={false} />
                <YAxis tick={TICK} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={TT} labelStyle={TT_LABEL} />
                <Line type="monotone" dataKey="exams"   name="Exams"    stroke="#059669" strokeWidth={2.5} dot={{ fill: "#059669", r: 4 }} />
                <Line type="monotone" dataKey="avgRisk" name="Avg Risk" stroke="#c8192e" strokeWidth={2.5} dot={{ fill: "#c8192e", r: 4 }} strokeDasharray="5 3" />
              </LineChart>
            </ResponsiveContainer>
          </Card>

          <Card className="p-6">
            <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest mb-5">AI Module Performance</div>
            <ResponsiveContainer width="100%" height={180}>
              <RadarChart data={radarData}>
                <PolarGrid stroke="rgba(0,0,0,0.07)" />
                <PolarAngleAxis dataKey="metric" tick={{ fill: "#94a3b8", fontSize: 10, fontFamily: "JetBrains Mono" }} />
                <Radar dataKey="value" stroke="#c8192e" fill="#c8192e" fillOpacity={0.1} strokeWidth={2} />
              </RadarChart>
            </ResponsiveContainer>
          </Card>
        </div>
      </div>
    </div>
  );
}

// ─── App Root ─────────────────────────────────────────────────────────────────

export default function App() {
  const [view, setView] = useState<View>("landing");

  const renderView = () => {
    switch (view) {
      case "landing":    return <Landing setView={setView} />;
      case "login":      return <LoginPage setView={setView} />;
      case "student":    return <StudentDashboard setView={setView} />;
      case "instructor": return <InstructorDashboard setView={setView} />;
      case "admin":      return <AdminDashboard />;
      case "exam":       return <ExamRoom setView={setView} />;
      case "enroll":     return <FaceEnrollment />;
      case "monitor":    return <AIMonitor />;
      case "reports":    return <Reports />;
      case "analytics":  return <Analytics />;
      default:           return <Landing setView={setView} />;
    }
  };

  return (
    <div className="bg-background text-foreground" style={{ fontFamily: "'Inter', sans-serif" }}>
      <style>{`
        .font-display { font-family: 'Barlow Condensed', sans-serif; }
        .font-mono    { font-family: 'JetBrains Mono', monospace;   }
        * { scrollbar-width: thin; scrollbar-color: rgba(0,0,0,0.12) transparent; }
        *::-webkit-scrollbar { width: 4px; height: 4px; }
        *::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.12); border-radius: 9999px; }
      `}</style>
      <Topbar view={view} setView={setView} />
      {renderView()}
    </div>
  );
}
