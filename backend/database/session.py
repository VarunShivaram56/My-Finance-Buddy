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


def _ensure_database_exists() -> None:
    url = make_url(settings.database_url)
    if url.get_backend_name() == "mysql":
        db_name = url.database
        if not db_name:
            return
            
        temp_url = url.set(database="")
        temp_engine = create_engine(temp_url, isolation_level="AUTOCOMMIT")
        with temp_engine.connect() as conn:
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db_name}`"))
        temp_engine.dispose()


def initialize_database() -> None:
    from database.models import Base as ModelBase

    _ensure_database_exists()
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
        if "user_id" not in user_columns:
            _execute_ddl("ALTER TABLE users ADD COLUMN user_id VARCHAR(64) NOT NULL DEFAULT ''")
            _create_index_if_missing("users", "ix_users_user_id", ["user_id"])
        if "password_hash" not in user_columns:
            _execute_ddl("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255) NOT NULL DEFAULT ''")
        if "password_salt" not in user_columns:
            _execute_ddl("ALTER TABLE users ADD COLUMN password_salt VARCHAR(255) NOT NULL DEFAULT ''")
        # Drop the legacy email column — it is no longer used and blocks inserts
        if "email" in user_columns:
            if engine.dialect.name == "mysql":
                # MySQL: check if email has a UNIQUE index/key and drop it first
                try:
                    _execute_ddl("ALTER TABLE users DROP INDEX email")
                except Exception:
                    pass
                try:
                    _execute_ddl("ALTER TABLE users DROP INDEX ix_users_email")
                except Exception:
                    pass
                _execute_ddl("ALTER TABLE users DROP COLUMN email")
            else:
                # SQLite doesn't support DROP COLUMN in older versions, make it nullable
                try:
                    _execute_ddl("ALTER TABLE users DROP COLUMN email")
                except Exception:
                    pass

    if "non_banking_transactions" not in tables:
        _execute_ddl(
            """
            CREATE TABLE non_banking_transactions (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                user_id INTEGER NOT NULL,
                transaction_date DATE NOT NULL,
                beneficiary VARCHAR(255) NOT NULL,
                amount FLOAT NOT NULL,
                transaction_type VARCHAR(20) NOT NULL,
                category VARCHAR(50) NOT NULL DEFAULT 'Others / Uncategorized',
                description TEXT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_non_banking_transaction_user FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
            if engine.dialect.name != "sqlite"
            else """
            CREATE TABLE non_banking_transactions (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                transaction_date DATE NOT NULL,
                beneficiary VARCHAR(255) NOT NULL,
                amount FLOAT NOT NULL,
                transaction_type VARCHAR(20) NOT NULL,
                category VARCHAR(50) NOT NULL DEFAULT 'Others / Uncategorized',
                description TEXT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        _create_index_if_missing("non_banking_transactions", "ix_non_banking_transactions_user_id", ["user_id"])
    else:
        non_banking_columns = {column["name"] for column in inspector.get_columns("non_banking_transactions")}
        if "category" not in non_banking_columns:
            _execute_ddl(
                "ALTER TABLE non_banking_transactions ADD COLUMN category VARCHAR(50) NOT NULL DEFAULT 'Others / Uncategorized'"
            )

    if "loans" not in tables:
        _execute_ddl(
            """
            CREATE TABLE loans (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                user_id INTEGER NOT NULL,
                loan_name VARCHAR(255) NOT NULL,
                lender VARCHAR(255) NOT NULL,
                principal_amount DOUBLE NOT NULL,
                interest_rate DOUBLE NOT NULL,
                tenure_months INTEGER NOT NULL,
                emi_amount DOUBLE NOT NULL DEFAULT 0,
                start_date DATE NOT NULL,
                total_paid DOUBLE NOT NULL DEFAULT 0,
                status VARCHAR(20) NOT NULL DEFAULT 'active',
                notes TEXT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_loan_user FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
            if engine.dialect.name != "sqlite"
            else """
            CREATE TABLE loans (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                loan_name VARCHAR(255) NOT NULL,
                lender VARCHAR(255) NOT NULL,
                principal_amount DOUBLE NOT NULL,
                interest_rate DOUBLE NOT NULL,
                tenure_months INTEGER NOT NULL,
                emi_amount DOUBLE NOT NULL DEFAULT 0,
                start_date DATE NOT NULL,
                total_paid DOUBLE NOT NULL DEFAULT 0,
                status VARCHAR(20) NOT NULL DEFAULT 'active',
                notes TEXT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        _create_index_if_missing("loans", "ix_loans_user_id", ["user_id"])

    if "assets" not in tables:
        _execute_ddl(
            """
            CREATE TABLE assets (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                user_id INTEGER NOT NULL,
                asset_name VARCHAR(255) NOT NULL,
                purchase_price DOUBLE NOT NULL,
                purchase_year INTEGER NOT NULL,
                rate_per_year DOUBLE NOT NULL DEFAULT 0,
                notes TEXT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_asset_user FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
            if engine.dialect.name != "sqlite"
            else """
            CREATE TABLE assets (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                asset_name VARCHAR(255) NOT NULL,
                purchase_price DOUBLE NOT NULL,
                purchase_year INTEGER NOT NULL,
                rate_per_year DOUBLE NOT NULL DEFAULT 0,
                notes TEXT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        _create_index_if_missing("assets", "ix_assets_user_id", ["user_id"])


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
