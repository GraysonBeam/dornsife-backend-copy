import logging
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from logging import Logger

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session, sessionmaker

from src.Models.Base import Base
from src.Models.Event import Event
from src.Models.EventType import EventType
from src.Repositories.EventsRepository import DeletionOutcome, EventsRepository


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def logger() -> Logger:
    return logging.getLogger("test_events_logger")


@pytest.fixture
def events_repo(logger: Logger, db_session: Session) -> EventsRepository:
    return EventsRepository(logger, db_session)


@pytest.fixture
def test_event_type(db_session: Session) -> EventType:
    event_type = EventType(type="Workshop")
    db_session.add(event_type)
    db_session.commit()
    return event_type


@pytest.fixture
def test_event(db_session: Session, test_event_type: EventType) -> Event:
    now = datetime.now(UTC)
    event = Event(
        name="Test Event",
        description="A test event",
        start_datetime=now + timedelta(hours=1),
        end_datetime=now + timedelta(hours=2),
        location="Room 101",
        type_id=test_event_type.id,
    )
    db_session.add(event)
    db_session.commit()
    return event


def make_event(
    db_session: Session,
    event_type_id: int,
    *,
    name: str = "Event",
    start_offset_hours: float = 1,
    end_offset_hours: float = 2,
) -> Event:
    """Helper to create and persist an event with configurable time offsets."""
    now = datetime.now(UTC)
    event = Event(
        name=name,
        description="",
        start_datetime=now + timedelta(hours=start_offset_hours),
        end_datetime=now + timedelta(hours=end_offset_hours),
        location="TBD",
        type_id=event_type_id,
    )
    db_session.add(event)
    db_session.commit()
    return event


def test_delete_event_success(
    events_repo: EventsRepository, db_session: Session, test_event: Event
) -> None:
    result = events_repo.delete_by_id(event_id=test_event.id)
    db_session.commit()

    assert result == DeletionOutcome.SUCCESS

    db_session.expire_all()
    deleted = db_session.query(Event).filter(Event.id == test_event.id).first()
    assert deleted is None


def test_delete_event_not_found(events_repo: EventsRepository) -> None:
    result = events_repo.delete_by_id(event_id="non-existent-id")

    assert result == DeletionOutcome.NOT_FOUND


def test_delete_event_removes_only_target(
    events_repo: EventsRepository,
    db_session: Session,
    test_event_type: EventType,
    test_event: Event,
) -> None:
    """Deleting one event must not affect other events in the table."""
    other_event = make_event(db_session, test_event_type.id, name="Other Event")

    result = events_repo.delete_by_id(event_id=test_event.id)
    db_session.commit()

    assert result == DeletionOutcome.SUCCESS
    db_session.expire_all()
    assert db_session.query(Event).filter(Event.id == other_event.id).first() is not None


def test_delete_same_event_twice(
    events_repo: EventsRepository, db_session: Session, test_event: Event
) -> None:
    events_repo.delete_by_id(event_id=test_event.id)
    db_session.commit()

    result = events_repo.delete_by_id(event_id=test_event.id)

    assert result == DeletionOutcome.NOT_FOUND


def test_delete_event_logs_success(
    events_repo: EventsRepository,
    db_session: Session,
    test_event: Event,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="test_events_logger"):
        events_repo.delete_by_id(event_id=test_event.id)

    assert any("Successfully deleted" in msg for msg in caplog.messages)


def test_delete_event_logs_not_found(
    events_repo: EventsRepository, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger="test_events_logger"):
        events_repo.delete_by_id(event_id="non-existent-id")

    assert any("non-existent" in msg for msg in caplog.messages)


def test_get_active_events_returns_empty_when_no_events(
    events_repo: EventsRepository,
) -> None:
    result = events_repo.get_active_events()

    assert result == []


def test_get_active_events_includes_event_ended_within_8h(
    events_repo: EventsRepository,
    db_session: Session,
    test_event_type: EventType,
) -> None:
    """Event that ended 3 hours ago should be included."""
    make_event(
        db_session,
        test_event_type.id,
        name="Ended 3h Ago",
        start_offset_hours=-5,
        end_offset_hours=-3,
    )

    result = events_repo.get_active_events()

    assert len(result) == 1
    assert result[0].name == "Ended 3h Ago"


def test_get_active_events_includes_event_ended_at_8h_boundary(
    events_repo: EventsRepository,
    db_session: Session,
    test_event_type: EventType,
) -> None:
    """Event that ended exactly 8 hours ago should be included (boundary)."""
    make_event(
        db_session,
        test_event_type.id,
        name="Ended At Boundary",
        start_offset_hours=-10,
        end_offset_hours=-7.99,
    )

    result = events_repo.get_active_events()

    assert any(e.name == "Ended At Boundary" for e in result)


def test_get_active_events_excludes_event_ended_over_8h_ago(
    events_repo: EventsRepository,
    db_session: Session,
    test_event_type: EventType,
) -> None:
    """Event that ended 9 hours ago should be excluded."""
    make_event(
        db_session,
        test_event_type.id,
        name="Too Old",
        start_offset_hours=-12,
        end_offset_hours=-9,
    )

    result = events_repo.get_active_events()

    assert result == []


def test_get_active_events_includes_event_starting_within_12h(
    events_repo: EventsRepository,
    db_session: Session,
    test_event_type: EventType,
) -> None:
    """Event starting in 6 hours should be included."""
    make_event(
        db_session,
        test_event_type.id,
        name="Starting Soon",
        start_offset_hours=6,
        end_offset_hours=7,
    )

    result = events_repo.get_active_events()

    assert any(e.name == "Starting Soon" for e in result)


