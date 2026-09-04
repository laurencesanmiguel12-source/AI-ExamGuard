import { useState } from "react";
import { Link } from "react-router-dom";
import { Building2, ArrowRight, Clock } from "lucide-react";
import { registerSchool } from "../../api/schools";
import Card from "../../components/ui/Card";
import { TextField } from "../../components/ui/FormField";

const EMPTY_FORM = {
  code: "",
  name: "",
  slug: "",
  email: "",
  password: "",
  first_name: "",
  last_name: "",
};

function slugify(text) {
  return text.toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
}

export default function SchoolSignup() {
  const [form, setForm] = useState(EMPTY_FORM);
  const [slugEdited, setSlugEdited] = useState(false);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  function handleNameChange(name) {
    setForm((f) => ({ ...f, name, slug: slugEdited ? f.slug : slugify(name) }));
  }

  function handleSlugChange(rawSlug) {
    setSlugEdited(true);
    setForm((f) => ({ ...f, slug: slugify(rawSlug) }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      // No redirect to login any more: the school is created "pending" and its admin cannot sign
      // in until a platform administrator approves it (backend returns 403 with that reason).
      // Sending them to a login screen that is guaranteed to reject them would read as a bug.
      await registerSchool(form);
      setDone(true);
    } catch (err) {
      setError(err.response?.data?.detail ?? "Couldn't register your school. Check your details and try again.");
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

      {/* <main>, not a div: these pages render outside Layout, which owns the app's
            main landmark, so without this the public pages have none at all. */}
      <main className="relative w-full max-w-md px-6">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-primary/10 border border-primary/20 mb-4">
            <Building2 className="w-7 h-7 text-primary" />
          </div>
          <h1 className="font-display font-black text-foreground text-4xl">Register Your School</h1>
          <p className="text-muted-foreground text-sm mt-1">AI ExamGuard — set up your school's admin account</p>
        </div>

        <Card className="p-6">
          {done ? (
            <div className="py-4 text-center">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-amber-50 border border-amber-200 mb-4">
                <Clock className="w-6 h-6 text-amber-600" />
              </div>
              <h2 className="font-display font-bold text-foreground text-xl mb-2">
                Registration pending review
              </h2>
              <p className="text-sm text-muted-foreground">
                Thanks — <span className="text-foreground font-medium">{form.name}</span> has been
                submitted to the platform administrator for review.
              </p>
              <p className="text-sm text-muted-foreground mt-3">
                Your admin account (<span className="text-foreground">{form.email}</span>) is
                already created. You'll be able to sign in with it as soon as the school is
                approved — there's nothing else to fill in.
              </p>
              <Link
                to="/"
                className="inline-block mt-6 text-sm text-primary hover:underline"
              >
                Back to home
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit}>
              {error && (
                <div className="mb-4 rounded-xl bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-600">
                  {error}
                </div>
              )}

              <TextField
                label="School Name"
                required
                value={form.name}
                onChange={(e) => handleNameChange(e.target.value)}
                placeholder="Arellano University"
              />
              <TextField
                label="Login URL"
                required
                value={form.slug}
                onChange={(e) => handleSlugChange(e.target.value)}
                placeholder="arellano-university"
              />
              {form.slug && (
                <p className="text-xs text-muted-foreground -mt-3 mb-4">
                  Your school will sign in at /{form.slug}/login
                </p>
              )}
              <TextField
                label="School Code"
                required
                value={form.code}
                onChange={(e) => setForm({ ...form, code: e.target.value })}
                placeholder="AU"
              />

              <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest mb-3 mt-5 pt-4 border-t border-border">
                Your Admin Account
              </div>

              <div className="grid grid-cols-2 gap-3">
                <TextField
                  label="First Name"
                  required
                  value={form.first_name}
                  onChange={(e) => setForm({ ...form, first_name: e.target.value })}
                />
                <TextField
                  label="Last Name"
                  required
                  value={form.last_name}
                  onChange={(e) => setForm({ ...form, last_name: e.target.value })}
                />
              </div>


              <TextField
                label="Email Address"
                type="email"
                required
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
              />

              <TextField
                label="Password"
                type="password"
                required
                minLength={8}
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
              />

              <button
                type="submit"
                disabled={submitting}
                className="w-full flex items-center justify-center gap-2 bg-primary hover:bg-primary/90 disabled:opacity-50 text-white py-3 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors mt-2"
              >
                <ArrowRight className="w-4 h-4" /> {submitting ? "Registering school…" : "Register School"}
              </button>
            </form>
          )}
        </Card>

        <div className="text-center mt-6 text-sm text-muted-foreground">
          Already have an account?{" "}
          <Link to="/login" className="text-primary hover:underline">
            Sign in
          </Link>
        </div>
      </main>
    </div>
  );
}
