"""
App (End user) authentication HTTP routes.
"""

from dependency_injector.wiring import Provide, inject
from fastapi import Depends, status

from portal.application.auth.app_auth_service import AppAuthService
from portal.application.auth.commands import AppOtpRequestCommand, AppOtpVerifyCommand, LogoutCommand, RefreshTokenCommand
from portal.application.auth.mappers import member_login_result_to_api, otp_request_result_to_api, token_result_to_api
from portal.application.auth.refresh_token_service import RefreshTokenService
from portal.container import Container
from portal.libs.depends.rate_limiters import WRITE_RATE_LIMITERS
from portal.routers.auth_router import AuthRouter
from portal.serializers.apis.v1.auth import MemberLoginResponse, MemberOtpRequest, MemberOtpRequestResponse, MemberOtpVerifyRequest
from portal.serializers.mixins import LogoutRequest, LogoutResponse, RefreshTokenRequest, TokenResponse

router: AuthRouter = AuthRouter()


@router.post(
    "/otp",
    response_model=MemberOtpRequestResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
    require_auth=False,
    dependencies=[*WRITE_RATE_LIMITERS],
    operation_id="request_member_otp",
    summary="Request an email one-time passcode",
    description=(
        "Email a six-digit passcode to the address. The acknowledgement is identical whether or not the "
        "email has an account, and repeated requests for the same email are throttled (429)."
    ),
)
@inject
async def app_request_otp(body: MemberOtpRequest, app_auth_service: AppAuthService = Depends(Provide[Container.app_auth_service])):
    result = await app_auth_service.request_otp(AppOtpRequestCommand(email=body.email))
    return otp_request_result_to_api(result)


@router.post(
    "/otp/verify",
    response_model=MemberLoginResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
    require_auth=False,
    dependencies=[*WRITE_RATE_LIMITERS],
    operation_id="verify_member_otp",
    summary="Verify an email one-time passcode",
    description="Redeem a live passcode to sign in, provisioning the End user on first use. Every rejection returns the same generic 401.",
)
@inject
async def app_verify_otp(body: MemberOtpVerifyRequest, app_auth_service: AppAuthService = Depends(Provide[Container.app_auth_service])):
    result = await app_auth_service.verify_otp(AppOtpVerifyCommand(email=body.email, code=body.code))
    return member_login_result_to_api(result)


@router.post("/refresh", response_model=TokenResponse, response_model_by_alias=True, require_auth=False)
@inject
async def app_refresh_token(body: RefreshTokenRequest, refresh_token_service: RefreshTokenService = Depends(Provide[Container.refresh_token_service])):
    result = await refresh_token_service.refresh_member_token(RefreshTokenCommand(refresh_token=body.refresh_token))
    return token_result_to_api(result)


@router.post("/logout", response_model=LogoutResponse, response_model_by_alias=True, require_auth=False)
@inject
async def app_logout(body: LogoutRequest, refresh_token_service: RefreshTokenService = Depends(Provide[Container.refresh_token_service])):
    await refresh_token_service.logout_member(LogoutCommand(access_token=body.access_token, refresh_token=body.refresh_token))
    return LogoutResponse(message="Logged out")
