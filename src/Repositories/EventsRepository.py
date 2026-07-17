from datetime import UTC, datetime, timedelta
from enum import Enum
from logging import Logger

from sqlalchemy import and_, desc, or_, select
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session

from src.Models.Event import Event
from src.Models.EventType import EventType


class DeletionOutcome(Enum):
    SUCCESS = "success"
    NOT_FOUND = "not_found"
    CONSTRAINT_VIOLATION = "constraint_violation"


class EventsRepository:
    def __init__(self, logger: Logger, db: Session):
        self.logger = logger
        self.db = db

    def delete_by_id(self, event_id: str) -> DeletionOutcome:
        try:
            event_to_delete = self.db.query(Event).filter(Event.id == event_id).first()

            if not event_to_delete:
                self.logger.warning(f"Deletion attempted on non-existent event: {event_id}")
                return DeletionOutcome.NOT_FOUND

            self.db.delete(event_to_delete)
            self.logger.info(f"Successfully deleted event {event_id}")
            return DeletionOutcome.SUCCESS

        except IntegrityError as e:
            self.logger.warning(
                f"Constraint violation preventing deletion of event {event_id}: {e.orig}"
            )
            return DeletionOutcome.CONSTRAINT_VIOLATION

        except SQLAlchemyError as e:
            self.logger.error(f"Unexpected database error deleting event {event_id}: {e}")
            raise

    def get_active_events(self) -> list[Event]:
        """
        returns a list of available events within the next hour asked within specific
        """
        cur = datetime.now(UTC)
        offset_8 = timedelta(hours=8)  # event has passed for up to 8 hours
        offset_12 = timedelta(hours=12)  # event hasn't passed within the next 12 or more hours

        try:
            events = list(
                self.db.query(Event)
                .order_by(Event.start_datetime)
                .filter(
                    or_(
                        and_(cur >= Event.end_datetime, Event.end_datetime >= cur - offset_8),
                        and_(cur <= Event.start_datetime, Event.start_datetime <= cur + offset_12),
                        and_(Event.start_datetime <= cur, Event.end_datetime >= cur),
                    )
                )
            )

            self.logger.info("Successfully extracted active events")
            return events

        except OperationalError:
            self.logger.warning("Events Repository: Failure to extract events table")
            raise

        except SQLAlchemyError as e:
            self.logger.error(f"Unexpected database error fetching active events: {e}")
            raise

    def get_events(self, page: int, event_name: str | None) -> list[Event]:
        query = self.db.query(Event)
        query = query.order_by(desc(Event.start_datetime))
        if event_name is not None:
            query = query.filter(Event.name.ilike(f"%{event_name}%"))
        return query.offset((page - 1) * 10).limit(10).all()

    def get_event_by_id(self, event_id: str) -> Event:
        event = self.db.execute(select(Event).where(Event.id == event_id)).scalar_one()
        return event

    def create_event(
        self,
        name: str,
        description: str,
        location: str,
        type_id: int,
        start_datetime: datetime,
        end_datetime: datetime,
    ) -> Event:
        """Create a new event in the database."""
        self.logger.info(f"Attempting to create new event: {name}")

        try:
            new_event: Event = Event(
                name=name,
                description=description,
                location=location,
                type_id=type_id,
                start_datetime=start_datetime,
                end_datetime=end_datetime,
            )
            self.db.add(new_event)
            self.db.flush()
            self.logger.info(f"Created event with ID {new_event.id}")
            return new_event

        except SQLAlchemyError as e:
            self.logger.error(f"Database error creating event: {str(e)}")
            raise

    def update_event_fields(
        self,
        event_id: str,
        name: str | None = None,
        description: str | None = None,
        location: str | None = None,
        type_id: int | None = None,
        start_datetime: datetime | None = None,
        end_datetime: datetime | None = None,
    ) -> Event | None:
        self.logger.info(f"Attempting to update fields for event {event_id}")

        try:
            event = self.db.query(Event).filter(Event.id == event_id).first()
        except SQLAlchemyError as e:
            self.logger.error(f"Database error fetching event {event_id}: {e}")
            raise

        if not event:
            self.logger.warning(f"Event {event_id} not found for update")
            return None

        field_map: dict[str, str | int | datetime | None] = {
            "name": name,
            "description": description,
            "location": location,
            "type_id": type_id,
            "start_datetime": start_datetime,
            "end_datetime": end_datetime,
        }

        updated_fields: list[str] = []
        for field, value in field_map.items():
            if value is not None:
                setattr(event, field, value)
                updated_fields.append(field)

        try:
            self.db.flush()
        except SQLAlchemyError as e:
            self.logger.error(f"Database error updating event {event_id}: {e}")
            raise

        self.logger.info(f"Successfully updated {updated_fields} for event {event_id}")
        return event

    def get_all_event_types_from_db(self) -> list[tuple[int, str]] | None:
        """Returns array of event types from DB as (id, type) tuples."""
        try:
            event_types = self.db.query(EventType).all()
            if not event_types:
                self.logger.warning("No event types found in eventtypes table")
                return None
            return [(et.id, et.type) for et in event_types]
        except SQLAlchemyError as e:
            self.logger.error(f"Database error fetching event types: {e}")
            raise
