from uuid import UUID, uuid4

import pytest

from app.application.user_service import UserService
from app.domain.entities.user import User, UserRole
from app.domain.errors import BusinessRuleViolation


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


class TestUserService:
    def setup_method(self):
        self.repo = FakeUserRepo()
        self.service = UserService(self.repo)

    def _add_admin(self) -> User:
        u = User(email="admin@test.com", password_hash="hash", role=UserRole.ADMINISTRATOR)
        self.repo.add(u)
        return u

    def test_list_all_empty(self):
        assert self.service.list_all() == []

    def test_list_all_returns_users(self):
        self._add_admin()
        assert len(self.service.list_all()) == 1

    def test_get_returns_user(self):
        admin = self._add_admin()
        result = self.service.get(admin.id)
        assert result.id == admin.id

    def test_get_raises_on_missing(self):
        with pytest.raises(LookupError):
            self.service.get(uuid4())

    def test_create_adds_user(self):
        u = self.service.create("user@test.com", "Pass123!", UserRole.OPERATOR)
        assert u.email == "user@test.com"
        assert u.role == UserRole.OPERATOR
        assert u.password_hash != "Pass123!"

    def test_create_rejects_duplicate_email(self):
        self.service.create("dup@test.com", "Pass123!", UserRole.VIEWER)
        with pytest.raises(BusinessRuleViolation, match="already exists"):
            self.service.create("dup@test.com", "Pass123!", UserRole.OPERATOR)

    def test_create_without_organization(self):
        u = self.service.create("no-org@test.com", "Pass123!", UserRole.OPERATOR)
        assert u.organization_id is None

    def test_create_with_organization(self):
        org_id = uuid4()
        u = self.service.create("with-org@test.com", "Pass123!", UserRole.VIEWER, organization_id=org_id)
        assert u.organization_id == org_id

    def test_update_role_changes_role(self):
        u = self.service.create("u@test.com", "Pass123!", UserRole.VIEWER)
        updated = self.service.update_role(u.id, UserRole.OPERATOR)
        assert updated.role == UserRole.OPERATOR

    def test_update_role_raises_on_missing(self):
        with pytest.raises(LookupError):
            self.service.update_role(uuid4(), UserRole.ADMINISTRATOR)

    def test_update_password_changes_hash(self):
        u = self.service.create("u@test.com", "Pass123!", UserRole.OPERATOR)
        old_hash = u.password_hash
        updated = self.service.update_password(u.id, "NewPass456!")
        assert updated.password_hash != old_hash

    def test_deactivate_sets_inactive(self):
        u = self.service.create("u@test.com", "Pass123!", UserRole.OPERATOR)
        updated = self.service.deactivate(u.id)
        assert updated.is_active is False

    def test_activate_sets_active(self):
        u = self.service.create("u@test.com", "Pass123!", UserRole.OPERATOR)
        self.service.deactivate(u.id)
        updated = self.service.activate(u.id)
        assert updated.is_active is True

    def test_activate_idempotent(self):
        u = self.service.create("u@test.com", "Pass123!", UserRole.OPERATOR)
        updated = self.service.activate(u.id)
        assert updated.is_active is True

    def test_soft_delete_removes_user(self):
        u = self.service.create("u@test.com", "Pass123!", UserRole.OPERATOR)
        self.service.soft_delete(u.id)
        assert self.repo.get(u.id) is None

    def test_soft_delete_raises_on_admin(self):
        admin = self._add_admin()
        with pytest.raises(BusinessRuleViolation, match="Cannot delete an Administrator"):
            self.service.soft_delete(admin.id)
