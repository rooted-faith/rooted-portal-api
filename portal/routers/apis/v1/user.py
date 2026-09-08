"""
Member End user API routes (ADR 0008).
"""

from dependency_injector.wiring import Provide, inject
from fastapi import Depends
from starlette import status

from portal.application.app.end_user_service import EndUserService
from portal.application.app.mappers import reonboarding_flag_result_to_member_api
from portal.container import Container
from portal.exceptions.responses import UnauthorizedException
from portal.libs.contexts.user_context import get_user_context
from portal.libs.depends.rate_limiters import WRITE_RATE_LIMITERS
from portal.routers.auth_router import AuthRouter
from portal.serializers.apis.v1.user import MemberReonboarding

router: AuthRouter = AuthRouter()


@router.post(
    "/me/reonboarding/acknowledge",
    response_model=MemberReonboarding,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
    dependencies=[*WRITE_RATE_LIMITERS],
    operation_id="acknowledge_member_reonboarding",
    summary="Acknowledge a replayed onboarding",
    description="Clear the Admin-set reonboarding flag once the person has finished (or skipped) onboarding again. A no-op when nothing was flagged.",
)
@inject
async def acknowledge_reonboarding(end_user_service: EndUserService = Depends(Provide[Container.end_user_service])) -> MemberReonboarding:
    user_context = get_user_context()
    if user_context is None:
        raise UnauthorizedException(detail="Authentication required")

    result = await end_user_service.acknowledge_reonboarding(auth_user_id=user_context.user_id)
    return reonboarding_flag_result_to_member_api(result)
