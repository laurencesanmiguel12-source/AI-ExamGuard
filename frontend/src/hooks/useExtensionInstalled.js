import { useCallback, useEffect, useState } from "react";

const EXTENSION_ID = import.meta.env.VITE_EXTENSION_ID;
const PROBE_TIMEOUT_MS = 1500;

/**
 * Is the Tab Monitor extension installed right now? Answered outside any exam session.
 *
 * useExtensionMonitor already does this, but only for a live session: it needs a sessionId, it
 * arms violation logging, and it holds the port open with a 4s ping. None of that belongs on a
 * dashboard, so this is a one-shot probe instead.
 *
 * It sends PING rather than INIT on purpose. background.js answers PING with PONG from the bare
 * connection handler, while INIT registers the port in its `ports` map against a sessionId - so
 * probing with INIT would enrol a null-session port in the extension's routing table just to ask
 * a yes/no question. PING proves the extension is there and leaves no trace.
 *
 * Four outcomes, because "not installed" and "cannot tell" call for different words on screen:
 *   checking     - probe in flight
 *   installed    - PONG received
 *   missing      - Chrome, but nothing answered
 *   unsupported  - not a Chromium browser, or no extension id configured; the extension cannot
 *                  be installed here at all, so telling them to install it would be a dead end
 */
export default function useExtensionInstalled() {
  const [status, setStatus] = useState("checking");
  const [attempt, setAttempt] = useState(0);

  const recheck = useCallback(() => {
    setStatus("checking");
    setAttempt((a) => a + 1);
  }, []);

  useEffect(() => {
    if (!window.chrome?.runtime?.connect || !EXTENSION_ID) {
      setStatus("unsupported");
      return;
    }

    let settled = false;
    let port;

    function settle(next) {
      if (settled) return;
      settled = true;
      setStatus(next);
      try {
        port?.disconnect();
      } catch {
        // already gone
      }
    }

    // Chrome resolves a connect() to an absent extension asynchronously via onDisconnect, but a
    // present-and-wedged one may never answer either, so the timeout is the backstop.
    const timeoutId = setTimeout(() => settle("missing"), PROBE_TIMEOUT_MS);

    try {
      port = window.chrome.runtime.connect(EXTENSION_ID, { name: "examguard-probe" });
    } catch {
      clearTimeout(timeoutId);
      setStatus("missing");
      return;
    }

    port.onMessage.addListener((message) => {
      if (message?.type === "PONG" || message?.type === "INIT_ACK") settle("installed");
    });
    port.onDisconnect.addListener(() => settle("missing"));

    try {
      port.postMessage({ type: "PING" });
    } catch {
      settle("missing");
    }

    return () => {
      settled = true;
      clearTimeout(timeoutId);
      try {
        port?.disconnect();
      } catch {
        // already gone
      }
    };
  }, [attempt]);

  return { status, recheck };
}
