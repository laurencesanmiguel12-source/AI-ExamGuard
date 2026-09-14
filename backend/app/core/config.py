from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    # Comma-separated list, e.g. "https://examguard.pages.dev,https://api.example.com" - kept as a
    # single string (not list[str]) so a plain unquoted value in .env parses without pydantic-settings'
    # JSON-decoding rules for complex env types.
    ALLOWED_ORIGINS: str = "http://localhost:5173"

    # Outbound email, used only to tell platform admins a school is waiting for review. Every
    # field is optional and empty by default: with no SMTP_HOST the app sends nothing at all and
    # simply logs what it would have sent, so a fresh clone and the test suite need no mail
    # server. Notifications are best-effort either way - see NotificationService.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    # Envelope sender. Falls back to SMTP_USERNAME when unset, which is what most providers
    # require anyway (they reject a From: that isn't the authenticated account).
    SMTP_FROM: str = ""
    # Where school-approval alerts go. Comma-separated. If empty, every super_admin account's own
    # email address is used instead, so this normally needs no configuration.
    PLATFORM_NOTIFY_EMAILS: str = ""
    # Used to build the "review it here" link in the notification body.
    FRONTEND_BASE_URL: str = "http://localhost:5173"

    # How many face-check/object-check inferences may run at once (main.py hands this to anyio's
    # thread limiter, whose own default of 40 is far too high here - each inference thread lazily
    # builds its OWN copy of the three YOLO models plus a YuNet detector, since none of them are
    # thread-safe; see object_detection_service.py).
    #
    # 2, not a core count, and this is measured rather than assumed: sweeping 2/4/8 at 10
    # concurrent students changed aggregate throughput by nothing at all (10.7 / 10.7 / 10.9
    # req/s), because ultralytics and OpenCV already parallelize a SINGLE inference across every
    # core - a second concurrent inference just splits the same CPU rather than adding capacity.
    # So extra threads buy no throughput and cost real memory (1.74GB RSS at 2, 2.19GB at 8).
    # What the threadpool actually buys is keeping the event loop free, which one spare thread
    # already achieves. Re-measure on the real deploy host with backend/loadtest/ before changing.
    INFERENCE_THREADS: int = 2

    # Build the YOLO models during startup instead of on the first student's first poll. See
    # ObjectDetectionService.prewarm for the 45.6s that otherwise lands on whoever starts first.
    #
    # Off in the test suite, which creates a TestClient - and therefore runs this lifespan - once
    # per test: 300-odd tests that never touch inference would each rebuild three models. The
    # suite sets it via the environment in conftest rather than the production default moving.
    PREWARM_INFERENCE: bool = True

    # How often the person-COUNT model runs, in polls. 1 = every frame, as it always did.
    #
    # The whole cost of the base yolov8s model is a person count: 58% of a frame's inference on
    # the deploy host (498ms of 861ms), measured 2026-09-08. Two cheaper ways to get that count
    # were measured on 2026-09-14 and both failed on real evidence frames:
    #
    #   * yolov8n-pose, which already runs on nearly every frame and is a person model, disagreed
    #     with yolov8s on the >1 decision in 2 of 29 frames - in both directions.
    #   * the same weights at imgsz=512 lost a genuine second person in 2 of 15 frames; at 416
    #     and 320, 4 of 15. The second person in these frames is a hand or forearm at the edge,
    #     which is exactly what a lower input resolution throws away first.
    #
    # So the count is not made cheaper - it is taken less often, which is what its timescale
    # actually calls for. A phone is glanced at for a second and needs a fast sample rate; a
    # second person in the room is there for minutes. On polls where it is skipped the previous
    # count is reported and the MULTIPLE_PEOPLE episode is left untouched, so nothing is decided
    # from a frame that was never examined.
    #
    # The cost is detection latency, and it is paid in POLLS, so the wall-clock figure depends on
    # the frontend's CAPTURE_INTERVAL_MS rather than on anything here. At its current 5s a second
    # person is noticed up to (N-1)=2 polls later than before - 10s of added delay, 15s worst case
    # from the moment they appear. That is the trade: someone leaning in to help is present for
    # minutes, a phone is glanced at for a second, and only the phone detector still runs on every
    # frame. Re-read this number if CAPTURE_INTERVAL_MS moves; set to 1 to restore per-frame
    # counting.
    PERSON_COUNT_EVERY_N_POLLS: int = 3

    model_config = SettingsConfigDict(env_file=".env")

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    @property
    def platform_notify_list(self) -> list[str]:
        return [e.strip() for e in self.PLATFORM_NOTIFY_EMAILS.split(",") if e.strip()]

    @property
    def email_enabled(self) -> bool:
        return bool(self.SMTP_HOST.strip())


settings = Settings()