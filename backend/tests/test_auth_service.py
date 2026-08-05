from uuid import UUID

import pytest

from app.application.auth_service import AuthenticationError, AuthService
from app.config.settings import Settings
from app.domain.entities.user import User, UserRole
from app.security.passwords import hash_password


class FakeUserRepo:
    def __init__(self):
        self._data: dict[UUID, User] = {}

    def get(self, uid: UUID) -> User | None:
        return self._data.get(uid)

    def get_by_email(self, email: str) -> User | None:
        for u in self._data.values():
            if u.email == email:
                return u
        return None

    def add(self, u: User) -> User:
        self._data[u.id] = u
        return u

    def update(self, u: User) -> User:
        self._data[u.id] = u
        return u

    def list_all(self) -> list[User]:
        return list(self._data.values())

    def soft_delete(self, uid: UUID) -> None:
        if uid in self._data:
            del self._data[uid]

    def has_role(self, role: UserRole) -> bool:
        return any(u.role == role for u in self._data.values())


class TestAuthService:
    def setup_method(self):
        self.repo = FakeUserRepo()
        self.settings = Settings(
            environment="test",
            database_url="sqlite:///:memory:",
            jwt_secret_key="test-secret-key-for-testing-only",
            jwt_access_token_minutes=30,
            jwt_refresh_token_days=7,
            admin_email="admin@test.com",
            admin_password="Admin123!",
            model_storage_path="./test_models",
        )
        self.service = AuthService(self.repo, self.settings)

    def test_ensure_initial_admin_creates_when_none(self):
        user = self.service.ensure_initial_administrator()
        assert user is not None
        assert user.email == "admin@test.com"
        assert user.role == UserRole.ADMINISTRATOR

    def test_ensure_initial_admin_returns_none_when_exists(self):
        existing = User(email="existing@test.com", password_hash="hash", role=UserRole.ADMINISTRATOR)
        self.repo.add(existing)
        result = self.service.ensure_initial_administrator()
        assert result is None

    def test_ensure_initial_admin_raises_without_env_vars(self):
        bad_settings = Settings(
            environment="test",
            database_url="sqlite:///:memory:",
            jwt_secret_key="key",
            jwt_access_token_minutes=30,
            jwt_refresh_token_days=7,
            admin_email="",
            admin_password="",
            model_storage_path="./test_models",
        )
        bad_service = AuthService(self.repo, bad_settings)
        with pytest.raises(RuntimeError, match="ADMIN_EMAIL and ADMIN_PASSWORD"):
            bad_service.ensure_initial_administrator()

    def test_authenticate_success(self):
        self.repo.add(User(
            email="user@test.com",
            password_hash=hash_password("Pass123!"),
            role=UserRole.OPERATOR,
        ))
        access, refresh, user = self.service.authenticate("user@test.com", "Pass123!")
        assert access is not None
        assert refresh is not None
        assert user.email == "user@test.com"

    def test_authenticate_fails_on_wrong_password(self):
        self.repo.add(User(
            email="user@test.com",
            password_hash=hash_password("CorrectPass1!"),
            role=UserRole.OPERATOR,
        ))
        with pytest.raises(AuthenticationError, match="Invalid email or password"):
            self.service.authenticate("user@test.com", "wrong")

    def test_authenticate_fails_on_missing_email(self):
        with pytest.raises(AuthenticationError, match="Invalid email or password"):
            self.service.authenticate("noone@test.com", "Pass123!")

    def test_authenticate_fails_on_inactive_user(self):
        u = User(email="inactive@test.com", password_hash=hash_password("Pass123!"), role=UserRole.VIEWER)
        u.is_active = False
        self.repo.add(u)
        with pytest.raises(AuthenticationError, match="Invalid email or password"):
            self.service.authenticate("inactive@test.com", "Pass123!")

    def test_authenticate_fails_on_deleted_user(self):
        u = User(email="deleted@test.com", password_hash=hash_password("Pass123!"), role=UserRole.VIEWER)
        u.soft_delete()
        self.repo.add(u)
        with pytest.raises(AuthenticationError, match="Invalid email or password"):
            self.service.authenticate("deleted@test.com", "Pass123!")
