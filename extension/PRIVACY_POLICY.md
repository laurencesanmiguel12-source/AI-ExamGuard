# AI-ExamGuard Tab Monitor — Privacy Policy

*Last updated: 2026-08-01*

This policy covers the AI-ExamGuard Tab Monitor browser extension only, not the AI ExamGuard web
application itself.

## What the extension does

The extension is inert until it is connected to by an active AI ExamGuard exam page. Once
connected, for the duration of that exam session, it watches for browser tab navigation to a
fixed, small list of AI chatbot sites (e.g. ChatGPT, Claude, Gemini, Copilot, Perplexity) and
search engines (Google, Bing). When a match occurs, it reports:

- Which site category was visited (AI tool or search engine)
- The matched domain
- A timestamp
- A screenshot of that browser tab, **only** if it happened to be the tab currently visible on
  screen at the exact moment of detection (the extension has no ability to screenshot a background
  tab)

This information is sent only to the specific AI ExamGuard exam page the student is actively
taking an exam on. The extension verifies the origin of any page connecting to it before accepting
the connection, so no other website can request this data from the extension.

## What the extension does not do

- It does not operate outside of an active, connected AI ExamGuard exam session.
- It does not read page content, form inputs, keystrokes, or clipboard data on any site.
- It does not collect general browsing history - only navigation events matching its fixed
  monitored-site list are ever inspected or reported, and only while an exam session is active.
- It does not block, close, or modify any tab or page - detection only, no enforcement.
- It does not sell, share, or transmit any data to any third party. The only network communication
  it performs is reporting a detection event to the connected AI ExamGuard exam page itself.
- It does not use analytics, tracking, or advertising of any kind.

## Data retention

Detection events and any captured screenshots are stored by the AI ExamGuard application as part
of the exam session's violation record, subject to AI ExamGuard's own data retention policy
(evidence is retained for a bounded period and is deletable by an administrator). The extension
itself stores nothing locally beyond its in-memory connection state for the current browser
session.

## Permissions

- **tabs / webNavigation**: required to detect which site a tab has navigated to.
- **Host permissions**, scoped to the specific monitored sites listed above only (not all
  websites): required to capture an evidence screenshot of one of those tabs at the moment of
  detection. No permission is requested for, and no data is ever read from, any site outside this
  fixed list.

## Contact

Questions about this extension or this policy: aueteeap2026@gmail.com
