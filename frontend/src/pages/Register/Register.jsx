import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Shield, ArrowRight } from "lucide-react";
import { register } from "../../api/auth";
import { getCourses } from "../../api/courses";
import Card from "../../components/ui/Card";
import { TextField, SelectField } from "../../components/ui/FormField";

const EMPTY_FORM = {
  username: "",
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
  const navigate = useNavigate();

  useEffect(() => {
    getCourses().then((c) => {
      setCourses(c);
      setForm((f) => ({ ...f, course_id: c[0]?.id ?? "" }));
    });
  }, []);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await register({ ...form, course_id: Number(form.course_id) });
      setDone(true);
      setTimeout(() => navigate("/login"), 1500);
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

      <div className="relative w-full max-w-md px-6">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-primary/10 border border-primary/20 mb-4">
            <Shield className="w-7 h-7 text-primary" />
          </div>
          <h1 className="font-display font-black text-foreground text-4xl">Student Registration</h1>
          <p className="text-muted-foreground text-sm mt-1">AI ExamGuard — Arellano University</p>
        </div>

        <Card className="p-6">
          {done ? (
            <div className="text-center py-6">
              <p className="text-sm text-foreground">Account created. Redirecting to login…</p>
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
                label="Username"
                required
                value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value })}
              />

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
          <Link to="/login" className="text-primary hover:underline">
            Sign in
          </Link>
        </div>
      </div>
    </div>
  );
}
