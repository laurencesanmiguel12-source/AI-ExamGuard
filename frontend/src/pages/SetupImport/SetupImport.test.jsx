import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("../../api/setupImport", () => ({ importSetupCsv: vi.fn() }));

const { default: SetupImport } = await import("./SetupImport");

describe("Bulk Import page", () => {
  it("names itself the same way the sidebar entry does", () => {
    // The sidebar-label-matches-page-title convention: the sidebar says "Bulk Import", so
    // landing here must confirm you arrived somewhere with that name.
    render(<SetupImport />);
    expect(screen.getByRole("heading", { name: "Bulk Import" })).toBeInTheDocument();
  });

  it("places itself in the area that owns what it creates", () => {
    render(<SetupImport />);
    expect(screen.getByText("Academic Management")).toBeInTheDocument();
  });

  it("carries the actual importer, not just a heading", () => {
    render(<SetupImport />);
    expect(screen.getByRole("button", { name: /^import$/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/choose a setup csv/i)).toBeInTheDocument();
  });

  it("still offers the template and the column guide", () => {
    // These are what make the page usable without documentation - the whole reason it is worth
    // surfacing in the sidebar rather than leaving buried in a dashboard tab.
    render(<SetupImport />);
    expect(screen.getByRole("button", { name: /download template/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /column guide/i })).toBeInTheDocument();
  });

  it("does not repeat its own title inside the panel", () => {
    // The panel used to carry its own heading; under a PageHeader that would say the same thing
    // twice on one screen.
    render(<SetupImport />);
    expect(screen.getAllByText(/bulk import/i)).toHaveLength(1);
  });
});
