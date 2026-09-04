import { useEffect, useId, useRef } from "react";
import { X } from "lucide-react";

// Every dialog in the app renders through here (edit forms on each list page, and every delete
// confirmation via ConfirmDialog), so the accessibility work belongs in this one component rather
// than being repeated - or forgotten - per caller.
export default function Modal({ title, onClose, children }) {
  const titleId = useId();
  const panelRef = useRef(null);

  useEffect(() => {
    // Remember what was focused so it can be restored on close - otherwise a keyboard user is
    // dumped back at the top of the document every time they dismiss a dialog.
    const previouslyFocused = document.activeElement;

    // Move focus into the dialog. Without this, focus stays behind on the page and a screen
    // reader never announces that a dialog opened.
    panelRef.current?.focus();

    function onKeyDown(event) {
      if (event.key === "Escape") {
        event.stopPropagation();
        onClose();
        return;
      }

      if (event.key !== "Tab") return;

      // Focus trap: Tab must cycle within the dialog. Queried on each keypress rather than once
      // on mount because these dialogs contain forms whose focusable contents change (fields
      // disabling while a delete is in flight, validation errors appearing).
      const focusables = panelRef.current?.querySelectorAll(
        'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      );
      if (!focusables || focusables.length === 0) return;

      const first = focusables[0];
      const last = focusables[focusables.length - 1];

      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", onKeyDown, true);
    return () => {
      document.removeEventListener("keydown", onKeyDown, true);
      if (previouslyFocused instanceof HTMLElement) previouslyFocused.focus();
    };
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className="w-full max-w-md bg-card border border-border rounded-xl shadow-lg outline-none"
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h3 id={titleId} className="font-display font-bold text-lg text-foreground">{title}</h3>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close dialog"
            className="text-muted-foreground hover:text-foreground"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}
