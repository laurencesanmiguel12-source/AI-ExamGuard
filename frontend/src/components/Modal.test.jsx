import { useState } from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Modal from "./Modal";

function open(children = <p>body</p>) {
  const onClose = vi.fn();
  const utils = render(<Modal title="Add Exam" onClose={onClose}>{children}</Modal>);
  return { onClose, ...utils };
}

describe("Modal", () => {
  it("keeps the close button reachable no matter how tall the form is", () => {
    // The defense-panel report: a ten-field form overflowed a centred, position-fixed panel, so
    // the X ended up ABOVE the top of the window and submit below the bottom of it. The header
    // must not scroll away with the body.
    const { container } = open();
    const panel = container.querySelector('[role="dialog"]');
    const header = screen.getByRole("button", { name: /close dialog/i }).parentElement;

    expect(panel.className).toMatch(/max-h-/);
    expect(panel.className).toMatch(/flex-col/);
    expect(header.className).toMatch(/shrink-0/);
  });

  it("scrolls the body rather than the whole panel", () => {
    const { container } = open();
    const body = container.querySelector('[role="dialog"] > div:last-child');

    expect(body.className).toMatch(/overflow-y-auto/);
    // Without min-h-0 a flex child refuses to shrink below its content, and the overflow rule
    // silently does nothing - the exact failure this is guarding.
    expect(body.className).toMatch(/min-h-0/);
  });

  it("lets the backdrop scroll as a fallback on a very short window", () => {
    const { container } = open();
    expect(container.firstChild.className).toMatch(/overflow-y-auto/);
  });

  it("still closes on the X", async () => {
    const { onClose } = open();
    await userEvent.click(screen.getByRole("button", { name: /close dialog/i }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("still closes on Escape", async () => {
    const { onClose } = open();
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("keeps its dialog semantics and labelling", () => {
    open();
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(dialog.getAttribute("aria-labelledby")).toBeTruthy();
    expect(screen.getByText("Add Exam")).toBeInTheDocument();
  });

  it("renders its children", () => {
    open(<button>Save exam</button>);
    expect(screen.getByRole("button", { name: "Save exam" })).toBeInTheDocument();
  });

  it("lets you type a whole word into a field without losing the caret", async () => {
    // The defense-panel report: "cannot type continuously". Every parent re-render passed a new
    // onClose arrow function, the focus effect re-ran, and focus jumped from the input back to
    // the dialog container - so a field accepted one character at a time.
    function Host() {
      const [value, setValue] = useState("");
      // Deliberately a fresh arrow each render, exactly as every real caller writes it.
      return (
        <Modal title="Add Instructor" onClose={() => {}}>
          <input
            aria-label="First name"
            value={value}
            onChange={(e) => setValue(e.target.value)}
          />
        </Modal>
      );
    }
    render(<Host />);

    const field = screen.getByLabelText("First name");
    field.focus();
    await userEvent.keyboard("Noelito");

    expect(field).toHaveValue("Noelito");
    expect(document.activeElement).toBe(field);
  });

  it("focuses the dialog once on open, not on every re-render", async () => {
    function Host() {
      const [n, setN] = useState(0);
      return (
        <Modal title="Add Instructor" onClose={() => {}}>
          <button onClick={() => setN(n + 1)}>bump {n}</button>
          <input aria-label="Email" />
        </Modal>
      );
    }
    render(<Host />);

    const field = screen.getByLabelText("Email");
    field.focus();
    // A re-render from anything else in the form must not steal the caret either.
    await userEvent.click(screen.getByRole("button", { name: /bump/i }));
    field.focus();
    await userEvent.keyboard("a@b.co");

    expect(field).toHaveValue("a@b.co");
  });
});
