import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Shield, Users, Lock, ArrowRight, Eye, Clock, AlertTriangle } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { useSchool, useSchoolNav, useSchoolSlug } from "../../hooks/useSchoolNav";
import Card from "../../components/ui/Card";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const { login, isAuthenticated } = useAuth();
  const navigate = useSchoolNav();
  const schoolSlug = useSchoolSlug();
  const school = useSchool();

  useEffect(() => {
    if (isAuthenticated) {
      navigate("/dashboard", { replace: true });
    }
  }, [isAuthenticated, navigate]);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login(email, password);
      navigate("/dashboard");
    } catch {
      setError("Invalid email or password.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-secondary relative overflow-hidden">
      <div
        className="absolute top-0 right-0 w-96 h-96 rounded-full opacity-[0.06]"
        style={{ background: "radial-gradient(circle,#c8192e,transparent)" }}
      />
      <div
        className="absolute bottom-0 left-0 w-80 h-80 rounded-full opacity-[0.05]"
        style={{ background: "radial-gradient(circle,#1a4fa8,transparent)" }}
      />

      {/* <main>, not a div: these pages render outside Layout, which owns the app's main
          landmark, so without this the public pages have none at all. */}
      <main className="relative w-full max-w-md px-6">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-primary/10 border border-primary/20 mb-4">
            <Shield className="w-7 h-7 text-primary" />
          </div>
          <h1 className="font-display font-black text-foreground text-4xl">Secure Login</h1>
          <p className="text-muted-foreground text-sm mt-1">AI ExamGuard — {school?.name ?? "…"}</p>
        </div>

        {/* Shown before the form rather than only after a failed attempt: someone returning to
            their own school's login link should learn it is still under review without having to
            type credentials that are guaranteed to be refused. */}
        {school?.status === "pending" && (
          <Card className="p-5 mb-4 border-amber-200 bg-amber-50">
            <div className="flex gap-3">
              <Clock className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-foreground">Registration pending review</p>
                <p className="text-sm text-muted-foreground mt-1">
                  This school is waiting to be approved by the platform administrator. Your admin
                  account already exists — sign-in starts working as soon as it's approved.
                </p>
              </div>
            </div>
          </Card>
        )}

        {school?.status === "rejected" && (
          <Card className="p-5 mb-4 border-red-200 bg-red-50">
            <div className="flex gap-3">
              <AlertTriangle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-foreground">Registration not approved</p>
                <p className="text-sm text-muted-foreground mt-1">
                  {school.review_note
                    ? `Reason: ${school.review_note}`
                    : "Contact the platform administrator for details."}
                </p>
              </div>
            </div>
          </Card>
        )}

        <Card className="p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div role="alert" className="rounded-xl bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-600">
                {error}
              </div>
            )}

            <div>
              <label htmlFor="login-email" className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest block mb-1.5">
                Email Address
              </label>
              <div className="flex items-center gap-2 bg-secondary border border-border rounded-xl px-4 py-3 focus-within:border-primary/40 transition-colors">
                <Users className="w-4 h-4 text-muted-foreground" />
                <input
                  id="login-email"
                  name="email"
                  autoComplete="username"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="bg-transparent text-sm text-foreground placeholder:text-muted-foreground/50 flex-1 outline-none"
                  placeholder="you@arellano.edu"
                />
              </div>
            </div>

            <div>
              <label htmlFor="login-password" className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest block mb-1.5">
                Password
              </label>
              <div className="flex items-center gap-2 bg-secondary border border-border rounded-xl px-4 py-3 focus-within:border-primary/40 transition-colors">
                <Lock className="w-4 h-4 text-muted-foreground" />
                <input
                  id="login-password"
                  name="password"
                  autoComplete="current-password"
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="bg-transparent text-sm text-foreground placeholder:text-muted-foreground/50 flex-1 outline-none"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full flex items-center justify-center gap-2 bg-primary hover:bg-primary/90 disabled:opacity-50 text-white py-3 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors mt-2"
            >
              <ArrowRight className="w-4 h-4" /> {submitting ? "Signing in…" : "Sign in"}
            </button>
            <div className="text-center text-[11px] font-mono text-muted-foreground">
              JWT-secured · Role-based access control
            </div>
          </form>
        </Card>

        <div className="text-center mt-6 text-sm text-muted-foreground">
          New student?{" "}
          <Link to={`/${schoolSlug}/register`} className="text-primary hover:underline">
            Create an account
          </Link>
        </div>
        <div className="text-center mt-2 text-sm text-muted-foreground">
          New school?{" "}
          <Link to="/schools/register" className="text-primary hover:underline">
            Register your school
          </Link>
        </div>

        <div className="flex items-center justify-center gap-3 mt-6 text-[11px] font-mono text-muted-foreground">
          <span className="flex items-center gap-1"><Lock className="w-3 h-3" /> Encrypted</span>
          <span>·</span>
          <span className="flex items-center gap-1"><Eye className="w-3 h-3" /> Biometric</span>
          <span>·</span>
          <span className="flex items-center gap-1"><Shield className="w-3 h-3" /> JWT Auth</span>
        </div>
      </main>
    </div>
  );
}
