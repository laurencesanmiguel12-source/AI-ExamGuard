import { useState } from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Modal from "./Modal";

// Every dialog in the app (edit forms on the list pages, every delete confirmation) renders
// through this component, so these guarantees hold app-wide or nowhere.
describe("Modal", () => {
  it("exposes itself to assistive tech as a dialog named by its heading", () => {
    render(<Modal title="Delete Course" onClose={() => {}}>body</Modal>);

    const dialog = screen.getByRole("dialog");
    expect(dialog).toBeInTheDocument();
    expect(dialog.getAttribute("aria-modal")).toBe("true");
    // The accessible name has to come from the visible heading, not a duplicated string.
    expect(screen.getByRole("dialog", { name: "Delete Course" })).toBeInTheDocument();
  });

  it("moves focus into the dialog on open", () => {
    render(<Modal title="Edit" onClose={() => {}}>body</Modal>);

    // Without this a screen reader never announces the dialog and a keyboard user is still
    // tabbing through the page behind it.
    expect(document.activeElement).toBe(screen.getByRole("dialog"));
  });

  it("closes on Escape", async () => {
    const onClose = vi.fn();
    render(<Modal title="Edit" onClose={onClose}>body</Modal>);

    await userEvent.keyboard("{Escape}");

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("closes from the close button", async () => {
    const onClose = vi.fn();
    render(<Modal title="Edit" onClose={onClose}>body</Modal>);

    await userEvent.click(screen.getByRole("button", { name: "Close dialog" }));

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("keeps Tab inside the dialog", async () => {
    render(
      <Modal title="Edit" onClose={() => {}}>
        <button type="button">Save</button>
      </Modal>
    );

    // Close button and Save are the only focusables; tabbing past the last must wrap to the
    // first rather than escaping to the page underneath.
    await userEvent.tab();
    await userEvent.tab();
    await userEvent.tab();

    expect(screen.getByRole("dialog").contains(document.activeElement)).toBe(true);
  });

  it("restores focus to whatever opened it", async () => {
    function Harness() {
      const [open, setOpen] = useState(false);
      return (
        <>
          <button type="button" onClick={() => setOpen(true)}>Open</button>
          {open && <Modal title="Edit" onClose={() => setOpen(false)}>body</Modal>}
        </>
      );
    }
    render(<Harness />);
    const opener = screen.getByRole("button", { name: "Open" });

    await userEvent.click(opener);
    await userEvent.keyboard("{Escape}");

    expect(document.activeElement).toBe(opener);
  });
});
