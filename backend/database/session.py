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

def check_database_connection() -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
