from collections.abc import Sequence
from datetime import datetime
from logging import Logger
from typing import Any

from sqlalchemy import Integer, case, func
from sqlalchemy.engine import Row
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from src.Models.Attendance import Attendance
from src.Models.CheckInMethodType import CheckInMethodType
from src.Models.CheckInProof import CheckInProof
from src.Models.Event import Event
from src.Models.EventType import EventType
from src.Models.User import RaceLookup, User
from src.Utils.Validators import ValidationError


class AttendanceRepository:
    def __init__(self, logger: Logger, db: Session):
        self.logger = logger
        self.db = db

    def delete_by_id(self, id: str) -> str:
        record = self.db.get(Attendance, id)

        if not record:
            self.logger.warning(f"Record {id} not found")
            return "NOT_FOUND"

        try:
            self.db.delete(record)
            self.logger.info(f"Deleted attendance record {id}")
            return "RECORD_DELETED"

        except IntegrityError as e:
            self.logger.error(f"Cannot delete record {id} due to constraints: {e}")
            raise

    def create_attendance_record(
        self, user_id: str, event_instance_id: str, check_in_method_id: int
    ) -> CheckInProof:
        self.logger.info(
            "Creating and inserting attendance record for User %s at event %s",
            user_id,
            event_instance_id,
        )
        try:
            new_record: Attendance = Attendance(
                user_id=user_id,
                event_instance_id=event_instance_id,
                check_in_method_id=check_in_method_id,
            )

            self.db.add(new_record)
            self.db.flush()
        except IntegrityError as e:
            if "unique" in str(e.orig).lower():
                self.logger.error(
                    "Attendance record for user id %s at event id %s already exists",
                    user_id,
                    event_instance_id,
                )
                raise ValidationError(
                    "Attendance record for this user and event combination already exists"
                ) from e
            raise
        except SQLAlchemyError as e:
            self.logger.error(
                "Error creating attendance record with user_id %s for event %s due to error: %s",
                user_id,
                event_instance_id,
                e,
            )
            raise

        # new_record should be updated with fields generated server side
        # if insert succeeds, otherwise error
        return CheckInProof(new_record.id, new_record.created_at)

    def get_event_zip_bucket(self, event_id: str) -> Sequence[Row[tuple[str | None, int]]]:
        try:
            return (
                self.db.query(
                    User.zip_code,
                    func.count(User.zip_code).label("zip_code_count"),
                )
                .select_from(Attendance)
                .join(User, Attendance.user_id == User.id)
                .where(Attendance.event_instance_id == event_id)
                .where(User.zip_code.isnot(None))
                .group_by(User.zip_code)
                .order_by(func.count(User.zip_code).desc())
                .all()
            )
        except SQLAlchemyError as e:
            self.logger.error(
                "Database error fetching zip buckets for event %s: %s",
                event_id,
                e,
            )
            raise

    def get_event_race_bucket(self, event_id: str) -> Sequence[Row[tuple[str, int]]]:
        try:
            return (
                self.db.query(
                    RaceLookup.description,
                    func.count(User.race_id).label("race_count"),
                )
                .select_from(Attendance)
                .join(User, Attendance.user_id == User.id)
                .join(RaceLookup, User.race_id == RaceLookup.race_id)
                .where(Attendance.event_instance_id == event_id)
                .where(User.race_id.isnot(None))
                .group_by(RaceLookup.description)
                .order_by(func.count(User.race_id).desc())
                .all()
            )
        except SQLAlchemyError as e:
            self.logger.error(
                "Database error fetching race buckets for event %s: %s",
                event_id,
                e,
            )
            raise

    def get_event_age_bucket(self, event_id: str) -> Sequence[Row[tuple[str, int]]]:
        try:
            age = func.extract(
                "year",
                func.age(func.current_date(), User.date_of_birth),
            )

            age_bucket = case(
                (age < 18, "Under 18"),
                (age.between(18, 24), "18-24"),
                (age.between(25, 34), "25-34"),
                (age.between(35, 44), "35-44"),
                else_="45+",
            ).label("age_bucket")

            return (
                self.db.query(
                    age_bucket,
                    func.count().label("attendee_count"),
                )
                .select_from(Attendance)
                .join(User, Attendance.user_id == User.id)
                .where(Attendance.event_instance_id == event_id)
                .where(User.date_of_birth.isnot(None))
                .group_by(age_bucket)
                .order_by(age_bucket)
                .all()
            )
        except SQLAlchemyError as e:
            self.logger.error(
                "Database error fetching age buckets for event %s: %s",
                event_id,
                e,
            )
            raise

    def get_attendance_by_event_id(self, event_id: str) -> list[Attendance]:
        self.logger.info("Fetching attendance records for event_id %s", event_id)

        records = self.db.query(Attendance).filter(Attendance.event_instance_id == event_id).all()

        self.logger.info("Found %d attendance record(s) for event_id %s", len(records), event_id)
        return records

    def _analytics_records_query(self):
        """Build admin analytics query (lazy; call .where/.order_by/.all() to execute)."""
        age = func.cast(
            (func.extract("year", func.current_date()) - func.extract("year", User.date_of_birth)),
            Integer(),
        )
        has_parent = User.parent_id.isnot(None)

        return (
            self.db.query(
                Event.name.label("event_name"),
                Event.start_datetime.label("event_start_time"),
                Event.end_datetime.label("event_end_time"),
                Event.location.label("event_location"),
                EventType.type.label("event_type"),
                age.label("user_age"),
                User.zip_code.label("user_zip_code"),
                has_parent.label("has_parent"),
                CheckInMethodType.methodtype.label("check_in_method"),
                RaceLookup.description.label("user_race"),
            )
            .select_from(Attendance)
            .join(Event, Attendance.event_instance_id == Event.id)
            .join(EventType, Event.type_id == EventType.id)
            .join(User, Attendance.user_id == User.id, isouter=True)
            .join(RaceLookup, User.race_id == RaceLookup.race_id, isouter=True)
            .join(
                CheckInMethodType,
                Attendance.check_in_method_id == CheckInMethodType.checkinid,
            )
        )

    def get_analytics_data_after_date(self, date: datetime) -> list[Row[Any]]:
        """Get analytics data for attendance records after a specified date.

        Returns rows containing:
        (event_name, event_start_time, event_end_time, event_location, event_type,
         user_age, user_zip_code, has_parent, check_in_method, user_race)

        Results are ordered by event start time.
        """
        self.logger.info("Fetching analytics data for attendance records after date %s", date)

        try:
            records = (
                self._analytics_records_query()
                .where(Event.start_datetime >= date)
                .order_by(Event.start_datetime.asc())
                .all()
            )

            self.logger.info(
                "Found %d analytics records for attendance after date %s",
                len(records),
                date,
            )
            return records

        except SQLAlchemyError as e:
            self.logger.error(
                "Database error fetching analytics data after date %s: %s",
                date,
                e,
            )
            raise

    def get_analytics_data_by_event_id(self, event_id: str) -> list[Row[Any]]:
        """Get analytics data for attendance records for a specific event.

        Returns rows containing:
        (event_name, event_start_time, event_end_time, event_location, event_type,
         user_age, user_zip_code, has_parent, check_in_method, user_race)

        Results are ordered by check-in time.
        """
        self.logger.info("Fetching analytics data for event_id %s", event_id)

        try:
            records = (
                self._analytics_records_query()
                .where(Attendance.event_instance_id == event_id)
                .order_by(Attendance.check_in_time.asc())
                .all()
            )

            self.logger.info(
                "Found %d analytics records for event_id %s",
                len(records),
                event_id,
            )
            return records

        except SQLAlchemyError as e:
            self.logger.error(
                "Database error fetching analytics data for event_id %s: %s",
                event_id,
                e,
            )
            raise
