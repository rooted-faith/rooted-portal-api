from datetime import date

import pytest
from fastapi.routing import APIRoute

from portal.application.auth.results import HeaderInfo
from portal.domain.devotion.entities import AnonymousDailyLesson, DailyLesson, Passage
from portal.libs.contexts.request_context import RequestContext
from portal.libs.contexts.user_context import UserContext
from portal.routers.apis.v1 import devotion as devotion_router_module
from portal.routers.apis.v1.devotion import get_daily_lesson, get_today_daily_lesson, router


class StubDevotionService:
    async def get_daily_lesson(self, lesson_date, locale_id, locale_code, include_authored_sections):
        assert locale_code == "en"
        if include_authored_sections:
            return DailyLesson(
                date=lesson_date,
                passage=Passage(start="JHN.3.16", end="JHN.3.16", ref="John 3:16", verses=["Verse text"]),
                reflect=["Reflect"],
                apply="Apply",
                pray="Pray",
            )
        return AnonymousDailyLesson(date=lesson_date, passage=Passage(start="JHN.3.16", end="JHN.3.16", ref="John 3:16", verses=["Verse text"]))


def stub_request_context(monkeypatch, user_context=None):
    monkeypatch.setattr(devotion_router_module, "get_resolved_locale_id", lambda: None)
    monkeypatch.setattr(devotion_router_module, "get_resolved_locale_code", lambda: "en")
    monkeypatch.setattr(devotion_router_module, "get_request_context", lambda: None)
    monkeypatch.setattr(devotion_router_module, "get_user_context", lambda: user_context)


def test_devotion_today_route_is_available_as_get():
    routes = [route for route in router.routes if isinstance(route, APIRoute)]
    assert any(route.path == "/today" and "GET" in route.methods for route in routes)
    assert any(route.path == "/lessons/{date}" and "GET" in route.methods for route in routes)
    for route in routes:
        auth_config = route.endpoint.__auth_config__
        assert auth_config.require_auth is False
        assert auth_config.optional_auth is True


@pytest.mark.asyncio
async def test_anonymous_today_response_omits_authored_sections(monkeypatch):
    stub_request_context(monkeypatch)

    response = await get_today_daily_lesson(date_=date(2026, 9, 8), devotion_service=StubDevotionService())
    payload = response.model_dump(mode="json", by_alias=True)

    assert payload["locked"] == ["reflect", "apply", "pray", "note"]
    assert not {"reflect", "apply", "pray", "note"} & payload.keys()
    assert "data" not in payload


@pytest.mark.asyncio
async def test_signed_in_today_response_includes_authored_sections(monkeypatch):
    stub_request_context(monkeypatch, UserContext(user_id="11111111-1111-1111-1111-111111111111"))

    response = await get_today_daily_lesson(date_=date(2026, 9, 8), devotion_service=StubDevotionService())
    payload = response.model_dump(mode="json", by_alias=True)

    assert payload["locked"] == []
    assert payload["reflect"] == ["Reflect"]
    assert payload["apply"] == "Apply"
    assert payload["pray"] == "Pray"


@pytest.mark.asyncio
async def test_past_date_uses_same_anonymous_gating(monkeypatch):
    stub_request_context(monkeypatch)

    response = await get_daily_lesson(date_=date(2026, 9, 7), devotion_service=StubDevotionService())
    payload = response.model_dump(mode="json", by_alias=True)

    assert payload["date"] == "2026-09-07"
    assert payload["locked"] == ["reflect", "apply", "pray", "note"]
    assert not {"reflect", "apply", "pray"} & payload.keys()


@pytest.mark.asyncio
async def test_past_date_uses_same_signed_in_gating(monkeypatch):
    stub_request_context(monkeypatch, UserContext(user_id="11111111-1111-1111-1111-111111111111"))

    response = await get_daily_lesson(date_=date(2026, 9, 7), devotion_service=StubDevotionService())
    payload = response.model_dump(mode="json", by_alias=True)

    assert payload["date"] == "2026-09-07"
    assert payload["locked"] == []
    assert payload["reflect"] == ["Reflect"]
    assert payload["apply"] == "Apply"
    assert payload["pray"] == "Pray"


@pytest.mark.asyncio
async def test_unaccepted_default_locale_is_not_used_as_translation_fallback(monkeypatch):
    captured = {}

    class CapturingService(StubDevotionService):
        async def get_daily_lesson(self, lesson_date, locale_id, locale_code, include_authored_sections):
            captured.update(locale_id=locale_id, locale_code=locale_code)
            return await super().get_daily_lesson(lesson_date, locale_id, "en", include_authored_sections)

    monkeypatch.setattr(devotion_router_module, "get_resolved_locale_id", lambda: object())
    monkeypatch.setattr(devotion_router_module, "get_resolved_locale_code", lambda: "en")
    monkeypatch.setattr(
        devotion_router_module, "get_request_context", lambda: RequestContext(headers=HeaderInfo(), locale_candidates=["fr"], resolved_locale_code="en")
    )

    monkeypatch.setattr(devotion_router_module, "get_user_context", lambda: None)

    await get_today_daily_lesson(date_=date(2026, 9, 8), devotion_service=CapturingService())

    assert captured == {"locale_id": None, "locale_code": None}
