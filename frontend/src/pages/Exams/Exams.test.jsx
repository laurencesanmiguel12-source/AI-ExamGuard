import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const mocks = vi.hoisted(() => ({
  user: null,
  getExams: vi.fn(),
  createExam: vi.fn(),
  updateExam: vi.fn(),
  deleteExam: vi.fn(),
  getSubjects: vi.fn(),
  getInstructors: vi.fn(),
  getSections: vi.fn(),
}));

vi.mock("react-router-dom", () => ({
  Link: ({ children }) => <span>{children}</span>,
}));
vi.mock("../../hooks/useSchoolNav", () => ({ useSchoolSlug: () => "arellano-university" }));
vi.mock("../../context/AuthContext", () => ({ useAuth: () => ({ user: mocks.user }) }));
vi.mock("../../api/exams", () => ({
  getExams: mocks.getExams,
  createExam: mocks.createExam,
  updateExam: mocks.updateExam,
  deleteExam: mocks.deleteExam,
}));
vi.mock("../../api/subjects", () => ({ getSubjects: mocks.getSubjects }));
vi.mock("../../api/instructors", () => ({ getInstructors: mocks.getInstructors }));
vi.mock("../../api/academic", () => ({ getSections: mocks.getSections }));

const { default: Exams } = await import("./Exams");

const INSTRUCTOR = { id: 3, user_id: 9, employee_number: "EMP-1", instructor_name: "Ana Cruz" };

function section(overrides) {
  return {
    id: 5,
    code: "BSCS-3A",
    subject_id: 2,
    instructor_id: 3,
    subject_code: "CS-101",
    subject_name: "Intro to Programming",
    term_name: "1st Semester",
    academic_year_label: "2026-2027",
    enrolled_count: 3,
    ...overrides,
  };
}

async function show({ role = "instructor", sections = [section()], exams = [] } = {}) {
  mocks.user = { id: 9, role_name: role, school_id: 1 };
  mocks.getExams.mockResolvedValue(exams);
  mocks.getSubjects.mockResolvedValue([{ id: 2, code: "CS-101", name: "Intro to Programming" }]);
  mocks.getInstructors.mockResolvedValue([INSTRUCTOR]);
  mocks.getSections.mockResolvedValue(sections);
  render(<Exams />);
  await waitFor(() => expect(mocks.getSections).toHaveBeenCalled());
}

beforeEach(() => vi.clearAllMocks());

describe("Exam form — an exam belongs to a section", () => {
  it("files a new exam under a section instead of a subject and an instructor", async () => {
    // The defect this closes: the form sent subject_id and instructor_id and never sent a
    // section, so every exam created through the live UI after the section link shipped had no
    // section at all - and so could never inherit a class list.
    await show();

    await userEvent.click(await screen.findByRole("button", { name: /add exam/i }));

    expect(screen.getByLabelText("Section")).toBeInTheDocument();
    expect(screen.queryByLabelText("Subject")).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/instructor \(reassign\)/i)).not.toBeInTheDocument();
  });

  it("sends section_id and nothing that could contradict it", async () => {
    mocks.createExam.mockResolvedValue({});
    await show();

    await userEvent.click(await screen.findByRole("button", { name: /add exam/i }));
    await userEvent.type(screen.getByLabelText("Title"), "Midterm");
    await userEvent.type(screen.getByLabelText("Start Time"), "2026-10-01T09:00");
    await userEvent.type(screen.getByLabelText("End Time"), "2026-10-01T11:00");
    await userEvent.click(screen.getByRole("button", { name: /create exam/i }));

    await waitFor(() => expect(mocks.createExam).toHaveBeenCalled());
    const payload = mocks.createExam.mock.calls[0][0];
    expect(payload.section_id).toBe(5);
    expect(payload).not.toHaveProperty("subject_id");
    expect(payload).not.toHaveProperty("instructor_id");
  });

  it("warns before an exam is filed under a class with nobody in it", async () => {
    // Choosing an empty section produces an exam that admits no students and looks correctly
    // configured until somebody tries to start it. Said here, it costs one click to avoid.
    await show({ sections: [section({ enrolled_count: 0 })] });

    await userEvent.click(await screen.findByRole("button", { name: /add exam/i }));

    expect(screen.getByText(/will admit no students/i)).toBeInTheDocument();
  });

  it("does not warn when the class has students in it", async () => {
    await show();

    await userEvent.click(await screen.findByRole("button", { name: /add exam/i }));

    expect(screen.queryByText(/will admit no students/i)).not.toBeInTheDocument();
  });

  it("offers an instructor only the sections they teach", async () => {
    // The server refuses the rest with a 403, so listing them is an invitation to a failure.
    await show({
      sections: [section(), section({ id: 6, code: "BSCS-3B", instructor_id: 99 })],
    });

    await userEvent.click(await screen.findByRole("button", { name: /add exam/i }));

    const options = screen.getByLabelText("Section").querySelectorAll("option");
    expect(options).toHaveLength(1);
    expect(options[0].textContent).toContain("BSCS-3A");
  });

  it("offers an admin every section in the school", async () => {
    await show({
      role: "admin",
      sections: [section(), section({ id: 6, code: "BSCS-3B", instructor_id: 99 })],
    });

    await userEvent.click(await screen.findByRole("button", { name: /add exam/i }));

    expect(screen.getByLabelText("Section").querySelectorAll("option")).toHaveLength(2);
  });

  it("says where sections come from rather than only disabling the button", async () => {
    await show({ sections: [] });

    expect(await screen.findByText(/set up a section first/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /add exam/i })).toBeDisabled();
  });

  it("tells an instructor with no classes that that is why they cannot add an exam", async () => {
    await show({ sections: [section({ instructor_id: 99 })] });

    expect(await screen.findByText(/aren't teaching any section yet/i)).toBeInTheDocument();
  });

  it("shows which class an existing exam belongs to", async () => {
    await show({
      exams: [{ id: 1, title: "Midterm", subject_id: 2, instructor_id: 3, section_id: 5, is_active: true }],
    });

    expect(await screen.findByText(/BSCS-3A · 1st Semester/)).toBeInTheDocument();
  });
});
