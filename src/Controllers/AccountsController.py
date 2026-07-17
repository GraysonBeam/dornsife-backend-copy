from datetime import date
from logging import getLogger
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.Database.dependencies import get_db_session
from src.Models.AccountActivation import AccountActivation
from src.Models.exceptions import NotFoundException
from src.Repositories.PendingRegistrationRepository import PendingRegistrationRepository
from src.Repositories.UsersRepository import UsersRepository
from src.Schemas.ActivateAccountRequest import ActivateAccountRequest
from src.Schemas.ActivateAccountResponse import ActivateAccountResponse
from src.Schemas.AddChildRequest import AddChildRequest
from src.Schemas.AddChildResponse import AddChildResponse
from src.Schemas.ManualLookupRequest import ManualLookupRequest
from src.Schemas.ManualLookupResponse import ManualLookupResponse
from src.Schemas.PaginatedUsersResponse import PaginatedUsersResponse
from src.Schemas.UpdateUserProfileRequest import UpdateUserProfileRequest
from src.Schemas.UpdateUserProfileResponse import UpdateUserProfileResponse
from src.Schemas.UserProfileResponse import UserProfileResponse
from src.Services.AccountService import AccountService
from src.Services.VerificationService import VerificationService
from src.Utils.Validators import ValidationError, Validator

accounts_router = APIRouter()

logger = getLogger(__name__)


def get_account_service(db: Annotated[Session, Depends(get_db_session)]) -> AccountService:
    return AccountService(
        logger,
        PendingRegistrationRepository(logger, db),
        UsersRepository(logger, db),
        VerificationService(logger),
    )


@accounts_router.post("/activate", response_model=ActivateAccountResponse)
async def activate_account(
    request: ActivateAccountRequest,
    account_service: Annotated[AccountService, Depends(get_account_service)],
) -> ActivateAccountResponse:
    # request validation first
    id: str = request.id
    verification_code: str = request.verification_code
    verification_type: str = request.verification_type.strip().lower()
    logger.info(
        "Validating activate account request: id %s, verification_code %s", id, verification_code
    )

    if verification_type != "email" and verification_type != "sms":
        logger.error(
            "Sending bad request response for invalid verification type %s", verification_type
        )
        raise HTTPException(
            status_code=400, detail=f"Invalid verification type {verification_type}"
        )

    try:
        Validator.validate_uuid_string(id)
        Validator.validate_verification_token(verification_code)
    except ValidationError as e:
        message: str = str(e)
        reason: str = "id" if "ID" in message else "verification code"
        raise HTTPException(status_code=400, detail=f"invalid {reason}: {message}") from e

    logger.info("Processing account activation")
    try:
        acct_act: AccountActivation = account_service.process_account_activation(
            id, verification_code, verification_type
        )
        return ActivateAccountResponse(
            qr_token=acct_act.qr_token, uuid=acct_act.uuid, type=acct_act.type.value
        )
    except Exception as e:
        if isinstance(e, NotFoundException):
            logger.error("Sending not found response from error %s", e)
            raise HTTPException(status_code=404, detail=e.args[0]) from e
        else:
            logger.error("Sending error response for generic error %s", e)
            raise HTTPException(status_code=500, detail="An internal server error occurred") from e


@accounts_router.get("/userProfile/{uuid}", response_model=UserProfileResponse)
async def get_user_profile(
    account_service: Annotated[AccountService, Depends(get_account_service)], uuid: str
) -> UserProfileResponse:
    try:
        user_profile = account_service.get_user_profile_by_uuid(uuid)
        if user_profile is None:
            raise NotFoundException("User not found")
        return UserProfileResponse(
            first_name=user_profile["first_name"],
            last_name=user_profile["last_name"],
            email=user_profile["email"] or None,
            phone_number=user_profile["phone_number"] or None,
            date_of_birth=user_profile["date_of_birth"],
            zip_code=user_profile["zip_code"] or None,
            address=user_profile["address"] or None,
            race=user_profile["race"],
        )
    except Exception as e:
        if isinstance(e, NotFoundException):
            logger.error("User not found")
            raise HTTPException(status_code=404, detail=e.args[0]) from e
        else:
            logger.error("Sending error response for generic error %s", e)
            raise HTTPException(status_code=500, detail="An internal server error occurred") from e


