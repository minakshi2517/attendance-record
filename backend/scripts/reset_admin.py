"""Apply DEFAULT_ADMIN_* from .env to the database (create or update admin)."""
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app import models  # noqa: E402
from app.utils.auth_utils import hash_password  # noqa: E402


def main() -> None:
  db = SessionLocal()
  try:
    admin = db.query(models.Admin).order_by(models.Admin.id).first()
    hashed = hash_password(settings.DEFAULT_ADMIN_PASSWORD)

    if admin is None:
      db.add(
        models.Admin(
          username=settings.DEFAULT_ADMIN_USER,
          email=settings.DEFAULT_ADMIN_EMAIL,
          hashed_pwd=hashed,
        )
      )
      action = "created"
    else:
      admin.username = settings.DEFAULT_ADMIN_USER
      admin.email = settings.DEFAULT_ADMIN_EMAIL
      admin.hashed_pwd = hashed
      action = "updated"

    db.commit()
    print(f"Admin {action}: username={settings.DEFAULT_ADMIN_USER}")
  finally:
    db.close()


if __name__ == "__main__":
  main()
