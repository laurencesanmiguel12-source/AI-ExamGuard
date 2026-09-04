import { afterEach, expect } from "vitest";
import { cleanup } from "@testing-library/react";

// Unmount between tests so a query in one spec can never match a component another spec left in
// the document.
afterEach(cleanup);

// A couple of matchers we actually use, defined here rather than pulling in jest-dom - the
// frontend keeps its dependency list deliberately short (see the frontend-stack memory), and
// these two cover what these specs assert.
expect.extend({
  toBeInTheDocument(received) {
    const pass = received !== null && received !== undefined && document.body.contains(received);
    return {
      pass,
      message: () =>
        pass
          ? "expected element not to be in the document"
          : "expected element to be in the document, but it was not found",
    };
  },
  toBeDisabled(received) {
    const pass = received?.disabled === true || received?.getAttribute?.("aria-disabled") === "true";
    return {
      pass,
      message: () => (pass ? "expected element not to be disabled" : "expected element to be disabled"),
    };
  },
});
