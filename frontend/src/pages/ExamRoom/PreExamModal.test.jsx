import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PreExamModal from "./PreExamModal";

function open() {
  const onConfirm = vi.fn();
  const onCancel = vi.fn();
  render(<PreExamModal examTitle="CS-101 Mock Exam" onConfirm={onConfirm} onCancel={onCancel} />);
  return { onConfirm, onCancel };
}

async function goToAgreement() {
  await userEvent.click(screen.getByRole("button", { name: /next: confirm/i }));
}

describe("PreExamModal", () => {
  it("presents the terms as one statement, not a list of boxes to tick", async () => {
    // The previous eight checkboxes were unbound - ticking them did nothing and skipping them
    // blocked nothing - so they implied a gate that never existed.
    open();
    await goToAgreement();

    expect(screen.queryAllByRole("checkbox")).toHaveLength(0);
  });

  it("still covers every point the old checklist listed", async () => {
    open();
    await goToAgreement();

    const text = document.body.textContent;
    for (const point of [
      /extension/i,
      /webcam/i,
      /well-lit/i,
      /phone/i,
      /stay on the exam tab/i,
      /AI assistants/i,
      /photo up to the camera/i,
      /looking away/i,
      /risk score/i,
      /instructor/i,
    ]) {
      expect(text).toMatch(point);
    }
  });

  it("makes the button itself the act of agreeing", async () => {
    // With no separate checkbox, the button label has to carry the consent - "Enter Exam Room"
    // alone would not be an affirmative agreement to anything.
    open();
    await goToAgreement();

    expect(screen.getByRole("button", { name: /i agree/i })).toBeInTheDocument();
  });

  it("enters the exam on that single click, with nothing else to tick first", async () => {
    const { onConfirm } = open();
    await goToAgreement();

    await userEvent.click(screen.getByRole("button", { name: /i agree/i }));

    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("lets a student back out instead", async () => {
    const { onCancel, onConfirm } = open();
    await goToAgreement();

    await userEvent.click(screen.getByRole("button", { name: /cancel/i }));

    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it("shows the rules before asking the student to agree to them", () => {
    open();

    // Lands on the rules, not the agreement - agreeing to something not yet shown would be
    // meaningless.
    expect(screen.getByText(/proctoring rules/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /i agree/i })).toBe(null);
  });
});
