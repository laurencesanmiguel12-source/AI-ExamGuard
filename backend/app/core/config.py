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