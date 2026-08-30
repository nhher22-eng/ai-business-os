from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.models import (
    Base,
    BusinessWorkspace,
    DetailPageJob,
    Product,
    ProductComponent,
    ProductDetail,
    ProductRelation,
    ProductSKU,
    ReviewSource,
)
from app.services.detail_page_studio import (
    approve_version,
    build_sections,
    create_prepared_version,
    ensure_defaults,
    qa_summary,
    run_qa,
)


def make_db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def seed(db: Session):
    ws = BusinessWorkspace(tenant_id="t", name="Commerce", slug="commerce")
    db.add(ws); db.flush()
    product = Product(
        tenant_id="t", workspace_id=ws.id, product_code="IRRIGATION", name="8mm 자동 관수키트",
        status="draft", sales_channel="naver-smartstore", description="8mm 미세분무 관수키트",
    )
    db.add(product); db.flush()
    detail = ProductDetail(
        tenant_id="t", product_id=product.id, specification="8mm / 분무스틱 20cm",
        usage="베란다, 텃밭, 플랜터 관수", installation_method="수도 연결 → 호스 배치 → T형 연결구 → 분무스틱",
        cautions="워터타이머는 별도 추가상품",
    )
    db.add(detail)
    for meters, qty in [("10m", 10), ("20m", 20), ("30m", 30)]:
        sku = ProductSKU(
            tenant_id="t", product_id=product.id, sku_code=f"KIT-{meters}", name=meters,
            option_value=meters, status="active",
        )
        db.add(sku); db.flush()
        db.add(ProductComponent(
            tenant_id="t", product_id=product.id, sku_id=sku.id, component_code="SPRAY-STICK",
            name="20cm 분무스틱", quantity=qty, unit="개", status="active",
        ))
        db.add(ProductComponent(
            tenant_id="t", product_id=product.id, sku_id=sku.id, component_code="TEE",
            name="T형 연결구", quantity=qty, unit="개", status="active",
        ))
    db.add(ProductRelation(
        tenant_id="t", source_product_id=product.id, relation_type="ADD_ON",
        display_name="워터타이머", target_url="https://example.com/timer", is_active=True,
    ))
    db.add(ReviewSource(
        tenant_id="t", product_id=product.id, channel="naver", external_review_id="R1",
        rating=5, review_text="베란다에서 사용하기 편리했습니다.", is_verified=True,
    ))
    db.commit()
    return ws, product


def test_detail_sections_keep_reviews_and_conditionally_add_relations():
    db = make_db(); ws, product = seed(db)
    rows = build_sections(db, tenant_id="t", product_id=product.id, strategy="review_first")
    by_type = {r["section_type"]: r for r in rows}
    assert by_type["REVIEW_SUMMARY"]["is_required"] is False
    assert by_type["REVIEW_DETAIL"]["is_required"] is False
    assert by_type["REVIEW_SUMMARY"]["content_json"]["data_status"] == "ready"
    assert by_type["ADD_ON"]["is_enabled"] is True
    assert by_type["ADD_ON"]["content_json"]["items"][0]["name"] == "워터타이머"
    assert by_type["RELATED_PRODUCTS"]["is_enabled"] is False


def test_qa_requires_human_ack_for_review_but_blocks_no_fact_error():
    db = make_db(); ws, product = seed(db)
    brand, templates = ensure_defaults(db, tenant_id="t", workspace_id=ws.id)
    job = DetailPageJob(tenant_id="t", workspace_id=ws.id, product_id=product.id)
    db.add(job); db.flush()
    version = create_prepared_version(
        db, job=job, template=templates[0], brand=brand, visual_style="natural",
        page_strategy="review_first", change_summary="test",
    )
    db.commit()
    qa = run_qa(db, job=job, version=version)
    db.commit()
    assert qa_summary(qa) == "REVIEW"  # image assets still require review
    assert not any(x.status == "FAIL" for x in qa)
    approve_version(db, job=job, version=version, acknowledge_review=True)
    db.commit()
    assert job.status == "approved"
    assert job.approved_version_no == version.version_no
