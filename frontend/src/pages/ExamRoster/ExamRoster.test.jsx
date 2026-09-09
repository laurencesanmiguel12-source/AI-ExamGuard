import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

const mocks = vi.hoisted(() => ({
  getExam: vi.fn(),
  getExamRoster: vi.fn(),
  getExamRosterSource: vi.fn(),
  getAvailableRosterStudents: vi.fn(),
}));

vi.mock("react-router-dom", () => ({ useParams: () => ({ examId: "1" }) }));
vi.mock("../../hooks/useSchoolNav", () => ({ useSchoolNav: () => vi.fn() }));
vi.mock("../../api/exams", () => ({ getExam: mocks.getExam }));
vi.mock("../../api/examRoster", () => ({
  getExamRoster: mocks.getExamRoster,
  getExamRosterSource: mocks.getExamRosterSource,
  getAvailableRosterStudents: mocks.getAvailableRosterStudents,
  addExamRosterStudent: vi.fn(),
  removeExamRosterStudent: vi.fn(),
  bulkAddExamRosterStudents: vi.fn(),
}));

const { default: ExamRoster } = await import("./ExamRoster");

function student(id) {
  return { id, student_name: `Student ${id}`, student_number: `S${id}` };
}

async function show({ source, roster = [], available = [], is_active = false }) {
  mocks.getExam.mockResolvedValue({ id: 1, title: "CS-101 Mock Exam", is_active });
  mocks.getExamRoster.mockResolvedValue(roster.map((s) => ({ id: s.id, student: s })));
  mocks.getExamRosterSource.mockResolvedValue(source);
  mocks.getAvailableRosterStudents.mockResolvedValue(available);
  render(<ExamRoster />);
  await waitFor(() => expect(screen.getByRole("heading", { name: "CS-101 Mock Exam" })).toBeInTheDocument());
}

beforeEach(() => vi.clearAllMocks());

describe("ExamRoster — which roster is actually in force", () => {
  it("says the class list is inherited rather than claiming nobody can sit the exam", async () => {
    // The regression this exists to prevent: before roster inheritance, an empty roster table
    // meant nobody could open the exam, and the page said so. It now means the section's class
    // list applies. Reading roster.length instead of the server's answer tells a healthy exam's
    // instructor their whole class is locked out.
    await show({ source: { source: "SECTION", count: 3, admits_nobody: false } });

    expect(screen.getByRole("status")).toHaveTextContent(/admitting the 3 students enrolled/i);
    expect(screen.queryByText(/nobody can open this exam/i)).not.toBeInTheDocument();
  });

  it("warns that rostering anyone replaces the inherited class list rather than adding to it", async () => {
    // Explicit beats inherited per-EXAM, not per-student, so adding one student silently drops
    // everybody else. That is a one-click way to lock a class out and it is not guessable.
    await show({
      source: { source: "SECTION", count: 3, admits_nobody: false },
      available: [student(7)],
    });

    expect(screen.getByText(/replaces/i)).toBeInTheDocument();
  });

  it("does not nudge an inherited exam to add the students it already admits", async () => {
    // "N students aren't on the roster yet" is correct advice only for an exam that keeps its own
    // roster; acting on it here would convert the exam to an explicit roster.
    await show({
      source: { source: "SECTION", count: 3, admits_nobody: false },
      available: [student(7)],
    });

    expect(screen.queryByText(/aren't on the roster yet/i)).not.toBeInTheDocument();
  });

  it("reports the lockout an empty section causes, which looks identical to a healthy exam", async () => {
    // The live case this was built for: CS-101 Mock Exam, no explicit rows, section with nobody
    // enrolled. Correct behaviour (it must not invent a roster) but invisible until it is said.
    await show({ source: { source: "SECTION", count: 0, admits_nobody: true } });

    expect(screen.getByRole("alert")).toHaveTextContent(/nobody can open this exam/i);
    expect(screen.getByRole("alert")).toHaveTextContent(/section has nobody enrolled/i);
  });

  it("distinguishes having no section at all from having an empty one", async () => {
    // Different repair: one is "enrol the section", the other is "there is no section to enrol".
    await show({ source: { source: "NONE", count: 0, admits_nobody: true } });

    expect(screen.getByRole("alert")).toHaveTextContent(/isn't linked to a section/i);
  });

  it("says an explicit roster overrides the section, so the section's size is not a surprise", async () => {
    await show({
      source: { source: "EXPLICIT", count: 2, admits_nobody: false },
      roster: [student(1), student(2)],
    });

    expect(screen.getByRole("status")).toHaveTextContent(/restricted to the 2 students/i);
    expect(screen.getByRole("status")).toHaveTextContent(/section's class list does not apply/i);
  });

  it("still raises the active-exam alarm, now on admitting nobody rather than on an empty table", async () => {
    await show({ source: { source: "SECTION", count: 0, admits_nobody: true }, is_active: true });

    expect(screen.getByText(/active but admits nobody/i)).toBeInTheDocument();
  });

  it("does not raise it for an active exam whose inherited class list is healthy", async () => {
    await show({ source: { source: "SECTION", count: 3, admits_nobody: false }, is_active: true });

    expect(screen.queryByText(/admits nobody/i)).not.toBeInTheDocument();
  });
});
