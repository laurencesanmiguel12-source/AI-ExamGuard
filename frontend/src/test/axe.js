import axe from "axe-core";

// Rules that cannot be judged in jsdom and would otherwise report noise:
//
// - colour-contrast needs real layout and computed styles; jsdom has neither, so axe can only
//   ever return "incomplete" for it. Contrast still needs a browser pass - see the note in the
//   quality report. Disabled here so it doesn't masquerade as a pass.
// - region / landmark rules expect a whole document. These tests render one component into a
//   bare container, so a missing <main> is an artefact of the harness, not of the app.
const JSDOM_UNSUPPORTED = {
  "color-contrast": { enabled: false },
  region: { enabled: false },
  "landmark-one-main": { enabled: false },
  "page-has-heading-one": { enabled: false },
  "html-has-lang": { enabled: false },
  "document-title": { enabled: false },
};

/**
 * Runs axe over a container and returns its violations, worst first.
 * Only WCAG 2 A/AA rules - the level nearly every institutional accessibility policy cites.
 */
export async function audit(container, { rules = {} } = {}) {
  const results = await axe.run(container, {
    runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"] },
    rules: { ...JSDOM_UNSUPPORTED, ...rules },
  });

  const order = { critical: 0, serious: 1, moderate: 2, minor: 3 };
  return results.violations.sort((a, b) => order[a.impact] - order[b.impact]);
}

/** Renders violations as something readable in a failure message rather than a wall of JSON. */
export function describeViolations(violations) {
  return violations
    .map((v) => {
      const where = v.nodes.map((n) => `      ${n.html.slice(0, 120)}`).join("\n");
      return `  [${v.impact}] ${v.id} — ${v.help}\n${where}`;
    })
    .join("\n");
}
