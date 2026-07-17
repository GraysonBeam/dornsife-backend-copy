from __future__ import annotations

from datetime import date
from logging import Logger

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, aliased

from src.Models.DisplayUserRecord import DisplayUserRecord
from src.Models.User import RaceLookup, User
from src.Utils.Validators import ValidationError, Validator


class UsersRepository:
    def __init__(self, logger: Logger, db: Session):
        self.logger = logger
        self.db = db

    def get_user_by_id(self, user_id: str):
        self.logger.info(f"Retrieving user with id: {user_id}")
        return self.db.get(User, user_id)

    def get_race(self, user_id: str, race_id: int) -> str:
        self.logger.info(f"Retrieving race from user: {user_id}")
        race = self.db.get(RaceLookup, race_id)
        if race is None:
            raise ValueError("Race not found")
        return race.description

    def get_user_by_qr(self, qr_token: str):
        self.logger.info(f"Retrieving user with qr: {qr_token}")
        user = self.db.query(User).filter(User.qr_token == qr_token).first()
        if user and user.is_active:
            return user
        return None

    def get_users_by_email(self, email: str) -> list[User]:
        self.logger.info(f"Retrieving users with email: {email}")
        return (
            self.db.query(User).filter(User.email == email).filter(User.is_active.is_(True)).all()
        )

    def get_users_by_phone_number(self, phone_number: str) -> list[User]:
        self.logger.info(f"Retrieving users with phone number: {phone_number}")
        validated_phone_number = Validator.validate_phone_number(phone_number)
        return (
            self.db.query(User)
            .filter(User.phone_number == validated_phone_number)
            .filter(User.is_active.is_(True))
            .all()
        )

    def set_active_status(self, user: User, is_active: bool):
        user.is_active = is_active
        self.db.add(user)

    def set_email(self, user: User, new_email: str):
        validated_email = Validator.validate_email(new_email)
        user.email = validated_email
        user.phone_number = None
        self.db.add(user)

    def set_phone_number(self, user: User, new_phone_number: str):
        validated_phone_number = Validator.validate_phone_number(new_phone_number)
        user.email = None
        user.phone_number = validated_phone_number
        self.db.add(user)

    # soft-delete a user with its id
    def delete_user(self, user_id: str):
        user = self.get_user_by_id(user_id)
        if not user:
            self.logger.warning(f"User with id: {user_id} not found")
            return "user_not_found"

        if not user.is_active:
            self.logger.warning(f"User with id: {user_id} already deleted")
            return "already_deleted"

        self.set_active_status(user, False)
        self.logger.info(f"User with id: {user_id} is deleted")
        return "deleted"

    def get_all_races_from_db(self) -> list[tuple[int, str]] | None:
        """Returns array of race options"""
        race_table = self.db.query(RaceLookup).all()

        if not race_table:
            self.logger.warning("Error extracting race from Race_Lookup table")
            return

        res: list[tuple[int, str]] = []
        for race in race_table:
            res.append((race.race_id, race.description))

        return res

    # add and validate users info to the database and returns user id
    def add_user(
        self,
        first_name: str,
        last_name: str,
        email: str | None,
        phone_number: str | None,
        date_of_birth: str,
        zip_code: str,
        address: str,
        race_id: int,
        qr_token: str,
        parent_id: str | None,
        is_active: bool = False,
    ) -> User:
        self.logger.info(
            "Attempting to create user with email: %s, phone_number: %s", email, phone_number
        )

        try:
            validated_email, validated_phone = Validator.validate_contact_fields(
                email,
                phone_number,
                require_one=True,
                missing_message="Either email or phone_number is required",
            )

            # Validate all inputs
            validated_first_name = Validator.validate_required_string(first_name, "First name")
            validated_last_name = Validator.validate_required_string(last_name, "Last name")
            validated_dob = Validator.validate_date_of_birth(date_of_birth)
            validated_zip = Validator.validate_zip_code(zip_code)

            # Create user
            new_user = User(
                first_name=validated_first_name,
                last_name=validated_last_name,
                email=validated_email,
                phone_number=validated_phone,
                date_of_birth=validated_dob,
                zip_code=validated_zip,
                address=address,
                race_id=race_id,
                qr_token=qr_token,
                parent_id=parent_id,
                is_active=is_active,
            )

            self.db.add(new_user)
            self.db.flush()

            self.logger.info(
                "Created inactive user with ID %s (email=%s, phone_number=%s)",
                new_user.id,
                validated_email,
                validated_phone,
            )
            return new_user

        except IntegrityError as e:
            if "qr_token" in str(e.orig):
                raise ValidationError("QR token already exists") from e
            raise

        except SQLAlchemyError as e:
            self.logger.error(f"Database error creating user {email}: {str(e)}")
            raise

    def update_user_fields(
        self,
        user_id: str,
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
        phone_number: str | None = None,
        date_of_birth: date | None = None,
        zip_code: str | None = None,
        address: str | None = None,
        race_id: int | None = None,
    ) -> str:
        self.logger.info(f"Attempting to update fields for user {user_id}")

        user = self.get_user_by_id(user_id)

        if not user:
            self.logger.warning(f"User {user_id} not found")
            return "user_not_found"

        if not user.is_active:
            self.logger.warning(f"User {user_id} is inactive, update rejected")
            return "user_inactive"

        validated_email, validated_phone_number = Validator.validate_contact_fields(
            email,
            phone_number,
            require_one=False,
        )

        updates: dict[str, str | date | int | None] = {
            "first_name": first_name,
            "last_name": last_name,
            "date_of_birth": date_of_birth,
            "zip_code": zip_code,
            "address": address,
            "race_id": race_id,
        }

        if validated_email:
            updates["email"] = validated_email
            updates["phone_number"] = None

        if validated_phone_number:
            updates["email"] = None
            updates["phone_number"] = validated_phone_number

        updated_fields: list[str] = []
        for field, value in updates.items():
            if value is not None:
                setattr(user, field, value)
                updated_fields.append(field)
            elif field in {"email", "phone_number"}:
                setattr(user, field, None)
                updated_fields.append(field)

        if not updated_fields:
            self.logger.info(f"No fields provided to update for user {user_id}")
            return "no_fields_provided"

        try:
            self.db.flush()
        except IntegrityError as e:
            self.logger.error(f"Integrity error updating user {user_id}: {e}")
            raise ValidationError("Invalid race_id provided") from e

        self.logger.info(f"Successfully updated {updated_fields} for user {user_id}")
        return "success"

    def get_users_paginated(self, page: int, page_size: int) -> list[DisplayUserRecord]:
        self.logger.info(f"Retrieving users paginated: page {page}, page size {page_size}")
        ParentUser = aliased(User)
        rows = (
            self.db.query(
                User,
                RaceLookup.description.label("race_description"),
                ParentUser.first_name.label("parent_first_name"),
                ParentUser.last_name.label("parent_last_name"),
            )
            .join(RaceLookup, User.race_id == RaceLookup.race_id)
            .outerjoin(ParentUser, User.parent_id == ParentUser.id)
            .order_by(User.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return [
            DisplayUserRecord(
                first_name=user.first_name,
                last_name=user.last_name,
                email=user.email,
                phone_number=user.phone_number,
                date_of_birth=user.date_of_birth.strftime("%Y-%m-%d")
                if user.date_of_birth
                else None,
                zip_code=user.zip_code,
                address=user.address,
                race_description=race_description,
                is_active=user.is_active,
                parent_first_name=parent_first_name,
                parent_last_name=parent_last_name,
            )
            for user, race_description, parent_first_name, parent_last_name in rows
        ]
