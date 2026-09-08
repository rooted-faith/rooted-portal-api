"""
Map End user application results to API serializers.
"""

from portal.application.app.results import ReonboardingFlagResult
from portal.serializers.admin.v1.end_user import AdminEndUserReonboarding
from portal.serializers.apis.v1.user import MemberReonboarding


def reonboarding_flag_result_to_admin_api(result: ReonboardingFlagResult) -> AdminEndUserReonboarding:
    """
    Map the reonboarding flag state to the admin API response model.
    :param result:
    :return:
    """
    return AdminEndUserReonboarding(end_user_id=result.end_user_id, reonboarding_requested_at=result.reonboarding_requested_at)


def reonboarding_flag_result_to_member_api(result: ReonboardingFlagResult) -> MemberReonboarding:
    """
    Map the reonboarding flag state to the member API response model.
    :param result:
    :return:
    """
    return MemberReonboarding(reonboarding_requested_at=result.reonboarding_requested_at)
