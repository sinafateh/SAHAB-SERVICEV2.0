from logging.config import fileConfig
from pathlib import Path
import os
import sys

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context


# -------------------------------------------------
# Alembic Config
# -------------------------------------------------
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# -------------------------------------------------
# Add project root to sys.path
# -------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))


# -------------------------------------------------
# Load .env manually
# -------------------------------------------------
def load_dotenv_file():
    env_path = BASE_DIR / ".env"

    if not env_path.exists():
        return

    with env_path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            os.environ.setdefault(key, value)


load_dotenv_file()


# -------------------------------------------------
# Import Base and all models
# -------------------------------------------------
from app.models.base import Base

# مهم:
# این import باعث می‌شود همه مدل‌ها داخل metadata ثبت شوند.
import app.models  # noqa: F401


target_metadata = Base.metadata


# -------------------------------------------------
# Database URL
# -------------------------------------------------
def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        try:
            from app.config import settings

            database_url = getattr(settings, "DATABASE_URL", None) or getattr(
                settings, "database_url", None
            )
        except Exception:
            database_url = None

    if not database_url:
        database_url = config.get_main_option("sqlalchemy.url")

    if not database_url:
        raise RuntimeError("DATABASE_URL پیدا نشد.")

    return database_url


database_url = get_database_url()
config.set_main_option("sqlalchemy.url", database_url)


# -------------------------------------------------
# Offline migrations
# -------------------------------------------------
def run_migrations_offline() -> None:
    url = get_database_url()

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# -------------------------------------------------
# Online migrations
# -------------------------------------------------
def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section)

    if configuration is None:
        configuration = {}

    configuration["sqlalchemy.url"] = get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# -------------------------------------------------
# Run
# -------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
