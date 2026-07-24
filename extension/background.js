import { matchDomain } from "./blocklist.js";

const EXPECTED_ORIGIN = "http://localhost:5173";

// Keyed by an incrementing id, not by sessionId - a student could have multiple exam tabs open.
const ports = new Map();
let nextPortId = 1;

function broadcast(message) {
  for (const { port } of ports.values()) {
    try {
      port.postMessage(message);
    } catch {
      // port likely already gone; onDisconnect will clean it up
    }
  }
}

chrome.runtime.onConnectExternal.addListener((port) => {
  if (port.sender?.origin && port.sender.origin !== EXPECTED_ORIGIN) {
    port.disconnect();
    return;
  }

  const portId = nextPortId++;
  ports.set(portId, { port, sessionId: null });

  port.onMessage.addListener((message) => {
    if (!message || typeof message !== "object") return;

    if (message.type === "INIT") {
      ports.set(portId, { port, sessionId: message.sessionId });
      port.postMessage({ type: "INIT_ACK", version: "0.1.0" });
    } else if (message.type === "PING") {
      port.postMessage({ type: "PONG", ts: Date.now() });
    }
  });

  port.onDisconnect.addListener(() => {
    ports.delete(portId);
  });
});

chrome.webNavigation.onCommitted.addListener((details) => {
  if (details.frameId !== 0) return; // top-frame navigations only
  if (ports.size === 0) return; // no active exam session watching

  const match = matchDomain(details.url);
  if (!match) return;

  broadcast({
    type: "SITE_DETECTED",
    category: match.category,
    domain: match.domain,
    detectedAt: Date.now(),
  });
});
