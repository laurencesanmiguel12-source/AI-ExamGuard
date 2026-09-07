import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ViolationAlertModal from "./ViolationAlertModal";

describe("ViolationAlertModal", () => {
  it("explains what was flagged in the student's own terms", () => {
    render(<ViolationAlertModal eventType="TAB_SWITCH" count={1} onDismiss={() => {}} />);

    expect(screen.getByRole("dialog", { name: /left the exam tab/i })).toBeInTheDocument();
    expect(screen.getByText(/stay on this tab until you submit/i)).toBeInTheDocument();
  });

  it("reassures the student their work and time are intact", () => {
    // The single biggest worry when an unexpected modal appears mid-exam is "have I lost my
    // answers / my time?". Saying so up front is the difference between a useful warning and a
    // frightening one.
    render(<ViolationAlertModal eventType="COPY_PASTE" count={1} onDismiss={() => {}} />);

    expect(screen.getByText(/answers are saved/i)).toBeInTheDocument();
    expect(screen.getByText(/timer has not been paused/i)).toBeInTheDocument();
  });

  it("does not accuse the student when the detector may simply be wrong", () => {
    render(<ViolationAlertModal eventType="PHONE_DETECTED" count={1} onDismiss={() => {}} />);

    const body = screen.getByRole("dialog").textContent;
    expect(body).toMatch(/if this is a mistake/i);
    expect(body).not.toMatch(/cheat/i);
  });

  it("mentions a repeat count only once it is actually repeating", () => {
    const { unmount } = render(
      <ViolationAlertModal eventType="TAB_SWITCH" count={1} onDismiss={() => {}} />
    );
    expect(screen.queryByText(/this has now happened/i)).toBe(null);
    unmount();

    render(<ViolationAlertModal eventType="TAB_SWITCH" count={4} onDismiss={() => {}} />);
    expect(screen.getByText(/happened 4 times/i)).toBeInTheDocument();
  });

  it("dismisses on the button", async () => {
    const onDismiss = vi.fn();
    render(<ViolationAlertModal eventType="TAB_SWITCH" count={1} onDismiss={onDismiss} />);

    await userEvent.click(screen.getByRole("button", { name: /continue exam/i }));

    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it("offers to restore full screen, and uses the dismissing click to do it", async () => {
    // Re-entering full screen requires a user gesture, so it has to happen on this click - a
    // student cannot be expected to know the shortcut.
    const request = vi.fn().mockResolvedValue(undefined);
    document.documentElement.requestFullscreen = request;
    const onDismiss = vi.fn();

    render(<ViolationAlertModal eventType="FULLSCREEN_EXIT" count={1} onDismiss={onDismiss} />);
    await userEvent.click(screen.getByRole("button", { name: /return to full screen/i }));

    expect(request).toHaveBeenCalled();
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it("still says something useful for an event type it has no copy for", () => {
    render(<ViolationAlertModal eventType="SOME_NEW_SIGNAL" count={1} onDismiss={() => {}} />);

    expect(screen.getByRole("dialog", { name: /something was flagged/i })).toBeInTheDocument();
  });
});
