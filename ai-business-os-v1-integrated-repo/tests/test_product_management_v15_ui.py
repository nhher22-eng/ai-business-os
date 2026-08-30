from app.product_detail_v2_ui import DETAIL_HTML_V2


def test_integrated_management_keeps_approved_tabs_and_execution_modes():
    for marker in ("상품정보", "상품설명", "옵션·SKU", "가격·재고·배송", "등록 자료", "판매콘텐츠", "판매채널", "사용자 직접 실행", "설정 기반 자동화", "Agent 판단 실행", "Agent 실행 허용"):
        assert marker in DETAIL_HTML_V2


def test_product_information_and_description_fields_match_decision():
    for marker in ("대표이미지", "상품 분류 · 신규등록 기준값", "주재질", "보조재질", "중량", "길이", "폭", "높이", "용량", "인증 관련", "구성품", "추가 FACT 메모", "특징 (한 줄에 하나)", "장점 (한 줄에 하나)", "용도 (한 줄에 하나)", "사용방법 (한 줄에 하나)", "주의사항 (한 줄에 하나)", "AI 제안"):
        assert marker in DETAIL_HTML_V2


def test_assets_support_assignment_and_separate_enlargement():
    for marker in ("등록된 원본 이미지", "이미지 생성·가공", "imageCard('hero'", "imageCard('right_45'", "imageCard('front'", "assignImage(role)", "openImage", "moveImage", "이 원본 선택", "object-fit:contain"):
        assert marker in DETAIL_HTML_V2


def test_shipping_is_editable_fee_not_placeholder():
    assert "<label>배송비</label>" in DETAIL_HTML_V2
    assert "별도 배송설정 연결 예정" not in DETAIL_HTML_V2
