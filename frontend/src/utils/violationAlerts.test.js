import { describe, it, expect } from "vitest";
import { shouldRaiseAlert, VIOLATION_ALERT_COOLDOWN_MS } from "./violationAlerts";

describe("shouldRaiseAlert", () => {
  it("interrupts the first time a violation happens", () => {
    expect(shouldRaiseAlert({}, "TAB_SWITCH", 1000)).toBe(true);
  });

  it("stays quiet while the same violation keeps firing", () => {
    // The object check polls every few seconds. Without this, a phone left in view reopens the
    // modal continuously and the student cannot sit the exam at all.
    const seen = {};
    const t0 = 1000;
    expect(shouldRaiseAlert(seen, "PHONE_DETECTED", t0)).toBe(true);

    for (const dt of [3000, 6000, 15000, 29000]) {
      expect(shouldRaiseAlert(seen, "PHONE_DETECTED", t0 + dt)).toBe(false);
    }
  });

  it("allows a fresh interruption once the cooldown has passed", () => {
    const seen = {};
    shouldRaiseAlert(seen, "TAB_SWITCH", 1000);

    expect(shouldRaiseAlert(seen, "TAB_SWITCH", 1000 + VIOLATION_ALERT_COOLDOWN_MS)).toBe(true);
  });

  it("tracks each violation type independently", () => {
    // A phone cooldown must not silence a first-ever "we can't see your face", which is
    // immediately actionable and unrelated.
    const seen = {};
    shouldRaiseAlert(seen, "PHONE_DETECTED", 1000);

    expect(shouldRaiseAlert(seen, "FACE_LOST", 1001)).toBe(true);
  });

  it("treats a violation at time 0 as having been shown", () => {
    // Guards a falsy-check bug: `if (previous && ...)` would let t=0 through as never-shown.
    const seen = {};
    expect(shouldRaiseAlert(seen, "TAB_SWITCH", 0)).toBe(true);
    expect(shouldRaiseAlert(seen, "TAB_SWITCH", 10)).toBe(false);
  });
});
