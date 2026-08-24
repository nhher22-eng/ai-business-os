from app.api.content_copy import TARGET_SLOTS, _candidate
from app.workflow_ui import COPY, HOME


def test_home_exposes_company_work_and_five_support_tools():
    assert "오늘의 업무" in HOME
    assert "도구가 아닌 실제 업무를 선택" in HOME
    assert "AI Agent의 다음 업무 제안" in HOME
    assert "FACT 확정·예산 증액·외부 게시를 자동 수행하지 않습니다" in HOME
    assert "상품 기본정보 등록" in HOME
    assert "이미지 요소 자산 생성기" in HOME
    assert "콘텐츠 문안 생성기" in HOME
    assert "템플릿 제작기" in HOME
    assert "상세페이지 생성기" in HOME
    assert 'href="/product-registration"' in HOME
    assert 'href="/image-assets"' in HOME
    assert 'href="/content-copy-studio"' in HOME
    assert 'href="/template-maker"' in HOME
    assert 'href="/detail-page-builder"' in HOME


def test_content_copy_ui_preserves_fact_and_approval_boundary():
    assert "AI 제안은 2차 FACT 후보" in COPY
    assert "원본 FACT를 수정하지 않으며" in COPY
    assert "승인된 표현 자산" in COPY
    assert "용도에 따라 요구 슬롯 자동 변경" in COPY


def test_copy_requirements_change_by_target():
    assert dict(TARGET_SLOTS["detail_page"])["headline"] == "메인 헤드라인"
    assert "cta" in dict(TARGET_SLOTS["advertisement"])
    assert "installation" in dict(TARGET_SLOTS["manual"])
    assert "installation" not in dict(TARGET_SLOTS["catalog"])


def test_fact_substitution_candidate_keeps_source_keys():
    text, keys, method = _candidate(
        "specification",
        {
            "product_name": "테스트 상품",
            "description": "",
            "features": [],
            "usage": "",
            "dimensions": {"width": "20 cm"},
            "material": "스틸",
            "installation": "",
            "caution": "",
        },
    )
    assert "20 cm" in text
    assert "스틸" in text
    assert keys == ["dimensions", "primary_material"]
    assert method == "fact_substitution"
