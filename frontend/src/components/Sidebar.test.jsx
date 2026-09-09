import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

const mocks = vi.hoisted(() => ({ user: null, getSchoolsForReview: vi.fn() }));

vi.mock("../context/AuthContext", () => ({ useAuth: () => ({ user: mocks.user }) }));
vi.mock("../hooks/useSchoolNav", () => ({
  useSchool: () => ({ id: 1, name: "Arellano University", slug: "arellano-university" }),
  useSchoolSlug: () => "arellano-university",
}));
vi.mock("../api/schools", () => ({ getSchoolsForReview: mocks.getSchoolsForReview }));

const { default: Sidebar } = await import("./Sidebar");

function showAs(role) {
  mocks.user = { id: 1, first_name: "A", role_name: role };
  return render(
    <MemoryRouter initialEntries={["/arellano-university/dashboard"]}>
      <Sidebar open={false} onClose={() => {}} />
    </MemoryRouter>
  );
}

beforeEach(() => {
  mocks.getSchoolsForReview.mockResolvedValue([]);
});

describe("Sidebar — Bulk Import", () => {
  it("gives an admin a way to reach bulk import without hunting through dashboard tabs", () => {
    showAs("admin");

    const link = screen.getByRole("link", { name: /bulk import/i });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "/arellano-university/setup-import");
  });

  it("sits with the three things it creates", () => {
    showAs("admin");
    expect(screen.getByText("Academic Management")).toBeInTheDocument();
  });

  it("is not offered to an instructor", () => {
    // It creates courses, subjects and instructor accounts - all admin-only elsewhere in the
    // sidebar, and the route is behind ProtectedRoute allowedRoles={["admin"]}, so offering the
    // link to an instructor would just walk them into a redirect.
    showAs("instructor");
    expect(screen.queryByRole("link", { name: /bulk import/i })).toBe(null);
  });

  it("is not offered to a student", () => {
    showAs("student");
    expect(screen.queryByRole("link", { name: /bulk import/i })).toBe(null);
  });
});

describe("Sidebar — existing entries still intact", () => {
  it("keeps the admin's academic pages", () => {
    showAs("admin");
    for (const label of [/course management/i, /subject management/i, /instructor management/i,
                         /student management/i, /exam management/i]) {
      expect(screen.getByRole("link", { name: label })).toBeInTheDocument();
    }
  });

  it("still withholds the platform-wide queue from a school admin", () => {
    // hasRole treats an "admin" entry as satisfied by a super admin, so this entry is
    // super_admin-only on purpose - regression guard for that distinction.
    showAs("admin");
    expect(screen.queryByRole("link", { name: /school approvals/i })).toBe(null);
  });
});

describe("Sidebar — the academic hierarchy", () => {
  it("gives an admin the calendar the rest of the hierarchy depends on", () => {
    // A section needs a term and a class list needs a section, so with no way to reach the
    // calendar the entities existed in the API and nowhere else.
    showAs("admin");
    expect(screen.getByRole("link", { name: /academic calendar/i })).toBeInTheDocument();
  });

  it("puts the calendar above the things that depend on it", () => {
    // Working down the sidebar in order has to produce a school that is actually set up.
    showAs("admin");
    const labels = screen.getAllByRole("link").map((a) => a.textContent);
    expect(labels.indexOf("Academic Calendar")).toBeLessThan(labels.indexOf("Sections & Class Lists"));
  });

  it("lets an instructor see the classes they teach", () => {
    // Read-only for them - the page hides its own admin controls - but an instructor with no
    // route to their own class list is the same dead end new instructors already hit once.
    showAs("instructor");
    expect(screen.getByRole("link", { name: /sections & class lists/i })).toBeInTheDocument();
  });

  it("keeps the calendar itself admin-only", () => {
    showAs("instructor");
    expect(screen.queryByRole("link", { name: /academic calendar/i })).toBe(null);
  });

  it("shows a student neither", () => {
    showAs("student");
    expect(screen.queryByRole("link", { name: /academic calendar/i })).toBe(null);
    expect(screen.queryByRole("link", { name: /sections & class lists/i })).toBe(null);
  });
});
