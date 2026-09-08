import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ExtensionInstallCard, { ExtensionStatusRow } from "./ExtensionInstallCard";
import { EXTENSION_STORE_URL } from "../constants/extension";

describe("ExtensionInstallCard", () => {
  it("stays out of the way while the probe is still in flight", () => {
    // Flashing "install the extension" for a second before the answer arrives would nag every
    // student on every load, including the ones who already have it.
    const { container } = render(<ExtensionInstallCard status="checking" />);
    expect(container).toBeEmptyDOMElement();
  });

  it("says nothing once the extension answers", () => {
    const { container } = render(<ExtensionInstallCard status="installed" />);
    expect(container).toBeEmptyDOMElement();
  });

  it("offers the store link when nothing answered", () => {
    render(<ExtensionInstallCard status="missing" />);

    const link = screen.getByRole("link", { name: /get the extension/i });
    expect(link).toHaveAttribute("href", EXTENSION_STORE_URL);
    expect(link).toHaveAttribute("target", "_blank");
    // Opening a new tab without this leaves the opener reachable from the store page.
    expect(link.getAttribute("rel")).toContain("noopener");
  });

  it("lets a student re-probe after installing, without a full reload", () => {
    const onRecheck = vi.fn();
    render(<ExtensionInstallCard status="missing" onRecheck={onRecheck} />);

    return userEvent.click(screen.getByRole("button", { name: /installed it/i })).then(() => {
      expect(onRecheck).toHaveBeenCalledTimes(1);
    });
  });

  it("on a non-Chrome browser, points at the real fix instead of a dead link", () => {
    // The store link cannot help here - the extension will not install at all - so offering it
    // would send the student somewhere that cannot work.
    render(<ExtensionInstallCard status="unsupported" />);

    expect(screen.getByText(/use google chrome/i)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /get the extension/i })).toBe(null);
  });
});

describe("ExtensionStatusRow", () => {
  it("confirms a working install, so the feature is not only ever nagging", () => {
    render(<ExtensionStatusRow status="installed" />);
    expect(screen.getByText(/extension installed/i)).toBeInTheDocument();
  });

  it("reports a missing one", () => {
    render(<ExtensionStatusRow status="missing" />);
    expect(screen.getByText(/not installed/i)).toBeInTheDocument();
  });
});
