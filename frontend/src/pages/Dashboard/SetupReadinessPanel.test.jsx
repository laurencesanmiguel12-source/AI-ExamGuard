import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

const mocks = vi.hoisted(() => ({ getSetupReadiness: vi.fn() }));

vi.mock("../../api/setupImport", () => mocks);
vi.mock("../../hooks/useSchoolNav", () => ({ useSchoolSlug: () => "arellano-university" }));

const { default: SetupReadinessPanel } = await import("./SetupReadinessPanel");

const EMPTY = {
  current_year: "2026-2027",
  active_term: "1st Semester",
  instructors_without_subjects: [],
  subjects_without_instructor: [],
  subjects_without_section: [],
  sections_without_enrollment: [],
  ready: true,
  blocking_step: null,
};

async function show(overrides = {}) {
  mocks.getSetupReadiness.mockResolvedValue({ ...EMPTY, ...overrides });
  render(
    <MemoryRouter>
      <SetupReadinessPanel />
    </MemoryRouter>
  );
  await waitFor(() =>
    expect(screen.getByRole("heading", { name: /what's left to set up/i })).toBeInTheDocument()
  );
}

beforeEach(() => vi.clearAllMocks());

describe("Setup readiness", () => {
  it("names one next step rather than handing over four lists", async () => {
    // Six things to choose between is not an answer to "what do I do next". The report walks the
    // program flow in order, so the first unmet item genuinely is the next thing to do.
    await show({
      ready: false,
      blocking_step: "No sections in 1st Semester yet. Open one per class being taught.",
      subjects_without_section: [{ id: 1, label: "CS-101 Intro", detail: "BSCS" }],
      instructors_without_subjects: [{ id: 2, label: "Ana Cruz", detail: "Employee EMP-1" }],
    });

    expect(screen.getByRole("status")).toHaveTextContent(/no sections in 1st semester yet/i);
  });

  it("says a school is ready once one class could sit an exam", async () => {
    // Ready means "a class could sit an exam today", not "everything is tidy" - nagging a running
    // school about loose ends it has chosen to leave is how a checklist gets ignored.
    await show({ subjects_without_instructor: [{ id: 3, label: "IT-101 Web", detail: "BSIT" }] });

    expect(screen.getByRole("status")).toHaveTextContent(/ready to run exams/i);
    expect(screen.getByRole("status")).toHaveTextContent(/nothing is blocked/i);
  });

  it("lists instructors who arrived without a subject, which is the floating case", async () => {
    // The panel's words: "it can be left floating then add a workflow to connect them".
    await show({
      instructors_without_subjects: [{ id: 2, label: "Ana Cruz", detail: "Employee EMP-1" }],
    });

    expect(
      screen.getByRole("heading", { name: /instructors teaching nothing \(1\)/i })
    ).toBeInTheDocument();
    expect(screen.getByText("Ana Cruz")).toBeInTheDocument();
  });

  it("gives every group a route to the screen that fixes it", async () => {
    // A list saying "these are unlinked" with no way to link them is a report, not a workflow.
    await show({
      subjects_without_instructor: [{ id: 3, label: "IT-101 Web", detail: "BSIT" }],
      sections_without_enrollment: [{ id: 4, label: "CS-101 A", detail: "Nobody enrolled" }],
    });

    expect(screen.getByRole("link", { name: /assign an instructor/i })).toHaveAttribute(
      "href",
      "/arellano-university/instructors"
    );
    expect(screen.getByRole("link", { name: /enrol students/i })).toHaveAttribute(
      "href",
      "/arellano-university/sections"
    );
  });

  it("hides groups that have nothing in them", async () => {
    await show({ subjects_without_instructor: [{ id: 3, label: "IT-101 Web" }] });

    expect(screen.getByRole("heading", { name: /subjects nobody teaches/i })).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: /instructors teaching nothing/i })
    ).not.toBeInTheDocument();
  });

  it("says so plainly when nothing is left unconnected", async () => {
    await show();

    expect(screen.getByText(/nothing is left unconnected/i)).toBeInTheDocument();
  });

  it("names the term it is checking, because the answer changes every term", async () => {
    await show();

    expect(screen.getByText(/2026-2027 · 1st Semester/)).toBeInTheDocument();
  });

  it("says when no term is running rather than showing a blank", async () => {
    await show({
      active_term: null,
      ready: false,
      blocking_step: "No term is running. Activate one on the Academic Calendar so classes have somewhere to sit.",
    });

    expect(screen.getByText(/no term running/i)).toBeInTheDocument();
  });

  it("caps a long list rather than printing three hundred names", async () => {
    await show({
      subjects_without_instructor: Array.from({ length: 15 }, (_, i) => ({
        id: i + 1,
        label: `SUB-${i + 1}`,
      })),
    });

    expect(screen.getByText("+3 more")).toBeInTheDocument();
  });
});