def test_get_active_events_includes_event_starting_at_12h_boundary(
    events_repo: EventsRepository,
    db_session: Session,
    test_event_type: EventType,
) -> None:
    """Event starting exactly 12 hours from now should be included (boundary)."""
    make_event(
        db_session,
        test_event_type.id,
        name="12h Boundary",
        start_offset_hours=12,
        end_offset_hours=13,
    )

    result = events_repo.get_active_events()

    assert any(e.name == "12h Boundary" for e in result)


def test_get_active_events_excludes_event_starting_beyond_12h(
    events_repo: EventsRepository,
    db_session: Session,
    test_event_type: EventType,
) -> None:
    """Event starting 24 hours from now should be excluded."""
    make_event(
        db_session,
        test_event_type.id,
        name="Far Future",
        start_offset_hours=24,
        end_offset_hours=25,
    )

    result = events_repo.get_active_events()

    assert result == []


def test_get_active_events_returns_sorted_by_start_datetime(
    events_repo: EventsRepository,
    db_session: Session,
    test_event_type: EventType,
) -> None:
    make_event(
        db_session, test_event_type.id, name="Later", start_offset_hours=10, end_offset_hours=11
    )
    make_event(
        db_session, test_event_type.id, name="Earlier", start_offset_hours=6, end_offset_hours=7
    )

    result = events_repo.get_active_events()

    start_times = [e.start_datetime for e in result]
    assert start_times == sorted(start_times)


def test_get_active_events_returns_multiple_events(
    events_repo: EventsRepository,
    db_session: Session,
    test_event_type: EventType,
) -> None:
    for i in range(3):
        make_event(
            db_session,
            test_event_type.id,
            name=f"Event {i}",
            start_offset_hours=3 + i,
            end_offset_hours=4 + i,
        )

    result = events_repo.get_active_events()

    assert len(result) == 3


def test_get_active_events_mixes_ended_and_upcoming(
    events_repo: EventsRepository,
    db_session: Session,
    test_event_type: EventType,
) -> None:
    """Both branches should contribute events to the same result list."""
    make_event(
        db_session,
        test_event_type.id,
        name="Recently Ended",
        start_offset_hours=-5,
        end_offset_hours=-3,
    )
    make_event(
        db_session,
        test_event_type.id,
        name="Starting Soon",
        start_offset_hours=6,
        end_offset_hours=7,
    )

    result = events_repo.get_active_events()

    names = [e.name for e in result]
    assert "Recently Ended" in names
    assert "Starting Soon" in names


def test_get_event_by_id_throws_error_if_no_events_exist(
    events_repo: EventsRepository,
    db_session: Session,
) -> None:
    with pytest.raises(NoResultFound):
        events_repo.get_event_by_id("0")


def test_get_event_by_id_retrieves_event_record_successfully(
    events_repo: EventsRepository,
    db_session: Session,
    test_event: Event,
) -> None:
    result: Event = events_repo.get_event_by_id(test_event.id)

    assert result.id == test_event.id
    assert result.name == test_event.name
    assert result.description == test_event.description
    assert result.start_datetime == test_event.start_datetime
    assert result.end_datetime == test_event.end_datetime
    assert result.location == test_event.location
    assert result.type_id == test_event.type_id
    assert result.created_at == test_event.created_at
    assert result.updated_at == test_event.updated_at


# @pytest.fixture
# def event_type(db_session: Session) -> EventType:
#     """Create test EventType."""
#     et = EventType(type="Workshop")
#     db_session.add(et)
#     db_session.commit()
#     return et


def test_create_event_success(
    events_repo: EventsRepository,
    db_session: Session,
    test_event_type: EventType,  # ← Use this instead of event_type
) -> None:
    """Test create_event stores event in database."""
    start = datetime.now(UTC) + timedelta(hours=1)
    end = datetime.now(UTC) + timedelta(hours=2)

    event = events_repo.create_event(
        name="Team Meeting",
        description="Weekly sync",
        location="Room A",
        type_id=test_event_type.id,  # ← Use test_event_type
        start_datetime=start,
        end_datetime=end,
    )

    db_session.commit()

    saved = db_session.query(Event).filter(Event.id == event.id).first()
    assert saved is not None
    assert saved.name == "Team Meeting"


def test_create_event_stores_all_fields(
    events_repo: EventsRepository,
    db_session: Session,
    test_event_type: EventType,
) -> None:
    """Test create_event stores all provided fields."""
    start = datetime.now(UTC) + timedelta(hours=1)
    end = datetime.now(UTC) + timedelta(hours=2)

    event = events_repo.create_event(
        name="Complete Event",
        description="Full details",
        location="Building A",
        type_id=test_event_type.id,
        start_datetime=start,
        end_datetime=end,
    )

    db_session.commit()

    saved = db_session.query(Event).filter(Event.id == event.id).first()
    assert saved is not None
    assert saved.name == "Complete Event"
    assert saved.description == "Full details"
    assert saved.location == "Building A"
    assert saved.type_id == test_event_type.id
    assert saved.start_datetime == start.replace(tzinfo=None)
    assert saved.end_datetime == end.replace(tzinfo=None)


def test_get_all_event_types_from_db_success(
    events_repo: EventsRepository,
    test_event_type: EventType,
) -> None:
    res = events_repo.get_all_event_types_from_db()
    assert res is not None
    assert len(res) == 1
    assert res[0] == (test_event_type.id, "Workshop")


def test_get_all_event_types_from_db_empty(
    events_repo: EventsRepository,
    db_session: Session,
) -> None:
    db_session.query(EventType).delete()
    db_session.commit()

    res = events_repo.get_all_event_types_from_db()
    assert res is None
