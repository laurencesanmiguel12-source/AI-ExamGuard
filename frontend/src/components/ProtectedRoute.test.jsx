import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

let mockAuth = { user: null, loading: false, isAuthenticated: false };

vi.mock("../context/AuthContext", () => ({ useAuth: () => mockAuth }));
vi.mock("../hooks/useSchoolNav", () => ({ useSchoolSlug: () => "arellano-university" }));

const { default: ProtectedRoute } = await import("./ProtectedRoute");

function renderAt(path, allowedRoles) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/:schoolSlug" element={<ProtectedRoute allowedRoles={allowedRoles} />}>
          <Route path="secret" element={<div>protected content</div>} />
        </Route>
        <Route path="/:schoolSlug/login" element={<div>login page</div>} />
        <Route path="/:schoolSlug/dashboard" element={<div>dashboard</div>} />
      </Routes>
    </MemoryRouter>
  );
}

const as = (role) => ({ user: { role_name: role }, loading: false, isAuthenticated: true });

describe("ProtectedRoute", () => {
  beforeEach(() => {
    mockAuth = { user: null, loading: false, isAuthenticated: false };
  });

  it("sends an unauthenticated visitor to their school's login", () => {
    renderAt("/arellano-university/secret", ["admin"]);

    expect(screen.getByText("login page")).toBeInTheDocument();
  });

  it("lets an allowed role through", () => {
    mockAuth = as("admin");
    renderAt("/arellano-university/secret", ["admin"]);

    expect(screen.getByText("protected content")).toBeInTheDocument();
  });

  it("bounces a disallowed role to the dashboard rather than showing the page", () => {
    mockAuth = as("student");
    renderAt("/arellano-university/secret", ["admin"]);

    expect(screen.getByText("dashboard")).toBeInTheDocument();
    expect(screen.queryByText("protected content")).toBe(null);
  });

  it("treats a super admin as satisfying an admin gate", () => {
    // Mirrors the backend, where require_admin accepts admin AND super_admin.
    mockAuth = as("super_admin");
    renderAt("/arellano-university/secret", ["admin"]);

    expect(screen.getByText("protected content")).toBeInTheDocument();
  });

  it("keeps a school admin out of a super-admin-only route", () => {
    // The School Approvals queue decides which schools exist platform-wide. Every other "admin"
    // gate admits a super admin, so this is the one direction that must NOT be symmetric.
    mockAuth = as("admin");
    renderAt("/arellano-university/secret", ["super_admin"]);

    expect(screen.queryByText("protected content")).toBe(null);
    expect(screen.getByText("dashboard")).toBeInTheDocument();
  });

  it("waits instead of redirecting while the session is still resolving", () => {
    // Redirecting during the auth check would bounce a signed-in user to login on every refresh.
    mockAuth = { user: null, loading: true, isAuthenticated: false };
    renderAt("/arellano-university/secret", ["admin"]);

    expect(screen.queryByText("login page")).toBe(null);
    expect(screen.queryByText("protected content")).toBe(null);
  });
});
