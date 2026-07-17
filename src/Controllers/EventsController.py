from logging import getLogger
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.Database.dependencies import get_db_session
from src.Models.exceptions import NotFoundException
from src.Repositories.EventsRepository import EventsRepository
from src.Schemas.EventCreatedResponse import EventCreatedResponse
from src.Schemas.EventRegistrationRequest import EventRegistrationRequest
from src.Schemas.EventTypesResponse import EventTypesResponse
from src.Schemas.GetActiveEventsResponse import GetActiveEventsResponse
from src.Schemas.GetEventResponse import EventItem, GetEventsResponse
from src.Schemas.UpdateEventRequest import UpdateEventRequest
from src.Schemas.UpdateEventResponse import UpdateEventResponse
from src.Services.EventRegisterService import EventRegisterService
from src.Utils.Validators import ValidationError

events_router = APIRouter()

logger = getLogger(__name__)


def get_event_reg_serv(db: Annotated[Session, Depends(get_db_session)]) -> EventRegisterService:
    return EventRegisterService(logger, EventsRepository(logger, db))


@events_router.get("/activeEvents", response_model=GetActiveEventsResponse)
async def get_active_events(
    events_reg_serv: Annotated[EventRegisterService, Depends(get_event_reg_serv)],
) -> GetActiveEventsResponse:
    try:
        req = events_reg_serv.get_active_events()
        res = GetActiveEventsResponse(events=req if req else [])
        return res
    except Exception as e:
        logger.error("Sending error response for generic error %s", e)
        raise HTTPException(status_code=500, detail="An internal server error occurred") from e


@events_router.get("/events", response_model=GetEventsResponse)
async def get_events(
    events_reg_serv: Annotated[EventRegisterService, Depends(get_event_reg_serv)],
    page: Annotated[int, Query(ge=1, description="1-based page number")],
    event_name: Annotated[str | None, Query(description="optional event name to filter by")] = None,
) -> GetEventsResponse:
    try:
        req = events_reg_serv.get_events(page, event_name)
        res = GetEventsResponse(
            events=[
                EventItem(
                    id=str(event.id),
                    name=event.name,
                    description=event.description,
                    start_datetime=event.start_datetime,
                    end_datetime=event.end_datetime,
                    location=event.location,
                    type_id=event.type_id,
                )
                for event in req
            ]
        )
        return res
    except Exception as e:
        logger.error("Sending error response for generic error %s", e)
        raise HTTPException(status_code=500, detail="An internal server error occurred") from e


@events_router.get("/eventTypes", response_model=EventTypesResponse)
async def get_all_event_types(
    events_reg_serv: Annotated[EventRegisterService, Depends(get_event_reg_serv)],
) -> EventTypesResponse:
    try:
        types = events_reg_serv.get_event_types()
        return EventTypesResponse(event_types=types if types else [])
    except Exception as e:
        logger.error("Error getting event types: %s", e)
        raise HTTPException(status_code=500, detail="An internal server error occurred") from e


@events_router.put("/{event_id}", response_model=UpdateEventResponse)
async def update_event(
    event_id: str,
    event_request: UpdateEventRequest,
    events_reg_serv: Annotated[EventRegisterService, Depends(get_event_reg_serv)],
) -> UpdateEventResponse:
    """Update an existing event's fields."""

    if not any(
        [
            event_request.name,
            event_request.description,
            event_request.location,
            event_request.type_id,
            event_request.start_datetime,
            event_request.end_datetime,
        ]
    ):
        raise HTTPException(status_code=400, detail="No fields provided to update")

    try:
        result = events_reg_serv.update_event(event_id, event_request)

        if result is None:
            raise NotFoundException(f"Event {event_id} not found")

        return result

    except NotFoundException as e:
        logger.error("Event not found: %s", e)
        raise HTTPException(status_code=404, detail=e.args[0]) from e

    except ValidationError as e:
        logger.warning("Validation error updating event %s: %s", event_id, e)
        raise HTTPException(status_code=400, detail=str(e)) from e

    except ValueError as e:
        logger.warning("Value error updating event %s: %s", event_id, e)
        raise HTTPException(status_code=400, detail=str(e)) from e

    except Exception as e:
        logger.error("Unexpected error updating event %s: %s", event_id, e)
        raise HTTPException(status_code=500, detail="An internal server error occurred") from e


@events_router.post("", response_model=EventCreatedResponse, status_code=201)
async def create_event(
    event_request: EventRegistrationRequest,
    events_reg_serv: Annotated[EventRegisterService, Depends(get_event_reg_serv)],
) -> EventCreatedResponse:
    """Create a new event."""
    try:
        return events_reg_serv.create_event(event_request)

    except ValidationError as e:
        logger.warning("Validation error creating event: %s", str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e

    except ValueError as e:
        logger.warning("Error creating event: %s", str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e

    except Exception as e:
        logger.error("Unexpected error creating event: %s", str(e))
        raise HTTPException(status_code=500, detail="An internal server error occurred") from e
