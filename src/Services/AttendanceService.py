from logging import Logger

from src.Models.Attendance import Attendance
from src.Models.CheckInProof import CheckInProof
from src.Models.exceptions import NotFoundException
from src.Models.User import User
from src.Repositories.AttendanceRepository import AttendanceRepository
from src.Repositories.UsersRepository import UsersRepository


class AttendanceService:
    def __init__(
        self, logger: Logger, attendance_repo: AttendanceRepository, user_repo: UsersRepository
    ):
        self.logger = logger
        self.attendance_repo = attendance_repo
        self.user_repo = user_repo

    def check_into_event(
        self, qr_token: str, event_id: str, check_in_method_id: int
    ) -> CheckInProof:
        self.logger.info("Starting to check into event id %s", event_id)

        self.logger.info("Getting user from qr code token %s", qr_token)
        user: User | None = self.user_repo.get_user_by_qr(qr_token)

        if user is None:
            self.logger.error("User with qr_token %s not found", qr_token)
            raise NotFoundException("User not found from qr_token provided")

        self.logger.info(
            "Creating attendance record for user id %s at event d %s", user.id, event_id
        )

        check_in_record: CheckInProof = self.attendance_repo.create_attendance_record(
            user_id=user.id,
            event_instance_id=event_id,
            check_in_method_id=check_in_method_id,
        )

        return check_in_record

    def get_event_zip_bucket(self, event_id: str):
        return self.attendance_repo.get_event_zip_bucket(event_id)

    def get_event_race_bucket(self, event_id: str):
        return self.attendance_repo.get_event_race_bucket(event_id)

    def get_event_age_bucket(self, event_id: str):
        return self.attendance_repo.get_event_age_bucket(event_id)

    def get_event_attendance(self, event_id: str) -> list[Attendance]:
        self.logger.info("Getting attendance for event_id %s", event_id)
        return self.attendance_repo.get_attendance_by_event_id(event_id)
