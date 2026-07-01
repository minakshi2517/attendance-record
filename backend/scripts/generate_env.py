"""Generate .env and apply admin credentials. Run once after install or to rotate secrets."""
import secrets
import string
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = BACKEND_DIR / ".env"
CREDS_PATH = BACKEND_DIR / "ADMIN_CREDENTIALS.local.txt"


def _password(length: int = 24) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(c.islower() for c in pwd)
            and any(c.isupper() for c in pwd)
            and any(c.isdigit() for c in pwd)
            and any(c in "!@#$%^&*" for c in pwd)
        ):
            return pwd


def main() -> None:
  force = "--force" in sys.argv
  if ENV_PATH.exists() and not force:
    print(f".env already exists at {ENV_PATH}")
    print("Use --force to regenerate (this rotates secrets and admin password).")
    return

  username = f"ananta_mgr_{secrets.token_hex(3)}"
  password = _password()
  secret_key = secrets.token_urlsafe(48)
  setup_key = secrets.token_urlsafe(32)

  env_content = f"""# Auto-generated — do NOT commit to git
DATABASE_URL=sqlite:///./attendance.db
SECRET_KEY={secret_key}
SETUP_KEY={setup_key}
DEFAULT_ADMIN_USER={username}
DEFAULT_ADMIN_PASSWORD={password}
DEFAULT_ADMIN_EMAIL=admin@ananta.local
ALLOWED_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
ACCESS_TOKEN_EXPIRE_MINUTES=480
"""

  creds_content = f"""ATTENDANCE SYSTEM — ADMIN CREDENTIALS (keep private, delete after saving elsewhere)
Generated: run generate_env.py

Username: {username}
Password: {password}

Setup API key (first-time /api/auth/setup only): {setup_key}
"""

  ENV_PATH.write_text(env_content, encoding="utf-8")
  CREDS_PATH.write_text(creds_content, encoding="utf-8")
  print(f"Wrote {ENV_PATH}")
  print(f"Wrote {CREDS_PATH}")
  print()
  print("Login credentials:")
  print(f"  Username: {username}")
  print(f"  Password: {password}")


if __name__ == "__main__":
  main()
