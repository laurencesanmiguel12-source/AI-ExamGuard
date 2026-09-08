import { useEffect, useState } from "react";
import { CalendarClock, AlarmClock, Clock } from "lucide-react";
import { getDeadlineState, tickIntervalMs } from "../utils/examDeadline";

// Colour carries the urgency, but never alone - the wording changes too ("Due in 3h 12m" vs
// "Past due"), so the badge still reads correctly in greyscale or to a colour-blind student.
const STYLES = {
  upcoming: "text-muted-foreground border-border bg-secondary",
  soon: "text-amber-800 border-amber-300 bg-amber-50",
  urgent: "text-red-700 border-red-300 bg-red-50",
  overdue: "text-red-700 border-red-300 bg-red-50",
};

const ICONS = { upcoming: CalendarClock, soon: Clock, urgent: AlarmClock, overdue: AlarmClock };

/**
 * The live "time remaining" pill next to an exam's due date.
 *
 * Deliberately says "Past due" and not "Closed": the backend does not enforce end_time
 * (start_exam checks is_active, eligibility and face enrolment only), so an overdue exam whose
 * instructor left it active can still be started. Claiming it is closed would be the same
 * failure as the pre-exam checklist that looked like a gate and gated nothing.
 */
export default function DeadlineBadge({ endTime, startTime = null, className = "" }) {
  const [now, setNow] = useState(() => Date.now());
  const state = getDeadlineState(endTime, now, startTime);

  const interval = state.status === "none" ? null : tickIntervalMs(state.remainingMs);
  useEffect(() => {
    if (interval === null) return;
    const id = setInterval(() => setNow(Date.now()), interval);
    return () => clearInterval(id);
  }, [interval]);

  if (state.status === "none") return null;

  const Icon = ICONS[state.status];
  const text = state.status === "overdue" ? `Past due — ${state.label}` : `Due in ${state.label}`;

  return (
    <span
      // The countdown changes without the student doing anything, so a screen reader that has
      // already moved on should not be dragged back to it - polite, and only the text matters.
      aria-live="polite"
      className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 font-mono text-[10px] ${
        STYLES[state.status]
      } ${className}`}
    >
      <Icon className="h-3 w-3 shrink-0" aria-hidden="true" />
      {text}
    </span>
  );
}
