from logging import getLogger
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.Controllers.EventsController import get_event_reg_serv
from src.Database.dependencies import get_db_session
from src.Models.CheckInMethodType import CheckInMethodsEnum
from src.Models.CheckInProof import CheckInProof
from src.Models.exceptions import NotFoundException
from src.Repositories.AttendanceRepository import AttendanceRepository
from src.Repositories.UsersRepository import UsersRepository
from src.Schemas.AttendeeResponse import AttendeeResponse
from src.Schemas.CheckInRequest import CheckInRequest
from src.Schemas.CheckInResponse import CheckInResponse
from src.Schemas.EventAttendanceResponse import EventAttendanceResponse
from src.Schemas.GetEventBucketAgeResponse import (
    EventAgeBucketItem,
    GetEventBucketAgeResponse,
)
from src.Schemas.GetEventBucketRaceResponse import (
    EventRaceBucketItem,
    GetEventBucketRaceResponse,
)
from src.Schemas.GetEventBucketZipResponse import (
    EventZipBucketItem,
    GetEventBucketZipResponse,
)
from src.Services.AttendanceService import AttendanceService
from src.Services.EventRegisterService import EventRegisterService
from src.Utils.Validators import ValidationError

attendance_router = APIRouter()

logger = getLogger()


def get_attendance_service(db: Annotated[Session, Depends(get_db_session)]) -> AttendanceService:
    return AttendanceService(
        logger,
        attendance_repo=AttendanceRepository(logger, db),
        user_repo=UsersRepository(logger, db),
    )


@attendance_router.post("/checkIn", response_model=CheckInResponse)
async def check_in(
    request: CheckInRequest,
    attendance_service: Annotated[AttendanceService, Depends(get_attendance_service)],
    event_service: Annotated[EventRegisterService, Depends(get_event_reg_serv)],
) -> CheckInResponse:
    qr_token: str = request.qr_token
    event_id: str = request.event_id
    check_in_method: CheckInMethodsEnum = (
        CheckInMethodsEnum.MANUAL if request.is_manual_check_in else CheckInMethodsEnum.QR_CODE
    )

    logger.info("Validating event_id %s", event_id)
    event_exists = event_service.validate_event_id(event_id=event_id)
    if not event_exists:
        logger.error(
            "Sending not found response for event corresponding to event_id %s not being found.",
            event_id,
        )
        raise HTTPException(
            status_code=404, detail=f"Invalid event_id {event_id}. Event does not exist"
        )

    logger.info("Processing checking in for an event")
    try:
        check_in_proof: CheckInProof = attendance_service.check_into_event(
            qr_token, event_id, check_in_method_id=check_in_method.value
        )

        return CheckInResponse(
            attendance_id=check_in_proof.attendance_id, timestamp=check_in_proof.timestamp
        )
    except NotFoundException as e:
        logger.error("Sending not found response from error %s", e)
        raise HTTPException(status_code=404, detail=e.args[0]) from e
    except ValidationError as e:
        logger.error("Sending bad request response from error %s", e)
        raise HTTPException(status_code=400, detail=e.args[0]) from e
    except Exception as e:
        logger.error("Sending error response for generic error %s", e)
        raise HTTPException(status_code=500, detail="An Internal Server Error occurred.") from e


@attendance_router.get("/event-zip-bucket", response_model=GetEventBucketZipResponse)
async def get_event_bucket_zip(
    event_id: str,
    attendance_service: Annotated[AttendanceService, Depends(get_attendance_service)],
) -> GetEventBucketZipResponse:
    try:
        rows = attendance_service.get_event_zip_bucket(event_id)
        return GetEventBucketZipResponse(
            buckets=[
                EventZipBucketItem(
                    zip_code=row.zip_code,
                    zip_code_count=row.zip_code_count,
                )
                for row in rows
            ]
        )
    except Exception as e:
        logger.error("Sending error response for generic error %s", e)
        raise HTTPException(status_code=500, detail="An Internal Server Error occurred.") from e


@attendance_router.get("/event-race-bucket", response_model=GetEventBucketRaceResponse)
async def get_event_bucket_race(
    event_id: str,
    attendance_service: Annotated[AttendanceService, Depends(get_attendance_service)],
) -> GetEventBucketRaceResponse:
    try:
        rows = attendance_service.get_event_race_bucket(event_id)
        return GetEventBucketRaceResponse(
            buckets=[
                EventRaceBucketItem(
                    race=row.description,
                    race_count=row.race_count,
                )
                for row in rows
            ]
        )
    except Exception as e:
        logger.error("Sending error response for generic error %s", e)
        raise HTTPException(status_code=500, detail="An Internal Server Error occurred.") from e


@attendance_router.get("/event-age-bucket", response_model=GetEventBucketAgeResponse)
async def get_event_bucket_age(
    event_id: str,
    attendance_service: Annotated[AttendanceService, Depends(get_attendance_service)],
) -> GetEventBucketAgeResponse:
    try:
        rows = attendance_service.get_event_age_bucket(event_id)
        return GetEventBucketAgeResponse(
            buckets=[
                EventAgeBucketItem(
                    age_bucket=row.age_bucket,
                    attendee_count=row.attendee_count,
                )
                for row in rows
            ]
        )
    except Exception as e:
        logger.error("Sending error response for generic error %s", e)
        raise HTTPException(status_code=500, detail="An Internal Server Error occurred.") from e


@attendance_router.get("/event/{event_id}", response_model=EventAttendanceResponse)
async def get_event_attendance(
    event_id: str,
    attendance_service: Annotated[AttendanceService, Depends(get_attendance_service)],
    event_service: Annotated[EventRegisterService, Depends(get_event_reg_serv)],
) -> EventAttendanceResponse:
    logger.info("Getting attendance for event_id %s", event_id)

    event_exists = event_service.validate_event_id(event_id=event_id)
    if not event_exists:
        logger.error("Event not found for event_id %s", event_id)
        raise HTTPException(
            status_code=404,
            detail=f"Invalid event_id {event_id}. Event does not exist",
        )
    try:
        records = attendance_service.get_event_attendance(event_id)

        attendees = [
            AttendeeResponse(
                attendance_id=str(record.id),
                first_name=record.user.first_name if record.user else None,
                last_name=record.user.last_name if record.user else None,
                check_in_time=record.check_in_time,
            )
            for record in records
        ]

        return EventAttendanceResponse(event_id=event_id, attendees=attendees)

    except Exception as e:
        logger.error("Error getting attendance for event_id %s: %s", event_id, e)
        raise HTTPException(status_code=500, detail="An Internal Server Error occurred.") from e
