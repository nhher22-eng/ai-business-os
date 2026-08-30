from app.services import canva_v12_copy_ai
from app.services.canva_v12_copy_ai import (
    AI_BLOCKED_FIELDS,
    AI_ELIGIBLE_FIELDS,
    _safe_proposals,
    generate_canva_v12_copy_candidates,
)


def test_ai_never_generates_reviews_or_policy_facts():
    assert "review_1_text" not in AI_ELIGIBLE_FIELDS
    assert "shipping_copy" not in AI_ELIGIBLE_FIELDS
    raw = {
        "hero_headline": "근거 기반 문안",
        "review_1_text": "가짜 리뷰",
        "shipping_copy": "임의 배송정책",
        "unknown": "알 수 없는 필드",
    }
    assert _safe_proposals(raw) == {"hero_headline": "근거 기반 문안"}
    assert {"review_1_text", "shipping_copy"} <= AI_BLOCKED_FIELDS


def test_ai_is_blocked_until_facts_are_confirmed():
    proposals, meta = generate_canva_v12_copy_candidates(
        product_name="상품",
        confirmed_facts={"facts_confirmed": False},
        approved_copy={},
    )
    assert proposals == {}
    assert meta["provider"] == "blocked"
    assert meta["reason"] == "facts_unconfirmed"


def test_ai_response_is_sanitized_before_showing_candidates(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "output_text": (
                    '{"hero_headline":"근거 기반 후보",'
                    '"review_1_text":"가짜 리뷰",'
                    '"shipping_copy":"임의 배송조건"}'
                )
            }

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def post(self, *_args, **_kwargs):
            return FakeResponse()

    monkeypatch.setattr(canva_v12_copy_ai.settings, "openai_api_key", "test-key")
    monkeypatch.setattr(canva_v12_copy_ai.httpx, "Client", FakeClient)
    proposals, meta = generate_canva_v12_copy_candidates(
        product_name="8mm 자동 관수키트",
        confirmed_facts={"facts_confirmed": True, "usage": "화분 관수"},
        approved_copy={},
    )
    assert proposals == {"hero_headline": "근거 기반 후보"}
    assert meta["provider"] == "openai-canva-copy-v1.2"
    assert meta["auto_saved"] is False
    assert meta["auto_approved"] is False
