import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// vi.hoisted so the mock function itself is the module export, rather than a wrapper closing
// over it - with a wrapper, a rejection is attributed to the test file and reported as
// unhandled even though the component catches it.
const { importSetupCsv } = vi.hoisted(() => ({ importSetupCsv: vi.fn() }));
vi.mock("../../api/setupImport", () => ({ importSetupCsv }));

const { default: SetupImportPanel } = await import("./SetupImportPanel");

const csvFile = () =>
  new File(["type,code,name\ncourse,BSCS,CS\n"], "setup.csv", { type: "text/csv" });

describe("SetupImportPanel", () => {
  // Clear call history and install a benign default, rather than mockReset(): resetting to a
  // bare mock and only later attaching a rejecting implementation leaves the rejection
  // attributed to this file and reported as unhandled, even though the component catches it.
  beforeEach(() => {
    importSetupCsv.mockClear();
    importSetupCsv.mockImplementation(async () => ({
      created_courses: 0, created_subjects: 0, created_instructors: 0,
      skipped_existing: 0, errors: [],
    }));
  });

  it("keeps import disabled until a file is chosen", () => {
    render(<SetupImportPanel />);
    expect(screen.getByRole("button", { name: /^import$/i })).toBeDisabled();
  });

  it("reports what was actually created, broken down by type", async () => {
    importSetupCsv.mockResolvedValue({
      created_courses: 2, created_subjects: 3, created_instructors: 1,
      skipped_existing: 0, errors: [],
    });
    render(<SetupImportPanel />);

    await userEvent.upload(screen.getByLabelText(/choose a setup csv/i), csvFile());
    await userEvent.click(screen.getByRole("button", { name: /^import$/i }));

    expect(await screen.findByText(/added 6 records/i)).toBeInTheDocument();
    expect(screen.getByText(/2 courses · 3 subjects · 1 instructor/i)).toBeInTheDocument();
  });

  it("says plainly when a re-upload added nothing new", async () => {
    // Re-uploading an edited sheet is normal; "Added 0 records" would read as a failure.
    importSetupCsv.mockResolvedValue({
      created_courses: 0, created_subjects: 0, created_instructors: 0,
      skipped_existing: 4, errors: [],
    });
    render(<SetupImportPanel />);

    await userEvent.upload(screen.getByLabelText(/choose a setup csv/i), csvFile());
    await userEvent.click(screen.getByRole("button", { name: /^import$/i }));

    expect(await screen.findByText(/nothing new to add/i)).toBeInTheDocument();
    expect(screen.getByText(/4 already existed/i)).toBeInTheDocument();
  });

  it("lists skipped rows by line number without implying the whole file failed", async () => {
    importSetupCsv.mockResolvedValue({
      created_courses: 1, created_subjects: 0, created_instructors: 0,
      skipped_existing: 0,
      errors: [{ row: 3, message: "no course with code 'NOPE'" }],
    });
    render(<SetupImportPanel />);

    await userEvent.upload(screen.getByLabelText(/choose a setup csv/i), csvFile());
    await userEvent.click(screen.getByRole("button", { name: /^import$/i }));

    expect(await screen.findByText(/everything else was imported/i)).toBeInTheDocument();
    expect(screen.getByText(/row 3: no course with code 'NOPE'/i)).toBeInTheDocument();
  });

  it("announces a failed import rather than only colouring it", async () => {
    // Rejected on a later tick rather than synchronously. A promise that is already rejected
    // the moment it is created is briefly unhandled before the component's await attaches, and
    // the runner reports that as a failure even though the component does catch it.
    importSetupCsv.mockImplementation(
      () =>
        new Promise((_resolve, reject) =>
          setTimeout(() => {
            const err = new Error("request failed");
            err.response = { data: { detail: "CSV needs a 'type' column" } };
            reject(err);
          }, 0)
        )
    );
    render(<SetupImportPanel />);

    await userEvent.upload(screen.getByLabelText(/choose a setup csv/i), csvFile());
    await userEvent.click(screen.getByRole("button", { name: /^import$/i }));

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toMatch(/type. column/i);
  });

  it("explains the columns on request", async () => {
    render(<SetupImportPanel />);
    await userEvent.click(screen.getByRole("button", { name: /column guide/i }));

    expect(screen.getByText(/separated by semicolons/i)).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByText(/skipped rather than duplicated/i)).toBeInTheDocument()
    );
  });
});
