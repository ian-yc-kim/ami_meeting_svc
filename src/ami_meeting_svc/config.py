import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///:memory:")

# Authentication configuration
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
try:
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
except ValueError:
    ACCESS_TOKEN_EXPIRE_MINUTES = 30

def _parse_bool_env(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return str(value).lower() in ("1", "true", "yes", "y")

COOKIE_SECURE = _parse_bool_env(os.getenv("COOKIE_SECURE"), True)
