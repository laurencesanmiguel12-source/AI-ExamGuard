import { useCallback, useEffect, useRef, useState } from "react";

const IDLE_TIMEOUT_MS = 10 * 60 * 1000;
const WARNING_BEFORE_MS = 60 * 1000;
const ACTIVITY_EVENTS = ["mousemove", "mousedown", "keydown", "touchstart", "scroll", "wheel"];

// Only mounted inside Layout.jsx, which take-exam/:examId and face-enrollment deliberately don't
// use (see App.jsx's route tree) - a student reading a long question or posing for enrollment
// captures without touching the mouse/keyboard for 10 minutes is normal, not "idle", and getting
// logged out mid-exam would lose their session outright. This only ever watches the
// logged-in-and-browsing surfaces (dashboards, admin/instructor management pages, results).
export default function useIdleLogout(onIdle) {
  const [warning, setWarning] = useState(false);
  const idleTimer = useRef(null);
  const warningTimer = useRef(null);

  // Read at fire-time via the ref, never as a dependency - useSchoolNav()'s navigate() is a new
  // function every render (confirmed - it's an unmemoized inline arrow function), so Layout's
  // onIdle prop changes identity on every navigation between sibling routes under the same
  // layout. Real bug found live: with onIdle as a scheduleTimers dependency, every such
  // navigation re-ran the mount effect and silently reset the whole countdown - confirmed via a
  // precise page-internal-timer test where the warning fired once but the actual logout never
  // did after a full un-reset wait. Capturing the latest callback in a ref instead means nothing
  // here depends on the caller's function identity at all.
  const onIdleRef = useRef(onIdle);
  onIdleRef.current = onIdle;

  const clearTimers = useCallback(() => {
    clearTimeout(idleTimer.current);
    clearTimeout(warningTimer.current);
  }, []);

  // Pure scheduling, no state writes - kept separate from handleActivity below so the
  // warning-pauses-ambient-listeners effect (which depends on `warning`) never fights itself by
  // having its own dependency change trigger a state write that flips it right back. Depends on
  // clearTimers only (stable, empty deps) - not on onIdle - so this itself stays stable forever.
  const scheduleTimers = useCallback(() => {
    clearTimers();
    warningTimer.current = setTimeout(() => setWarning(true), IDLE_TIMEOUT_MS - WARNING_BEFORE_MS);
    idleTimer.current = setTimeout(() => onIdleRef.current(), IDLE_TIMEOUT_MS);
  }, [clearTimers]);

  const handleActivity = useCallback(() => {
    setWarning(false);
    scheduleTimers();
  }, [scheduleTimers]);

  useEffect(() => {
    scheduleTimers();
    return clearTimers;
    // Intentionally empty - run exactly once on mount. scheduleTimers/clearTimers are stable
    // (see above), so this isn't actually suppressing a real dependency change, just documenting
    // that the effect itself is deliberately mount/unmount-only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    // Paused while the warning modal is showing - only its own "Stay logged in" button
    // (handleActivity, same function) can dismiss it, not a stray mousemove elsewhere.
    if (warning) return undefined;

    ACTIVITY_EVENTS.forEach((event) => window.addEventListener(event, handleActivity, { passive: true }));
    return () => {
      ACTIVITY_EVENTS.forEach((event) => window.removeEventListener(event, handleActivity));
    };
  }, [handleActivity, warning]);

  return { warning, stayLoggedIn: handleActivity };
}
