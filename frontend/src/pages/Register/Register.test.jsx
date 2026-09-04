import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";

const registerStudent = vi.fn();
const getCourses = vi.fn();
let mockSchool = { id: 1, name: "Arellano University", slug: "arellano-university", status: "approved" };

vi.mock("../../api/auth", () => ({ register: (...args) => registerStudent(...args) }));
vi.mock("../../api/courses", () => ({ getCourses: (...args) => getCourses(...args) }));
vi.mock("../../hooks/useSchoolNav", () => ({
  useSchool: () => mockSchool,
  useSchoolNav: () => vi.fn(),
  useSchoolSlug: () => "arellano-university",
}));

const { default: Register } = await import("./Register");

function renderRegister() {
  return render(
    <MemoryRouter initialEntries={["/arellano-university/register"]}>
      <Routes>
        <Route path="/:schoolSlug/register" element={<Register />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("Register", () => {
  beforeEach(() => {
    registerStudent.mockReset();
    getCourses.mockReset();
    mockSchool = { id: 1, name: "Arellano University", slug: "arellano-university", status: "approved" };
  });

  it("loads the courses for the school in the URL", async () => {
    getCourses.mockResolvedValue([{ id: 1, code: "BSCS", name: "BS Computer Science" }]);
    renderRegister();

    // Regression guard: the page reads school.id, and a change that dropped id from the
    // by-slug API response shipped a form that requested school_id=undefined and then sat on
    // "Loading courses…" forever with submit disabled.
    await waitFor(() => expect(getCourses).toHaveBeenCalledWith(1));
    expect(await screen.findByRole("option", { name: /bs computer science/i })).toBeInTheDocument();
  });

  it("keeps submit disabled while no course can be offered", async () => {
    getCourses.mockResolvedValue([]);
    renderRegister();

    // A student cannot belong to no course, so submitting would only 422. Better to block it
    // and say so than to let them fill the whole form first.
    await waitFor(() => expect(getCourses).toHaveBeenCalled());
    expect(screen.getByRole("button", { name: /create account/i })).toBeDisabled();
  });

  it("submits the chosen course as a number, not the select's string value", async () => {
    getCourses.mockResolvedValue([{ id: 7, code: "BSIT", name: "BS Information Technology" }]);
    registerStudent.mockResolvedValue({});
    renderRegister();
    await screen.findByRole("option", { name: /bs information technology/i });

    await userEvent.type(screen.getByLabelText(/first name/i), "Ana");
    await userEvent.type(screen.getByLabelText(/last name/i), "Reyes");
    await userEvent.type(screen.getByLabelText(/email/i), "ana@arellano.edu");
    await userEvent.type(screen.getByLabelText(/password/i), "TestPass123!");
    await userEvent.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => expect(registerStudent).toHaveBeenCalled());
    // The backend rejects a string course_id, and a select always yields strings.
    expect(registerStudent.mock.calls[0][0].course_id).toBe(7);
  });

  it("labels every field so the form is navigable by name", async () => {
    getCourses.mockResolvedValue([{ id: 1, code: "BSCS", name: "BS Computer Science" }]);
    renderRegister();
    await screen.findByRole("option", { name: /bs computer science/i });

    for (const label of [/first name/i, /last name/i, /email/i, /password/i, /course/i]) {
      expect(screen.getByLabelText(label)).toBeInTheDocument();
    }
  });
});
