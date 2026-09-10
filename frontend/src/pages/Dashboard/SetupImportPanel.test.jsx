import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// vi.hoisted so the mock function itself is the module export, rather than a wrapper closing
// over it - with a wrapper, a rejection is attributed to the test file and reported as
// unhandled even though the component catches it.
const { importSetupCsv, previewSetupCsv, getSetupReadiness } = vi.hoisted(() => ({
  importSetupCsv: vi.fn(),
  previewSetupCsv: vi.fn(),
  getSetupReadiness: vi.fn(),
}));
vi.mock("../../api/setupImport", () => ({
  importSetupCsv,
  previewSetupCsv,
  getSetupReadiness,
}));

const { default: SetupImportPanel } = await import("./SetupImportPanel");

const csvFile = () =>
  new File(["type,code,name\ncourse,BSCS,CS\n"], "setup.csv", { type: "text/csv" });

const EMPTY = {
  created_courses: 0, created_subjects: 0, created_instructors: 0,
  skipped_existing: 0, errors: [],
};

async function choose() {
  render(<SetupImportPanel />);
  await userEvent.upload(screen.getByLabelText(/choose a setup csv/i), csvFile());
}

describe("SetupImportPanel", () => {
  // Clear call history and install a benign default, rather than mockReset(): resetting to a
  // bare mock and only later attaching a rejecting implementation leaves the rejection
  // attributed to this file and reported as unhandled, even though the component catches it.
  beforeEach(() => {
    importSetupCsv.mockClear();
    previewSetupCsv.mockClear();
    importSetupCsv.mockImplementation(async () => ({ ...EMPTY }));
    previewSetupCsv.mockImplementation(async () => ({ ...EMPTY, preview: true }));
  });

  it("keeps both actions disabled until a file is chosen", () => {
    render(<SetupImportPanel />);
    expect(screen.getByRole("button", { name: /check this file/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /import for real/i })).toBeDisabled();
  });

  it("reports what was actually created, broken down by type", async () => {
    importSetupCsv.mockResolvedValue({
      created_courses: 2, created_subjects: 3, created_instructors: 1,
      skipped_existing: 0, errors: [],
    });
    await choose();

    await userEvent.click(screen.getByRole("button", { name: /import for real/i }));

    expect(await screen.findByText(/added 6 records/i)).toBeInTheDocument();
    expect(screen.getByText(/2 courses · 3 subjects · 1 instructor/i)).toBeInTheDocument();
  });

  it("says plainly when a re-upload added nothing new", async () => {
    // Re-uploading an edited sheet is normal; "Added 0 records" would read as a failure.
    importSetupCsv.mockResolvedValue({
      created_courses: 0, created_subjects: 0, created_instructors: 0,
      skipped_existing: 4, errors: [],
    });
    await choose();

    await userEvent.click(screen.getByRole("button", { name: /import for real/i }));

    expect(await screen.findByText(/nothing new to add/i)).toBeInTheDocument();
    expect(screen.getByText(/4 already existed/i)).toBeInTheDocument();
  });

  it("lists skipped rows by line number without implying the whole file failed", async () => {
    importSetupCsv.mockResolvedValue({
      created_courses: 1, created_subjects: 0, created_instructors: 0,
      skipped_existing: 0,
      errors: [{ row: 3, message: "no course with code 'NOPE'" }],
    });
    await choose();

    await userEvent.click(screen.getByRole("button", { name: /import for real/i }));

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
    await choose();

    await userEvent.click(screen.getByRole("button", { name: /import for real/i }));

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

describe("Bulk import — the process, said out loud", () => {
  beforeEach(() => {
    previewSetupCsv.mockImplementation(async () => ({ ...EMPTY, preview: true }));
  });

  it("states the four steps rather than showing a file box and a button", () => {
    // The panel asked for a visible process flow. The checking step in particular is the one
    // people skip when nothing tells them it exists.
    render(<SetupImportPanel />);

    expect(screen.getByText("Download the template")).toBeInTheDocument();
    expect(screen.getByText("Fill it in with Excel")).toBeInTheDocument();
    expect(screen.getByText("Check the file")).toBeInTheDocument();
  });

  it("tells the user to use Excel and which CSV option to pick", () => {
    // "note especially to the user to use Excel" - and the specific trap, which is that Excel's
    // plain CSV export mangles accented names.
    render(<SetupImportPanel />);

    expect(screen.getByText(/use excel, and save as csv utf-8/i)).toBeInTheDocument();
  });
});

describe("Bulk import — checking a file before importing it", () => {
  const RESULT = {
    created_courses: 2, created_subjects: 3, created_instructors: 1,
    skipped_existing: 4, errors: [],
  };

  beforeEach(() => {
    importSetupCsv.mockClear();
    previewSetupCsv.mockClear();
    importSetupCsv.mockImplementation(async () => ({ ...RESULT, preview: false }));
    previewSetupCsv.mockImplementation(async () => ({ ...RESULT, preview: true }));
  });

  it("checks without importing", async () => {
    await choose();

    await userEvent.click(screen.getByRole("button", { name: /check this file/i }));

    await waitFor(() => expect(previewSetupCsv).toHaveBeenCalled());
    expect(importSetupCsv).not.toHaveBeenCalled();
  });

  it("says nothing has been imported yet, in the future tense", async () => {
    // A preview that reads like a receipt is worse than no preview: somebody skims it, sees
    // "Added 6 records", and walks away believing their data is in.
    await choose();

    await userEvent.click(screen.getByRole("button", { name: /check this file/i }));

    expect(await screen.findByText(/would add 6 records/i)).toBeInTheDocument();
    expect(screen.getByText(/nothing has been imported yet/i)).toBeInTheDocument();
  });

  it("reports the duplicates the import would skip, which is what was asked for", async () => {
    await choose();

    await userEvent.click(screen.getByRole("button", { name: /check this file/i }));

    expect(await screen.findByText(/4 already exist/i)).toBeInTheDocument();
  });

  it("offers to import straight from the check result", async () => {
    await choose();

    await userEvent.click(screen.getByRole("button", { name: /check this file/i }));
    await userEvent.click(await screen.findByRole("button", { name: /import this file/i }));

    await waitFor(() => expect(importSetupCsv).toHaveBeenCalled());
  });

  it("says bad rows would be skipped, not that they were", async () => {
    previewSetupCsv.mockResolvedValue({
      ...RESULT,
      preview: true,
      errors: [{ row: 4, message: "no course with code 'NOSUCH'" }],
    });
    await choose();

    await userEvent.click(screen.getByRole("button", { name: /check this file/i }));

    expect(await screen.findByText(/would be skipped/i)).toBeInTheDocument();
    expect(screen.getByText(/row 4/i)).toBeInTheDocument();
  });

  it("reads as a receipt once the import is real", async () => {
    await choose();

    await userEvent.click(screen.getByRole("button", { name: /import for real/i }));

    expect(await screen.findByText(/added 6 records/i)).toBeInTheDocument();
    expect(screen.queryByText(/nothing has been imported yet/i)).not.toBeInTheDocument();
  });
});
