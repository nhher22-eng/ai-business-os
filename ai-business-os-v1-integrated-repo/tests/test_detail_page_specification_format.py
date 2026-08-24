from app.services.detail_page_studio import (
    _clean_detail_specification,
    _feature_specification,
)


def test_formats_json_dimensions_without_product_specific_values():
    raw = (
        '주재질: 원목 | 보조재질: 스테인리스 | 중량: 40kg | '
        '사이즈: {"length":"1200mm","width":"450mm","height":"650mm"} | '
        '제조사: 테스트'
    )
    cleaned = _clean_detail_specification(raw)

    assert "크기: 길이 1200mm · 폭 450mm · 높이 650mm" in cleaned
    assert '{"length"' not in cleaned
    assert "주재질: 원목\n보조재질: 스테인리스" in cleaned


def test_formats_single_quoted_dimensions():
    raw = "사이즈: {'length': '900mm', 'width': '300mm', 'height': '500mm'}"
    cleaned = _clean_detail_specification(raw)

    assert "크기: 길이 900mm · 폭 300mm · 높이 500mm" in cleaned
    assert "{'length'" not in cleaned


def test_feature_specification_keeps_material_and_physical_features():
    cleaned = _clean_detail_specification(
        "주재질: 원목 | 보조재질: 스테인리스 | 중량: 40kg | "
        "추가 FACT: 이동용 우레탄바퀴 및 드레인 출수구 포함"
    )
    feature = _feature_specification(cleaned)

    assert "주재질: 원목" in feature
    assert "보조재질: 스테인리스" in feature
    assert "우레탄바퀴" in feature
    assert "드레인 출수구" in feature
