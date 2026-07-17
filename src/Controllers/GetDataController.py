from datetime import datetime
from logging import getLogger
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.Database.dependencies import get_db_session
from src.Repositories.AttendanceRepository import AttendanceRepository
from src.Schemas.DataAfterDateResponse import DataAfterDateResponse
from src.Schemas.EventAttendanceDataResponse import EventAttendanceDataResponse
from src.Services.AdminAnalyticsService import AdminAnalyticsService

data_router = APIRouter()

logger = getLogger(__name__)


def get_admin_analytics_service(
    db: Annotated[Session, Depends(get_db_session)],
) -> AdminAnalyticsService:
    """Dependency to get AdminAnalyticsService instance."""
    return AdminAnalyticsService(
        logger=logger,
        attendance_repository=AttendanceRepository(logger, db),
    )


@data_router.get(
    "/dataAfterDate",
    response_model=DataAfterDateResponse,
    summary="Get attendance analytics data after a date",
    description="Retrieve attendance data for events starting on or after the specified date. "
    "Returns deidentified attendance records suitable for statistical analysis.",
)
async def get_attendance_data_after_date(
    date: Annotated[
        datetime, Query(description="Date (inclusive) to retrieve attendance data after")
    ],
    admin_analytics_service: Annotated[AdminAnalyticsService, Depends(get_admin_analytics_service)],
) -> DataAfterDateResponse:
    """
    Get attendance analytics data for events after a specified date.

    This endpoint returns attendance records without sensitive PII (like names, emails, DOB),
    making it suitable for statistical analysis and reporting to staff.

    Query Parameters:
    - date: ISO 8601 formatted date (e.g., 2024-01-15 or 2024-01-15T10:00:00)

    Returns:
    - records: List of attendance analytics records with event and user data
    - total_count: Total number of records returned
    """
    logger.info("Received request for attendance data after date: %s", date)

    try:
        result = admin_analytics_service.get_attendance_data_after_date(date)
        logger.info(
            "Successfully retrieved %d attendance records after date %s", result.total_count, date
        )
        return result

    except SQLAlchemyError as e:
        logger.error("Database error retrieving attendance data after date %s: %s", date, e)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while retrieving attendance data",
        ) from e

    except Exception as e:
        logger.error("Unexpected error retrieving attendance data after date %s: %s", date, e)
        raise HTTPException(
            status_code=500,
            detail="An internal server error occurred",
        ) from e


@data_router.get(
    "/eventAttendanceData/{event_id}",
    response_model=EventAttendanceDataResponse,
    summary="Get attendance analytics data for a specific event",
    description="Retrieve attendance analytics data for a specific event ID. "
    "Returns deidentified attendance records suitable for statistical analysis.",
)
async def get_attendance_data_by_event_id(
    event_id: Annotated[
        str, Path(description="The ID of the event to retrieve attendance data for")
    ],
    admin_analytics_service: Annotated[AdminAnalyticsService, Depends(get_admin_analytics_service)],
) -> EventAttendanceDataResponse:
    """
    Get attendance analytics data for a specific event.

    This endpoint returns attendance records for a single event without sensitive PII
    (like names, emails, DOB), making it suitable for statistical analysis and reporting to staff.

    Path Parameters:
    - event_id: UUID of the event

    Returns:
    - records: List of attendance analytics records with event and user data
    - total_count: Total number of records returned
    """
    logger.info("Received request for attendance data for event_id: %s", event_id)

    if not event_id or not event_id.strip():
        logger.warning("Received request with empty event_id")
        raise HTTPException(
            status_code=400,
            detail="event_id parameter is required and cannot be empty",
        )

    try:
        result = admin_analytics_service.get_attendance_data_by_event_id(event_id)
        logger.info(
            "Successfully retrieved %d attendance records for event_id %s",
            result.total_count,
            event_id,
        )
        return result

    except SQLAlchemyError as e:
        logger.error("Database error retrieving attendance data for event_id %s: %s", event_id, e)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while retrieving attendance data",
        ) from e

    except Exception as e:
        logger.error("Unexpected error retrieving attendance data for event_id %s: %s", event_id, e)
        raise HTTPException(
            status_code=500,
            detail="An internal server error occurred",
        ) from e
