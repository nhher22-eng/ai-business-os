from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import Base, BusinessWorkspace, DetailPageJob, Product, ProductDetail
from app.services.detail_page_studio import create_prepared_version, ensure_defaults, run_qa


def test_conditional_sections_are_hidden_and_spec_image_is_optional():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    ws = BusinessWorkspace(tenant_id="t", name="Commerce", slug="commerce")
    db.add(ws); db.flush()
    p = Product(tenant_id="t", workspace_id=ws.id, product_code="P", name="Product", status="draft")
    db.add(p); db.flush()
    db.add(ProductDetail(tenant_id="t", product_id=p.id, specification="8mm / 20cm", usage="베란다"))
    db.flush()
    brand, templates = ensure_defaults(db, tenant_id="t", workspace_id=ws.id)
    job = DetailPageJob(tenant_id="t", workspace_id=ws.id, product_id=p.id)
    db.add(job); db.flush()
    v = create_prepared_version(db, job=job, template=templates[0], brand=brand, visual_style="natural", page_strategy="review_first", change_summary="test")
    db.commit()
    rows = {x.section_type: x for x in v.sections} if getattr(v, 'sections', None) else {}
    # Load through relationship-independent query for portability.
    from app.db.models import DetailPageSection
    rows = {x.section_type: x for x in db.query(DetailPageSection).filter(DetailPageSection.version_id == v.id).all()}
    assert rows["ADD_ON"].is_enabled is False and rows["ADD_ON"].qa_status == "hidden"
    assert rows["RELATED_PRODUCTS"].is_enabled is False and rows["RELATED_PRODUCTS"].qa_status == "hidden"
    qa = run_qa(db, job=job, version=v)
    codes = {x.check_code: x for x in qa}
    assert codes["SPEC_DATA"].status == "PASS"
    # Missing lifestyle still legitimately needs human review; SPEC image alone does not.
    assert codes["IMAGE_ASSETS"].status == "REVIEW"
