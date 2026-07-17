from logging import getLogger
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.Database.dependencies import get_db_session
from src.Models.exceptions import NotFoundException, RegistrationExpiredException
from src.Repositories.PendingRegistrationRepository import PendingRegistrationRepository
from src.Repositories.UsersRepository import UsersRepository
from src.Schemas.RaceOptionsResponse import RaceOptionsResponse
from src.Schemas.ResendVerificationRequest import ResendVerificationRequest
from src.Schemas.ResendVerificationResponse import ResendVerificationResponse
from src.Schemas.UserRegistrationRequest import UserRegistrationRequest
from src.Schemas.UserRegistrationResponse import UserRegistrationResponse
from src.Services.ResendVerificationService import ResendVerificationService
from src.Services.UserRegisterService import UserRegisterService
from src.Services.VerificationService import VerificationService
from src.Utils.Validators import ValidationError, Validator

user_register_router = APIRouter()

logger = getLogger(__name__)


def get_user_reg_service(db: Annotated[Session, Depends(get_db_session)]) -> UserRegisterService:
    return UserRegisterService(
        logger,
        UsersRepository(logger, db),
        PendingRegistrationRepository(logger, db),
        VerificationService(logger),
    )


def get_resend_service(
    db: Annotated[Session, Depends(get_db_session)],
) -> ResendVerificationService:
    return ResendVerificationService(
        logger, PendingRegistrationRepository(logger, db), VerificationService(logger)
    )


@user_register_router.get("/raceOptions", response_model=RaceOptionsResponse)
async def get_all_races(
    user_reg_serv: Annotated[UserRegisterService, Depends(get_user_reg_service)],
) -> RaceOptionsResponse:
    try:
        races = user_reg_serv.get_race_options()
        return RaceOptionsResponse(races=races if races else [])
    except Exception as e:
        logger.error("Error getting race options: %s", e)
        raise HTTPException(status_code=500, detail="An internal server error occurred") from e


@user_register_router.post("/resend", response_model=ResendVerificationResponse)
async def resend_verification_email(
    request: ResendVerificationRequest,
    resend_service: Annotated[ResendVerificationService, Depends(get_resend_service)],
) -> ResendVerificationResponse:
    pending_registration_id = request.pending_registration_id
    logger.info("Received resend request for pending registration %s", pending_registration_id)
    verification_type = request.verification_type.strip().lower()
    if verification_type != "email" and verification_type != "sms":
        logger.error(
            "Sending bad request response for invalid verification type %s", verification_type
        )
        raise HTTPException(
            status_code=400, detail=f"Invalid verification type: {verification_type}"
        )

    try:
        Validator.validate_uuid_string(pending_registration_id)
    except ValidationError as exc:
        logger.warning("Invalid pending_registration_id: %s", exc)
        raise HTTPException(
            status_code=400, detail=f"invalid pending_registration_id: {exc}"
        ) from exc

    try:
        resend_service.resend_verification(pending_registration_id, verification_type)
        return ResendVerificationResponse(status="success")
    except RegistrationExpiredException as exc:
        logger.warning("Resend rejected — registration %s is expired", pending_registration_id)
        raise HTTPException(status_code=410, detail=str(exc)) from exc
    except NotFoundException as exc:
        logger.error("Resend rejected — %s not found", pending_registration_id)
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Resend failed with unexpected error: %s", exc)
        raise HTTPException(status_code=500, detail="An internal server error occurred") from exc


@user_register_router.post("/user", response_model=UserRegistrationResponse)
async def register_user(
    user_payload: UserRegistrationRequest,
    user_reg_serv: Annotated[UserRegisterService, Depends(get_user_reg_service)],
) -> UserRegistrationResponse:
    try:
        pending_id = user_reg_serv.create_inactive_user(user_payload)
        if not pending_id:
            raise HTTPException(status_code=500, detail="Registration failed")
        response = UserRegistrationResponse(status="success", pending_registration_id=pending_id)
        return response
    except HTTPException:
        raise
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Registration failed") from exc
