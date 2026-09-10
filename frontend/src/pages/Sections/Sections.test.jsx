import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const mocks = vi.hoisted(() => ({
  user: null,
  navigate: vi.fn(),
  getSections: vi.fn(),
  createSection: vi.fn(),
  updateSection: vi.fn(),
  deleteSection: vi.fn(),
  getAcademicYears: vi.fn(),
  getTerms: vi.fn(),
  getSubjects: vi.fn(),
  getInstructors: vi.fn(),
}));

vi.mock("../../api/academic", () => ({
  getSections: mocks.getSections,
  createSection: mocks.createSection,
  updateSection: mocks.updateSection,
  deleteSection: mocks.deleteSection,
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
    course_code: "BSCS",
    instructor_name: "Ana Cruz",
    subject_id: 2,
    term_id: 9,
    instructor_id: 3,
    capacity: null,
    schedule: null,
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
  mocks.getInstructors.mockResolvedValue([
    { id: 3, instructor_name: "Ana Cruz" },
    { id: 7, instructor_name: "Ben Santos" },
  ]);
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

  it("opens the section's details from its row", async () => {
    // Reported in QA against every list page: a row should answer "what is this" before it does
    // anything else, and offer the correction from inside the answer.
    await show();

    await userEvent.click(await screen.findByText("BSCS-3A"));

    expect(await screen.findByRole("dialog")).toHaveTextContent(/BSCS-3A/);
    expect(mocks.navigate).not.toHaveBeenCalled();
  });

  it("names the course, not just the subject", async () => {
    // A section named its subject and never the programme, so CS-101 under BSCS and CS-101 under
    // BSIT read as the same class.
    await show({ sections: [section({ course_code: "BSCS" })] });

    expect(await screen.findByText("BSCS")).toBeInTheDocument();
  });

  it("still reaches the class list, from its own control", async () => {
    // The button lives in a cell. Before DataTable learned to ignore clicks on controls, this
    // also opened the row's detail dialog behind it - the "2 modals pop up" report.
    await show();

    // Exact name: the row itself is a button whose accessible name is its whole text, which
    // contains "Manage" too.
    await userEvent.click(await screen.findByRole("button", { name: "Manage" }));

    expect(mocks.navigate).toHaveBeenCalledWith("/sections/5");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("offers the edit from inside the detail dialog", async () => {
    await show();

    await userEvent.click(await screen.findByText("BSCS-3A"));
    await userEvent.click(await screen.findByRole("button", { name: /edit section/i }));

    expect(screen.getByLabelText("Section Code")).toBeInTheDocument();
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

describe("Sections — correcting and removing", () => {
  it("lets a section be corrected instead of being permanent once created", async () => {
    // The gap that mattered most: a section built with the wrong instructor could not be fixed,
    // and every exam on it is attributed through that section.
    mocks.updateSection.mockResolvedValue({});
    await show();

    await userEvent.click(await screen.findByRole("button", { name: "Edit" }));
    const code = screen.getByLabelText("Section Code");
    await userEvent.clear(code);
    await userEvent.type(code, "BSCS-3B");
    await userEvent.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() => expect(mocks.updateSection).toHaveBeenCalled());
    const [id, payload] = mocks.updateSection.mock.calls[0];
    expect(id).toBe(5);
    expect(payload.code).toBe("BSCS-3B");
    // Not sent: they are what makes this section this class, and the server rejects them.
    expect(payload).not.toHaveProperty("subject_id");
    expect(payload).not.toHaveProperty("term_id");
  });

  it("shows subject and term as settled facts rather than editable fields", async () => {
    await show();

    await userEvent.click(await screen.findByRole("button", { name: "Edit" }));

    // Scoped to the dialog: the page's own term FILTER is also labelled "Term", and a
    // page-wide query would match that instead and pass for the wrong reason.
    const dialog = within(screen.getByRole("dialog"));
    expect(dialog.queryByLabelText("Subject")).not.toBeInTheDocument();
    expect(dialog.queryByLabelText("Term")).not.toBeInTheDocument();
    expect(dialog.getByText(/cannot be changed/i)).toBeInTheDocument();
  });

  it("warns that reassigning the class hands over its exams too", async () => {
    // exam.instructor_id is derived from the section, so this is not just a label change - the
    // new instructor becomes the owner and the old one loses access.
    await show();

    await userEvent.click(await screen.findByRole("button", { name: "Edit" }));
    await userEvent.selectOptions(screen.getByLabelText("Instructor"), "7");

    expect(screen.getByText(/every exam set on it goes with them/i)).toBeInTheDocument();
  });

  it("does not warn while the instructor is unchanged", async () => {
    await show();

    await userEvent.click(await screen.findByRole("button", { name: "Edit" }));

    expect(screen.queryByText(/every exam set on it goes with them/i)).not.toBeInTheDocument();
  });

  it("surfaces the server's reason for refusing a delete", async () => {
    mocks.deleteSection.mockRejectedValue({
      response: { data: { detail: "1 exam is set on this section. Move or delete them first." } },
    });
    await show();

    await userEvent.click(await screen.findByRole("button", { name: "Delete" }));
    // The row's icon button and the dialog's confirm button share the name "Delete", so the
    // confirm has to be taken from inside the dialog.
    await userEvent.click(
      within(screen.getByRole("dialog")).getByRole("button", { name: /^delete$/i })
    );

    expect(await screen.findByText(/1 exam is set on this section/i)).toBeInTheDocument();
  });

  it("gives an instructor neither control", async () => {
    await show({ role: "instructor" });

    await waitFor(() => expect(screen.getByText("BSCS-3A")).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: "Edit" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete" })).not.toBeInTheDocument();
  });
});
