import os
from unittest.mock import MagicMock

os.environ.setdefault("VERIFICATION_TTL", "1440")

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.Controllers.UserRegisterController import get_resend_service
from src.Models.exceptions import NotFoundException, RegistrationExpiredException
from src.Services.ResendVerificationService import ResendVerificationService


@pytest.fixture
def app():
    from src.main import app

    return app


@pytest.fixture
def client(app: FastAPI):
    return TestClient(app)


@pytest.fixture
def mock_resend_service():
    return MagicMock(spec=ResendVerificationService)


def test_resend_success(client: TestClient, app: FastAPI, mock_resend_service: MagicMock):
    mock_resend_service.resend_verification.return_value = None
    app.dependency_overrides[get_resend_service] = lambda: mock_resend_service

    response = client.post(
        "/userRegistration/resend",
        json={
            "pending_registration_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "verification_type": "email",
        },
    )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    mock_resend_service.resend_verification.assert_called_once_with(
        "3fa85f64-5717-4562-b3fc-2c963f66afa6", "email"
    )


def test_resend_returns_404_when_not_found(
    client: TestClient, app: FastAPI, mock_resend_service: MagicMock
):
    mock_resend_service.resend_verification.side_effect = NotFoundException(
        "Pending registration not found"
    )
    app.dependency_overrides[get_resend_service] = lambda: mock_resend_service

    response = client.post(
        "/userRegistration/resend",
        json={
            "pending_registration_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "verification_type": "email",
        },
    )

    app.dependency_overrides.clear()
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_resend_returns_410_when_expired(
    client: TestClient, app: FastAPI, mock_resend_service: MagicMock
):
    mock_resend_service.resend_verification.side_effect = RegistrationExpiredException(
        "Pending registration has expired"
    )
    app.dependency_overrides[get_resend_service] = lambda: mock_resend_service

    response = client.post(
        "/userRegistration/resend",
        json={
            "pending_registration_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "verification_type": "sms",
        },
    )

    app.dependency_overrides.clear()
    assert response.status_code == 410
    assert "expired" in response.json()["detail"].lower()


def test_resend_returns_400_for_invalid_uuid(
    client: TestClient, app: FastAPI, mock_resend_service: MagicMock
):
    app.dependency_overrides[get_resend_service] = lambda: mock_resend_service

    response = client.post(
        "/userRegistration/resend",
        json={"pending_registration_id": "not-a-uuid", "verification_type": "email"},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 400
    assert "pending_registration_id" in response.json()["detail"]
    mock_resend_service.resend_verification.assert_not_called()


def test_resend_returns_500_on_unexpected_error(
    client: TestClient, app: FastAPI, mock_resend_service: MagicMock
):
    mock_resend_service.resend_verification.side_effect = Exception("unexpected db failure")
    app.dependency_overrides[get_resend_service] = lambda: mock_resend_service

    response = client.post(
        "/userRegistration/resend",
        json={
            "pending_registration_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "verification_type": "email",
        },
    )

    app.dependency_overrides.clear()
    assert response.status_code == 500
    assert response.json()["detail"] == "An internal server error occurred"


def test_resend_returns_400_on_invalid_verification_type(
    client: TestClient, app: FastAPI, mock_resend_service: MagicMock
):
    app.dependency_overrides[get_resend_service] = lambda: mock_resend_service

    response = client.post(
        "/userRegistration/resend",
        json={
            "pending_registration_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "verification_type": "type",
        },
    )
    app.dependency_overrides.clear()
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid verification type: type"
