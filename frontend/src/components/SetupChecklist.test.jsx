import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

vi.mock("../hooks/useSchoolNav", () => ({ useSchoolSlug: () => "arellano-university" }));

const { default: SetupChecklist } = await import("./SetupChecklist");

const show = (counts) =>
  render(
    <MemoryRouter>
      <SetupChecklist counts={counts} />
    </MemoryRouter>
  );

const EMPTY = { courses: 0, subjects: 0, instructors: 0, exams: 0 };

describe("SetupChecklist", () => {
  it("shows a brand-new school every step, in dependency order", () => {
    show(EMPTY);

    const steps = screen.getAllByRole("listitem").map((li) => li.textContent);
    expect(steps).toHaveLength(4);
    expect(steps[0]).toMatch(/add a course/i);
    expect(steps[1]).toMatch(/add a subject/i);
    expect(steps[2]).toMatch(/instructor/i);
    expect(steps[3]).toMatch(/create an exam/i);
  });

  it("points Start at the first thing still outstanding, not the first step", () => {
    show({ ...EMPTY, courses: 1, subjects: 2 });

    const start = screen.getByRole("link", { name: /start/i });
    expect(start.getAttribute("href")).toBe("/arellano-university/instructors");
  });

  it("tracks progress", () => {
    show({ ...EMPTY, courses: 1 });
    expect(screen.getByText("1 of 4 done")).toBeInTheDocument();
  });

  it("disappears once the school is set up, rather than lingering as clutter", () => {
    show({ courses: 1, subjects: 1, instructors: 1, exams: 1 });
    expect(screen.queryByText(/finish setting up your school/i)).toBe(null);
    expect(screen.queryAllByRole("listitem")).toHaveLength(0);
  });

  it("marks completed steps for screen readers, not by colour alone", () => {
    show({ ...EMPTY, courses: 1 });
    // The visual cue is a tick and a strikethrough; neither is announced, so the state is also
    // written out in text for anyone who cannot see it.
    expect(screen.getByText(/add a course/i).textContent).toMatch(/done/i);
  });
});
