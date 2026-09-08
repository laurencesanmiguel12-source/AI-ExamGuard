import { Puzzle, Download, RefreshCw, CheckCircle2, MonitorSmartphone } from "lucide-react";
import Card from "./ui/Card";
import { EXTENSION_STORE_URL } from "../constants/extension";

// Shown on the student dashboard whenever the extension is not answering. It stays put rather
// than being dismissible: unlike the face-enrolment modal there is no server-side gate behind it
// (start_exam never checks for the extension), so if this is dismissed the student finds out at
// the extension-check screen with the clock already running.
export default function ExtensionInstallCard({ status, onRecheck }) {
  if (status === "checking" || status === "installed") return null;

  const unsupported = status === "unsupported";

  return (
    <Card
      className={`mb-6 p-5 ${
        unsupported ? "border-border bg-secondary/60" : "border-blue-200 bg-blue-50"
      }`}
    >
      <div className="flex flex-wrap items-center gap-4">
        <div className="shrink-0">
          {unsupported ? (
            <MonitorSmartphone className="h-5 w-5 text-muted-foreground" />
          ) : (
            <Puzzle className="h-5 w-5 text-blue-700" />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-foreground">
            {unsupported
              ? "Use Google Chrome for your exams"
              : "Install the browser extension before your first exam"}
          </p>
          <p className="mt-0.5 text-sm text-muted-foreground">
            {unsupported
              ? "The Tab Monitor extension only runs on Chrome, and your exam cannot start without it. Sign in again from Chrome when it is time to sit your exam."
              : "Your exams check for the Tab Monitor extension before they start. Installing it now takes a few seconds — doing it with the exam clock already running does not."}
          </p>
        </div>
        {!unsupported && (
          <div className="flex shrink-0 flex-wrap items-center gap-2">
            <a
              href={EXTENSION_STORE_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 rounded-xl bg-primary px-4 py-2 text-[11px] font-mono uppercase tracking-wider text-white transition-colors hover:bg-primary/90"
            >
              <Download className="h-3.5 w-3.5" aria-hidden="true" /> Get the extension
            </a>
            <button
              onClick={onRecheck}
              className="inline-flex items-center gap-1.5 rounded-xl border border-border px-3 py-2 text-[11px] font-mono uppercase tracking-wider text-muted-foreground transition-colors hover:text-foreground"
            >
              <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" /> I've installed it
            </button>
          </div>
        )}
      </div>
    </Card>
  );
}

// The reassuring counterpart, for the sidebar status card - a student who did install it should
// be able to see that it worked, otherwise the only feedback the feature ever gives is nagging.
export function ExtensionStatusRow({ status }) {
  const installed = status === "installed";
  const label = {
    checking: "Checking…",
    installed: "Extension installed",
    missing: "Extension not installed",
    unsupported: "Chrome required",
  }[status];

  return (
    <div className="flex items-center gap-2">
      {installed ? (
        <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-700" aria-hidden="true" />
      ) : (
        <Puzzle className="h-3.5 w-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
      )}
      <span className={`text-[11px] font-mono ${installed ? "text-emerald-700" : "text-muted-foreground"}`}>
        {label}
      </span>
    </div>
  );
}
