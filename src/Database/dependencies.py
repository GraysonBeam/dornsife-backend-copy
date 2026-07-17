from collections.abc import Generator

from sqlalchemy.orm import Session

from .database import get_session_local


def get_db_session() -> Generator[Session, None, None]:
    session_local = get_session_local()
    db = session_local()
    try:
        yield db
        db.commit()
    except:
        db.rollback()
        raise
    finally:
        db.close()
