import { useNavigate } from "react-router-dom";
import {
  Shield, Eye, BarChart3, CheckCircle, Lock, Star, ClipboardList,
  GraduationCap, Users, Activity, Download,
} from "lucide-react";
import PublicTopbar from "../../components/PublicTopbar";
import SectionTag from "../../components/ui/SectionTag";

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
    desc: "Built-in accommodations for students who need checks disabled, and a full student appeal workflow with instructor review on every flagged violation.",
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

      {/* Background canvas */}
      <rect width="520" height="400" fill="#f8fafc"/>
      <rect width="520" height="400" fill="url(#heroDots)"/>

      {/* Decorative geometric accents */}
      <circle cx="480" cy="40" r="60" fill="#eff6ff" opacity="0.6"/>
      <circle cx="40"  cy="350" r="50" fill="#fff1f2" opacity="0.5"/>
      <circle cx="480" cy="370" r="35" fill="#f0fdf4" opacity="0.5"/>

      {/* Laptop stand */}
      <rect x="168" y="284" width="184" height="12" rx="3" fill="#e2e8f0"/>
      <rect x="148" y="294" width="224" height="7" rx="3.5" fill="#cbd5e1"/>

      {/* Monitor outer shell */}
      <rect x="88" y="34" width="326" height="256" rx="14" fill="#ffffff" stroke="#e2e8f0" strokeWidth="2"/>

      {/* Titlebar */}
      <rect x="88" y="34" width="326" height="30" rx="14" fill="#f1f5f9"/>
      <rect x="88" y="48" width="326" height="16" fill="#f1f5f9"/>
      <circle cx="108" cy="49" r="5" fill="#fca5a5"/>
      <circle cx="124" cy="49" r="5" fill="#fde68a"/>
      <circle cx="140" cy="49" r="5" fill="#86efac"/>
      <text x="251" y="53" textAnchor="middle" fontFamily="JetBrains Mono,monospace" fontSize="8" fill="#64748b">AI ExamGuard · CS411 · Ana Reyes</text>
      <circle cx="388" cy="49" r="3" fill="#f97316" opacity="0.7"/>
      <text x="384" y="52" fontFamily="JetBrains Mono,monospace" fontSize="5.5" fill="#fff">30</text>

      {/* Screen content (dark) */}
      <rect x="96" y="64" width="310" height="218" fill="url(#screenBg)" clipPath="url(#screenClip)"/>

      {/* Fine grid overlay on screen */}
      <g clipPath="url(#screenClip)" opacity="0.06">
        {[...Array(10)].map((_,i) => <line key={`vg${i}`} x1={96+i*31} y1="64" x2={96+i*31} y2="282" stroke="#60a5fa" strokeWidth="0.5"/>)}
        {[...Array(8)].map((_,i) => <line key={`hg${i}`} x1="96" y1={64+i*28} x2="406" y2={64+i*28} stroke="#60a5fa" strokeWidth="0.5"/>)}
      </g>

      {/* Abstract student silhouette */}
      <g clipPath="url(#screenClip)">
        <path d="M200 282 Q251 228 302 282 Z" fill="#1e3a5f" opacity="0.4"/>
        <ellipse cx="251" cy="168" rx="36" ry="42" fill="#1e3a5f" opacity="0.35"/>
        <rect x="237" y="207" width="28" height="22" rx="4" fill="#1e3a5f" opacity="0.3"/>
      </g>

      {/* Face detection overlay */}
      <g clipPath="url(#screenClip)">
        <g stroke="#10b981" strokeWidth="2.5" fill="none" filter="url(#glow)">
          <path d="M207 122 h-18 v18"/>
          <path d="M295 122 h18 v18"/>
          <path d="M207 214 h-18 v-18"/>
          <path d="M295 214 h18 v-18"/>
        </g>
        {[...Array(5)].map((_,row) =>
          [...Array(6)].map((_,col) => (
            <circle key={`fd${row}${col}`}
              cx={215 + col * 15} cy={132 + row * 16}
              r="1.8" fill="#10b981" opacity={0.3 + row*0.08}/>
          ))
        )}
        <rect x="189" y="122" width="124" height="2.5" fill="#10b981" opacity="0.85" className="scan"/>

        <rect x="215" y="104" width="72" height="15" rx="7.5" fill="rgba(16,185,129,0.18)"/>
        <rect x="215" y="104" width="72" height="15" rx="7.5" stroke="#10b981" strokeWidth="1" fill="none"/>
        <text x="251" y="115" textAnchor="middle" fontFamily="JetBrains Mono,monospace" fontSize="7" fill="#10b981">● VERIFIED</text>

        {[{l:"YOLO",y:74,c:"#fb923c"},{l:"FACE",y:88,c:"#10b981"},{l:"RISK",y:102,c:"#60a5fa"}].map(({l,y,c}) => (
          <g key={l}>
            <rect x="366" y={y} width="32" height="11" rx="3" fill="rgba(255,255,255,0.07)"/>
            <circle cx="371" cy={y+5.5} r="2.2" fill={c} className="blink"/>
            <text x="375" y={y+8.5} fontFamily="JetBrains Mono,monospace" fontSize="6.5" fill="rgba(255,255,255,0.75)">{l}</text>
          </g>
        ))}
      </g>

      {/* Bottom status bar on screen */}
      <g clipPath="url(#screenClip)">
        <rect x="96" y="248" width="310" height="34" fill="rgba(0,0,0,0.55)"/>
        <text x="112" y="261" fontFamily="JetBrains Mono,monospace" fontSize="6.5" fill="rgba(255,255,255,0.45)" letterSpacing="1">RISK SCORE</text>
        <text x="112" y="275" fontFamily="Barlow Condensed,sans-serif" fontSize="20" fontWeight="900" fill="#34d399">07</text>
        <rect x="152" y="263" width="100" height="5" rx="2.5" fill="rgba(255,255,255,0.1)"/>
        <rect x="152" y="263" width="7" height="5" rx="2.5" fill="#10b981"/>
        <text x="259" y="269" fontFamily="JetBrains Mono,monospace" fontSize="7" fill="#34d399">LOW</text>
        <text x="360" y="269" fontFamily="JetBrains Mono,monospace" fontSize="6.5" fill="rgba(255,255,255,0.35)">09:14:22</text>
      </g>

      {/* LEFT FLOAT: Risk Gauge card */}
      <g className="fa">
        <rect x="8" y="84" width="76" height="100" rx="12" fill="#fff" stroke="#e2e8f0" strokeWidth="1.5"/>
        <text x="46" y="100" textAnchor="middle" fontFamily="JetBrains Mono,monospace" fontSize="7" fill="#64748b" letterSpacing="1">RISK</text>
        <path d="M18 160 A28 28 0 0 1 74 160" stroke="#e2e8f0" strokeWidth="5" strokeLinecap="round" fill="none"/>
        <path d="M18 160 A28 28 0 0 1 74 160" stroke="url(#riskGradient)" strokeWidth="5" strokeLinecap="round" fill="none"
          strokeDasharray="88" strokeDashoffset="80" className="riskArc"/>
        <text x="46" y="156" textAnchor="middle" fontFamily="Barlow Condensed,sans-serif" fontSize="22" fontWeight="900" fill="#0f172a">07</text>
        <text x="46" y="167" textAnchor="middle" fontFamily="JetBrains Mono,monospace" fontSize="6.5" fill="#10b981">LOW</text>
        <rect x="14" y="174" width="48" height="5" rx="2.5" fill="#f1f5f9"/>
        <rect x="14" y="174" width="4" height="5" rx="2.5" fill="#10b981"/>
      </g>

      {/* TOP-RIGHT FLOAT: Alert card */}
      <g className="fb">
        <rect x="436" y="54" width="76" height="72" rx="12" fill="#fff" stroke="#fecdd3" strokeWidth="1.5"/>
        <rect x="436" y="54" width="76" height="24" rx="12" fill="#fff1f2"/>
        <rect x="436" y="66" width="76" height="12" fill="#fff1f2"/>
        <circle cx="450" cy="66" r="5" fill="#ef4444" opacity="0.8"/>
        <text x="460" y="69.5" fontFamily="JetBrains Mono,monospace" fontSize="7" fill="#c8192e" fontWeight="bold">ALERT</text>
        <text x="446" y="87" fontFamily="JetBrains Mono,monospace" fontSize="6.5" fill="#64748b">Phone</text>
        <text x="446" y="97" fontFamily="JetBrains Mono,monospace" fontSize="6.5" fill="#64748b">Detected</text>
        <text x="446" y="113" fontFamily="JetBrains Mono,monospace" fontSize="5.5" fill="#94a3b8">09:15:08</text>
        <circle cx="494" cy="107" r="8" fill="#fff1f2" stroke="#fecdd3" strokeWidth="1"/>
        <text x="494" y="111" textAnchor="middle" fontFamily="sans-serif" fontSize="11" fill="#c8192e">!</text>
      </g>

      {/* RIGHT FLOAT: Face match card */}
      <g className="fc">
        <rect x="436" y="158" width="76" height="56" rx="12" fill="#eff6ff" stroke="#bfdbfe" strokeWidth="1.5"/>
        <text x="448" y="172" fontFamily="JetBrains Mono,monospace" fontSize="6" fill="#1a4fa8" letterSpacing="0.5">FACE MATCH</text>
        <text x="448" y="186" fontFamily="Barlow Condensed,sans-serif" fontSize="18" fontWeight="900" fill="#1a4fa8">98.4%</text>
        <circle cx="494" cy="185" r="9" fill="#dbeafe" stroke="#93c5fd" strokeWidth="1"/>
        <text x="494" y="189" textAnchor="middle" fontSize="11" fill="#1d4ed8">✓</text>
        <text x="448" y="200" fontFamily="JetBrains Mono,monospace" fontSize="5.5" fill="#3b82f6">OpenCV · YuNet</text>
      </g>

      {/* BOTTOM FLOAT: Evidence retention card */}
      <g className="fb">
        <rect x="436" y="244" width="76" height="60" rx="12" fill="#f5f3ff" stroke="#ddd6fe" strokeWidth="1.5"/>
        <text x="448" y="258" fontFamily="JetBrains Mono,monospace" fontSize="6" fill="#7c3aed" letterSpacing="0.5">RETENTION</text>
        <text x="448" y="274" fontFamily="Barlow Condensed,sans-serif" fontSize="18" fontWeight="900" fill="#7c3aed">90d</text>
        <text x="448" y="288" fontFamily="JetBrains Mono,monospace" fontSize="5.5" fill="#8b5cf6">auto-purge evidence</text>
      </g>

      {/* Neural net art (bottom-left decorative) */}
      <g opacity="0.5">
        {([[24,310],[24,340],[24,370],[56,295],[56,325],[56,355],[56,385],[88,310],[88,340],[88,370]]).map(([x,y],i) => (
          <circle key={`n${i}`} cx={x} cy={y} r="5"
            fill={i<3?"#c8192e":i<7?"#1a4fa8":"#10b981"} opacity={0.18+i*0.03}/>
        ))}
        {([[24,310,56,295],[24,310,56,325],[24,340,56,325],[24,340,56,355],[24,370,56,355],[24,370,56,385],[56,295,88,310],[56,325,88,310],[56,325,88,340],[56,355,88,340],[56,355,88,370],[56,385,88,370]]).map(([x1,y1,x2,y2],i) => (
          <line key={`e${i}`} x1={x1} y1={y1} x2={x2} y2={y2} stroke="#1a4fa8" strokeWidth="0.8" opacity="0.18"/>
        ))}
      </g>

      {/* Live indicator badge */}
      <g className="fa">
        <rect x="8" y="54" width="82" height="22" rx="11" fill="#fff" stroke="#e2e8f0" strokeWidth="1.5"/>
        <circle cx="22" cy="65" r="4" fill="#c8192e" className="blink"/>
        <text x="30" y="69" fontFamily="JetBrains Mono,monospace" fontSize="7.5" fill="#0f172a" fontWeight="bold">LIVE</text>
        <text x="52" y="69" fontFamily="JetBrains Mono,monospace" fontSize="6" fill="#64748b">~15s poll</text>
      </g>
    </svg>
  );
}

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-background">
      <PublicTopbar />

      {/* HERO */}
      <section className="relative min-h-screen flex items-center pt-14 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-white via-blue-50/30 to-red-50/15"/>
        <div className="absolute inset-0 opacity-[0.035]"
          style={{ backgroundImage: "linear-gradient(rgba(0,0,0,1) 1px,transparent 1px),linear-gradient(90deg,rgba(0,0,0,1) 1px,transparent 1px)", backgroundSize: "56px 56px" }}/>
        <div className="absolute top-1/4 right-0 w-[700px] h-[700px] rounded-full opacity-[0.06]"
          style={{ background: "radial-gradient(circle, #c8192e 0%, transparent 70%)" }}/>
        <div className="absolute -bottom-24 -left-24 w-[500px] h-[500px] rounded-full opacity-[0.05]"
          style={{ background: "radial-gradient(circle, #1a4fa8 0%, transparent 70%)" }}/>

        <div className="relative max-w-screen-xl mx-auto px-6 py-20 grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <div>
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

            <div className="flex flex-wrap gap-3 mb-12">
              <button onClick={() => navigate("/schools/register")}
                className="inline-flex items-center gap-2 bg-primary hover:bg-primary/90 text-white px-6 py-3 rounded-xl text-[12px] font-mono uppercase tracking-widest transition-all shadow-sm">
                <Shield className="w-4 h-4"/> Register Free
              </button>
            </div>

            <div className="grid grid-cols-3 gap-6 pt-6 border-t border-border">
              {[
                { val: "0–100",  sub: "Auditable Risk Score"     },
                { val: "90 Days", sub: "Evidence Auto-Purge"     },
                { val: "Free",   sub: "To Register Your School" },
              ].map(({ val, sub }) => (
                <div key={sub}>
                  <div className="font-display text-[2.2rem] font-black text-foreground leading-none">{val}</div>
                  <div className="text-muted-foreground text-[11px] font-mono uppercase tracking-widest mt-1">{sub}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="relative w-full aspect-[4/3] max-w-[560px] mx-auto lg:mx-0">
            <ProctorCanvas/>
          </div>
        </div>
      </section>

      {/* TECH BELT */}
      <div className="border-y border-border bg-white overflow-hidden">
        <div className="max-w-screen-xl mx-auto px-6 py-5 flex items-center gap-0">
          <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-[0.2em] whitespace-nowrap pr-8 border-r border-border mr-8 flex-shrink-0">
            Powered by
          </span>
          <div className="flex items-center gap-8 flex-wrap">
            {[
              {
                name: "YuNet", sub: "Face Detection", color: "#1a4fa8", bg: "#eff6ff",
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
                name: "YOLOv8", sub: "Object Detection", color: "#c8192e", bg: "#fff1f2",
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
                name: "OpenCV", sub: "Computer Vision", color: "#059669", bg: "#f0fdf4",
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
                name: "PyTorch", sub: "Model Training", color: "#ea580c", bg: "#fff7ed",
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

      {/* WHY AI EXAMGUARD */}
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

      {/* GET STARTED IN MINUTES */}
      <section className="py-24 bg-background">
        <div className="max-w-screen-xl mx-auto px-6">
          <div className="max-w-xl mb-14">
            <SectionTag text="Get Started in Minutes"/>
            <h2 className="font-display font-black text-foreground text-5xl mb-3">From zero to your first proctored exam.</h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {ONBOARDING_STEPS.map(({ n, title, desc, icon: Icon, color }, i) => (
              <div key={n} className="relative">
                {i < ONBOARDING_STEPS.length - 1 && (
                  <div className="hidden lg:block absolute top-8 h-px bg-border z-0" style={{ width: "calc(100% - 44px)", left: 44 }}/>
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

      {/* CTA BANNER */}
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
            <button onClick={() => navigate("/schools/register")}
              className="inline-flex items-center gap-2 bg-primary hover:bg-primary/90 text-white px-8 py-3.5 rounded-xl text-[13px] font-mono uppercase tracking-widest transition-all shadow-md">
              <Shield className="w-4 h-4"/> Register Your School Free
            </button>
            <button onClick={() => navigate("/login")}
              className="inline-flex items-center gap-2 border border-white/20 text-white/70 hover:text-white hover:border-white/40 px-7 py-3.5 rounded-xl text-[13px] font-mono uppercase tracking-widest transition-all">
              <Lock className="w-4 h-4"/> Sign In
            </button>
          </div>
          <a href="https://chromewebstore.google.com/detail/ai-examguard-tab-monitor/gbkbkbcbbehpcoifmkenkjafkfbphmkf"
            target="_blank" rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-white/40 hover:text-white/70 text-[11px] font-mono uppercase tracking-widest mt-8 transition-colors">
            <Download className="w-3.5 h-3.5"/> Already registered? Get the Tab Monitor extension from the Chrome Web Store
          </a>
        </div>
      </section>
    </div>
  );
}
