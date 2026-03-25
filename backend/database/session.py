from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base, sessionmaker

from utils.config import settings


def _create_engine():
    url = make_url(settings.database_url)
    connect_args = {}
    engine_kwargs = {"pool_pre_ping": True}

    if url.get_backend_name() == "sqlite":
        connect_args["check_same_thread"] = False
    if connect_args:
        engine_kwargs["connect_args"] = connect_args

    return create_engine(settings.database_url, **engine_kwargs)


engine = _create_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def initialize_database() -> None:
    from database.models import Base as ModelBase

    ModelBase.metadata.create_all(bind=engine)
    _run_lightweight_migrations()


def check_database_connection() -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _run_lightweight_migrations() -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    if "statements" in tables:
        statement_columns = {column["name"] for column in inspector.get_columns("statements")}
        if "user_id" not in statement_columns:
            _execute_ddl("ALTER TABLE statements ADD COLUMN user_id INTEGER NULL")
            _create_index_if_missing("statements", "ix_statements_user_id", ["user_id"])

    if "users" in tables:
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        if "name" not in user_columns:
            _execute_ddl("ALTER TABLE users ADD COLUMN name VARCHAR(120) NOT NULL DEFAULT 'User'")
        if "password_hash" not in user_columns:
            _execute_ddl("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255) NOT NULL DEFAULT ''")
        if "password_salt" not in user_columns:
            _execute_ddl("ALTER TABLE users ADD COLUMN password_salt VARCHAR(255) NOT NULL DEFAULT ''")


def _execute_ddl(statement: str) -> None:
    with engine.begin() as connection:
        connection.execute(text(statement))


def _create_index_if_missing(table_name: str, index_name: str, columns: list[str]) -> None:
    inspector = inspect(engine)
    existing_indexes = {index["name"] for index in inspector.get_indexes(table_name)}
    if index_name in existing_indexes:
        return

    column_sql = ", ".join(columns)
    _execute_ddl(f"CREATE INDEX {index_name} ON {table_name} ({column_sql})")
