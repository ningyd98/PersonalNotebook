"""Alembic env.py — 数据库迁移环境配置"""

import os
import sys
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

# 确保 backend 在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

load_dotenv()

config = context.config

# 从环境变量构建同步 URL
db_user = os.getenv("POSTGRES_USER", "kb_user")
db_pass = os.getenv("POSTGRES_PASSWORD", "kb_password")
db_host = os.getenv("POSTGRES_HOST", "localhost")
db_port = os.getenv("POSTGRES_PORT", "5432")
db_name = os.getenv("POSTGRES_DB", "personal_kb")
sync_url = f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
config.set_main_option("sqlalchemy.url", sync_url)

fileConfig(config.config_file_name)

# 导入所有模型，确保 Base.metadata 包含所有表
from app.db.session import Base  # noqa: E402
import app.models.models  # noqa: E402 — 触发所有模型注册

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
