import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const mocks = vi.hoisted(() => ({
  user: null,
  navigate: vi.fn(),
  getSection: vi.fn(),
  getSectionRoster: vi.fn(),
  getTerms: vi.fn(),
  enrollStudents: vi.fn(),
  setEnrollmentStatus: vi.fn(),
  getStudents: vi.fn(),
}));

vi.mock("react-router-dom", () => ({ useParams: () => ({ sectionId: "5" }) }));
vi.mock("../../api/academic", () => ({
  getSection: mocks.getSection,
  getSectionRoster: mocks.getSectionRoster,
  getTerms: mocks.getTerms,
  enrollStudents: mocks.enrollStudents,
  setEnrollmentStatus: mocks.setEnrollmentStatus,
}));
vi.mock("../../api/students", () => ({ getStudents: mocks.getStudents }));
vi.mock("../../context/AuthContext", () => ({ useAuth: () => ({ user: mocks.user }) }));
vi.mock("../../hooks/useSchoolNav", () => ({ useSchoolNav: () => mocks.navigate }));

const { default: SectionRoster } = await import("./SectionRoster");

const SECTION = {
  id: 5,
  term_id: 9,
  code: "BSCS-3A",
  label: "CS-101 BSCS-3A",
  subject_code: "CS-101",
  subject_name: "Intro to Programming",
  term_name: "1st Semester",
  academic_year_label: "2026-2027",
  instructor_name: "Ana Cruz",
};

function enrolment(id, status = "ENROLLED") {
  return {
    id,
    section_id: 5,
    student_id: id,
    status,
    enrolled_at: "2026-08-01T00:00:00",
    student_name: `Student ${id}`,
    student_number: `S${id}`,
  };
}

async function show({
  role = "admin",
  roster = [enrolment(1)],
  students = [{ id: 1, student_name: "Student 1", student_number: "S1" }],
  termStatus = "ACTIVE",
} = {}) {
  mocks.user = { id: 1, role_name: role };
  mocks.getSection.mockResolvedValue(SECTION);
  mocks.getSectionRoster.mockResolvedValue(roster);
  mocks.getStudents.mockResolvedValue(students);
  mocks.getTerms.mockResolvedValue([{ id: 9, name: "1st Semester", status: termStatus }]);
  render(<SectionRoster />);
  await waitFor(() =>
    expect(screen.getByRole("heading", { name: "CS-101 BSCS-3A" })).toBeInTheDocument()
  );
}

beforeEach(() => vi.clearAllMocks());

describe("Section class list", () => {
  it("warns that an empty class list is an exam nobody can open", async () => {
    // This is the same lockout the exam roster screen reports, said one step earlier - here it
    // can still be fixed by enrolling somebody rather than only diagnosed.
    await show({ roster: [] });

    expect(screen.getByRole("alert")).toHaveTextContent(/nobody is enrolled in this section/i);
    expect(screen.getByRole("alert")).toHaveTextContent(/admit no students at all/i);
  });

  it("says what a healthy class list means for the exams that inherit it", async () => {
    await show({ roster: [enrolment(1), enrolment(2)] });

    expect(screen.getByRole("status")).toHaveTextContent(/2 students enrolled/i);
  });

  it("shows dropped students instead of hiding them", async () => {
    // A roster that silently omits a dropped student looks like the student was never enrolled,
    // which is exactly the state somebody comes here to correct.
    await show({ roster: [enrolment(1, "DROPPED")] });

    expect(mocks.getSectionRoster).toHaveBeenCalledWith("5", { activeOnly: false });
    expect(screen.getByText("DROPPED")).toBeInTheDocument();
  });

  it("counts only enrolled students as admitted, not dropped ones", async () => {
    // The count has to match what an exam would actually admit; counting DROPPED rows would
    // report a class list that does not exist.
    await show({ roster: [enrolment(1), enrolment(2, "DROPPED")] });

    expect(screen.getByRole("status")).toHaveTextContent(/1 student enrolled/i);
  });

  it("offers Drop on an enrolled student and Reinstate on a dropped one", async () => {
    await show({ roster: [enrolment(1), enrolment(2, "DROPPED")] });

    expect(screen.getByRole("button", { name: "Drop" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reinstate" })).toBeInTheDocument();
  });

  it("drops a student through the enrolment status endpoint", async () => {
    mocks.setEnrollmentStatus.mockResolvedValue({});
    await show({ roster: [enrolment(1)] });

    await userEvent.click(screen.getByRole("button", { name: "Drop" }));

    await waitFor(() => expect(mocks.setEnrollmentStatus).toHaveBeenCalledWith("5", 1, "DROPPED"));
  });

  it("locks enrolment on a closed term and says where to reopen it", async () => {
    // The server refuses enrolment into a closed term. Showing the picker anyway would only
    // produce a refusal after the work of selecting people.
    await show({ termStatus: "CLOSED", roster: [] });

    expect(screen.getByText(/is closed, so enrolment is locked/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /select all/i })).not.toBeInTheDocument();
  });

  it("does not offer an instructor the enrolment controls the server reserves for admins", async () => {
    await show({ role: "instructor", roster: [enrolment(1)] });

    expect(screen.queryByRole("button", { name: "Drop" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /select all/i })).not.toBeInTheDocument();
  });

  it("reports what enrolling actually did rather than just succeeding silently", async () => {
    // Enrolment is deliberately re-runnable, so "3 enrolled" and "3 already enrolled" are both
    // successes that mean completely different things.
    mocks.enrollStudents.mockResolvedValue({
      enrolled: 1,
      reinstated: 0,
      skipped_already_enrolled: 2,
      errors: [],
    });
    await show({
      roster: [],
      students: [
        { id: 1, student_name: "Student 1", student_number: "S1" },
        { id: 2, student_name: "Student 2", student_number: "S2" },
      ],
    });

    await userEvent.click(screen.getByRole("button", { name: /select all 2/i }));
    await userEvent.click(screen.getByRole("button", { name: /enrol 2 selected/i }));

    await waitFor(() => expect(mocks.enrollStudents).toHaveBeenCalledWith("5", [1, 2]));
    expect(await screen.findByText(/1 enrolled, 2 already enrolled/i)).toBeInTheDocument();
  });

  it("surfaces the per-student errors a partial enrolment reports", async () => {
    // One bad id does not abandon the rest, so the failures have to be shown alongside the
    // successes or they vanish.
    mocks.enrollStudents.mockResolvedValue({
      enrolled: 1,
      reinstated: 0,
      skipped_already_enrolled: 0,
      errors: ["student #99 is not in this school"],
    });
    await show({ roster: [], students: [{ id: 1, student_name: "Student 1", student_number: "S1" }] });

    await userEvent.click(screen.getByRole("button", { name: /select all 1/i }));
    await userEvent.click(screen.getByRole("button", { name: /enrol 1 selected/i }));

    expect(await screen.findByText("student #99 is not in this school")).toBeInTheDocument();
  });
});
