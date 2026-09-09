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
  toHaveAttribute(received, name, expected) {
    const actual = received?.getAttribute?.(name);
    const present = actual !== null && actual !== undefined;
    const pass = expected === undefined ? present : actual === expected;
    return {
      pass,
      actual,
      expected,
      message: () =>
        expected === undefined
          ? `expected element ${pass ? "not " : ""}to have attribute "${name}"`
          : `expected "${name}" to be "${expected}", got ${present ? `"${actual}"` : "no such attribute"}`,
    };
  },
  toHaveValue(received, expected) {
    const actual = received?.value;
    const pass = actual === expected;
    return {
      pass,
      actual,
      expected,
      message: () => `expected field value to be "${expected}", got "${actual}"`,
    };
  },
  toHaveTextContent(received, expected) {
    // Asserts against the element's rendered text rather than a whole-document query, which is
    // what lets a spec pin a message to the specific banner that must carry it - "is this string
    // somewhere on the page" would pass even when the wrong element said it.
    const actual = received?.textContent ?? "";
    const pass = expected instanceof RegExp ? expected.test(actual) : actual.includes(expected);
    return {
      pass,
      message: () =>
        `expected element text ${pass ? "not " : ""}to match ${expected}, got "${actual}"`,
    };
  },
  toBeEmptyDOMElement(received) {
    // A component that renders null leaves its container with no child nodes at all. Whitespace
    // between JSX elements never reaches the DOM, so this needs no trimming.
    const pass = received?.childNodes?.length === 0;
    return {
      pass,
      message: () =>
        pass
          ? "expected element to render something, but it was empty"
          : `expected element to be empty, but it contained: ${received?.innerHTML}`,
    };
  },
});
