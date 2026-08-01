// Pure matching logic, no chrome.* dependency - keeps this independently testable
// (see training/../verify_blocklist.mjs-style scripts) without a browser.
//
// Every hostname listed here also needs a matching entry in manifest.json's host_permissions -
// captureVisibleTab (background.js's evidence-screenshot capture) only works without a user
// gesture if the extension has host permission for that specific site. JSON can't hold this
// comment next to the list it's about, so it lives here instead - keep both in sync by hand.

export const BLOCKLIST = [
  { category: "SEARCH_ENGINE", hostnames: ["www.google.com", "google.com"], pathPrefix: "/search" },
  { category: "SEARCH_ENGINE", hostnames: ["www.bing.com", "bing.com"], pathPrefix: "/search" },
  { category: "AI_TOOL", hostnames: ["chatgpt.com", "chat.openai.com"] },
  { category: "AI_TOOL", hostnames: ["gemini.google.com", "bard.google.com"] },
  { category: "AI_TOOL", hostnames: ["claude.ai"] },
  { category: "AI_TOOL", hostnames: ["perplexity.ai", "www.perplexity.ai"] },
  { category: "AI_TOOL", hostnames: ["you.com"] },
  { category: "AI_TOOL", hostnames: ["poe.com"] },
  { category: "AI_TOOL", hostnames: ["copilot.microsoft.com"] },
  { category: "AI_TOOL", hostnames: ["meta.ai"] },
];

export function matchDomain(url) {
  let parsed;
  try {
    parsed = new URL(url);
  } catch {
    return null;
  }
  const host = parsed.hostname.toLowerCase();
  for (const entry of BLOCKLIST) {
    if (!entry.hostnames.includes(host)) continue;
    if (entry.pathPrefix && !parsed.pathname.startsWith(entry.pathPrefix)) continue;
    return { category: entry.category, domain: host };
  }
  return null;
}
