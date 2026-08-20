from app.product_image_suggestion_ui_patch import (
    inject_image_studio_suggestion_edit_mode,
    inject_product_image_suggestion_ui,
)
from app.services.product_image_suggestions import build_image_suggestion_plan


def test_image_suggestion_plan_uses_safe_hard_lock_ready_roles():
    plan = build_image_suggestion_plan(
        "테스트 상품",
        {
            "operating": {"usage": ["베란다 화분 관리"]},
            "marketing": {
                "features": ["등록 FACT 기반 구성"],
                "selling_points": ["설치 후 사용 흐름이 이해하기 쉬움"],
                "content_direction": "실제 사용 환경 중심",
            },
        },
    )

    assert [row["image_type"] for row in plan] == ["HERO", "LIFESTYLE", "EXPLANATION"]
    assert all(row["usage_context"] == "SMARTSTORE" for row in plan)
    assert all("기준 이미지" in row["request_text"] for row in plan)
    assert "베란다 화분 관리" in plan[1]["request_text"]


def test_product_registration_patch_adds_image_suggestion_actions():
    source = "<script>document.getElementById('saveFacts').onclick=saveFacts;</script>"
    patched = inject_product_image_suggestion_ui(source)

    assert "product-image-suggestion-ui-v1" in patched
    assert "편집 후 채택" in patched
    assert "adoptImageSuggestion" in patched
    assert "product-image-suggestions" in patched
    assert inject_product_image_suggestion_ui(patched) == patched


def test_image_studio_patch_adds_contextual_edit_mode():
    marker = "init().catch(e=>{el('sessionStatus').textContent='연결 오류';console.error(e)});"
    source = f"<script>{marker}</script>"
    patched = inject_image_studio_suggestion_edit_mode(source)

    assert "suggestion-edit-mode-v1" in patched
    assert "AI 제안 이미지 편집 모드" in patched
    assert "adoptSuggestionAndReturn" in patched
    assert "hard_lock" in patched
    assert inject_image_studio_suggestion_edit_mode(patched) == patched
