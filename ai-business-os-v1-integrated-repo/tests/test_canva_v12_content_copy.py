import pytest
from fastapi import HTTPException

from app.api.content_copy import (
    CanvaV12AIProposalBody,
    TARGET_SLOTS,
    SaveCandidateBody,
    _candidate,
    canva_v12_ai_candidates,
)
from app.workflow_ui import COPY
from app.services.canva_v12_text_export import (
    CANVA_V12_COPY_FIELDS,
    FACT_BOUND_FIELDS,
    SKU_BOUND_FIELDS,
)


def test_canva_v12_copy_slots_exclude_fact_and_sku_bound_fields():
    slot_names = tuple(name for name, _ in TARGET_SLOTS["canva_v12"])
    assert slot_names == CANVA_V12_COPY_FIELDS
    assert not (set(slot_names) & FACT_BOUND_FIELDS)
    assert not (set(slot_names) & SKU_BOUND_FIELDS)
    assert len(slot_names) + len(FACT_BOUND_FIELDS) + len(SKU_BOUND_FIELDS) == 72


def test_canva_v12_target_is_accepted_by_copy_asset_request():
    body = SaveCandidateBody(
        target_type="canva_v12",
        slot_key="hero_headline",
        content="승인할 문안",
    )
    assert body.target_type == "canva_v12"


def test_canva_candidate_uses_fact_only_where_a_basis_exists():
    facts = {
        "product_name": "8mm 자동 관수키트",
        "description": "확정 설명",
        "features": "확정 특징",
        "usage": "확정 용도",
        "dimensions": {"호스 외경": "8mm"},
        "material": "확정 재질",
        "installation": None,
        "caution": None,
    }
    assert _candidate("hero_headline", facts)[0] == "확정 특징"
    assert _candidate("review_1_text", facts)[0] == ""


def test_copy_ui_requires_explicit_ai_execution_and_human_approval():
    assert "Canva 미작성 문안 AI 제안" in COPY
    assert "execution_approved:true" in COPY
    assert "자동 저장·승인되지 않습니다" in COPY
    assert "이 문안 검토·승인" in COPY
    assert "/canva-v12/ai-candidates" in COPY


def test_ai_endpoint_refuses_execution_without_explicit_approval():
    with pytest.raises(HTTPException) as exc:
        canva_v12_ai_candidates(
            "product-id",
            CanvaV12AIProposalBody(execution_approved=False),
            tenant_id="tenant",
            db=None,
        )
    assert exc.value.status_code == 409
