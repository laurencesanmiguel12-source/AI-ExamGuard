import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Shield, Building2, ArrowRight } from "lucide-react";
import { getSchools } from "../../api/schools";
import Card from "../../components/ui/Card";

export default function SchoolPicker() {
  const [schools, setSchools] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    getSchools()
      .then(setSchools)
      .catch(() => setError(true));
  }, []);

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
          <h1 className="font-display font-black text-foreground text-4xl">Find Your School</h1>
          <p className="text-muted-foreground text-sm mt-1">AI ExamGuard — sign in through your school</p>
        </div>

        <Card className="p-6">
          {error ? (
            <p className="text-sm text-red-600 text-center py-4">Couldn't load schools. Please try again.</p>
          ) : schools === null ? (
            <p className="text-sm text-muted-foreground text-center py-4">Loading schools…</p>
          ) : schools.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">No schools registered yet.</p>
          ) : (
            <div className="space-y-2">
              {schools.map((s) => (
                <Link
                  key={s.id}
                  to={`/${s.slug}/login`}
                  className="flex items-center gap-3 rounded-xl border border-border px-4 py-3 hover:border-primary/40 hover:bg-black/[0.02] transition-colors"
                >
                  <Building2 className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                  <span className="text-sm text-foreground flex-1">{s.name}</span>
                  <ArrowRight className="w-4 h-4 text-muted-foreground" />
                </Link>
              ))}
            </div>
          )}
        </Card>

        <div className="text-center mt-6 text-sm text-muted-foreground">
          New school?{" "}
          <Link to="/schools/register" className="text-primary hover:underline">
            Register your school
          </Link>
        </div>
      </div>
    </div>
  );
}
