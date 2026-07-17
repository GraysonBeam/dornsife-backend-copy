from datetime import datetime
from logging import Logger
from typing import Any

from sqlalchemy import Row
from sqlalchemy.exc import SQLAlchemyError

from src.Repositories.AttendanceRepository import AttendanceRepository
from src.Schemas.AttendanceAnalyticsRecord import AttendanceAnalyticsRecord
from src.Schemas.DataAfterDateResponse import DataAfterDateResponse
from src.Schemas.EventAttendanceDataResponse import EventAttendanceDataResponse


class AdminAnalyticsService:
    """Service for retrieving and formatting attendance analytics data for admin dashboard.

    Handles fetching attendance data and converting it into analytics-friendly formats
    that exclude sensitive PII while providing statistical insights.
    """

    def __init__(self, logger: Logger, attendance_repository: AttendanceRepository):
        self.logger = logger
        self.attendance_repository = attendance_repository

    def _convert_to_analytics_records(
        self, records: list[Row[Any]]
    ) -> list[AttendanceAnalyticsRecord]:
        analytics_records = [
            AttendanceAnalyticsRecord(
                event_name=record[0],
                event_start_time=record[1],
                event_end_time=record[2],
                event_location=record[3],
                event_type=record[4],
                user_age=record[5],
                user_zip_code=record[6],
                has_parent=record[7],
                check_in_method=record[8],
                user_race=record[9],
            )
            for record in records
        ]
        return analytics_records

    def get_attendance_data_after_date(self, date: datetime) -> DataAfterDateResponse:
        """Get attendance analytics data for events after a specified date.

        Args:
            date: The date after which to retrieve event data (inclusive)

        Returns:
            DataAfterDateResponse containing analytics records and total count

        Raises:
            SQLAlchemyError if database query fails
        """
        self.logger.info("Retrieving attendance analytics data after date %s", date)

        try:
            records = self.attendance_repository.get_analytics_data_after_date(date)
            analytics_records = self._convert_to_analytics_records(records)

            self.logger.info(
                "Successfully formatted %d analytics records for date %s",
                len(analytics_records),
                date,
            )

            return DataAfterDateResponse(
                records=analytics_records,
                total_count=len(analytics_records),
            )

        except SQLAlchemyError as e:
            self.logger.error(
                "Error retrieving attendance analytics data after date %s: %s",
                date,
                e,
            )
            raise

    def get_attendance_data_by_event_id(self, event_id: str) -> EventAttendanceDataResponse:
        """Get attendance analytics data for a specific event.

        Args:
            event_id: The ID of the event to retrieve attendance data for

        Returns:
            EventAttendanceDataResponse containing analytics records and total count

        Raises:
            SQLAlchemyError if database query fails
        """
        self.logger.info("Retrieving attendance analytics data for event_id %s", event_id)

        try:
            records = self.attendance_repository.get_analytics_data_by_event_id(event_id)
            analytics_records = self._convert_to_analytics_records(records)

            self.logger.info(
                "Successfully formatted %d analytics records for event_id %s",
                len(analytics_records),
                event_id,
            )

            return EventAttendanceDataResponse(
                records=analytics_records,
                total_count=len(analytics_records),
            )

        except SQLAlchemyError as e:
            self.logger.error(
                "Error retrieving attendance analytics data for event_id %s: %s",
                event_id,
                e,
            )
            raise
