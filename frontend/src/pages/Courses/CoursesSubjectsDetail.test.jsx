import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

/**
 * "Clicking a row on each management on the sidebar should show all the details and have the
 * option to edit the row." Instructors and Students already had a detail dialog; Courses and
 * Subjects had none at all, so a row could only be edited or deleted.
 */
const mocks = vi.hoisted(() => ({
  user: { id: 1, role_name: "admin", school_id: 1 },
  getCourses: vi.fn(),
  createCourse: vi.fn(),
  updateCourse: vi.fn(),
  deleteCourse: vi.fn(),
  getSubjects: vi.fn(),
  createSubject: vi.fn(),
  updateSubject: vi.fn(),
  deleteSubject: vi.fn(),
}));

vi.mock("../../api/courses", () => ({
  getCourses: mocks.getCourses,
  createCourse: mocks.createCourse,
  updateCourse: mocks.updateCourse,
  deleteCourse: mocks.deleteCourse,
}));
vi.mock("../../api/subjects", () => ({
  getSubjects: mocks.getSubjects,
  createSubject: mocks.createSubject,
  updateSubject: mocks.updateSubject,
  deleteSubject: mocks.deleteSubject,
}));
vi.mock("../../context/AuthContext", () => ({ useAuth: () => ({ user: mocks.user }) }));

const { default: Courses } = await import("./Courses");
const { default: Subjects } = await import("../Subjects/Subjects");

const COURSE = { id: 2, code: "BSCS", name: "BS Computer Science" };
const SUBJECT = { id: 7, code: "CS-101", name: "Intro to Programming", course_id: 2 };

beforeEach(() => {
  vi.clearAllMocks();
  mocks.getCourses.mockResolvedValue([COURSE]);
  mocks.getSubjects.mockResolvedValue([SUBJECT]);
});

describe("Courses — a row answers what it is", () => {
  it("opens the details when the row is clicked", async () => {
    render(<Courses />);
    await waitFor(() => expect(screen.getByText("BS Computer Science")).toBeInTheDocument());

    await userEvent.click(screen.getByText("BS Computer Science"));

    const dialog = await screen.findByRole("dialog");
    expect(dialog).toHaveTextContent("BSCS");
  });

  it("offers the edit from inside the details", async () => {
    render(<Courses />);
    await waitFor(() => expect(screen.getByText("BS Computer Science")).toBeInTheDocument());

    await userEvent.click(screen.getByText("BS Computer Science"));
    await userEvent.click(await screen.findByRole("button", { name: /edit course/i }));

    expect(screen.getByLabelText("Code")).toHaveValue("BSCS");
  });
});

describe("Subjects — a row answers what it is, and which course it belongs to", () => {
  it("names the course in the details rather than only its code in the table", async () => {
    render(<Subjects />);
    await waitFor(() => expect(screen.getByText("Intro to Programming")).toBeInTheDocument());

    await userEvent.click(screen.getByText("Intro to Programming"));

    const dialog = await screen.findByRole("dialog");
    expect(dialog).toHaveTextContent("BS Computer Science");
  });

  it("offers the edit from inside the details", async () => {
    render(<Subjects />);
    await waitFor(() => expect(screen.getByText("Intro to Programming")).toBeInTheDocument());

    await userEvent.click(screen.getByText("Intro to Programming"));
    await userEvent.click(await screen.findByRole("button", { name: /edit subject/i }));

    expect(screen.getByLabelText("Code")).toHaveValue("CS-101");
  });
});
