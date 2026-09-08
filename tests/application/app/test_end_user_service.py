"""
Application-service seam: the Admin-triggered reonboarding flag (stub port, ADR 0008).

Admin sets the flag on one End user, the client sees it on its next login, and
acknowledging clears it. Acknowledging when nothing is flagged is a no-op.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

import pytest

from portal.application.app.commands import RequestReonboardingCommand
from portal.application.app.end_user_service import EndUserService
from portal.domain.app.entities import EndUser
from portal.exceptions.responses import NotFoundException, UnauthorizedException


class StubEndUserRepository:
    def __init__(self):
        self.by_id: dict[UUID, EndUser] = {}

    def seed(self, *, reonboarding_requested_at: Optional[datetime] = None) -> EndUser:
        end_user = EndUser(id=uuid4(), auth_user_id=uuid4(), reonboarding_requested_at=reonboarding_requested_at)
        self.by_id[end_user.id] = end_user
        return end_user

    async def create_end_user(self, *, end_user_id: UUID, auth_user_id: UUID) -> EndUser:
        raise NotImplementedError

    async def get_by_auth_user_id(self, auth_user_id: UUID):
        return next((end_user for end_user in self.by_id.values() if end_user.auth_user_id == auth_user_id), None)

    async def get_by_id(self, end_user_id: UUID):
        return self.by_id.get(end_user_id)

    async def set_reonboarding_requested_at(self, end_user_id: UUID, requested_at: Optional[datetime]):
        end_user = self.by_id.get(end_user_id)
        if end_user is None:
            return None
        updated = end_user.model_copy(update={"reonboarding_requested_at": requested_at})
        self.by_id[end_user_id] = updated
        return updated


@pytest.mark.asyncio
async def test_admin_request_sets_the_flag():
    repository = StubEndUserRepository()
    end_user = repository.seed()
    service = EndUserService(end_user_repository=repository)

    before = datetime.now(timezone.utc)
    result = await service.request_reonboarding(RequestReonboardingCommand(end_user_id=end_user.id))

    assert result.end_user_id == end_user.id
    assert result.reonboarding_requested_at is not None
    assert result.reonboarding_requested_at >= before
    assert repository.by_id[end_user.id].reonboarding_requested_at == result.reonboarding_requested_at


@pytest.mark.asyncio
async def test_admin_request_for_an_unknown_end_user_is_not_found():
    service = EndUserService(end_user_repository=StubEndUserRepository())

    with pytest.raises(NotFoundException):
        await service.request_reonboarding(RequestReonboardingCommand(end_user_id=uuid4()))


@pytest.mark.asyncio
async def test_acknowledging_clears_the_flag():
    repository = StubEndUserRepository()
    end_user = repository.seed(reonboarding_requested_at=datetime.now(timezone.utc))
    service = EndUserService(end_user_repository=repository)

    result = await service.acknowledge_reonboarding(auth_user_id=end_user.auth_user_id)

    assert result.end_user_id == end_user.id
    assert result.reonboarding_requested_at is None
    assert repository.by_id[end_user.id].reonboarding_requested_at is None


@pytest.mark.asyncio
async def test_acknowledging_when_nothing_is_flagged_is_a_no_op():
    repository = StubEndUserRepository()
    end_user = repository.seed()
    service = EndUserService(end_user_repository=repository)

    result = await service.acknowledge_reonboarding(auth_user_id=end_user.auth_user_id)

    assert result.reonboarding_requested_at is None


@pytest.mark.asyncio
async def test_acknowledging_without_an_end_user_row_is_unauthorized():
    service = EndUserService(end_user_repository=StubEndUserRepository())

    with pytest.raises(UnauthorizedException):
        await service.acknowledge_reonboarding(auth_user_id=uuid4())
