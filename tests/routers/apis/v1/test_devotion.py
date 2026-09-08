from datetime import date

import pytest
from fastapi.routing import APIRoute

from portal.domain.devotion.entities import AnonymousDailyLesson, Passage
from portal.routers.apis.v1 import devotion as devotion_router_module
from portal.routers.apis.v1.devotion import get_anonymous_daily_lesson, router


class StubDevotionService:
    async def get_anonymous_today(self, lesson_date, locale_id, locale_code):
        assert locale_code == "en"
        return AnonymousDailyLesson(date=lesson_date, passage=Passage(start="JHN.3.16", end="JHN.3.16", ref="John 3:16", verses=["Verse text"]))


def test_devotion_today_route_is_available_as_get():
    routes = [route for route in router.routes if isinstance(route, APIRoute)]
    assert any(route.path == "/today" and "GET" in route.methods for route in routes)


@pytest.mark.asyncio
async def test_anonymous_today_response_omits_authored_sections(monkeypatch):
    monkeypatch.setattr(devotion_router_module, "get_resolved_locale_id", lambda: None)
    monkeypatch.setattr(devotion_router_module, "get_resolved_locale_code", lambda: "en")

    response = await get_anonymous_daily_lesson(date_=date(2026, 9, 8), devotion_service=StubDevotionService())
    payload = response.model_dump(mode="json", by_alias=True)

    assert payload["locked"] == ["reflect", "apply", "pray", "note"]
    assert not {"reflect", "apply", "pray", "note"} & payload.keys()
    assert "data" not in payload
