"""Deploy-prep helper: the Chrome extension hardcodes the frontend's origin in two places -
extension/background.js's EXPECTED_ORIGIN (checked against chrome.runtime.onConnectExternal's
sender.origin, so the extension only accepts connections from the real app) and
extension/manifest.json's externally_connectable.matches (Chrome's own allowlist, enforced before
the extension's JS even runs). Both need to match whatever the frontend's real deploy origin ends
up being (e.g. a Cloudflare Pages URL), or the Tab Monitor extension silently refuses to connect.

This only touches those two files - the backend's ALLOWED_ORIGINS (backend/.env) and the frontend's
VITE_API_BASE_URL (frontend/.env) are separate env vars, not something a static Chrome extension
manifest can read at runtime, so this script prints a reminder for those rather than touching them.

Usage: python scripts/set_deploy_origin.py https://examguard.pages.dev
       (idempotent - safe to rerun with a new origin, or the same one twice)
"""
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKGROUND_JS = REPO_ROOT / "extension" / "background.js"
MANIFEST_JSON = REPO_ROOT / "extension" / "manifest.json"

ORIGIN_RE = re.compile(r'const EXPECTED_ORIGIN = "[^"]*";')
MATCHES_RE = re.compile(r'("matches":\s*)\[[^\]]*\]')


def update_background_js(origin: str) -> bool:
    text = BACKGROUND_JS.read_text(encoding="utf-8")
    new_text, count = ORIGIN_RE.subn(f'const EXPECTED_ORIGIN = "{origin}";', text)
    if count != 1:
        raise SystemExit(
            f"Expected exactly one EXPECTED_ORIGIN declaration in {BACKGROUND_JS}, found {count} - "
            "the file may have changed shape, check it by hand."
        )
    changed = new_text != text
    BACKGROUND_JS.write_text(new_text, encoding="utf-8")
    return changed


def update_manifest(origin: str) -> bool:
    """Surgical regex replace rather than json.load/dump, so an unrelated re-serialization doesn't
    reformat the whole file (different key order, indentation, single- vs multi-line arrays) and
    bury the one real change in diff noise."""
    text = MANIFEST_JSON.read_text(encoding="utf-8")
    # validate the file is still well-formed JSON with the shape this script assumes, before touching it
    manifest = json.loads(text)
    if "matches" not in manifest.get("externally_connectable", {}):
        raise SystemExit(f"{MANIFEST_JSON} has no externally_connectable.matches - check it by hand.")

    new_text, count = MATCHES_RE.subn(rf'\1["{origin}/*"]', text)
    if count != 1:
        raise SystemExit(f"Expected exactly one \"matches\" array in {MANIFEST_JSON}, found {count}.")
    changed = new_text != text
    MANIFEST_JSON.write_text(new_text, encoding="utf-8")
    return changed


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/set_deploy_origin.py <origin, e.g. https://examguard.pages.dev>")
    origin = sys.argv[1].rstrip("/")
    if not re.match(r"^https?://[^/]+$", origin):
        raise SystemExit(f"'{origin}' doesn't look like a bare origin (scheme://host[:port], no path) - check it")

    js_changed = update_background_js(origin)
    manifest_changed = update_manifest(origin)

    print(f"extension/background.js EXPECTED_ORIGIN -> {origin} ({'changed' if js_changed else 'already set'})")
    print(f"extension/manifest.json matches -> [\"{origin}/*\"] ({'changed' if manifest_changed else 'already set'})")
    print(
        "\nReminder - this script doesn't touch these, set them by hand:\n"
        f"  backend/.env: ALLOWED_ORIGINS={origin}\n"
        f"  frontend/.env (before `vite build`): VITE_API_BASE_URL=<the backend's real URL, not this one>\n"
        "  Reload the unpacked extension in chrome://extensions after this change."
    )


if __name__ == "__main__":
    main()
