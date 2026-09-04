import { Link } from "react-router-dom";
import { Check, ArrowRight } from "lucide-react";
import Card from "./ui/Card";
import { useSchoolSlug } from "../hooks/useSchoolNav";

/**
 * First-run guidance for a brand-new school.
 *
 * Setting AI ExamGuard up has a required order — a subject needs a course, an exam needs both a
 * subject and an instructor assigned to that subject, and a student can only sit an exam once
 * they are on its roster. None of that is discoverable: an admin landing on an empty system sees
 * five identical empty tables and has to work out the sequence by hitting errors.
 *
 * This states the order, shows how far along they are, and links to the next thing to do. It
 * disappears entirely once every step is done, so an established school never sees it.
 */
export default function SetupChecklist({ counts }) {
  const slug = useSchoolSlug();

  const steps = [
    {
      to: "/courses",
      label: "Add a course",
      done: counts.courses > 0,
      why: "The degree programme students register into. Everything else hangs off it.",
    },
    {
      to: "/subjects",
      label: "Add a subject",
      done: counts.subjects > 0,
      why: "The class an exam is actually set for. Needs a course first.",
    },
    {
      to: "/instructors",
      label: "Add an instructor and give them a subject",
      done: counts.instructors > 0,
      why: "Without a subject assigned, an instructor cannot create any exam.",
    },
    {
      to: "/exams",
      label: "Create an exam",
      done: counts.exams > 0,
      why: "Then open it to write questions and choose who sits it.",
    },
  ];

  const remaining = steps.filter((s) => !s.done);
  if (remaining.length === 0) return null;

  const next = remaining[0];
  const doneCount = steps.length - remaining.length;

  return (
    <Card className="mb-6 p-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="font-display text-lg font-bold text-foreground">Finish setting up your school</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            These need doing in order — each step depends on the one above it.
          </p>
        </div>
        <span className="font-mono text-xs text-muted-foreground">
          {doneCount} of {steps.length} done
        </span>
      </div>

      <ol className="flex flex-col gap-2">
        {steps.map((step) => (
          <li
            key={step.to}
            className={`flex items-start gap-3 rounded-xl border px-4 py-3 ${
              step.done
                ? "border-border bg-secondary/40"
                : step === next
                ? "border-primary/30 bg-primary/5"
                : "border-border"
            }`}
          >
            <span
              aria-hidden="true"
              className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-[10px] font-bold ${
                step.done
                  ? "border-emerald-700 bg-emerald-700 text-white"
                  : "border-border text-muted-foreground"
              }`}
            >
              {step.done ? <Check className="h-3 w-3" /> : steps.indexOf(step) + 1}
            </span>

            <div className="min-w-0 flex-1">
              <div className={`text-sm ${step.done ? "text-muted-foreground line-through" : "text-foreground font-medium"}`}>
                {step.label}
                <span className="sr-only">{step.done ? " — done" : " — still to do"}</span>
              </div>
              {!step.done && <p className="mt-0.5 text-sm text-muted-foreground">{step.why}</p>}
            </div>

            {step === next && (
              <Link
                to={`/${slug}${step.to}`}
                className="flex shrink-0 items-center gap-1.5 rounded-xl bg-primary px-3 py-1.5 text-[11px] font-mono uppercase tracking-wider text-white transition-colors hover:bg-primary/90"
              >
                Start <ArrowRight className="h-3 w-3" />
              </Link>
            )}
          </li>
        ))}
      </ol>
    </Card>
  );
}
