import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { audit, describeViolations } from "./axe";

// A machine-run WCAG 2 A/AA pass over the screens a user actually meets, so accessibility is
// something the suite enforces rather than something we assert. Two caveats stated plainly:
// colour contrast cannot be evaluated in jsdom (no layout), and this covers rendered markup, not
// how the app behaves under a real screen reader.

let mockSchool = { id: 1, name: "Arellano University", slug: "arellano-university", status: "approved" };
const getCourses = vi.fn();

vi.mock("../context/AuthContext", () => ({
  useAuth: () => ({ login: vi.fn(), isAuthenticated: false, user: null, loading: false }),
}));
vi.mock("../hooks/useSchoolNav", () => ({
  useSchool: () => mockSchool,
  useSchoolNav: () => vi.fn(),
  useSchoolSlug: () => "arellano-university",
}));
vi.mock("../api/courses", () => ({ getCourses: (...a) => getCourses(...a) }));
vi.mock("../api/auth", () => ({ register: vi.fn() }));
vi.mock("../api/schools", () => ({ registerSchool: vi.fn(), getSchoolsForReview: vi.fn(() => Promise.resolve([])) }));
vi.mock("../hooks/useIdleLogout", () => ({ default: () => ({ warning: false, stayLoggedIn: vi.fn() }) }));

const { default: Login } = await import("../pages/Login/Login");
const { default: Register } = await import("../pages/Register/Register");
const { default: SchoolSignup } = await import("../pages/SchoolSignup/SchoolSignup");
const { default: Modal } = await import("../components/Modal");
const { default: ConfirmDialog } = await import("../components/ConfirmDialog");
const { default: DataTable } = await import("../components/DataTable");
const { default: Sidebar } = await import("../components/Sidebar");
const { default: Layout } = await import("../components/Layout");

function atRoute(path, element) {
  return render(
    <MemoryRouter initialEntries={[`/arellano-university/${path}`]}>
      <Routes>
        <Route path={`/:schoolSlug/${path}`} element={element} />
      </Routes>
    </MemoryRouter>
  );
}

async function expectClean(container) {
  const violations = await audit(container);
  expect(violations, `\n${describeViolations(violations)}\n`).toEqual([]);
}

describe("accessibility (axe, WCAG 2 A/AA)", () => {
  beforeEach(() => {
    getCourses.mockResolvedValue([{ id: 1, code: "BSCS", name: "BS Computer Science" }]);
    mockSchool = { id: 1, name: "Arellano University", slug: "arellano-university", status: "approved" };
  });

  it("sign-in page", async () => {
    const { container } = atRoute("login", <Login />);
    await expectClean(container);
  });

  it("sign-in page showing a pending-school notice", async () => {
    mockSchool = { ...mockSchool, status: "pending" };
    const { container } = atRoute("login", <Login />);
    await expectClean(container);
  });

  it("student registration", async () => {
    const { container } = atRoute("register", <Register />);
    await screen.findByRole("option", { name: /bs computer science/i });
    await expectClean(container);
  });

  it("school signup", async () => {
    const { container } = render(
      <MemoryRouter>
        <SchoolSignup />
      </MemoryRouter>
    );
    await expectClean(container);
  });

  it("dialog shell", async () => {
    const { container } = render(
      <Modal title="Edit Course" onClose={() => {}}>
        <label htmlFor="x">Name</label>
        <input id="x" />
      </Modal>
    );
    await expectClean(container);
  });

  it("delete confirmation", async () => {
    const { container } = render(
      <ConfirmDialog message="Delete this course?" onConfirm={() => {}} onCancel={() => {}} />
    );
    await expectClean(container);
  });

  // Rendered by every list page (Courses, Subjects, Students, Instructors, Exams), so one
  // violation here would be one violation five times over.
  it("data table with rows and row actions", async () => {
    const { container } = render(
      <DataTable
        columns={[
          { key: "code", label: "Code" },
          { key: "name", label: "Name" },
        ]}
        rows={[{ id: 1, code: "BSCS", name: "BS Computer Science" }]}
        onEdit={() => {}}
        onDelete={() => {}}
      />
    );
    await expectClean(container);
  });

  it("data table in its empty state", async () => {
    const { container } = render(
      <DataTable columns={[{ key: "code", label: "Code" }]} rows={[]} emptyLabel="No courses yet." />
    );
    await expectClean(container);
  });

  // WCAG 2.4.1 Bypass Blocks. axe cannot flag this - the criterion is about nav repeating across
  // pages, not about any single page's markup - so it is asserted directly.
  it("offers a skip link past the repeated navigation", async () => {
    render(
      <MemoryRouter initialEntries={["/arellano-university"]}>
        <Routes>
          <Route path="/:schoolSlug" element={<Layout />} />
        </Routes>
      </MemoryRouter>
    );

    const skip = screen.getByRole("link", { name: /skip to main content/i });
    expect(skip.getAttribute("href")).toBe("#main-content");
    // The target has to be focusable, or following the link moves the viewport but not focus.
    expect(document.getElementById("main-content").getAttribute("tabindex")).toBe("-1");
  });

  // Present on every authenticated screen.
  it("sidebar navigation", async () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/arellano-university/dashboard"]}>
        <Sidebar open onClose={() => {}} />
      </MemoryRouter>
    );
    await expectClean(container);
  });
});
