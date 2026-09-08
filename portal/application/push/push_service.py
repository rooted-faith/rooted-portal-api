"""
Push application service.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from portal.application.push.results import DeviceResult, NotificationResult
from portal.domain.app.ports import EndUserRepositoryPort
from portal.domain.push.constants import DeliveryStatus, PushSendStatus
from portal.domain.push.entities import Device, LocalizedNotificationCopy, NotificationDeliveryDraft
from portal.domain.push.ports import DeviceRepositoryPort, NotificationRepositoryPort, PushGatewayPort
from portal.libs.logger import logger
from portal.libs.tracing.distributed_trace import distributed_trace


class PushService:
    """Device registration & lifecycle, and Notification send, use cases."""

    def __init__(
        self,
        device_repository: DeviceRepositoryPort,
        end_user_repository: EndUserRepositoryPort,
        notification_repository: NotificationRepositoryPort,
        push_gateway: PushGatewayPort,
    ):
        self._device_repository = device_repository
        self._end_user_repository = end_user_repository
        self._notification_repository = notification_repository
        self._push_gateway = push_gateway

    @distributed_trace()
    async def resolve_end_user_id(self, auth_user_id: Optional[UUID]) -> Optional[UUID]:
        """Map an authenticated auth.user.id to its app.user.id (End user), or None when unauthenticated."""
        if auth_user_id is None:
            return None
        end_user = await self._end_user_repository.get_by_auth_user_id(auth_user_id)
        return end_user.id if end_user else None

    @distributed_trace()
    async def register_device(
        self, *, device_key: str, token: str, platform: str, app_version: Optional[str], locale: Optional[str], end_user_id: Optional[UUID]
    ) -> DeviceResult:
        """
        Upsert by device_key: unconditionally overwrite token/platform/app_version/
        locale/last_used_at, and set end_user_id to whatever this call resolved (the
        signed-in End user's id, or None if unauthenticated).
        """
        return await self._device_repository.upsert_device(
            device_key=device_key,
            token=token,
            platform=platform,
            app_version=app_version,
            locale=locale,
            end_user_id=end_user_id,
            last_used_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _group_by_locale(devices: list[Device]) -> dict[Optional[str], list[Device]]:
        """Bucket devices by their own locale, preserving the repository's order."""
        groups: dict[Optional[str], list[Device]] = {}
        for device in devices:
            groups.setdefault(device.locale, []).append(device)
        return groups

    @distributed_trace()
    async def notify(self, *, end_user_id: UUID, category: str, copy: LocalizedNotificationCopy, data: Optional[dict] = None) -> NotificationResult:
        """
        Create a Notification for an End user and fan it out to every active Device
        it owns, one send per distinct Device locale so each install gets copy in the
        language it is actually set to (ADR 0009). Zero active devices is a valid
        no-op (the Notification row is still created). Never raises to the caller — a
        gateway exception becomes a failed NotificationDelivery for that group's devices.
        """
        notification = await self._notification_repository.create_notification(
            end_user_id=end_user_id, category=category, title=copy.default.title, body=copy.default.body, data=data
        )

        devices = await self._device_repository.list_active_devices(end_user_id)
        if not devices:
            return notification

        deliveries: list[NotificationDeliveryDraft] = []
        unregistered_device_ids: list[UUID] = []
        for locale, group in self._group_by_locale(devices).items():
            group_copy = copy.for_locale(locale)
            try:
                send_results = await self._push_gateway.send_multicast(
                    tokens=[device.token for device in group], title=group_copy.title, body=group_copy.body, data=data
                )
            except Exception as error:
                logger.warning(f"Push gateway send_multicast failed for notification {notification.id} (locale {locale}): {error}")
                deliveries.extend(
                    NotificationDeliveryDraft(notification_id=notification.id, device_id=device.id, status=DeliveryStatus.FAILED, error=str(error))
                    for device in group
                )
                continue

            delivered_at = datetime.now(timezone.utc)
            for device, result in zip(group, send_results):
                if result.status == PushSendStatus.SUCCESS:
                    deliveries.append(
                        NotificationDeliveryDraft(
                            notification_id=notification.id, device_id=device.id, status=DeliveryStatus.SUCCESS, delivered_at=delivered_at
                        )
                    )
                    continue

                deliveries.append(
                    NotificationDeliveryDraft(notification_id=notification.id, device_id=device.id, status=DeliveryStatus.FAILED, error=result.error)
                )
                if result.status == PushSendStatus.UNREGISTERED:
                    unregistered_device_ids.append(device.id)

        await self._notification_repository.record_deliveries(deliveries)
        if unregistered_device_ids:
            await self._device_repository.deactivate_devices(unregistered_device_ids)

        return notification
