import { matchDomain } from "./blocklist.js";

const EXPECTED_ORIGIN = "https://scholarship-eat-mathematics-corrected.trycloudflare.com";

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

// Evidence for AI_TOOL_DETECTED/SEARCH_ENGINE_DETECTED - a screenshot of the offending tab at
// the moment it's detected. captureVisibleTab can only capture whichever tab is currently the
// ACTIVE tab of its window (there's no way to screenshot a background tab), so this is best-effort:
// null whenever the matched navigation happened in a tab that wasn't the visible one, or the
// capture otherwise fails (permission not granted for that host, tab closed mid-capture, etc.) -
// the violation still gets reported either way, just without a screenshot attached that time.
async function captureEvidenceScreenshot(tabId) {
  try {
    const tab = await chrome.tabs.get(tabId);
    if (!tab.active) return null;
    // jpeg, not the captureVisibleTab default of png - matches the backend's evidence storage/
    // serving code, which assumes .jpg/image/jpeg for every violation type's evidence uniformly.
    return await chrome.tabs.captureVisibleTab(tab.windowId, { format: "jpeg", quality: 80 });
  } catch {
    return null;
  }
}

chrome.webNavigation.onCommitted.addListener((details) => {
  if (details.frameId !== 0) return; // top-frame navigations only
  if (ports.size === 0) return; // no active exam session watching

  const match = matchDomain(details.url);
  if (!match) return;

  captureEvidenceScreenshot(details.tabId).then((screenshot) => {
    broadcast({
      type: "SITE_DETECTED",
      category: match.category,
      domain: match.domain,
      detectedAt: Date.now(),
      screenshot, // data URL (image/jpeg) or null - see captureEvidenceScreenshot's docstring
    });
  });
});
