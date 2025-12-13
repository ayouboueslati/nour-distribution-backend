import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from app.core.config import settings
from app.models.base import Base  

# --- Alembic Config ---
config = context.config
fileConfig(config.config_file_name)
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# --- IMPORT ALL MODELS HERE ---
# If you don't import a model here, Alembic WILL NOT detect it
from app.models.user import User
from app.models.client import Client
from app.models.category import Category
from app.models.supplier import Supplier
from app.models.product import Product
from app.models.product_image import ProductImage
from app.models.inventory import InventoryMovement
from app.models.document import Document
from app.models.order import Order, OrderItem
from app.models.cart import Cart
from app.models.charge import Charge

# All models are attached to Base
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
