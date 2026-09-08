"""
End user administration use cases: the Admin-triggered reonboarding flag (ADR 0008).
"""

from datetime import datetime, timezone
from uuid import UUID

from portal.application.app.commands import RequestReonboardingCommand
from portal.application.app.results import ReonboardingFlagResult
from portal.domain.app.ports import EndUserRepositoryPort
from portal.exceptions.responses import NotFoundException, UnauthorizedException
from portal.libs.tracing.distributed_trace import distributed_trace


class EndUserService:
    """Set and clear the flag that makes the App replay onboarding for one End user."""

    def __init__(self, end_user_repository: EndUserRepositoryPort):
        self._end_user_repository = end_user_repository

    @distributed_trace()
    async def request_reonboarding(self, command: RequestReonboardingCommand) -> ReonboardingFlagResult:
        """Admin-only: mark an End user as needing to go through onboarding again."""
        end_user = await self._end_user_repository.set_reonboarding_requested_at(command.end_user_id, datetime.now(timezone.utc))
        if end_user is None:
            raise NotFoundException(detail="End user not found")
        return ReonboardingFlagResult(end_user_id=end_user.id, reonboarding_requested_at=end_user.reonboarding_requested_at)

    @distributed_trace()
    async def acknowledge_reonboarding(self, *, auth_user_id: UUID) -> ReonboardingFlagResult:
        """
        Clear the flag once the signed-in person has replayed (or skipped) onboarding.
        Acknowledging when nothing was flagged is a no-op, not an error.
        """
        end_user = await self._end_user_repository.get_by_auth_user_id(auth_user_id)
        if end_user is None:
            raise UnauthorizedException(detail="This credential has no End user")

        if end_user.reonboarding_requested_at is not None:
            await self._end_user_repository.set_reonboarding_requested_at(end_user.id, None)
        return ReonboardingFlagResult(end_user_id=end_user.id, reonboarding_requested_at=None)
