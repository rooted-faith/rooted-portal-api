"""
Tests for PushService.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from portal.application.push.push_service import PushService
from portal.domain.app.entities import EndUser
from portal.domain.push.constants import DeliveryStatus, PushSendStatus
from portal.domain.push.entities import Device, LocalizedNotificationCopy, Notification, NotificationCopy, PushSendResult


class StubDeviceRepository:
    def __init__(self):
        self.devices: dict[str, Device] = {}

    async def upsert_device(self, *, device_key, token, platform, app_version, locale, end_user_id, last_used_at):
        existing = self.devices.get(device_key)
        device = Device(
            id=existing.id if existing else uuid4(),
            device_key=device_key,
            token=token,
            platform=platform,
            end_user_id=end_user_id,
            is_active=existing.is_active if existing else True,
            last_used_at=last_used_at,
            app_version=app_version,
            locale=locale,
        )
        self.devices[device_key] = device
        return device

    async def list_active_devices(self, end_user_id):
        return [device for device in self.devices.values() if device.end_user_id == end_user_id and device.is_active]

    async def deactivate_devices(self, device_ids):
        for device_key, device in self.devices.items():
            if device.id in device_ids:
                self.devices[device_key] = device.model_copy(update={"is_active": False})


class StubEndUserRepository:
    def __init__(self, end_users: dict | None = None):
        self._end_users = end_users or {}

    async def create_end_user(self, *, end_user_id, auth_user_id):
        raise NotImplementedError

    async def get_by_auth_user_id(self, auth_user_id):
        return self._end_users.get(auth_user_id)


class StubNotificationRepository:
    def __init__(self):
        self.notifications: list[Notification] = []
        self.recorded_deliveries: list = []

    async def create_notification(self, *, end_user_id, category, title, body, data):
        notification = Notification(
            id=uuid4(), end_user_id=end_user_id, category=category, title=title, body=body, data=data, created_at=datetime.now(timezone.utc)
        )
        self.notifications.append(notification)
        return notification

    async def record_deliveries(self, deliveries):
        self.recorded_deliveries.extend(deliveries)


class StubPushGateway:
    def __init__(self, result_by_token: dict | None = None, raise_error: Exception | None = None):
        self._result_by_token = result_by_token or {}
        self._raise_error = raise_error
        self.calls: list[dict] = []

    async def send_multicast(self, *, tokens, title, body, data):
        self.calls.append({"tokens": tokens, "title": title, "body": body, "data": data})
        if self._raise_error:
            raise self._raise_error
        return [self._result_by_token.get(token, PushSendResult(token=token, status=PushSendStatus.SUCCESS)) for token in tokens]


def make_push_service(device_repository=None, end_user_repository=None, notification_repository=None, push_gateway=None) -> PushService:
    return PushService(
        device_repository or StubDeviceRepository(),
        end_user_repository or StubEndUserRepository(),
        notification_repository or StubNotificationRepository(),
        push_gateway or StubPushGateway(),
    )


@pytest.mark.asyncio
async def test_register_device_anonymous_leaves_end_user_id_none():
    service = make_push_service()
    result = await service.register_device(device_key="device-1", token="tok-1", platform="ios", app_version="1.0.0", locale="zh-Hant", end_user_id=None)
    assert result.end_user_id is None
    assert result.device_key == "device-1"
    assert result.token == "tok-1"
    assert result.platform == "ios"
    assert result.app_version == "1.0.0"
    assert result.locale == "zh-Hant"
    assert result.is_active is True


@pytest.mark.asyncio
async def test_register_device_authenticated_sets_end_user_id():
    end_user_id = uuid4()
    service = make_push_service()
    result = await service.register_device(device_key="device-1", token="tok-1", platform="android", app_version=None, locale=None, end_user_id=end_user_id)
    assert result.end_user_id == end_user_id


@pytest.mark.asyncio
async def test_reregistering_same_device_key_overwrites_previous_owner():
    repository = StubDeviceRepository()
    service = make_push_service(device_repository=repository)
    first_owner = uuid4()
    first = await service.register_device(device_key="device-1", token="tok-1", platform="ios", app_version="1.0.0", locale="zh-Hant", end_user_id=first_owner)

    second_owner = uuid4()
    second = await service.register_device(device_key="device-1", token="tok-2", platform="ios", app_version="1.1.0", locale="en", end_user_id=second_owner)

    assert second.id == first.id
    assert second.end_user_id == second_owner
    assert second.token == "tok-2"
    assert second.app_version == "1.1.0"
    assert second.locale == "en"  # a device whose system language changed re-registers with the new one


@pytest.mark.asyncio
async def test_reregistering_unauthenticated_after_sign_in_clears_end_user_id():
    """Sign-out case: the client calls again without a bearer token, overwriting end_user_id back to None."""
    repository = StubDeviceRepository()
    service = make_push_service(device_repository=repository)
    await service.register_device(device_key="device-1", token="tok-1", platform="ios", app_version="1.0.0", locale="zh-Hant", end_user_id=uuid4())

    signed_out = await service.register_device(device_key="device-1", token="tok-1", platform="ios", app_version="1.0.0", locale="zh-Hant", end_user_id=None)

    assert signed_out.end_user_id is None


@pytest.mark.asyncio
async def test_resolve_end_user_id_returns_none_when_unauthenticated():
    service = make_push_service()
    assert await service.resolve_end_user_id(None) is None


@pytest.mark.asyncio
async def test_resolve_end_user_id_maps_auth_user_id_to_end_user_id():
    auth_user_id = uuid4()
    end_user = EndUser(id=uuid4(), auth_user_id=auth_user_id)
    service = make_push_service(end_user_repository=StubEndUserRepository({auth_user_id: end_user}))

    assert await service.resolve_end_user_id(auth_user_id) == end_user.id


@pytest.mark.asyncio
async def test_resolve_end_user_id_returns_none_when_auth_user_has_no_end_user():
    service = make_push_service()
    assert await service.resolve_end_user_id(uuid4()) is None


def _make_device(end_user_id, token="tok", is_active=True, locale="zh-Hant") -> Device:
    return Device(
        id=uuid4(),
        device_key=str(uuid4()),
        token=token,
        platform="ios",
        end_user_id=end_user_id,
        is_active=is_active,
        last_used_at=datetime.now(timezone.utc),
        locale=locale,
    )


def _copy(title="title", body="body", by_locale=None) -> LocalizedNotificationCopy:
    return LocalizedNotificationCopy(default=NotificationCopy(title=title, body=body), by_locale=by_locale or {})


@pytest.mark.asyncio
async def test_notify_with_zero_active_devices_is_a_no_op():
    notification_repository = StubNotificationRepository()
    push_gateway = StubPushGateway()
    service = make_push_service(notification_repository=notification_repository, push_gateway=push_gateway)
    end_user_id = uuid4()

    result = await service.notify(end_user_id=end_user_id, category="prayer", copy=_copy(title="Someone prayed"))

    assert result.end_user_id == end_user_id
    assert len(notification_repository.notifications) == 1
    assert notification_repository.recorded_deliveries == []
    assert push_gateway.calls == []


@pytest.mark.asyncio
async def test_notify_fans_out_to_every_active_device_and_skips_inactive():
    end_user_id = uuid4()
    device_repository = StubDeviceRepository()
    active_one = _make_device(end_user_id, token="tok-active-1")
    active_two = _make_device(end_user_id, token="tok-active-2")
    inactive = _make_device(end_user_id, token="tok-inactive", is_active=False)
    other_user_device = _make_device(uuid4(), token="tok-other-user")
    for device in (active_one, active_two, inactive, other_user_device):
        device_repository.devices[device.device_key] = device

    push_gateway = StubPushGateway()
    service = make_push_service(device_repository=device_repository, push_gateway=push_gateway)

    await service.notify(end_user_id=end_user_id, category="prayer", copy=_copy())

    assert set(push_gateway.calls[0]["tokens"]) == {"tok-active-1", "tok-active-2"}


@pytest.mark.asyncio
async def test_notify_records_success_and_failed_deliveries():
    end_user_id = uuid4()
    device_repository = StubDeviceRepository()
    ok_device = _make_device(end_user_id, token="tok-ok")
    failing_device = _make_device(end_user_id, token="tok-fail")
    device_repository.devices[ok_device.device_key] = ok_device
    device_repository.devices[failing_device.device_key] = failing_device

    notification_repository = StubNotificationRepository()
    push_gateway = StubPushGateway(result_by_token={"tok-fail": PushSendResult(token="tok-fail", status=PushSendStatus.FAILED, error="boom")})
    service = make_push_service(device_repository=device_repository, notification_repository=notification_repository, push_gateway=push_gateway)

    await service.notify(end_user_id=end_user_id, category="prayer", copy=_copy())

    deliveries_by_device = {delivery.device_id: delivery for delivery in notification_repository.recorded_deliveries}
    assert deliveries_by_device[ok_device.id].status == DeliveryStatus.SUCCESS
    assert deliveries_by_device[failing_device.id].status == DeliveryStatus.FAILED
    assert deliveries_by_device[failing_device.id].error == "boom"


@pytest.mark.asyncio
async def test_notify_deactivates_device_classified_unregistered():
    end_user_id = uuid4()
    device_repository = StubDeviceRepository()
    unregistered_device = _make_device(end_user_id, token="tok-gone")
    device_repository.devices[unregistered_device.device_key] = unregistered_device

    notification_repository = StubNotificationRepository()
    push_gateway = StubPushGateway(result_by_token={"tok-gone": PushSendResult(token="tok-gone", status=PushSendStatus.UNREGISTERED, error="not registered")})
    service = make_push_service(device_repository=device_repository, notification_repository=notification_repository, push_gateway=push_gateway)

    await service.notify(end_user_id=end_user_id, category="prayer", copy=_copy())

    assert device_repository.devices[unregistered_device.device_key].is_active is False
    delivery = notification_repository.recorded_deliveries[0]
    assert delivery.status == DeliveryStatus.FAILED
    assert delivery.error == "not registered"


@pytest.mark.asyncio
async def test_notify_gateway_exception_records_failed_deliveries_and_does_not_raise():
    end_user_id = uuid4()
    device_repository = StubDeviceRepository()
    device = _make_device(end_user_id, token="tok-1")
    device_repository.devices[device.device_key] = device

    notification_repository = StubNotificationRepository()
    push_gateway = StubPushGateway(raise_error=RuntimeError("FCM unavailable"))
    service = make_push_service(device_repository=device_repository, notification_repository=notification_repository, push_gateway=push_gateway)

    result = await service.notify(end_user_id=end_user_id, category="prayer", copy=_copy())

    assert result is not None
    assert len(notification_repository.recorded_deliveries) == 1
    delivery = notification_repository.recorded_deliveries[0]
    assert delivery.status == DeliveryStatus.FAILED
    assert delivery.error == "FCM unavailable"
    assert device_repository.devices[device.device_key].is_active is True


@pytest.mark.asyncio
async def test_notify_sends_once_per_locale_group_with_that_group_s_copy():
    """Two devices set to different system languages must each get copy in their own language."""
    end_user_id = uuid4()
    device_repository = StubDeviceRepository()
    zh_device = _make_device(end_user_id, token="tok-zh", locale="zh-Hant")
    en_device = _make_device(end_user_id, token="tok-en", locale="en")
    second_zh_device = _make_device(end_user_id, token="tok-zh-2", locale="zh-Hant")
    for device in (zh_device, en_device, second_zh_device):
        device_repository.devices[device.device_key] = device

    push_gateway = StubPushGateway()
    notification_repository = StubNotificationRepository()
    service = make_push_service(device_repository=device_repository, notification_repository=notification_repository, push_gateway=push_gateway)

    copy = _copy(
        title="Someone prayed",
        body="Open Rooted to see it",
        by_locale={
            "zh-Hant": NotificationCopy(title="有人為你禱告", body="打開 Rooted 看看"),
            "en": NotificationCopy(title="Someone prayed for you", body="Open Rooted to see it"),
        },
    )
    await service.notify(end_user_id=end_user_id, category="prayer", copy=copy)

    assert len(push_gateway.calls) == 2
    calls_by_title = {call["title"]: call for call in push_gateway.calls}
    assert set(calls_by_title["有人為你禱告"]["tokens"]) == {"tok-zh", "tok-zh-2"}
    assert calls_by_title["有人為你禱告"]["body"] == "打開 Rooted 看看"
    assert calls_by_title["Someone prayed for you"]["tokens"] == ["tok-en"]

    # every device still gets exactly one delivery row
    assert len(notification_repository.recorded_deliveries) == 3
    assert {delivery.status for delivery in notification_repository.recorded_deliveries} == {DeliveryStatus.SUCCESS}


@pytest.mark.asyncio
async def test_notify_single_locale_device_set_still_makes_exactly_one_send_call():
    end_user_id = uuid4()
    device_repository = StubDeviceRepository()
    for token in ("tok-1", "tok-2", "tok-3"):
        device = _make_device(end_user_id, token=token, locale="zh-Hant")
        device_repository.devices[device.device_key] = device

    push_gateway = StubPushGateway()
    service = make_push_service(device_repository=device_repository, push_gateway=push_gateway)

    await service.notify(end_user_id=end_user_id, category="prayer", copy=_copy(by_locale={"zh-Hant": NotificationCopy(title="標題", body="內文")}))

    assert len(push_gateway.calls) == 1
    assert set(push_gateway.calls[0]["tokens"]) == {"tok-1", "tok-2", "tok-3"}
    assert push_gateway.calls[0]["title"] == "標題"


@pytest.mark.asyncio
async def test_notify_falls_back_to_default_copy_for_unknown_and_missing_locales():
    end_user_id = uuid4()
    device_repository = StubDeviceRepository()
    unknown_locale_device = _make_device(end_user_id, token="tok-ja", locale="ja")
    no_locale_device = _make_device(end_user_id, token="tok-none", locale=None)
    for device in (unknown_locale_device, no_locale_device):
        device_repository.devices[device.device_key] = device

    push_gateway = StubPushGateway()
    service = make_push_service(device_repository=device_repository, push_gateway=push_gateway)

    await service.notify(
        end_user_id=end_user_id,
        category="prayer",
        copy=_copy(title="fallback", body="fallback body", by_locale={"en": NotificationCopy(title="english", body="english body")}),
    )

    assert len(push_gateway.calls) == 2  # "ja" and None are distinct groups
    assert {call["title"] for call in push_gateway.calls} == {"fallback"}


@pytest.mark.asyncio
async def test_notify_gateway_failure_in_one_locale_group_does_not_stop_the_others():
    end_user_id = uuid4()
    device_repository = StubDeviceRepository()
    zh_device = _make_device(end_user_id, token="tok-zh", locale="zh-Hant")
    en_device = _make_device(end_user_id, token="tok-en", locale="en")
    for device in (zh_device, en_device):
        device_repository.devices[device.device_key] = device

    class FailFirstGateway(StubPushGateway):
        async def send_multicast(self, *, tokens, title, body, data):
            if "tok-zh" in tokens:
                self.calls.append({"tokens": tokens, "title": title, "body": body, "data": data})
                raise RuntimeError("FCM unavailable")
            return await super().send_multicast(tokens=tokens, title=title, body=body, data=data)

    notification_repository = StubNotificationRepository()
    push_gateway = FailFirstGateway()
    service = make_push_service(device_repository=device_repository, notification_repository=notification_repository, push_gateway=push_gateway)

    result = await service.notify(end_user_id=end_user_id, category="prayer", copy=_copy())

    assert result is not None
    deliveries_by_device = {delivery.device_id: delivery for delivery in notification_repository.recorded_deliveries}
    assert deliveries_by_device[zh_device.id].status == DeliveryStatus.FAILED
    assert deliveries_by_device[zh_device.id].error == "FCM unavailable"
    assert deliveries_by_device[en_device.id].status == DeliveryStatus.SUCCESS


@pytest.mark.asyncio
async def test_notify_persists_the_default_copy_on_the_notification_row():
    end_user_id = uuid4()
    notification_repository = StubNotificationRepository()
    service = make_push_service(notification_repository=notification_repository)

    await service.notify(
        end_user_id=end_user_id,
        category="prayer",
        copy=_copy(title="default title", body="default body", by_locale={"en": NotificationCopy(title="english", body="english body")}),
    )

    notification = notification_repository.notifications[0]
    assert notification.title == "default title"
    assert notification.body == "default body"