@accounts_router.put("/userProfile/{uuid}", response_model=UpdateUserProfileResponse)
async def update_user_profile(
    uuid: str,
    request: UpdateUserProfileRequest,
    account_service: Annotated[AccountService, Depends(get_account_service)],
) -> UpdateUserProfileResponse:
    logger.info("Received profile update request for uuid %s", uuid)

    try:
        Validator.validate_uuid_string(uuid)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"Invalid token: {e}") from e

    if request.email is not None:
        try:
            Validator.validate_email(request.email)
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=f"Invalid email: {e}") from e

    if request.phone_number is not None:
        try:
            Validator.validate_phone_number(request.phone_number)
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=f"Invalid phone number: {e}") from e

    date_of_birth: date | None = None
    if request.date_of_birth is not None:
        try:
            date_of_birth = Validator.validate_date_of_birth(request.date_of_birth)
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=f"Invalid date of birth: {e}") from e

    if request.zip_code is not None:
        try:
            Validator.validate_zip_code(request.zip_code)
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=f"Invalid zip code: {e}") from e

    try:
        result = account_service.update_user_profile(
            uuid=uuid,
            first_name=request.first_name,
            last_name=request.last_name,
            email=request.email,
            phone_number=request.phone_number,
            date_of_birth=date_of_birth,
            zip_code=request.zip_code,
            address=request.address,
            race_id=request.race_id,
        )
    except NotFoundException as e:
        logger.error("User not found during profile update: %s", e)
        raise HTTPException(status_code=404, detail=e.args[0]) from e
    except ValidationError as e:
        logger.error("Validation error during profile update: %s", e)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("Unexpected error during profile update for %s: %s", uuid, e)
        raise HTTPException(status_code=500, detail="An internal server error occurred") from e

    return UpdateUserProfileResponse(
        message=str(result.get("message") or ""),
        pending_registration_id=result.get("pending_registration_id"),
        first_name=result.get("first_name"),
        last_name=result.get("last_name"),
        email=result.get("email"),
        phone_number=result.get("phone_number"),
        date_of_birth=result.get("date_of_birth"),
        zip_code=result.get("zip_code"),
        address=result.get("address"),
        race=result.get("race"),
    )


@accounts_router.post("/add-child", response_model=AddChildResponse)
async def add_child(
    request: AddChildRequest,
    account_service: Annotated[AccountService, Depends(get_account_service)],
) -> AddChildResponse:
    try:
        return account_service.add_child(request)
    except Exception as e:
        if isinstance(e, NotFoundException):
            logger.error("Parent not found: %s", e)
            raise HTTPException(status_code=404, detail=e.args[0]) from e
        elif isinstance(e, ValidationError):
            logger.error("Invalid add child request: %s", e)
            raise HTTPException(status_code=400, detail=str(e)) from e
        else:
            logger.error("Error adding child: %s", e)
            raise HTTPException(status_code=500, detail="An internal server error occurred") from e


@accounts_router.post("/lookup")
def lookup_users(
    request: ManualLookupRequest,
    account_service: Annotated[AccountService, Depends(get_account_service)],
) -> list[ManualLookupResponse]:
    logger.info("Processing manual lookup request")
    try:
        results = account_service.lookup_users(
            email=request.email, phone_number=request.phone_number
        )
        return [ManualLookupResponse(**res) for res in results]
    except Exception as e:
        logger.error("Error in manual lookup: %s", e)
        raise HTTPException(status_code=500, detail="An internal server error occurred") from e


@accounts_router.get("/users/paginated", response_model=list[PaginatedUsersResponse])
async def get_users_paginated(
    page: Annotated[int, Query(ge=1, description="1-based page number")],
    account_service: Annotated[AccountService, Depends(get_account_service)],
) -> list[PaginatedUsersResponse]:
    displayed_users = account_service.get_users_paginated(page, 10)
    return [PaginatedUsersResponse(**vars(u)) for u in displayed_users]
