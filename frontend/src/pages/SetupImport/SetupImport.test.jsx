import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

const mocks = vi.hoisted(() => ({
  importSetupCsv: vi.fn(),
  previewSetupCsv: vi.fn(),
  getSetupReadiness: vi.fn(),
}));

vi.mock("../../api/setupImport", () => mocks);
vi.mock("../../hooks/useSchoolNav", () => ({ useSchoolSlug: () => "arellano-university" }));

const { default: SetupImport } = await import("./SetupImport");

// The readiness panel fetches on mount and renders Links, so the page needs a router and a
// resolved report to render at all.
mocks.getSetupReadiness.mockResolvedValue({
  current_year: "2026-2027",
  active_term: "1st Semester",
  instructors_without_subjects: [],
  subjects_without_instructor: [],
  subjects_without_section: [],
  sections_without_enrollment: [],
  ready: true,
  blocking_step: null,
});

function renderPage() {
  return render(
    <MemoryRouter>
      <SetupImport />
    </MemoryRouter>
  );
}

describe("Bulk Import page", () => {
  it("names itself the same way the sidebar entry does", () => {
    // The sidebar-label-matches-page-title convention: the sidebar says "Bulk Import", so
    // landing here must confirm you arrived somewhere with that name.
    renderPage();
    expect(screen.getByRole("heading", { name: "Bulk Import" })).toBeInTheDocument();
  });

  it("places itself in the area that owns what it creates", () => {
    renderPage();
    expect(screen.getByText("Academic Management")).toBeInTheDocument();
  });

  it("carries the actual importer, not just a heading", () => {
    renderPage();
    // Two buttons now, and the checking one leads - the panel asked to see what a file would do
    // before it does it, and a step nobody is told about is a step nobody takes.
    expect(screen.getByRole("button", { name: /check this file/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /import for real/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/choose a setup csv/i)).toBeInTheDocument();
  });

  it("still offers the template and the column guide", () => {
    // These are what make the page usable without documentation - the whole reason it is worth
    // surfacing in the sidebar rather than leaving buried in a dashboard tab.
    renderPage();
    expect(screen.getByRole("button", { name: /download template/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /column guide/i })).toBeInTheDocument();
  });

  it("does not repeat its own title inside the panel", () => {
    // The panel used to carry its own heading; under a PageHeader that would say the same thing
    // twice on one screen.
    renderPage();
    expect(screen.getAllByText(/bulk import/i)).toHaveLength(1);
  });
});
