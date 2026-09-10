import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import DataTable from "./DataTable";

/**
 * Reported in QA on the Instructors page: "clicking Manage, 2 modals pop up".
 *
 * The cause was general rather than specific to that page. DataTable stopped propagation on its
 * trailing Edit/Delete cell only, so any control a page rendered inside a normal column also
 * counted as a click on the row - firing the row's detail dialog behind whatever the control did.
 * Fixed once here so a page adding a button to a column does not have to remember.
 */
function setup({ onRowClick, onManage }) {
  const columns = [
    { key: "name", label: "Name" },
    {
      key: "manage",
      label: "Manage",
      render: (row) => (
        <button onClick={() => onManage(row)}>Manage subjects</button>
      ),
    },
  ];
  render(
    <DataTable
      columns={columns}
      rows={[{ id: 1, name: "Ana Cruz" }]}
      loading={false}
      onRowClick={onRowClick}
    />
  );
}

describe("DataTable — a control inside a cell is not a click on the row", () => {
  it("does not open the row when a button in a cell is clicked", async () => {
    const onRowClick = vi.fn();
    const onManage = vi.fn();
    setup({ onRowClick, onManage });

    await userEvent.click(screen.getByRole("button", { name: "Manage subjects" }));

    expect(onManage).toHaveBeenCalledTimes(1);
    expect(onRowClick).not.toHaveBeenCalled();
  });

  it("still opens the row when the row itself is clicked", async () => {
    const onRowClick = vi.fn();
    const onManage = vi.fn();
    setup({ onRowClick, onManage });

    await userEvent.click(screen.getByText("Ana Cruz"));

    expect(onRowClick).toHaveBeenCalledTimes(1);
    expect(onManage).not.toHaveBeenCalled();
  });

  it("does not open the row when Enter is pressed on a focused inner button", async () => {
    // The keyboard path had the same hole: the row's onKeyDown fires for anything focused inside
    // it, so Enter on the inner button opened the dialog as well as pressing the button.
    const onRowClick = vi.fn();
    const onManage = vi.fn();
    setup({ onRowClick, onManage });

    screen.getByRole("button", { name: "Manage subjects" }).focus();
    await userEvent.keyboard("{Enter}");

    expect(onManage).toHaveBeenCalledTimes(1);
    expect(onRowClick).not.toHaveBeenCalled();
  });

  it("still opens the row on Enter when the row holds focus", async () => {
    const onRowClick = vi.fn();
    setup({ onRowClick, onManage: vi.fn() });

    const row = screen.getByRole("button", { name: /ana cruz/i });
    row.focus();
    await userEvent.keyboard("{Enter}");

    expect(onRowClick).toHaveBeenCalledTimes(1);
  });
});
