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