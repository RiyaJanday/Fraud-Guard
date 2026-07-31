"""
Alembic environment script.

Pulls DATABASE_URL from our own Settings (app.core.config), and imports
app.models so every table is registered on Base.metadata before
`--autogenerate` compares it against the live database schema.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# --------------------------------------------------------------------- #
# Make `app.*` importable when Alembic is invoked from the project root.
# --------------------------------------------------------------------- #
import os
import sys

sys.path.insert(0, os.getcwd())

from app.core.config import get_settings  # noqa: E402
from app.database.base import Base  # noqa: E402
import app.models  # noqa: E402,F401 — registers every model on Base.metadata

# Alembic Config object, provides access to values in alembic.ini.
config = context.config

# Inject our real DATABASE_URL (from .env) instead of alembic.ini's blank value.
settings = get_settings()
config.set_main_option("sqlalchemy.url", str(settings.DATABASE_URL))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate — this is what makes
# `alembic revision --autogenerate` actually see our 9 tables.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (emits SQL to stdout)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations with a live DB connection — the normal path."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,  # detect column type changes, not just add/drop
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
