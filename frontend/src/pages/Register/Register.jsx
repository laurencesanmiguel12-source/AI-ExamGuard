import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Shield, ArrowRight, CheckCircle2, Download, Puzzle } from "lucide-react";
import { register } from "../../api/auth";
import { getCourses } from "../../api/courses";
import { useSchool, useSchoolNav, useSchoolSlug } from "../../hooks/useSchoolNav";
import Card from "../../components/ui/Card";
import { TextField, SelectField } from "../../components/ui/FormField";
import { EXTENSION_STORE_URL } from "../../constants/extension";

const EMPTY_FORM = {
  email: "",
  password: "",
  first_name: "",
  last_name: "",
  course_id: "",
};

export default function Register() {
  const [form, setForm] = useState(EMPTY_FORM);
  const [courses, setCourses] = useState([]);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const navigate = useSchoolNav();
  const schoolSlug = useSchoolSlug();
  const school = useSchool();

  // The school is fixed by the URL - only its courses are selectable.
  useEffect(() => {
    if (!school) return;
    getCourses(school.id).then((c) => {
      setCourses(c);
      setForm((f) => ({ ...f, course_id: c[0]?.id ?? "" }));
    });
  }, [school]);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await register({ ...form, course_id: Number(form.course_id) });
      setDone(true);
    } catch (err) {
      setError(err.response?.data?.detail ?? "Couldn't create your account. Check your details and try again.");
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
          <h1 className="font-display font-black text-foreground text-4xl">Student Registration</h1>
          <p className="text-muted-foreground text-sm mt-1">AI ExamGuard — {school?.name ?? "…"}</p>
        </div>

        <Card className="p-6">
          {done ? (
            <div className="py-2">
              <div className="flex flex-col items-center text-center">
                <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-emerald-200 bg-emerald-50">
                  <CheckCircle2 className="h-7 w-7 text-emerald-700" />
                </div>
                <p className="text-sm font-medium text-foreground">Account created</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  One thing to do before your first exam.
                </p>
              </div>

              {/* Installing the extension is the only exam prerequisite a student can finish
                  right now, on this screen, with no instructor involved - face enrolment needs
                  a signed-in session and a camera. This used to be a 1.5s "redirecting..."
                  message, which is not long enough to read, let alone act on. */}
              <div className="mt-5 rounded-xl border border-blue-200 bg-blue-50 p-4">
                <div className="flex items-start gap-3">
                  <Puzzle className="mt-0.5 h-4 w-4 shrink-0 text-blue-700" />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-foreground">
                      Install the Tab Monitor extension
                    </p>
                    <p className="mt-0.5 text-sm text-muted-foreground">
                      Your exams are proctored in Chrome and check for it before they start.
                      Install it now — it takes a few seconds, and doing it later means doing it
                      with the exam clock already running.
                    </p>
                    <a
                      href={EXTENSION_STORE_URL}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-3 inline-flex items-center gap-1.5 rounded-xl bg-primary px-4 py-2 text-[11px] font-mono uppercase tracking-wider text-white transition-colors hover:bg-primary/90"
                    >
                      <Download className="h-3.5 w-3.5" /> Get the extension
                    </a>
                  </div>
                </div>
              </div>

              <button
                onClick={() => navigate("/login")}
                className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl border border-border py-2.5 text-sm font-mono uppercase tracking-widest text-muted-foreground transition-colors hover:border-foreground/20 hover:text-foreground"
              >
                Continue to sign in <ArrowRight className="h-3.5 w-3.5" />
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit}>
              {error && (
                <div className="mb-4 rounded-xl bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-600">
                  {error}
                </div>
              )}

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
                placeholder="you@arellano.edu"
              />

              <TextField
                label="Password"
                type="password"
                required
                minLength={8}
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
              />

              <SelectField
                label="Course"
                required
                value={form.course_id}
                onChange={(e) => setForm({ ...form, course_id: e.target.value })}
              >
                {courses.length === 0 && <option value="">Loading courses…</option>}
                {courses.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.code} — {c.name}
                  </option>
                ))}
              </SelectField>

              <button
                type="submit"
                disabled={submitting || courses.length === 0}
                className="w-full flex items-center justify-center gap-2 bg-primary hover:bg-primary/90 disabled:opacity-50 text-white py-3 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors mt-2"
              >
                <ArrowRight className="w-4 h-4" /> {submitting ? "Creating account…" : "Create Account"}
              </button>
            </form>
          )}
        </Card>

        <div className="text-center mt-6 text-sm text-muted-foreground">
          Already have an account?{" "}
          <Link to={`/${schoolSlug}/login`} className="text-primary hover:underline">
            Sign in
          </Link>
        </div>
      </main>
    </div>
  );
}
