import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { audit } from "./axe";

// Guards the audit itself. a11y.test.jsx passing means nothing unless this harness can actually
// fail - a mis-set tag filter or an over-broad rule exclusion would turn the whole accessibility
// suite into a green no-op without anyone noticing.
describe("axe harness", () => {
  it("reports violations that are really there", async () => {
    const { container } = render(
      <div>
        <img src="x.png" />
        <input type="text" />
        <button></button>
      </div>
    );

    const ids = (await audit(container)).map((v) => v.id);

    expect(ids).toContain("image-alt");
    expect(ids).toContain("label");
    expect(ids).toContain("button-name");
  });

  it("passes markup that is correct", async () => {
    const { container } = render(
      <div>
        <img src="x.png" alt="A chart of exam results" />
        <label htmlFor="a">Name</label>
        <input id="a" type="text" />
        <button type="button">Save</button>
      </div>
    );

    expect(await audit(container)).toEqual([]);
  });
});
