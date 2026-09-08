// The Chrome Web Store listing for the Tab Monitor extension.
//
// Centralised because this URL was pasted literally into Landing, InstructorDashboard and
// ExamRoom, and the student-facing prompts added alongside it would have made five copies of a
// string that has to change together with VITE_EXTENSION_ID - the id is *in* the URL, so a
// re-publish under a new id would otherwise leave some links pointing at a listing that no
// longer matches the extension the app probes for.
export const EXTENSION_STORE_URL =
  "https://chromewebstore.google.com/detail/ai-examguard-tab-monitor/gbkbkbcbbehpcoifmkenkjafkfbphmkf";

export const EXTENSION_NAME = "AI ExamGuard Tab Monitor";
