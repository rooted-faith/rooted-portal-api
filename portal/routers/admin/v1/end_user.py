"""
Admin End user API routes (ADR 0008).
"""

import uuid

from dependency_injector.wiring import Provide, inject
from fastapi import Depends, status

from portal.application.app.commands import RequestReonboardingCommand
from portal.application.app.end_user_service import EndUserService
from portal.application.app.mappers import reonboarding_flag_result_to_admin_api
from portal.container import Container
from portal.libs.consts.permission import Permission
from portal.routers.auth_router import AuthRouter
from portal.serializers.admin.v1.end_user import AdminEndUserReonboarding

router: AuthRouter = AuthRouter(is_admin=True)


@router.post(
    path="/{end_user_id}/reonboarding",
    status_code=status.HTTP_200_OK,
    response_model=AdminEndUserReonboarding,
    response_model_by_alias=True,
    permissions=[Permission.SUPPORT_END_USER.modify],
    operation_id="request_end_user_reonboarding",
    summary="Flag an End user to replay onboarding",
    description="Set the reonboarding flag so the App presents onboarding again on this End user's next launch. The client clears it once done.",
)
@inject
async def request_end_user_reonboarding(
    end_user_id: uuid.UUID, end_user_service: EndUserService = Depends(Provide[Container.end_user_service])
) -> AdminEndUserReonboarding:
    """
    Flag one End user for reonboarding
    :param end_user_id:
    :param end_user_service:
    :return:
    """
    result = await end_user_service.request_reonboarding(RequestReonboardingCommand(end_user_id=end_user_id))
    return reonboarding_flag_result_to_admin_api(result)
