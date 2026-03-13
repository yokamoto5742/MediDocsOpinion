import sys
import re
from logging.config import fileConfig
from pathlib import Path
import configparser

from sqlalchemy import engine_from_config, pool

from alembic import context

# プロジェクトルートをsys.pathに追加
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# アプリケーション設定とモデルをインポート
from app.core.config import get_settings
from app.models import Base

# Alembic Config オブジェクト
config = context.config

config.file_config = configparser.ConfigParser(interpolation=None)
if config.config_file_name is not None:
    config.file_config.read(config.config_file_name)

original_url = str(get_settings().get_database_url())

# 強制的にローカルPCのPostgreSQL（ポート5432）に接続先を書き換える
db_url = re.sub(r"@[\w\.-]+:5432", "@localhost:5432", original_url)

config.set_main_option("sqlalchemy.url", db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
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
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        poolclass=pool.NullPool
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
