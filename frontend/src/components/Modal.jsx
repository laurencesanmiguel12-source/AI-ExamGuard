import { useEffect, useId, useRef } from "react";
import { X } from "lucide-react";

// Every dialog in the app renders through here (edit forms on each list page, and every delete
// confirmation via ConfirmDialog), so the accessibility work belongs in this one component rather
// than being repeated - or forgotten - per caller.
export default function Modal({ title, onClose, children }) {
  const titleId = useId();
  const panelRef = useRef(null);

  // Callers write onClose={() => setEditing(null)}, so `onClose` is a NEW function on every
  // render. Held in a ref, the setup effect below can depend on nothing and still call the
  // current one - see the comment on that effect for why this matters so much.
  const onCloseRef = useRef(onClose);
  useEffect(() => {
    onCloseRef.current = onClose;
  });

  // Runs ONCE per dialog, deliberately - the dependency array must stay empty.
  //
  // This effect used to depend on [onClose]. Because that prop is a fresh arrow function each
  // render, the effect tore down and re-ran on every single keystroke inside a form: the cleanup
  // restored focus to whatever was focused before the dialog opened, and the setup then called
  // panelRef.focus(), moving focus off the input and onto the dialog container. Typing a name
  // therefore accepted one character and dropped the caret - reported from the defense panel as
  // "cannot type continuously". Focusing the panel is correct on OPEN and wrong at any other
  // time, so it must not be tied to a prop that changes.
  useEffect(() => {
    // Remember what was focused so it can be restored on close - otherwise a keyboard user is
    // dumped back at the top of the document every time they dismiss a dialog.
    const previouslyFocused = document.activeElement;

    // Move focus into the dialog. Without this, focus stays behind on the page and a screen
    // reader never announces that a dialog opened.
    panelRef.current?.focus();

    function onKeyDown(event) {
      if (event.key === "Escape") {
        // A dialog rendered without onClose is a deliberate gate (the biometric consent step),
        // not an oversight. Calling the missing handler threw a TypeError and left the dialog
        // open, so Escape did nothing visible and broke the page underneath it.
        if (!onCloseRef.current) return;
        event.stopPropagation();
        onCloseRef.current();
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    // A dialog taller than the window used to be genuinely unusable, reported from the defense
    // panel as "cannot be scrolled and closed" - and it was both. The panel had no height limit
    // and nothing scrolled, so a long form (Add Exam is ten fields) simply overflowed past the
    // top and bottom of a centred, position-fixed box: the submit button was unreachable below
    // the fold and the X was off-screen ABOVE it, because vertical centring pushes the header
    // out of view once the panel outgrows the viewport. Escape still worked, which is why it
    // read as "broken" rather than "stuck" - the only way out was a key nobody thinks to press.
    //
    // Three things fix it together: the panel is capped at the viewport, the header and footer
    // stay put while only the body scrolls (so the close button is always reachable), and the
    // backdrop itself scrolls as a last resort on very short windows.
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 p-4 sm:items-center">
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className="my-auto flex max-h-[calc(100vh-2rem)] w-full max-w-md flex-col rounded-xl border border-border bg-card shadow-lg outline-none"
      >
        <div className="flex shrink-0 items-center justify-between border-b border-border px-5 py-4">
          <h3 id={titleId} className="font-display font-bold text-lg text-foreground">{title}</h3>
          {/* Rendered only when there is something for it to do. With no onClose it was a close
              button that visibly did nothing - worse than no button, because it says the dialog
              can be dismissed and then refuses. */}
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              aria-label="Close dialog"
              className="text-muted-foreground hover:text-foreground"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto p-5">{children}</div>
      </div>
    </div>
  );
}
