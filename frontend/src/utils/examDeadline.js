// Deadline maths for exam rows, kept pure and separate from the components that render it.
//
// `exam.end_time` has always been in the API response and on the create form, but nothing has
// ever shown it to a student - the dashboard only ever printed `start_time`. So the one date a
// student needs to plan around was the one date they could not see.
//
// One caveat this module is deliberately honest about: **the backend does not enforce
// end_time.** ExamSessionService.start_exam gates on is_active, eligibility and face enrolment
// only, and never looks at either end_time or start_time. So a passed deadline does not actually
// stop anyone, and the UI must not imply it does - see DEADLINE_IS_ADVISORY below and the way
// `overdue` is worded where it is rendered.

const MINUTE = 60 * 1000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

// Exposed so the calling component and its tests state the same thing rather than each deciding
// independently how much of a gate the deadline is.
export const DEADLINE_IS_ADVISORY = true;

export const URGENT_MS = HOUR;
export const SOON_MS = DAY;

/**
 * "2d 4h", "3h 12m", "45m", "under a minute" - coarse on purpose. A student reading a due date
 * wants to know whether to act now or tonight, and seconds ticking on a multi-day deadline is
 * noise that also forces a once-a-second re-render for no information.
 */
export function formatRemaining(ms) {
  if (ms <= 0) return "0m";
  if (ms < MINUTE) return "under a minute";

  if (ms >= DAY) {
    const days = Math.floor(ms / DAY);
    const hours = Math.floor((ms % DAY) / HOUR);
    return hours > 0 ? `${days}d ${hours}h` : `${days}d`;
  }
  if (ms >= HOUR) {
    const hours = Math.floor(ms / HOUR);
    const minutes = Math.floor((ms % HOUR) / MINUTE);
    return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`;
  }
  return `${Math.floor(ms / MINUTE)}m`;
}

/**
 * Classifies where an exam sits relative to its window.
 *
 * `notYetOpen` matters because "Due in 6d" on an exam that does not open for five of those days
 * reads as six days of working time. The two facts only mean something together.
 */
export function getDeadlineState(endTime, now = Date.now(), startTime = null) {
  if (!endTime) return { status: "none" };

  const end = new Date(endTime).getTime();
  if (Number.isNaN(end)) return { status: "none" };

  const start = startTime ? new Date(startTime).getTime() : null;
  const notYetOpen = start !== null && !Number.isNaN(start) && now < start;
  const remainingMs = end - now;

  if (remainingMs <= 0) {
    return {
      status: "overdue",
      remainingMs,
      notYetOpen: false,
      // Time *since* the deadline, so the row can say how stale it is.
      label: `${formatRemaining(-remainingMs)} ago`,
    };
  }

  const status =
    remainingMs <= URGENT_MS ? "urgent" : remainingMs <= SOON_MS ? "soon" : "upcoming";

  return { status, remainingMs, notYetOpen, label: formatRemaining(remainingMs) };
}

/**
 * How often a badge showing `label` needs to re-render to stay truthful.
 *
 * The label's own granularity decides this: while it reads "3h 12m" a 30s tick is already
 * finer than the text can show, but near zero the flip to overdue should not lag by half a
 * minute on the one screen where the deadline is the point.
 */
export function tickIntervalMs(remainingMs) {
  if (remainingMs === undefined || remainingMs === null) return 60 * 1000;
  const ms = Math.abs(remainingMs);
  if (ms <= 2 * MINUTE) return 1000;
  if (ms <= HOUR) return 15 * 1000;
  return 60 * 1000;
}
