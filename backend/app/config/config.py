import os
import secrets
from dotenv import load_dotenv

load_dotenv()


class Config:
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")

    ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
    IS_PRODUCTION = ENVIRONMENT == "production"
    IS_TEST = ENVIRONMENT == "test"

    # DEMO_MODE explicitly gates fake/mock evaluation results. Must be off in production.
    DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    if not JWT_SECRET_KEY:
        if IS_PRODUCTION:
            raise RuntimeError(
                "JWT_SECRET_KEY must be set via environment variable when ENVIRONMENT=production."
            )
        # Dev convenience only: ephemeral secret regenerated on every restart, so
        # existing tokens/sessions won't survive a reload. Set JWT_SECRET_KEY in
        # backend/.env for a stable secret during local development.
        JWT_SECRET_KEY = secrets.token_hex(32)
        print(
            "WARNING: JWT_SECRET_KEY not set in environment. Using an ephemeral "
            "development secret (tokens will be invalidated on restart). "
            "Set JWT_SECRET_KEY in backend/.env."
        )

    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    JWT_ALGORITHM = "HS256"

    _default_cors = "http://localhost:5173,http://localhost:5174,http://localhost:5175"
    CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", _default_cors).split(",")
        if origin.strip()
    ]

    # Public base URL used to build canonical/OG URLs and the sitemap (this backend's own origin).
    PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")

    # Where the "Apply" CTA on a public job page sends candidates (the React SPA).
    FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")

    # --- MongoDB ---
    # Required (no default) in production; a local mongod default is used in
    # development purely so `uvicorn main:app` boots without extra setup.
    MONGODB_URI = os.getenv("MONGODB_URI")
    if not MONGODB_URI:
        if IS_PRODUCTION:
            raise RuntimeError("MONGODB_URI must be set via environment variable when ENVIRONMENT=production.")
        MONGODB_URI = "mongodb://localhost:27017"

    MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "signaxai")
    MONGODB_TEST_DATABASE = os.getenv("MONGODB_TEST_DATABASE", "signaxai_test")

    # --- SMTP (password-reset OTP emails) ---
    # If SMTP_HOST is unset, emails are not sent — in development the OTP is
    # logged instead so the flow stays testable; in production this just means
    # no email goes out (still logged server-side as an error), never a crash.
    SMTP_HOST = os.getenv("SMTP_HOST")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", SMTP_USER)
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    # --- Password reset OTP ---
    PASSWORD_RESET_OTP_EXPIRE_MINUTES = int(os.getenv("PASSWORD_RESET_OTP_EXPIRE_MINUTES", "10"))
    PASSWORD_RESET_COOLDOWN_SECONDS = int(os.getenv("PASSWORD_RESET_COOLDOWN_SECONDS", "60"))
    PASSWORD_RESET_MAX_ATTEMPTS = int(os.getenv("PASSWORD_RESET_MAX_ATTEMPTS", "5"))

    # --- GitHub OAuth ("Continue with GitHub" + verified-repo-ownership gate) ---
    # A separate app/credential from GITHUB_TOKEN above — that one is a personal
    # access token used server-side for repo analysis; this is a registered
    # OAuth App used to verify a candidate's real GitHub identity.
    # Create one at https://github.com/settings/developers — callback URL must
    # exactly match GITHUB_OAUTH_REDIRECT_URI below.
    GITHUB_OAUTH_CLIENT_ID = os.getenv("GITHUB_OAUTH_CLIENT_ID")
    GITHUB_OAUTH_CLIENT_SECRET = os.getenv("GITHUB_OAUTH_CLIENT_SECRET")
    GITHUB_OAUTH_REDIRECT_URI = os.getenv("GITHUB_OAUTH_REDIRECT_URI", f"{PUBLIC_BASE_URL}/auth/github/callback")
    GITHUB_OAUTH_STATE_EXPIRE_MINUTES = int(os.getenv("GITHUB_OAUTH_STATE_EXPIRE_MINUTES", "10"))

    # Second factor required after GitHub identifies the account, before the
    # login/signup/link is actually completed — closes the "someone else is
    # using my already-authenticated laptop/GitHub session" gap that GitHub
    # OAuth alone doesn't cover.
    GITHUB_OTP_EXPIRE_MINUTES = int(os.getenv("GITHUB_OTP_EXPIRE_MINUTES", "10"))
    GITHUB_OTP_MAX_ATTEMPTS = int(os.getenv("GITHUB_OTP_MAX_ATTEMPTS", "5"))
    # Attempts allowed at the "type the email connected to your GitHub
    # account" step that gates the OTP being sent at all.
    GITHUB_EMAIL_CONFIRM_MAX_ATTEMPTS = int(os.getenv("GITHUB_EMAIL_CONFIRM_MAX_ATTEMPTS", "5"))

    @property
    def GITHUB_OAUTH_CONFIGURED(self) -> bool:
        return bool(self.GITHUB_OAUTH_CLIENT_ID and self.GITHUB_OAUTH_CLIENT_SECRET)

    # --- Codeforces (competitive-programming signal) ---
    # Create at https://codeforces.com/settings/api — issued as a KEY + SECRET
    # pair together. Public user data (rating, solved problems) works without
    # these too; they're only needed to sign a request per codeforces.com/apiHelp
    # so it isn't rate-limited as an anonymous caller.
    CODEFORCES_API_KEY = os.getenv("CODEFORCES_API_KEY")
    CODEFORCES_API_SECRET = os.getenv("CODEFORCES_API_SECRET")

    @property
    def CODEFORCES_API_CONFIGURED(self) -> bool:
        return bool(self.CODEFORCES_API_KEY and self.CODEFORCES_API_SECRET)

    @property
    def MONGODB_ACTIVE_DATABASE(self) -> str:
        # Belt-and-suspenders: tests always use MONGODB_TEST_DATABASE, even if a
        # caller forgets to override MONGODB_DATABASE explicitly, so a test run
        # can never accidentally write into the real database.
        return self.MONGODB_TEST_DATABASE if self.IS_TEST else self.MONGODB_DATABASE


config = Config()
