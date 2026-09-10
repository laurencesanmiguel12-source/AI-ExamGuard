import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const mocks = vi.hoisted(() => ({
  user: null,
  getStudents: vi.fn(),
  createStudent: vi.fn(),
  updateStudent: vi.fn(),
  deleteStudent: vi.fn(),
  getCourses: vi.fn(),
  getSubjects: vi.fn(),
}));

vi.mock("../../api/students", () => ({
  getStudents: mocks.getStudents,
  createStudent: mocks.createStudent,
  updateStudent: mocks.updateStudent,
  deleteStudent: mocks.deleteStudent,
}));
vi.mock("../../api/courses", () => ({ getCourses: mocks.getCourses }));
vi.mock("../../api/subjects", () => ({ getSubjects: mocks.getSubjects }));
vi.mock("../../context/AuthContext", () => ({ useAuth: () => ({ user: mocks.user }) }));

const { default: Students } = await import("./Students");

const SAM = {
  id: 4,
  student_number: "STU00042",
  course_id: 2,
  student_name: "Sam Jose Diaz",
  first_name: "Sam Jose",
  last_name: "Diaz",
  email: "sam@school.edu",
  accommodation_notes: "",
  skip_face_check: false,
  skip_object_check: false,
  extra_time_minutes: 0,
};

async function show(role = "admin") {
  mocks.user = { id: 1, role_name: role, school_id: 1 };
  mocks.getStudents.mockResolvedValue([SAM]);
  mocks.getCourses.mockResolvedValue([{ id: 2, code: "BSCS", name: "BS Computer Science" }]);
  mocks.getSubjects.mockResolvedValue([]);
  render(<Students />);
  await waitFor(() => expect(screen.getByText("Sam Jose Diaz")).toBeInTheDocument());
}

beforeEach(() => vi.clearAllMocks());

describe("Students — editing the whole person", () => {
  it("fills the form with the name and email, not only the record fields", async () => {
    // Same QA finding as Instructors: the form could change a student's course and their
    // accommodations but not the spelling of their own name.
    await show();

    await userEvent.click(screen.getByRole("button", { name: "Edit" }));

    expect(screen.getByLabelText("First Name")).toHaveValue("Sam Jose");
    expect(screen.getByLabelText("Last Name")).toHaveValue("Diaz");
    expect(screen.getByLabelText("Email Address")).toHaveValue("sam@school.edu");
    expect(screen.getByLabelText("Student Number")).toHaveValue("STU00042");
  });

  it("sends the name and email on save", async () => {
    mocks.updateStudent.mockResolvedValue({});
    await show();

    await userEvent.click(screen.getByRole("button", { name: "Edit" }));
    const last = screen.getByLabelText("Last Name");
    await userEvent.clear(last);
    await userEvent.type(last, "Diaz-Santos");
    await userEvent.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() => expect(mocks.updateStudent).toHaveBeenCalled());
    const [, payload] = mocks.updateStudent.mock.calls[0];
    expect(payload.last_name).toBe("Diaz-Santos");
    expect(payload.email).toBe("sam@school.edu");
    expect(payload.student_number).toBe("STU00042");
  });

  it("does not offer to set a password from the edit form", async () => {
    await show();

    await userEvent.click(screen.getByRole("button", { name: "Edit" }));

    expect(screen.queryByLabelText("Password")).not.toBeInTheDocument();
  });

  it("does not show a student number when creating, since it is generated", async () => {
    await show();

    await userEvent.click(screen.getByRole("button", { name: /add student/i }));

    expect(screen.queryByLabelText("Student Number")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
  });

  it("offers the edit from inside the detail dialog", async () => {
    await show();

    await userEvent.click(screen.getByText("Sam Jose Diaz"));
    await userEvent.click(await screen.findByRole("button", { name: /edit student/i }));

    expect(screen.getByLabelText("Student Number")).toHaveValue("STU00042");
  });

  it("gives an instructor the details without the edit", async () => {
    // Instructors get this page read-only; a dialog that offers an action the server refuses is
    // worse than one that does not offer it.
    await show("instructor");

    await userEvent.click(screen.getByText("Sam Jose Diaz"));

    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /edit student/i })).not.toBeInTheDocument();
  });
});
