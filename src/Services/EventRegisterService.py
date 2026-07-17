from logging import Logger

from src.Models.Event import Event
from src.Repositories.EventsRepository import EventsRepository
from src.Schemas.EventCreatedResponse import EventCreatedResponse
from src.Schemas.EventRegistrationRequest import EventRegistrationRequest
from src.Schemas.EventTypesResponse import EventTypeItem
from src.Schemas.GetActiveEventsResponse import ActiveEvent
from src.Schemas.UpdateEventRequest import UpdateEventRequest
from src.Schemas.UpdateEventResponse import UpdateEventResponse
from src.Utils.Validators import Validator


class EventRegisterService:
    def __init__(self, logger: Logger, eventsRepository: EventsRepository):
        self.logger = logger
        self.eventsRepository = eventsRepository

    def get_active_events(self) -> list[ActiveEvent]:
        self.logger.info("Getting active events from service side")
        events = self.eventsRepository.get_active_events()
        if not events:
            self.logger.info("Event register service: empty active events")
            return []
        self.logger.info("Event register service: successfully retrieved active events")

        return [
            ActiveEvent(
                id=str(event.id),
                name=event.name,
                start_datetime=event.start_datetime,
                end_datetime=event.end_datetime,
            )
            for event in events
        ]

    def get_events(self, page: int, event_name: str | None) -> list[Event]:
        self.logger.info("Getting events from service side")
        events = self.eventsRepository.get_events(page, event_name)
        if not events:
            self.logger.info("Event register service: empty events")
            return []
        self.logger.info("Event register service: successfully retrieved events")
        return events

    def validate_event_id(self, event_id: str) -> bool:
        self.logger.info("Validating event_id %s", event_id)
        try:
            self.eventsRepository.get_event_by_id(event_id=event_id)
        except Exception:
            self.logger.warning("Event with id %s could not be found or does not exist.", event_id)
            return False

        return True

    def create_event(self, event_data: EventRegistrationRequest) -> EventCreatedResponse:
        try:
            Validator.validate_event_time(event_data.start_datetime, event_data.end_datetime)

            event = self.eventsRepository.create_event(
                name=event_data.name,
                description=event_data.description,
                location=event_data.location,
                type_id=event_data.type_id,
                start_datetime=event_data.start_datetime,
                end_datetime=event_data.end_datetime,
            )

            self.logger.info("Created new event: name=%s id=%s", event_data.name, event.id)
            return EventCreatedResponse(id=event.id, status="created")

        except ValueError as e:
            self.logger.warning("Event validation failed: %s", str(e))
            raise
        except Exception as e:
            self.logger.error("Failed to create event: %s", str(e))
            raise

    def update_event(
        self, event_id: str, event_data: UpdateEventRequest
    ) -> UpdateEventResponse | None:
        self.logger.info("Updating event %s", event_id)

        if event_data.start_datetime is not None or event_data.end_datetime is not None:
            try:
                existing = self.eventsRepository.get_event_by_id(event_id)
            except Exception:
                self.logger.warning("Event %s not found for datetime validation", event_id)
                return None
            start = event_data.start_datetime or existing.start_datetime
            end = event_data.end_datetime or existing.end_datetime
            Validator.validate_event_time(start, end)

        event = self.eventsRepository.update_event_fields(
            event_id=event_id,
            name=event_data.name,
            description=event_data.description,
            location=event_data.location,
            type_id=event_data.type_id,
            start_datetime=event_data.start_datetime,
            end_datetime=event_data.end_datetime,
        )

        if event is None:
            self.logger.warning("Event %s not found for update", event_id)
            return None

        self.logger.info("Successfully updated event %s", event_id)

        return UpdateEventResponse(
            id=str(event.id),
            name=event.name,
            description=event.description,
            location=event.location,
            type_id=event.type_id,
            start_datetime=event.start_datetime,
            end_datetime=event.end_datetime,
        )

    def get_event_types(self) -> list[EventTypeItem] | None:
        """Returns event types as key (type) + id for the client."""
        self.logger.info("Getting event types from service side")
        res = self.eventsRepository.get_all_event_types_from_db()
        if not res:
            self.logger.info("Event register service: empty event types")
            return None
        self.logger.info("Event register service: successfully retrieved event types")
        return [EventTypeItem(key=event_type, id=type_id) for type_id, event_type in res]
