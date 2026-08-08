import { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Shield, Lock } from "lucide-react";

export default function PublicTopbar() {
  const navigate = useNavigate();
  const location = useLocation();
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", fn);
    return () => window.removeEventListener("scroll", fn);
  }, []);

  const solid = scrolled || location.pathname !== "/";

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        solid ? "bg-white/95 backdrop-blur border-b border-border shadow-sm" : "bg-white/80 backdrop-blur"
      }`}
    >
      <div className="max-w-screen-xl mx-auto px-6 h-14 flex items-center justify-between">
        <button onClick={() => navigate("/")} className="flex items-center gap-2.5 group">
          <div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center group-hover:scale-105 transition-transform">
            <Shield className="w-3.5 h-3.5 text-white" />
          </div>
          <div className="text-left">
            <div className="text-foreground font-display font-bold text-sm leading-none">AI ExamGuard</div>
            <div className="text-muted-foreground text-[9px] font-mono uppercase tracking-[0.2em]">
              Multi-School Proctoring
            </div>
          </div>
        </button>

        <button
          onClick={() => navigate("/login")}
          className="flex items-center gap-2 bg-primary hover:bg-primary/90 text-white text-[11px] font-mono uppercase tracking-widest px-4 py-2 rounded-lg transition-colors"
        >
          <Lock className="w-3.5 h-3.5" /> Login
        </button>
      </div>
    </header>
  );
}
