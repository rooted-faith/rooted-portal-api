"""
Map End user application results to API serializers.
"""

from portal.application.app.commands import UpdatePreferencesCommand
from portal.application.app.results import PreferencesResult, ReonboardingFlagResult
from portal.serializers.admin.v1.end_user import AdminEndUserReonboarding
from portal.serializers.apis.v1.user import MemberPreferences, MemberReonboarding, UpdateMemberPreferences


def update_preferences_to_command(serializer: UpdateMemberPreferences) -> UpdatePreferencesCommand:
    return UpdatePreferencesCommand.model_validate(serializer.model_dump(exclude_unset=True))


def preferences_result_to_api(result: PreferencesResult) -> MemberPreferences:
    return MemberPreferences.model_validate(result, from_attributes=True)


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
