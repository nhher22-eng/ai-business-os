from app.services.product_master_integration_patch import (
    _fact_summary,
    _feature_fact_summary,
)


def test_master_dimensions_are_rendered_without_json():
    summary = _fact_summary(
        {
            "primary_material": "원목",
            "secondary_material": "스테인리스",
            "weight": "40kg",
            "dimensions": {
                "length": "1800mm",
                "width": "600mm",
                "height": "700mm",
            },
            "manufacturer": "가든팜",
            "country_of_origin": "한국",
        }
    )

    assert summary is not None
    assert "크기: 길이 1800mm · 폭 600mm · 높이 700mm" in summary
    assert "{" not in summary
    assert "}" not in summary
    assert '"length"' not in summary


def test_master_fact_summary_uses_customer_readable_lines():
    summary = _fact_summary(
        {
            "primary_material": "원목",
            "certifications": ["인증 A", "인증 B"],
            "packaging": {"individual": "1개", "box": "2개"},
        }
    )

    assert summary == (
        "주재질: 원목\n"
        "인증: 인증 A · 인증 B\n"
        "포장: individual: 1개 · box: 2개"
    )


def test_feature_summary_excludes_dimensions_and_supplier_fields():
    summary = (
        "주재질: 원목\n"
        "보조재질: 스테인리스\n"
        "중량: 40kg\n"
        "크기: 길이 1800mm · 폭 600mm · 높이 700mm\n"
        "제조사: 가든팜\n"
        "추가 정보: 이동용 우레탄바퀴와 드레인 출수구 포함"
    )

    feature = _feature_fact_summary(summary)

    assert feature is not None
    assert "주재질: 원목" in feature
    assert "보조재질: 스테인리스" in feature
    assert "우레탄바퀴" in feature
    assert "드레인 출수구" in feature
    assert "크기:" not in feature
    assert "제조사:" not in feature
