import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

const mocks = vi.hoisted(() => ({
  getExamSessions: vi.fn(),
  getStudents: vi.fn(),
  getExams: vi.fn(),
  getSessionViolations: vi.fn(),
}));

vi.mock("../../api/examSessions", () => ({ getExamSessions: mocks.getExamSessions }));
vi.mock("../../api/students", () => ({ getStudents: mocks.getStudents }));
vi.mock("../../api/exams", () => ({ getExams: mocks.getExams }));
vi.mock("../../api/violations", () => ({ getSessionViolations: mocks.getSessionViolations }));
vi.mock("../../context/AuthContext", () => ({
  useAuth: () => ({ user: { id: 1, first_name: "Ana" } }),
}));
vi.mock("../../hooks/useSchoolNav", () => ({ useSchoolNav: () => vi.fn() }));

const { default: MyViolations } = await import("./MyViolations");

const STUDENT = { id: 7, user_id: 1 };
const violation = (over = {}) => ({
  id: 1, event_type: "PHONE_DETECTED", detail: null, created_at: "2026-09-09T02:00:00Z",
  has_evidence: false, appeal_status: null, appeal_reason: null, ...over,
});

function show() {
  return render(<MemoryRouter><MyViolations /></MemoryRouter>);
}

beforeEach(() => {
  mocks.getStudents.mockResolvedValue([STUDENT]);
  mocks.getExams.mockResolvedValue([{ id: 3, title: "CS-101 Mock Exam" }]);
  mocks.getExamSessions.mockResolvedValue([
    { id: 10, student_id: 7, exam_id: 3, started_at: "2026-09-09T01:00:00Z" },
  ]);
  mocks.getSessionViolations.mockResolvedValue([violation()]);
});

describe("Violations & Appeals", () => {
  it("shows a student everything flagged against them in one place", async () => {
    show();
    expect(await screen.findByText(/CS-101 Mock Exam/)).toBeInTheDocument();
    expect(screen.getByText(/1 violation across 1 attempt/i)).toBeInTheDocument();
  });

  it("offers the appeal action, which is the whole point of the page", async () => {
    show();
    // The capability already existed on ResultDetail; this page exists so a student can find it.
    expect(await screen.findByRole("button", { name: /contest this violation/i })).toBeInTheDocument();
  });

  it("aggregates across attempts rather than showing one exam at a time", async () => {
    mocks.getExamSessions.mockResolvedValue([
      { id: 10, student_id: 7, exam_id: 3, started_at: "2026-09-09T01:00:00Z" },
      { id: 11, student_id: 7, exam_id: 3, started_at: "2026-09-08T01:00:00Z" },
    ]);
    mocks.getSessionViolations.mockResolvedValue([violation(), violation({ id: 2 })]);
    show();

    expect(await screen.findByText(/4 violations across 2 attempts/i)).toBeInTheDocument();
  });

  it("hides attempts with a clean record instead of listing them as empty", async () => {
    mocks.getExamSessions.mockResolvedValue([
      { id: 10, student_id: 7, exam_id: 3, started_at: "2026-09-09T01:00:00Z" },
      { id: 11, student_id: 7, exam_id: 3, started_at: "2026-09-08T01:00:00Z" },
    ]);
    mocks.getSessionViolations.mockImplementation(async (id) => (id === 10 ? [violation()] : []));
    show();

    expect(await screen.findByText(/1 violation across 1 attempt/i)).toBeInTheDocument();
  });

  it("reassures a student with nothing flagged rather than showing a bare empty table", async () => {
    mocks.getSessionViolations.mockResolvedValue([]);
    show();

    expect(await screen.findByText(/nothing has been flagged/i)).toBeInTheDocument();
    expect(screen.getByText(/nothing to appeal/i)).toBeInTheDocument();
  });

  it("shows only this student's own sessions", async () => {
    mocks.getExamSessions.mockResolvedValue([
      { id: 10, student_id: 7, exam_id: 3, started_at: "2026-09-09T01:00:00Z" },
      { id: 99, student_id: 8, exam_id: 3, started_at: "2026-09-09T01:00:00Z" },
    ]);
    show();

    await screen.findByText(/1 violation across 1 attempt/i);
    expect(mocks.getSessionViolations).not.toHaveBeenCalledWith(99);
  });

  it("recovers from a failed load instead of hanging on Loading", async () => {
    mocks.getExamSessions.mockRejectedValue(new Error("boom"));
    show();

    expect(await screen.findByText(/couldn't load your violations/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
  });

  it("explains the unlinked-account case rather than showing an empty page", async () => {
    mocks.getStudents.mockResolvedValue([]);
    show();

    expect(await screen.findByText(/isn't linked to a student record/i)).toBeInTheDocument();
  });
});
