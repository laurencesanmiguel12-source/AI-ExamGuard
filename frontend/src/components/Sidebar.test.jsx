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
