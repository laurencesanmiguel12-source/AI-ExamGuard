import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, act } from "@testing-library/react";
import DeadlineBadge from "./DeadlineBadge";

const MINUTE = 60 * 1000;
const HOUR = 60 * MINUTE;
const NOW = new Date("2026-09-08T12:00:00Z");
const inMs = (ms) => new Date(NOW.getTime() + ms).toISOString();

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(NOW);
});
afterEach(() => {
  vi.useRealTimers();
});

describe("DeadlineBadge", () => {
  it("counts down to the due date", () => {
    render(<DeadlineBadge endTime={inMs(3 * HOUR + 12 * MINUTE)} />);
    expect(screen.getByText(/Due in 3h 12m/)).toBeInTheDocument();
  });

  it("says past due rather than closed, because the server does not close it", () => {
    // start_exam gates on is_active only and never reads end_time, so an overdue-but-active exam
    // can still be started. "Closed" would be the checklist mistake again: a stated gate that
    // does not exist.
    render(<DeadlineBadge endTime={inMs(-2 * HOUR)} />);

    const badge = screen.getByText(/Past due/);
    expect(badge).toBeInTheDocument();
    expect(badge.textContent).toMatch(/2h ago/);
    expect(screen.queryByText(/closed/i)).toBe(null);
  });

  it("updates itself as time passes without a re-render from the parent", () => {
    render(<DeadlineBadge endTime={inMs(90 * MINUTE)} />);
    expect(screen.getByText(/Due in 1h 30m/)).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(30 * MINUTE);
    });

    expect(screen.getByText(/Due in 1h/)).toBeInTheDocument();
  });

  it("flips to past due on its own when the deadline passes while on screen", () => {
    render(<DeadlineBadge endTime={inMs(30 * 1000)} />);
    expect(screen.getByText(/Due in under a minute/)).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(45 * 1000);
    });

    expect(screen.getByText(/Past due/)).toBeInTheDocument();
  });

  it("does not announce itself over whatever the student is reading", () => {
    // It re-renders on a timer with no user action behind it, so it must be polite.
    render(<DeadlineBadge endTime={inMs(2 * HOUR)} />);
    expect(screen.getByText(/Due in/).closest("[aria-live]")).toHaveAttribute(
      "aria-live",
      "polite"
    );
  });

  it("renders nothing when the exam has no end time", () => {
    const { container } = render(<DeadlineBadge endTime={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("stops its timer when unmounted", () => {
    const { unmount } = render(<DeadlineBadge endTime={inMs(2 * HOUR)} />);
    unmount();
    expect(vi.getTimerCount()).toBe(0);
  });
});
