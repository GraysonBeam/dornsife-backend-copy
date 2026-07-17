from datetime import UTC, datetime, timedelta

import pytest

from src.Utils.Validators import ValidationError, Validator


def test_validate_event_time_success() -> None:
    """Test validation passes with valid future times."""
    now = datetime.now(UTC)
    start = now + timedelta(hours=1)
    end = now + timedelta(hours=2)

    Validator.validate_event_time(start, end)


def test_validate_event_time_end_before_start() -> None:
    """Test validation fails when end is before start."""
    now = datetime.now(UTC)
    start = now + timedelta(hours=2)
    end = now + timedelta(hours=1)

    with pytest.raises(ValidationError) as exc_info:
        Validator.validate_event_time(start, end)

    assert "end_datetime must be after start_datetime" in str(exc_info.value)


def test_validate_event_time_end_equals_start() -> None:
    """Test validation fails when end equals start."""
    now = datetime.now(UTC) + timedelta(hours=1)

    with pytest.raises(ValidationError) as exc_info:
        Validator.validate_event_time(now, now)

    assert "end_datetime must be after start_datetime" in str(exc_info.value)


def test_validate_event_time_start_in_past() -> None:
    """Test validation fails when start is in the past."""
    now = datetime.now(UTC)
    start = now - timedelta(hours=1)
    end = now + timedelta(hours=1)

    with pytest.raises(ValidationError) as exc_info:
        Validator.validate_event_time(start, end)

    assert "start_datetime cannot be in the past" in str(exc_info.value)


def test_validate_event_time_with_naive_datetime() -> None:
    """Test validation works with naive datetime in future."""
    now = datetime.now(UTC)
    start = now + timedelta(hours=1)
    end = now + timedelta(hours=2)

    Validator.validate_event_time(start, end)


def test_validate_event_time_with_naive_datetime_in_past() -> None:
    """Test validation fails with naive datetime in past."""
    now = datetime.now(UTC)
    start = now - timedelta(hours=1)
    end = now + timedelta(hours=1)

    with pytest.raises(ValidationError) as exc_info:
        Validator.validate_event_time(start, end)

    assert "start_datetime cannot be in the past" in str(exc_info.value)
