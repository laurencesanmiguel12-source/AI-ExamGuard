import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const mocks = vi.hoisted(() => ({
  getInstructors: vi.fn(),
  createInstructor: vi.fn(),
  updateInstructor: vi.fn(),
  deleteInstructor: vi.fn(),
  getSubjects: vi.fn(),
  getStudents: vi.fn(),
  getInstructorSubjects: vi.fn(),
  assignInstructorSubject: vi.fn(),
  unassignInstructorSubject: vi.fn(),
}));

vi.mock("../../api/instructors", () => ({
  getInstructors: mocks.getInstructors,
  createInstructor: mocks.createInstructor,
  updateInstructor: mocks.updateInstructor,
  deleteInstructor: mocks.deleteInstructor,
}));
vi.mock("../../api/subjects", () => ({ getSubjects: mocks.getSubjects }));
vi.mock("../../api/students", () => ({ getStudents: mocks.getStudents }));
vi.mock("../../api/instructorSubjects", () => ({
  getInstructorSubjects: mocks.getInstructorSubjects,
  assignInstructorSubject: mocks.assignInstructorSubject,
  unassignInstructorSubject: mocks.unassignInstructorSubject,
}));

const { default: Instructors } = await import("./Instructors");

const ANA = {
  id: 3,
  user_id: 9,
  employee_number: "EMP-001",
  instructor_name: "Ana Maria Cruz",
  first_name: "Ana Maria",
  last_name: "Cruz",
  email: "ana@school.edu",
  assignments: [
    { subject_id: 1, subject_code: "CS-101", subject_name: "Intro", course_id: 2, course_code: "BSCS" },
  ],
};

async function show(rows = [ANA]) {
  mocks.getInstructors.mockResolvedValue(rows);
  mocks.getSubjects.mockResolvedValue([{ id: 1, code: "CS-101", name: "Intro" }]);
  mocks.getStudents.mockResolvedValue([]);
  mocks.getInstructorSubjects.mockResolvedValue([{ subject_id: 1 }]);
  render(<Instructors />);
  await waitFor(() => expect(screen.getByText("Ana Maria Cruz")).toBeInTheDocument());
}

beforeEach(() => vi.clearAllMocks());

describe("Instructors — clicking Manage", () => {
  it("opens only the subjects dialog, not the detail dialog behind it", async () => {
    // The QA report: "clicking Manage, 2 modals pop up". Manage is a button inside a cell, and
    // the row is itself clickable.
    await show();

    // Exact name: the row is itself a button whose accessible name is its whole text, which
    // contains "Manage" too.
    await userEvent.click(screen.getByRole("button", { name: "Manage" }));

    const dialogs = await screen.findAllByRole("dialog");
    expect(dialogs).toHaveLength(1);
    expect(dialogs[0]).toHaveTextContent(/subjects/i);
  });
});

describe("Instructors — editing the whole person", () => {
  it("fills the form with the name and email, not just the employee number", async () => {
    // The other QA report: "edit button only edits the employee number".
    await show();

    await userEvent.click(screen.getByRole("button", { name: "Edit" }));

    expect(screen.getByLabelText("First Name")).toHaveValue("Ana Maria");
    expect(screen.getByLabelText("Last Name")).toHaveValue("Cruz");
    expect(screen.getByLabelText("Email Address")).toHaveValue("ana@school.edu");
    expect(screen.getByLabelText("Employee Number")).toHaveValue("EMP-001");
  });

  it("takes the name from the stored halves rather than splitting the display name", async () => {
    // "Ana Maria Cruz" splits into the wrong halves, and an edit form that guesses writes the
    // guess back on save.
    await show();

    await userEvent.click(screen.getByRole("button", { name: "Edit" }));

    expect(screen.getByLabelText("First Name")).toHaveValue("Ana Maria");
  });

  it("sends the name and email on save", async () => {
    mocks.updateInstructor.mockResolvedValue({});
    await show();

    await userEvent.click(screen.getByRole("button", { name: "Edit" }));
    const first = screen.getByLabelText("First Name");
    await userEvent.clear(first);
    await userEvent.type(first, "Anna");
    await userEvent.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() => expect(mocks.updateInstructor).toHaveBeenCalled());
    const [id, payload] = mocks.updateInstructor.mock.calls[0];
    expect(id).toBe(3);
    expect(payload.first_name).toBe("Anna");
    expect(payload.email).toBe("ana@school.edu");
    expect(payload.employee_number).toBe("EMP-001");
  });

  it("does not offer to set a password from the edit form", async () => {
    // Setting somebody else's password is a different act from correcting their name.
    await show();

    await userEvent.click(screen.getByRole("button", { name: "Edit" }));

    expect(screen.queryByLabelText("Password")).not.toBeInTheDocument();
  });

  it("still asks for a password when creating", async () => {
    await show();

    await userEvent.click(screen.getByRole("button", { name: /add instructor/i }));

    expect(screen.getByLabelText("Password")).toBeInTheDocument();
  });
});

describe("Instructors — the row detail leads to the edit", () => {
  it("offers the edit from inside the detail dialog", async () => {
    // Opening a row to check a detail, finding it wrong, and having to close and hunt for the
    // pencil is the errand this removes.
    await show();

    await userEvent.click(screen.getByText("Ana Maria Cruz"));
    await userEvent.click(await screen.findByRole("button", { name: /edit instructor/i }));

    expect(screen.getByLabelText("Employee Number")).toHaveValue("EMP-001");
  });

  it("replaces the detail dialog rather than stacking the form on top of it", async () => {
    await show();

    await userEvent.click(screen.getByText("Ana Maria Cruz"));
    await userEvent.click(await screen.findByRole("button", { name: /edit instructor/i }));

    const dialogs = screen.getAllByRole("dialog");
    expect(dialogs).toHaveLength(1);
    expect(within(dialogs[0]).getByText("Edit Instructor")).toBeInTheDocument();
  });
});
