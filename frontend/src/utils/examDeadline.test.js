import { describe, it, expect } from "vitest";
import {
  formatRemaining,
  getDeadlineState,
  tickIntervalMs,
  URGENT_MS,
  SOON_MS,
} from "./examDeadline";

const MINUTE = 60 * 1000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;
const NOW = new Date("2026-09-08T12:00:00Z").getTime();
const iso = (ms) => new Date(NOW + ms).toISOString();

describe("formatRemaining", () => {
  it("drops to coarser units as the deadline gets further away", () => {
    expect(formatRemaining(45 * MINUTE)).toBe("45m");
    expect(formatRemaining(3 * HOUR + 12 * MINUTE)).toBe("3h 12m");
    expect(formatRemaining(2 * DAY + 4 * HOUR)).toBe("2d 4h");
  });

  it("omits an empty trailing unit rather than showing '3h 0m'", () => {
    expect(formatRemaining(3 * HOUR)).toBe("3h");
    expect(formatRemaining(2 * DAY)).toBe("2d");
  });

  it("does not count down in seconds", () => {
    // A student cannot act on "0h 0m 42s", and rendering it costs a re-render a second.
    expect(formatRemaining(42 * 1000)).toBe("under a minute");
  });

  it("never renders a negative duration", () => {
    expect(formatRemaining(-5 * HOUR)).toBe("0m");
    expect(formatRemaining(0)).toBe("0m");
  });
});

describe("getDeadlineState", () => {
  it("escalates from upcoming to soon to urgent as the deadline nears", () => {
    expect(getDeadlineState(iso(3 * DAY), NOW).status).toBe("upcoming");
    expect(getDeadlineState(iso(5 * HOUR), NOW).status).toBe("soon");
    expect(getDeadlineState(iso(20 * MINUTE), NOW).status).toBe("urgent");
  });

  it("puts the boundaries in the more urgent band, not the calmer one", () => {
    // Exactly one hour left is urgent, not "soon" - rounding a deadline in the student's
    // disfavour is the wrong direction to be wrong in.
    expect(getDeadlineState(iso(URGENT_MS), NOW).status).toBe("urgent");
    expect(getDeadlineState(iso(SOON_MS), NOW).status).toBe("soon");
  });

  it("reports a passed deadline as overdue, with how long ago it passed", () => {
    const state = getDeadlineState(iso(-2 * HOUR), NOW);
    expect(state.status).toBe("overdue");
    expect(state.label).toBe("2h ago");
  });

  it("flags an exam that has not opened yet, so 'due in 6d' is not read as 6 days of work", () => {
    const state = getDeadlineState(iso(6 * DAY), NOW, iso(5 * DAY));
    expect(state.notYetOpen).toBe(true);
    expect(state.label).toBe("6d");
  });

  it("does not call an already-open exam not-yet-open", () => {
    expect(getDeadlineState(iso(6 * DAY), NOW, iso(-1 * DAY)).notYetOpen).toBe(false);
  });

  it("an overdue exam is never also pending its start", () => {
    // Both true at once would render as a contradiction.
    const state = getDeadlineState(iso(-1 * HOUR), NOW, iso(-2 * HOUR));
    expect(state.status).toBe("overdue");
    expect(state.notYetOpen).toBe(false);
  });

  it("renders nothing rather than 'Invalid Date' for a missing or unparseable end time", () => {
    expect(getDeadlineState(null, NOW).status).toBe("none");
    expect(getDeadlineState(undefined, NOW).status).toBe("none");
    expect(getDeadlineState("not a date", NOW).status).toBe("none");
  });

  it("reads a timezone-qualified timestamp as the instant it names", () => {
    // The API sends tz-aware timestamps; +08:00 noon is 04:00Z, eight hours before NOW.
    const state = getDeadlineState("2026-09-08T12:00:00+08:00", NOW);
    expect(state.status).toBe("overdue");
    expect(state.label).toBe("8h ago");
  });
});

describe("tickIntervalMs", () => {
  it("ticks fast only when the label is about to change", () => {
    expect(tickIntervalMs(30 * 1000)).toBe(1000);
    expect(tickIntervalMs(30 * MINUTE)).toBe(15 * 1000);
    expect(tickIntervalMs(5 * DAY)).toBe(60 * 1000);
  });

  it("ticks fast just after the deadline too, not just before it", () => {
    expect(tickIntervalMs(-30 * 1000)).toBe(1000);
  });
});
