import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const mocks = vi.hoisted(() => ({
  user: null,
  navigate: vi.fn(),
  getSections: vi.fn(),
  createSection: vi.fn(),
  getAcademicYears: vi.fn(),
  getTerms: vi.fn(),
  getSubjects: vi.fn(),
  getInstructors: vi.fn(),
}));

vi.mock("../../api/academic", () => ({
  getSections: mocks.getSections,
  createSection: mocks.createSection,
  getAcademicYears: mocks.getAcademicYears,
  getTerms: mocks.getTerms,
}));
vi.mock("../../api/subjects", () => ({ getSubjects: mocks.getSubjects }));
vi.mock("../../api/instructors", () => ({ getInstructors: mocks.getInstructors }));
vi.mock("../../context/AuthContext", () => ({ useAuth: () => ({ user: mocks.user }) }));
vi.mock("../../hooks/useSchoolNav", () => ({ useSchoolNav: () => mocks.navigate }));

const { default: Sections } = await import("./Sections");

function section(overrides) {
  return {
    id: 5,
    code: "BSCS-3A",
    subject_code: "CS-101",
    subject_name: "Intro to Programming",
    term_name: "1st Semester",
    academic_year_label: "2026-2027",
    instructor_name: "Ana Cruz",
    enrolled_count: 3,
    ...overrides,
  };
}

async function show({ role = "admin", sections = [section()] } = {}) {
  mocks.user = { id: 1, role_name: role };
  mocks.getSections.mockResolvedValue(sections);
  mocks.getAcademicYears.mockResolvedValue([{ id: 1, label: "2026-2027" }]);
  mocks.getTerms.mockResolvedValue([{ id: 9, name: "1st Semester", status: "ACTIVE" }]);
  mocks.getSubjects.mockResolvedValue([{ id: 2, code: "CS-101", name: "Intro to Programming" }]);
  mocks.getInstructors.mockResolvedValue([{ id: 3, instructor_name: "Ana Cruz" }]);
  render(<Sections />);
  await waitFor(() => expect(mocks.getSections).toHaveBeenCalled());
}

beforeEach(() => vi.clearAllMocks());

describe("Sections & Class Lists", () => {
  it("names a section by everything that makes it one, not just its code", async () => {
    // A section is one subject, in one term, taught by one instructor. Showing only "BSCS-3A"
    // is exactly the problem the hierarchy exists to fix: two instructors on the same subject
    // were indistinguishable.
    await show();

    expect(await screen.findByText("BSCS-3A")).toBeInTheDocument();
    expect(screen.getByText(/CS-101 Intro to Programming/)).toBeInTheDocument();
    expect(screen.getByText(/1st Semester 2026-2027/)).toBeInTheDocument();
    expect(screen.getByText("Ana Cruz")).toBeInTheDocument();
  });

  it("flags a section with nobody in it, because that is an exam nobody can open", async () => {
    // An exam inheriting an empty class list admits no students at all and looks correctly
    // configured until someone tries to start it. The list is where that is cheapest to catch.
    await show({ sections: [section({ enrolled_count: 0 })] });

    expect(await screen.findByText("Nobody enrolled")).toBeInTheDocument();
  });

  it("opens a section's class list from its row", async () => {
    await show();

    await userEvent.click(await screen.findByText("BSCS-3A"));

    expect(mocks.navigate).toHaveBeenCalledWith("/sections/5");
  });

  it("does not offer an instructor a control the server would refuse", async () => {
    // Sections are readable by anyone in the school but created by require_admin only. An
    // instructor needs to see who is in the classes they teach; offering them "Add Section"
    // would promise something the API 403s.
    await show({ role: "instructor" });

    expect(screen.queryByRole("button", { name: /add section/i })).not.toBeInTheDocument();
  });

  it("gives an admin the control", async () => {
    await show();

    expect(await screen.findByRole("button", { name: /add section/i })).toBeInTheDocument();
  });

  it("names the missing prerequisite rather than just disabling the button", async () => {
    // A disabled button with no explanation is the state someone gets stuck in. A section needs
    // a term, and a term is created on a different page.
    mocks.user = { id: 1, role_name: "admin" };
    mocks.getSections.mockResolvedValue([]);
    mocks.getAcademicYears.mockResolvedValue([]);
    mocks.getTerms.mockResolvedValue([]);
    mocks.getSubjects.mockResolvedValue([{ id: 2, code: "CS-101", name: "Intro" }]);
    mocks.getInstructors.mockResolvedValue([{ id: 3, instructor_name: "Ana Cruz" }]);
    render(<Sections />);

    expect(await screen.findByText(/add a term on the academic calendar first/i)).toBeInTheDocument();
  });
});
