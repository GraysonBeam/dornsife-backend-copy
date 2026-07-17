import os

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        database_url = os.getenv("DORNSIFE_DATABASE_URL")
        if not database_url:
            raise RuntimeError(
                "DORNSIFE_DATABASE_URL is not set. Did you forget to create a .env file?"
            )
        _engine = create_engine(
            database_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            connect_args={"options": "-c timezone=utc"},
        )
    return _engine


def get_session_local() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine())
