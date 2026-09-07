// How long the same violation type stays quiet after it has interrupted the student once.
export const VIOLATION_ALERT_COOLDOWN_MS = 30000;

/**
 * Decides whether a violation should interrupt the student right now.
 *
 * Pure, and kept out of ExamRoom deliberately - the same reason the backend keeps
 * _record_candidate separate from the model call. This is the rule that stops the feature being
 * actively harmful: the object check polls every few seconds, so a phone left in view would
 * otherwise reopen the modal continuously and make the exam impossible to sit, which is the exact
 * opposite of what warning the student is for. Testing it here means a regression shows up as a
 * failing assertion rather than as an unusable exam.
 *
 * Mutates `lastShown` in place when it returns true, so the caller can hold it in a ref.
 */
export function shouldRaiseAlert(lastShown, eventType, now, cooldownMs = VIOLATION_ALERT_COOLDOWN_MS) {
  const previous = lastShown[eventType];
  if (previous !== undefined && now - previous < cooldownMs) return false;
  lastShown[eventType] = now;
  return true;
}
