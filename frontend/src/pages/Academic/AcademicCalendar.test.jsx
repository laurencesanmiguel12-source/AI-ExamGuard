import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const mocks = vi.hoisted(() => ({
  getAcademicYears: vi.fn(),
  createAcademicYear: vi.fn(),
  updateAcademicYear: vi.fn(),
  deleteAcademicYear: vi.fn(),
  setCurrentAcademicYear: vi.fn(),
  getTerms: vi.fn(),
  createTerm: vi.fn(),
  updateTerm: vi.fn(),
  deleteTerm: vi.fn(),
  setTermStatus: vi.fn(),
}));

vi.mock("../../api/academic", () => mocks);

const { default: AcademicCalendar } = await import("./AcademicCalendar");

const YEAR = { id: 1, label: "2026-2027", starts_on: "2026-08-01", ends_on: "2027-05-31", is_current: true };
const OLD_YEAR = { id: 2, label: "2025-2026", starts_on: "2025-08-01", ends_on: "2026-05-31", is_current: false };

function term(overrides) {
  return {
    id: 10,
    academic_year_id: 1,
    name: "1st Semester",
    sequence: 1,
    starts_on: "2026-08-01",
    ends_on: "2026-12-20",
    status: "PLANNED",
    ...overrides,
  };
}

async function show({ years = [YEAR], terms = [] } = {}) {
  mocks.getAcademicYears.mockResolvedValue(years);
  mocks.getTerms.mockResolvedValue(terms);
  render(<AcademicCalendar />);
  // The heading renders immediately, before either fetch settles, so waiting on it would prove
  // nothing. Wait for the terms call the year selection triggers - that is the last thing to land.
  if (years.length > 0) {
    await waitFor(() => expect(mocks.getTerms).toHaveBeenCalled());
  }
  await waitFor(() =>
    expect(screen.queryByText("Loading…")).not.toBeInTheDocument()
  );
}

beforeEach(() => vi.clearAllMocks());

