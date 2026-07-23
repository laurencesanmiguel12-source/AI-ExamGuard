import { useEffect } from "react";
import { logViolation } from "../api/violations";

const THROTTLE_MS = 3000;

export default function useProctoring(sessionId, active, onEvent) {
  useEffect(() => {
    if (!active || !sessionId) return;

    const lastLogged = {};

    function log(eventType) {
      const now = Date.now();
      if (lastLogged[eventType] && now - lastLogged[eventType] < THROTTLE_MS) return;
      lastLogged[eventType] = now;
      onEvent?.(eventType);
      logViolation(sessionId, eventType).catch(() => {});
    }

    function onVisibilityChange() {
      if (document.hidden) log("TAB_SWITCH");
    }
    function onFullscreenChange() {
      if (!document.fullscreenElement) log("FULLSCREEN_EXIT");
    }
    function onCopyPaste() {
      log("COPY_PASTE");
    }
    function onContextMenu() {
      log("RIGHT_CLICK");
    }

    document.addEventListener("visibilitychange", onVisibilityChange);
    document.addEventListener("fullscreenchange", onFullscreenChange);
    document.addEventListener("copy", onCopyPaste);
    document.addEventListener("paste", onCopyPaste);
    document.addEventListener("cut", onCopyPaste);
    document.addEventListener("contextmenu", onContextMenu);

    return () => {
      document.removeEventListener("visibilitychange", onVisibilityChange);
      document.removeEventListener("fullscreenchange", onFullscreenChange);
      document.removeEventListener("copy", onCopyPaste);
      document.removeEventListener("paste", onCopyPaste);
      document.removeEventListener("cut", onCopyPaste);
      document.removeEventListener("contextmenu", onContextMenu);
    };
  }, [sessionId, active]);
}
