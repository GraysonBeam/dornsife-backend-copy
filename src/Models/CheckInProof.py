from datetime import datetime


class CheckInProof:
    def __init__(self, attendance_id: str, timestamp: datetime) -> None:
        self.attendance_id = attendance_id
        self.timestamp = timestamp