describe("Academic Calendar", () => {
  it("opens on the year that is actually in force, not whichever sorted first", async () => {
    // Almost every visit is about the current year. Landing on an arbitrary one means the terms
    // list below is showing the wrong year's terms before anybody has touched anything.
    await show({ years: [OLD_YEAR, YEAR] });

    await waitFor(() => expect(mocks.getTerms).toHaveBeenCalledWith(YEAR.id));
    expect(screen.getByRole("button", { name: "2026-2027" })).toHaveAttribute("aria-pressed", "true");
  });

  it("says what is missing rather than showing an empty page when no year exists", async () => {
    await show({ years: [] });

    expect(screen.getByText("No school year yet")).toBeInTheDocument();
    expect(screen.getByText(/nothing below can be set up until one exists/i)).toBeInTheDocument();
  });

  it("shows a term's state, because whether a term is over is a decision and not a date", async () => {
    await show({ terms: [term({ status: "ACTIVE" })] });

    expect(await screen.findByText("Active")).toBeInTheDocument();
  });

  it("offers only the transitions the state machine actually allows", async () => {
    // PLANNED → ACTIVE → CLOSED → ACTIVE. Offering "Close" on a planned term would produce a
    // server refusal for something the UI invited.
    await show({ terms: [term({ status: "PLANNED" })] });
    expect(await screen.findByRole("button", { name: "Activate" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Close" })).not.toBeInTheDocument();
  });

  it("passes the server's refusal through instead of flattening it into a generic failure", async () => {
    // "'1st Semester' is still active. Close it before activating another term." already names
    // the exact thing to do; replacing it with "something went wrong" throws that away.
    mocks.setTermStatus.mockRejectedValue({
      response: { data: { detail: "'1st Semester' is still active. Close it before activating another term." } },
    });
    await show({ terms: [term({ id: 11, name: "2nd Semester", sequence: 2, status: "PLANNED" })] });

    await userEvent.click(await screen.findByRole("button", { name: "Activate" }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(/still active\. close it before activating/i)
    );
  });

  it("warns that closing a term completes its class lists before doing it", async () => {
    // Closing is not just a label change - it rewrites every ENROLLED row in the term to
    // COMPLETED, and reopening does not put them back.
    await show({ terms: [term({ status: "ACTIVE" })] });

    await userEvent.click(await screen.findByRole("button", { name: "Close" }));

    expect(screen.getByText(/marked as having completed it/i)).toBeInTheDocument();
    expect(mocks.setTermStatus).not.toHaveBeenCalled();
  });

  it("lets a closed term be reopened rather than pushing someone to edit the database", async () => {
    await show({ terms: [term({ status: "CLOSED" })] });

    expect(await screen.findByRole("button", { name: "Reopen" })).toBeInTheDocument();
  });
});

describe("Academic Calendar — correcting and removing", () => {
  it("lets a year be renamed rather than living with a typo forever", async () => {
    // Until now the hierarchy was create-only, so a mistyped label was permanent - while every
    // other entity in the app has had full CRUD from the start.
    mocks.updateAcademicYear.mockResolvedValue({});
    await show();

    await userEvent.click(screen.getByRole("button", { name: "Edit 2026-2027" }));
    const label = screen.getByLabelText("Label");
    await userEvent.clear(label);
    await userEvent.type(label, "AY 2026-27");
    await userEvent.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() => expect(mocks.updateAcademicYear).toHaveBeenCalled());
    expect(mocks.updateAcademicYear.mock.calls[0][1].label).toBe("AY 2026-27");
  });

  it("does not offer 'make current' inside the rename form", async () => {
    // Which year is current is a school-wide invariant with its own control on the row; a rename
    // form that could flip it would change two unrelated things from one save.
    await show();

    await userEvent.click(screen.getByRole("button", { name: "Edit 2026-2027" }));

    expect(screen.queryByLabelText(/make this the current school year/i)).not.toBeInTheDocument();
  });

  it("shows the server's reason when a year still has terms, not 'please try again'", async () => {
    // The refusal names what is attached, which is the only thing that tells someone what to
    // clear first. A generic retry message hides it and suggests something that cannot work.
    mocks.deleteAcademicYear.mockRejectedValue({
      response: { data: { detail: "'2026-2027' still has 2 terms. Delete those first." } },
    });
    await show();

    await userEvent.click(screen.getByRole("button", { name: "Delete 2026-2027" }));
    await userEvent.click(screen.getByRole("button", { name: /^delete$/i }));

    expect(await screen.findByText(/still has 2 terms/i)).toBeInTheDocument();
    expect(screen.queryByText(/please try again/i)).not.toBeInTheDocument();
  });

  it("lets a term be renamed and repositioned", async () => {
    mocks.updateTerm.mockResolvedValue({});
    await show({ terms: [term({ status: "PLANNED" })] });

    await userEvent.click(await screen.findByRole("button", { name: "Edit 1st Semester" }));
    const name = screen.getByLabelText("Name");
    await userEvent.clear(name);
    await userEvent.type(name, "First Semester");
    await userEvent.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() => expect(mocks.updateTerm).toHaveBeenCalled());
    expect(mocks.updateTerm.mock.calls[0][1].name).toBe("First Semester");
  });

  it("keeps status out of the term edit form", async () => {
    // Closing a term completes every enrolment in it. That belongs to the state-machine buttons
    // on the row, not to a form whose save button says "Save Changes".
    await show({ terms: [term({ status: "ACTIVE" })] });

    await userEvent.click(await screen.findByRole("button", { name: "Edit 1st Semester" }));

    expect(screen.queryByLabelText(/status/i)).not.toBeInTheDocument();
  });

  it("offers delete on a term and warns it is refused while sections exist", async () => {
    await show({ terms: [term()] });

    await userEvent.click(await screen.findByRole("button", { name: "Delete 1st Semester" }));

    expect(screen.getByText(/refused while it still has sections/i)).toBeInTheDocument();
    expect(mocks.deleteTerm).not.toHaveBeenCalled();
  });
});
