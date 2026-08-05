import logging

from app.config.settings import Settings
from app.domain.entities.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.security.passwords import hash_password, verify_password
from app.security.tokens import create_access_token, create_refresh_token

logger = logging.getLogger("app.auth")


class AuthenticationError(ValueError):
    """Raised when credentials cannot authenticate an active local user."""


class AuthService:
    def __init__(self, users: UserRepository, settings: Settings) -> None:
        self._users = users
        self._settings = settings

    def ensure_initial_administrator(self) -> User | None:
        if self._users.has_role(UserRole.ADMINISTRATOR):
            return None
        if not self._settings.admin_email or not self._settings.admin_password:
            raise RuntimeError(
                "ADMIN_EMAIL and ADMIN_PASSWORD are required when no Administrator exists."
            )
        return self._users.add(
            User(
                email=self._settings.admin_email.lower(),
                password_hash=hash_password(self._settings.admin_password),
                role=UserRole.ADMINISTRATOR,
            )
        )

    def authenticate(self, email: str, password: str) -> tuple[str, str, User]:
        user = self._users.get_by_email(email)
        if user is None or not user.is_active or user.deleted_at is not None:
            logger.warning("Failed login attempt for email: %s (user not found/inactive)", email)
            raise AuthenticationError("Invalid email or password.")
        if not verify_password(password, user.password_hash):
            logger.warning("Failed login attempt for email: %s (wrong password)", email)
            raise AuthenticationError("Invalid email or password.")
        logger.info("User %s (%s) authenticated successfully", user.id, email)
        return (
            create_access_token(user, self._settings),
            create_refresh_token(user, self._settings),
            user,
        )
