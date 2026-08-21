// Synthesized via Web Audio API rather than a shipped audio file - self-hosted/no external asset,
// same "don't depend on a third party being reachable" instinct as this project's MediaPipe WASM
// being committed rather than loaded from Google's CDN. A two-tone chime (short bell-like blip),
// not a raw beep.
let audioCtx = null;

function getContext() {
  if (!audioCtx) {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    audioCtx = new AudioContextClass();
  }
  // Browsers suspend a newly-created AudioContext until a user gesture - by the time this fires
  // (a live-monitor poll, well after the instructor has clicked into the dashboard) that gesture
  // has already happened, but resume() is a harmless no-op if it's already running.
  if (audioCtx.state === "suspended") {
    audioCtx.resume().catch(() => {});
  }
  return audioCtx;
}

function tone(ctx, frequency, startTime, duration) {
  const oscillator = ctx.createOscillator();
  const gain = ctx.createGain();
  oscillator.type = "sine";
  oscillator.frequency.value = frequency;
  gain.gain.setValueAtTime(0.001, startTime);
  gain.gain.exponentialRampToValueAtTime(0.2, startTime + 0.02);
  gain.gain.exponentialRampToValueAtTime(0.001, startTime + duration);
  oscillator.connect(gain);
  gain.connect(ctx.destination);
  oscillator.start(startTime);
  oscillator.stop(startTime + duration);
}

export function playNotificationChime() {
  try {
    const ctx = getContext();
    const now = ctx.currentTime;
    tone(ctx, 880, now, 0.15);
    tone(ctx, 1320, now + 0.12, 0.18);
  } catch {
    // Web Audio unsupported/blocked - silently skip. Never let a notification sound break the
    // live monitor itself.
  }
}
