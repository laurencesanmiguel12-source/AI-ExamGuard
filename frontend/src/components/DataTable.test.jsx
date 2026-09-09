import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import DataTable from "./DataTable";

const COLUMNS = [
  { key: "name", label: "Name" },
  { key: "code", label: "Code" },
];

const ROWS = [
  { id: 1, name: "Ana Cruz", code: "CS-101" },
  { id: 2, name: "Ben Reyes", code: "IT-201" },
  { id: 3, name: "Carla Uy", code: "CS-301" },
];

function show(props = {}) {
  return render(<DataTable columns={COLUMNS} rows={ROWS} {...props} />);
}

describe("DataTable — search", () => {
  it("renders no search box unless the caller asks for one", () => {
    show();
    expect(screen.queryByRole("searchbox")).toBe(null);
  });

  it("narrows the list as you type", async () => {
    show({ searchable: true });

    await userEvent.type(screen.getByRole("searchbox"), "ben");

    expect(screen.getByText("Ben Reyes")).toBeInTheDocument();
    expect(screen.queryByText("Ana Cruz")).toBe(null);
  });

  it("searches every column, not just the first", async () => {
    show({ searchable: true });

    await userEvent.type(screen.getByRole("searchbox"), "IT-201");

    expect(screen.getByText("Ben Reyes")).toBeInTheDocument();
    expect(screen.queryByText("Carla Uy")).toBe(null);
  });

  it("ignores case", async () => {
    show({ searchable: true });
    await userEvent.type(screen.getByRole("searchbox"), "ANA");
    expect(screen.getByText("Ana Cruz")).toBeInTheDocument();
  });

  it("treats multiple words as narrowing, not widening", async () => {
    // "carla cs" should find only Carla - a naive substring match would find nothing, and an
    // OR match would return everyone with either term.
    show({ searchable: true });

    await userEvent.type(screen.getByRole("searchbox"), "carla cs");

    expect(screen.getByText("Carla Uy")).toBeInTheDocument();
    expect(screen.queryByText("Ana Cruz")).toBe(null);
  });

  it("reports how much it is hiding", async () => {
    show({ searchable: true });
    await userEvent.type(screen.getByRole("searchbox"), "cs-");
    expect(screen.getByText("2 of 3 shown")).toBeInTheDocument();
  });

  it("distinguishes 'no matches' from 'nothing here yet'", async () => {
    // Telling someone "No records yet" when they mistyped sends them off to create a duplicate
    // of something that already exists.
    show({ searchable: true, emptyLabel: "No students yet." });

    await userEvent.type(screen.getByRole("searchbox"), "zzzz");

    expect(screen.getByText(/no matches for/i)).toBeInTheDocument();
    expect(screen.queryByText("No students yet.")).toBe(null);
  });

  it("can be cleared back to the full list from the empty state", async () => {
    show({ searchable: true });
    await userEvent.type(screen.getByRole("searchbox"), "zzzz");

    await userEvent.click(screen.getByRole("button", { name: /show all 3 records/i }));

    expect(screen.getByText("Ana Cruz")).toBeInTheDocument();
    expect(screen.getByText("Ben Reyes")).toBeInTheDocument();
  });

  it("clears from the X in the field too", async () => {
    show({ searchable: true });
    await userEvent.type(screen.getByRole("searchbox"), "ben");

    await userEvent.click(screen.getByRole("button", { name: /clear search/i }));

    expect(screen.getByText("Ana Cruz")).toBeInTheDocument();
  });

  it("still shows the genuine empty state when there is nothing to search", () => {
    render(<DataTable columns={COLUMNS} rows={[]} searchable emptyLabel="No students yet." />);
    expect(screen.getByText("No students yet.")).toBeInTheDocument();
  });

  it("matches on what the reader sees, via a column's search accessor", async () => {
    // Columns that render JSX would otherwise be unsearchable, or worse, match on markup.
    const columns = [
      { key: "name", label: "Name" },
      {
        key: "course",
        label: "Course",
        render: (row) => <span>{row.course.code}</span>,
        search: (row) => row.course.code,
      },
    ];
    const rows = [
      { id: 1, name: "Ana", course: { code: "BSCS" } },
      { id: 2, name: "Ben", course: { code: "BSIT" } },
    ];
    render(<DataTable columns={columns} rows={rows} searchable />);

    await userEvent.type(screen.getByRole("searchbox"), "bsit");

    expect(screen.getByText("Ben")).toBeInTheDocument();
    expect(screen.queryByText("Ana")).toBe(null);
  });
});

describe("DataTable — clickable rows", () => {
  it("does not announce rows as interactive when they are not", () => {
    show();
    expect(screen.queryAllByRole("button", { name: /ana cruz/i })).toHaveLength(0);
  });

  it("opens a row on click", async () => {
    const onRowClick = vi.fn();
    show({ onRowClick });

    await userEvent.click(screen.getByText("Ana Cruz"));

    expect(onRowClick).toHaveBeenCalledWith(ROWS[0]);
  });

  it("is reachable and activatable by keyboard", async () => {
    // A div with onClick would be invisible to Tab and unusable without a mouse.
    const onRowClick = vi.fn();
    show({ onRowClick });

    const rows = screen.getAllByRole("button");
    rows[0].focus();
    await userEvent.keyboard("{Enter}");

    expect(onRowClick).toHaveBeenCalledTimes(1);
  });

  it("activates on Space as well as Enter", async () => {
    const onRowClick = vi.fn();
    show({ onRowClick });

    screen.getAllByRole("button")[0].focus();
    await userEvent.keyboard(" ");

    expect(onRowClick).toHaveBeenCalledTimes(1);
  });

  it("does not open the row when Delete is clicked", async () => {
    // Otherwise the detail modal opens behind the delete confirmation.
    const onRowClick = vi.fn();
    const onDelete = vi.fn();
    show({ onRowClick, onDelete });

    await userEvent.click(screen.getAllByRole("button", { name: "Delete" })[0]);

    expect(onDelete).toHaveBeenCalledTimes(1);
    expect(onRowClick).not.toHaveBeenCalled();
  });

  it("does not open the row when Edit is clicked", async () => {
    const onRowClick = vi.fn();
    const onEdit = vi.fn();
    show({ onRowClick, onEdit });

    await userEvent.click(screen.getAllByRole("button", { name: "Edit" })[0]);

    expect(onEdit).toHaveBeenCalledTimes(1);
    expect(onRowClick).not.toHaveBeenCalled();
  });

  it("opens the row the search left visible, not the original index", async () => {
    const onRowClick = vi.fn();
    show({ onRowClick, searchable: true });

    await userEvent.type(screen.getByRole("searchbox"), "carla");
    await userEvent.click(screen.getByText("Carla Uy"));

    expect(onRowClick).toHaveBeenCalledWith(ROWS[2]);
  });
});
