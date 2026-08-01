# Chrome Web Store listing copy

Copy-paste source for the Developer Dashboard fields when submitting. Nothing here is
auto-published anywhere - it's just prepared text.

## Short description (max 132 characters)

```
Detects AI-tool and search-engine tab use during AI ExamGuard proctored exams and reports it to your instructor.
```
(114 characters)

## Detailed description

```
AI-ExamGuard Tab Monitor is the companion browser extension for AI ExamGuard, an academic exam
proctoring system. It only does anything while you have an AI ExamGuard exam open in another tab.

WHAT IT DOES
While a proctored exam is in progress, this extension watches for tab navigation to a small,
fixed list of AI chatbots (ChatGPT, Claude, Gemini, Copilot, Perplexity, and similar) and search
engines (Google, Bing) in ANY of your open tabs - not just the exam tab. If you navigate to one of
these sites, it reports the site category and a timestamp to your active exam session, and takes a
screenshot of that tab as evidence if it happens to be the tab you're currently viewing at that
moment.

WHAT IT DOES NOT DO
- It does not monitor your browsing at all outside of an active AI ExamGuard exam session.
- It does not read page content, keystrokes, or form data on any site.
- It does not block or close tabs - it only detects and reports.
- It does not send any data anywhere except the specific AI ExamGuard exam page you're taking the
  exam on (verified by origin before any connection is accepted).
- It has no visibility into any site outside its fixed monitored list.

PERMISSIONS, EXPLAINED
- tabs / webNavigation: needed to detect which site a browser tab has navigated to.
- Host permissions for the specific monitored sites only (not "all sites"): needed to capture an
  evidence screenshot of one of those tabs at the moment it's detected. No permission is requested
  for any site outside the fixed monitored list.

WHO THIS IS FOR
Students at institutions using AI ExamGuard for proctored online exams. Installing this without an
active AI ExamGuard exam does nothing - the extension is inert until an exam page connects to it.
```

## Category

Education (or Productivity, if Education isn't accepted for this listing type)

## Privacy policy

See PRIVACY_POLICY.md in this same folder - needs to be hosted somewhere with a stable public URL
(GitHub Pages, a hosted static page, etc.) before the Developer Dashboard will accept the listing;
it requires an actual reachable URL, not a pasted document.

## Screenshots (1280x800 or 640x400, at least one required)

`screenshots/screenshot1.png` - real capture from a live exam session (not a mockup), cropped/
resized to the required 1280x800 from the original. Shows the exam in progress with the AI
Monitor panel and Detection Status row (Face Detected / Phone / Tab Focus / Tab Monitor, all OK),
which is the extension's actual effect visible in context. More screenshots can be added the same
way (crop to 1.6:1 first, then resize to exactly 1280x800 or 640x400 - stretching without cropping
distorts the image).

## Known gotcha before submitting

manifest.json currently has a "key" field, which fixes this extension's ID
(ippkohhninlboeifildoaaehgjpdhgde) for local unpacked installs - frontend/.env's
VITE_EXTENSION_ID depends on this exact value. Whether the Chrome Web Store preserves this ID on
first publish or assigns its own depends on current Store behavior (not verified here - check at
submission time). If the published ID differs from the unpacked one, VITE_EXTENSION_ID needs
updating to match once the Store assigns a real ID, and every deployed frontend needs redeploying
with the new value before the published extension will actually connect to exam pages.
