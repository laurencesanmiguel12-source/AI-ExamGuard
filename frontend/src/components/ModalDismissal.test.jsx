import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import Modal from "./Modal";
import FaceEnrollmentGuideModal from "./FaceEnrollmentGuideModal";

/**
 * Found in a sweep of every modal, button and link.
 *
 * Modal always rendered its X and always called onClose on Escape. A dialog rendered without an
 * onClose - the biometric consent gate is one, deliberately - therefore showed a close button
 * that did nothing, and threw a TypeError on Escape while staying open.
 */
describe("Modal — a dialog with no close handler", () => {
  it("does not render a close button it cannot honour", () => {
    render(<Modal title="Gate">body</Modal>);

    expect(screen.queryByRole("button", { name: /close dialog/i })).not.toBeInTheDocument();
  });

  it("ignores Escape instead of throwing", async () => {
    render(<Modal title="Gate">body</Modal>);

    // Before the fix this called undefined() and the error surfaced from the keydown listener.
    await userEvent.keyboard("{Escape}");

    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("still closes on Escape when a handler is given", async () => {
    const onClose = vi.fn();
    render(
      <Modal title="Editable" onClose={onClose}>
        body
      </Modal>
    );

    await userEvent.keyboard("{Escape}");

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("still renders the close button when a handler is given", async () => {
    const onClose = vi.fn();
    render(
      <Modal title="Editable" onClose={onClose}>
        body
      </Modal>
    );

    await userEvent.click(screen.getByRole("button", { name: /close dialog/i }));

    expect(onClose).toHaveBeenCalledTimes(1);
  });
});

describe("Face enrollment consent — a choice needs both answers", () => {
  it("offers a way to decline, not only to agree", async () => {
    // The only exits were "I Understand, Continue" and the browser back button. For a biometric
    // consent step that is not a choice being offered.
    const onDecline = vi.fn();
    render(<FaceEnrollmentGuideModal onContinue={vi.fn()} onDecline={onDecline} />);

    await userEvent.click(screen.getByRole("button", { name: /not now/i }));

    expect(onDecline).toHaveBeenCalledTimes(1);
  });

  it("keeps Continue disabled until the consent box is ticked", async () => {
    render(<FaceEnrollmentGuideModal onContinue={vi.fn()} onDecline={vi.fn()} />);

    expect(screen.getByRole("button", { name: /i understand, continue/i })).toBeDisabled();

    await userEvent.click(screen.getByRole("checkbox"));

    expect(screen.getByRole("button", { name: /i understand, continue/i })).not.toBeDisabled();
  });

  it("does not require consent to leave", async () => {
    // Declining must not be gated on the checkbox - that would make the exit conditional on
    // agreeing to the thing being declined.
    const onDecline = vi.fn();
    render(<FaceEnrollmentGuideModal onContinue={vi.fn()} onDecline={onDecline} />);

    expect(screen.getByRole("button", { name: /not now/i })).not.toBeDisabled();
  });

  it("now honours the close button in its header", async () => {
    const onDecline = vi.fn();
    render(<FaceEnrollmentGuideModal onContinue={vi.fn()} onDecline={onDecline} />);

    await userEvent.click(screen.getByRole("button", { name: /close dialog/i }));

    expect(onDecline).toHaveBeenCalledTimes(1);
  });
});

describe("ConfirmDialog — the button says what it does", () => {
  it("still says Delete by default, since most callers are deleting", async () => {
    const { default: ConfirmDialog } = await import("./ConfirmDialog");
    render(<ConfirmDialog title="Delete Course" message="Sure?" onConfirm={vi.fn()} onCancel={vi.fn()} />);

    expect(screen.getByRole("button", { name: "Delete" })).toBeInTheDocument();
  });

  it("says what a non-delete confirmation actually does", async () => {
    // "Close Term" explained that enrolments would be marked completed and then offered a red
    // button labelled "Delete" - which reads as though the term is about to be destroyed.
    const { default: ConfirmDialog } = await import("./ConfirmDialog");
    render(
      <ConfirmDialog
        title="Close Term"
        message="Close 1st Semester?"
        confirmLabel="Close term"
        busyLabel="Closing…"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    );

    expect(screen.getByRole("button", { name: "Close term" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete" })).not.toBeInTheDocument();
  });
});
