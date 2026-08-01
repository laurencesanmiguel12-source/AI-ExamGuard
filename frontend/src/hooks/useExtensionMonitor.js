import { useCallback, useEffect, useRef, useState } from "react";
import { logViolation } from "../api/violations";

const EXTENSION_ID = import.meta.env.VITE_EXTENSION_ID;
const CONNECT_TIMEOUT_MS = 1500;
const PING_INTERVAL_MS = 4000;
const THROTTLE_MS = 3000;

// Tracks whether the AI-ExamGuard Tab Monitor browser extension is installed and connected,
// and relays its SITE_DETECTED events into the existing violation-logging pipeline once armed.
// `active` keeps the port alive across the extension-check screen AND in-progress phase (so it
// isn't torn down/reconnected when the phase transitions); `armed` independently gates whether
// detected events actually get logged, via a ref so toggling it doesn't reconnect the port.
export default function useExtensionMonitor(sessionId, active, armed, onDetected) {
  const [status, setStatus] = useState("checking");
  const [attempt, setAttempt] = useState(0);
  const armedRef = useRef(armed);

  useEffect(() => {
    armedRef.current = armed;
  }, [armed]);

  const retry = useCallback(() => {
    setStatus("checking");
    setAttempt((a) => a + 1);
  }, []);

  useEffect(() => {
    if (!active || !sessionId) return;

    if (!window.chrome?.runtime?.connect || !EXTENSION_ID) {
      setStatus("unavailable");
      return;
    }

    let cancelled = false;
    let port;
    const lastLogged = {};

    function log(eventType, detail, screenshotDataUrl) {
      const now = Date.now();
      if (lastLogged[eventType] && now - lastLogged[eventType] < THROTTLE_MS) return;
      lastLogged[eventType] = now;
      onDetected?.(eventType, detail);
      if (armedRef.current) {
        // screenshotDataUrl is a data: URL straight from the extension's captureVisibleTab (or
        // null - see background.js) - fetch() against a data: URL is just a synchronous decode,
        // no network request, the standard way to turn one into a Blob for upload.
        const evidence = screenshotDataUrl
          ? fetch(screenshotDataUrl).then((r) => r.blob())
          : Promise.resolve(null);
        evidence
          .then((blob) => logViolation(sessionId, eventType, detail, blob))
          .catch(() => {});
      }
    }

    const timeoutId = setTimeout(() => {
      if (!cancelled) setStatus((s) => (s === "checking" ? "unavailable" : s));
    }, CONNECT_TIMEOUT_MS);

    try {
      port = window.chrome.runtime.connect(EXTENSION_ID, { name: "examguard-monitor" });
    } catch {
      if (!cancelled) setStatus("unavailable");
      return () => clearTimeout(timeoutId);
    }

    port.onMessage.addListener((message) => {
      if (!message || cancelled) return;
      if (message.type === "INIT_ACK") {
        setStatus("connected");
      } else if (message.type === "SITE_DETECTED") {
        const eventType =
          message.category === "AI_TOOL" ? "AI_TOOL_DETECTED" : "SEARCH_ENGINE_DETECTED";
        log(eventType, message.domain, message.screenshot);
      }
    });

    port.onDisconnect.addListener(() => {
      if (!cancelled) setStatus("unavailable");
    });

    port.postMessage({ type: "INIT", sessionId });

    const pingId = setInterval(() => {
      try {
        port.postMessage({ type: "PING" });
      } catch {
        // disconnected; onDisconnect above handles the status flip
      }
    }, PING_INTERVAL_MS);

    return () => {
      cancelled = true;
      clearTimeout(timeoutId);
      clearInterval(pingId);
      try {
        port.disconnect();
      } catch {
        // already disconnected
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, active, attempt]);

  return { status, retry };
}
