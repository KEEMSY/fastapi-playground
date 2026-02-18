from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from src.database.database import Base
### 삭제되면 안됨 시작 ###
from src.domains.user.models import User
from src.domains.question.models import Question
from src.domains.answer.models import Answer
from src.domains.sync_example.database.models import SyncExample
from src.domains.async_example.database.models import AsyncExample, RelatedAsyncExample, DerivedFromAsyncExample
from src.domains.notification.models import Notification
### 삭제되면 안됨 끝 ###
# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# sqlalchemy.url 설정은 컨테이너(도커)주소로 관리가 되지 않아 실제 주소를 작성하였음. 24.05.19
if not config.get_main_option("sqlalchemy.url"):
    config.set_main_option("sqlalchemy.url", "mysql+pymysql://{username}:{password}@{host}:{port}/{db_name}".format(
        username="root", 
        password="test", 
        host="db",  # localhost 대신 docker-compose 서비스 이름 사용
        port="3306", # 도커 내부 포트 사용
        db_name="fastapi_playground"
    ))

    # For TestDB
    # config.set_main_option("sqlalchemy.url", "mysql+pymysql://{username}:{password}@{host}:{port}/{db_name}".format(
    #     username="root", password="test", host="localhost", port="3306", db_name="fastapi_test"
    # ))

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
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
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
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
