import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

// vi.hoisted for the same reason as SetupImportPanel.test.jsx: the mock function has to *be* the
// module export, not a wrapper closing over it.
const mocks = vi.hoisted(() => ({
  getExams: vi.fn(),
  getExamSessions: vi.fn(),
  getStudents: vi.fn(),
  getSessionRiskSummary: vi.fn(),
  getSessionViolations: vi.fn(),
  useExtensionInstalled: vi.fn(),
}));

vi.mock("../../api/exams", () => ({ getExams: mocks.getExams }));
vi.mock("../../api/examSessions", () => ({ getExamSessions: mocks.getExamSessions }));
vi.mock("../../api/students", () => ({ getStudents: mocks.getStudents }));
vi.mock("../../api/violations", () => ({
  getSessionRiskSummary: mocks.getSessionRiskSummary,
  getSessionViolations: mocks.getSessionViolations,
}));
vi.mock("../../hooks/useExtensionInstalled", () => ({ default: mocks.useExtensionInstalled }));
vi.mock("../../context/AuthContext", () => ({
  useAuth: () => ({
    user: { id: 1, first_name: "Ana", last_name: "Cruz", email: "ana@school.edu",
            role_name: "student", is_active: true },
  }),
}));
// recharts measures a real container; jsdom reports zero size, so it renders nothing useful and
// only adds noise. Stubbed to the exports this page imports.
const chartStub = () => null;
vi.mock("recharts", () => ({
  AreaChart: chartStub, Area: chartStub, XAxis: chartStub, YAxis: chartStub,
  Tooltip: chartStub, ResponsiveContainer: chartStub,
}));

const { default: StudentDashboard } = await import("./StudentDashboard");

const NOW = new Date("2026-09-08T12:00:00Z");
const HOUR = 60 * 60 * 1000;
const at = (ms) => new Date(NOW.getTime() + ms).toISOString();

const exam = (over = {}) => ({
  id: 1, title: "CS-101 Mock Exam", is_active: true, duration_minutes: 90, total_points: 100,
  start_time: at(-24 * HOUR), end_time: at(3 * HOUR + 12 * 60 * 1000), ...over,
});

const STUDENT = { id: 7, user_id: 1, face_model_path: "/models/7.yml", skip_face_check: false };

function show() {
  return render(
    <MemoryRouter initialEntries={["/arellano-university/dashboard"]}>
      <StudentDashboard />
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.setSystemTime(NOW);
  sessionStorage.clear();
  mocks.getExams.mockResolvedValue([exam()]);
  mocks.getExamSessions.mockResolvedValue([]);
  mocks.getStudents.mockResolvedValue([STUDENT]);
  mocks.getSessionRiskSummary.mockResolvedValue(null);
  mocks.getSessionViolations.mockResolvedValue([]);
  mocks.useExtensionInstalled.mockReturnValue({ status: "installed", recheck: vi.fn() });
});
afterEach(() => {
  vi.useRealTimers();
});

describe("StudentDashboard", () => {
  // The page renders at all. This exists because a previous edit left an undefined variable in
  // this JSX: lint passed, the build passed, and the dashboard rendered blank in the browser.
  it("renders without throwing", async () => {
    show();
    expect(await screen.findByText("Student Dashboard")).toBeInTheDocument();
  });

  it("shows each exam's due date and how long is left", async () => {
    show();

    // The absolute date, and separately the live countdown next to it.
    expect(await screen.findByText(/^Due .*2026/)).toBeInTheDocument();
    expect(screen.getByText(/Due in 3h 12m/)).toBeInTheDocument();
  });

  it("still shows when the exam opened, alongside the due date", async () => {
    show();
    expect(await screen.findByText(/^Opened /)).toBeInTheDocument();
  });

  it("says an exam is not open yet rather than implying the whole window is working time", async () => {
    mocks.getExams.mockResolvedValue([
      exam({ start_time: at(5 * 24 * HOUR), end_time: at(6 * 24 * HOUR) }),
    ]);
    show();

    expect(await screen.findByText(/^Opens /)).toBeInTheDocument();
  });

  it("warns that a past-due exam left active can still be started", async () => {
    // end_time is not enforced server-side, so this is the honest wording. If start_exam ever
    // starts rejecting past-due exams, this assertion should fail and be rewritten.
    mocks.getExams.mockResolvedValue([exam({ end_time: at(-2 * HOUR), is_active: true })]);
    show();

    expect(await screen.findByText(/Past due/)).toBeInTheDocument();
    expect(screen.getByText(/still open, but check with your instructor/i)).toBeInTheDocument();
  });

  it("prompts a student with no extension to install it", async () => {
    mocks.useExtensionInstalled.mockReturnValue({ status: "missing", recheck: vi.fn() });
    show();

    expect(await screen.findByRole("link", { name: /get the extension/i })).toBeInTheDocument();
  });

  it("does not nag a student who already has the extension", async () => {
    show();
    await screen.findByText("Student Dashboard");

    expect(screen.queryByRole("link", { name: /get the extension/i })).toBe(null);
    expect(screen.getByText(/extension installed/i)).toBeInTheDocument();
  });

  it("handles an exam with no due date rather than printing Invalid Date", async () => {
    mocks.getExams.mockResolvedValue([exam({ end_time: null })]);
    show();

    await screen.findByText("CS-101 Mock Exam");
    expect(screen.queryByText(/Invalid Date/)).toBe(null);
    expect(screen.queryByText(/^Due /)).toBe(null);
    expect(screen.queryByText(/Past due/)).toBe(null);
  });

  it("keeps showing exams when the risk lookups fail", async () => {
    mocks.getExamSessions.mockRejectedValue(new Error("boom"));
    show();

    expect(await screen.findByText("CS-101 Mock Exam")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText(/Due in 3h 12m/)).toBeInTheDocument());
  });
});
