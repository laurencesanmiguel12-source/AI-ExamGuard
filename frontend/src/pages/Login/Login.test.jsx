import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";

const login = vi.fn();
let mockSchool = { id: 1, name: "Arellano University", slug: "arellano-university", status: "approved" };

vi.mock("../../context/AuthContext", () => ({
  useAuth: () => ({ login, isAuthenticated: false }),
}));

vi.mock("../../hooks/useSchoolNav", () => ({
  useSchool: () => mockSchool,
  useSchoolNav: () => vi.fn(),
  useSchoolSlug: () => "arellano-university",
}));

const { default: Login } = await import("./Login");

function renderLogin() {
  return render(
    <MemoryRouter initialEntries={["/arellano-university/login"]}>
      <Routes>
        <Route path="/:schoolSlug/login" element={<Login />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("Login", () => {
  beforeEach(() => {
    login.mockReset();
    mockSchool = { id: 1, name: "Arellano University", slug: "arellano-university", status: "approved" };
  });

  it("labels both credential fields so they are reachable by name", () => {
    renderLogin();

    // getByLabelText only resolves through a real label/input association - this fails if the
    // htmlFor/id pairing regresses, which is exactly how these fields shipped originally.
    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it("submits the typed credentials", async () => {
    login.mockResolvedValue({});
    renderLogin();

    await userEvent.type(screen.getByLabelText(/email address/i), "admin@arellano.edu");
    await userEvent.type(screen.getByLabelText(/password/i), "secret123");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(login).toHaveBeenCalledWith("admin@arellano.edu", "secret123");
  });

  it("announces a failed sign-in rather than only colouring it red", async () => {
    login.mockRejectedValue(new Error("nope"));
    renderLogin();

    await userEvent.type(screen.getByLabelText(/email address/i), "admin@arellano.edu");
    await userEvent.type(screen.getByLabelText(/password/i), "wrong");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    // role="alert" is what makes a screen reader read the failure out; without it the only
    // signal is colour.
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("alert").textContent).toMatch(/invalid email or password/i);
  });

  it("tells a pending school it is awaiting review, before they try to sign in", () => {
    mockSchool = { ...mockSchool, status: "pending" };
    renderLogin();

    expect(screen.getByText(/registration pending review/i)).toBeInTheDocument();
  });

  it("gives a rejected school the reviewer's reason", () => {
    mockSchool = { ...mockSchool, status: "rejected", review_note: "Could not verify this institution." };
    renderLogin();

    expect(screen.getByText(/registration not approved/i)).toBeInTheDocument();
    expect(screen.getByText(/could not verify this institution/i)).toBeInTheDocument();
  });

  it("shows no status banner for an approved school", () => {
    renderLogin();

    expect(screen.queryByText(/pending review/i)).toBe(null);
    expect(screen.queryByText(/not approved/i)).toBe(null);
  });
});
