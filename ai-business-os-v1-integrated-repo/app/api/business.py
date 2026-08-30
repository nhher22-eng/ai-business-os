from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dashboard_session import require_business_auth
from app.db.models import BusinessWorkspace, Product, ProductSKU, ProductDetail, ProductComponent
from app.db.session import SessionLocal
from app.services.commerce_codes import normalize_product_code


router = APIRouter(
    prefix="/api/v1/business",
    tags=["business"],
    dependencies=[Depends(require_business_auth)],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class WorkspaceBody(BaseModel):
    name: str
    slug: str
    business_type: str = "commerce"
    mode: Literal["shadow", "controlled_live", "live"] = "shadow"


class ProductBody(BaseModel):
    workspace_id: str
    product_code: str
    name: str
    status: str = "draft"
    sales_channel: str | None = None
    description: str | None = None
    image_nonlocked_allowed: bool = False


class ProductImagePolicyBody(BaseModel):
    image_nonlocked_allowed: bool


@router.patch("/products/{product_id}/image-policy")
def update_product_image_policy(
    product_id: str,
    body: ProductImagePolicyBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    row = db.scalar(
        select(Product).where(Product.id == product_id, Product.tenant_id == tenant_id)
    )
    if row is None:
        raise HTTPException(status_code=404, detail="product not found")
    row.image_nonlocked_allowed = body.image_nonlocked_allowed
    db.commit()
    return {
        "id": row.id,
        "image_nonlocked_allowed": row.image_nonlocked_allowed,
    }



class SKUBody(BaseModel):
    product_id: str
    sku_code: str
    name: str
    option_value: str | None = None
    status: str = "active"


@router.post("/workspaces")
def create_workspace(
    body: WorkspaceBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    existing = db.scalar(
        select(BusinessWorkspace).where(
            BusinessWorkspace.tenant_id == tenant_id,
            BusinessWorkspace.slug == body.slug,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="workspace already exists")

    row = BusinessWorkspace(
        tenant_id=tenant_id,
        name=body.name,
        slug=body.slug,
        business_type=body.business_type,
        mode=body.mode,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "name": row.name,
        "slug": row.slug,
        "business_type": row.business_type,
        "status": row.status,
        "mode": row.mode,
    }


@router.get("/workspaces")
def list_workspaces(
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(BusinessWorkspace).where(
            BusinessWorkspace.tenant_id == tenant_id,
        )
    ).all()

    return [
        {
            "id": row.id,
            "name": row.name,
            "slug": row.slug,
            "business_type": row.business_type,
            "status": row.status,
            "mode": row.mode,
        }
        for row in rows
    ]


@router.post("/products")
def create_product(
    body: ProductBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    workspace = db.scalar(
        select(BusinessWorkspace).where(
            BusinessWorkspace.id == body.workspace_id,
            BusinessWorkspace.tenant_id == tenant_id,
        )
    )
    if workspace is None:
        raise HTTPException(status_code=404, detail="workspace not found")

    try:
        product_code = normalize_product_code(body.product_code)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    existing = db.scalar(
        select(Product).where(
            Product.workspace_id == body.workspace_id,
            func.lower(Product.product_code) == product_code.lower(),
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="product already exists")

    row = Product(
        tenant_id=tenant_id,
        workspace_id=body.workspace_id,
        product_code=product_code,
        name=body.name,
        status=body.status,
        sales_channel=body.sales_channel,
        description=body.description,
        image_nonlocked_allowed=body.image_nonlocked_allowed,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return {
        "id": row.id,
        "workspace_id": row.workspace_id,
        "product_code": row.product_code,
        "name": row.name,
        "status": row.status,
        "sales_channel": row.sales_channel,
        "description": row.description,
        "image_nonlocked_allowed": row.image_nonlocked_allowed,
    }


@router.get("/products")
def list_products(
    workspace_id: str = Query(...),
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(Product).where(
            Product.tenant_id == tenant_id,
            Product.workspace_id == workspace_id,
        )
    ).all()

    return [
        {
            "id": row.id,
            "product_code": row.product_code,
            "name": row.name,
            "status": row.status,
            "sales_channel": row.sales_channel,
            "description": row.description,
            "image_nonlocked_allowed": row.image_nonlocked_allowed,
        }
        for row in rows
    ]


@router.post("/skus")
def create_sku(
    body: SKUBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    product = db.scalar(
        select(Product).where(
            Product.id == body.product_id,
            Product.tenant_id == tenant_id,
        )
    )
    if product is None:
        raise HTTPException(status_code=404, detail="product not found")

    existing = db.scalar(
        select(ProductSKU).where(
            ProductSKU.product_id == body.product_id,
            ProductSKU.sku_code == body.sku_code,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="sku already exists")

    row = ProductSKU(
        tenant_id=tenant_id,
        product_id=body.product_id,
        sku_code=body.sku_code,
        name=body.name,
        option_value=body.option_value,
        status=body.status,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return {
        "id": row.id,
        "product_id": row.product_id,
        "sku_code": row.sku_code,
        "name": row.name,
        "option_value": row.option_value,
        "status": row.status,
    }


@router.get("/skus")
def list_skus(
    product_id: str = Query(...),
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(ProductSKU).where(
            ProductSKU.tenant_id == tenant_id,
            ProductSKU.product_id == product_id,
        )
    ).all()

    return [
        {
            "id": row.id,
            "sku_code": row.sku_code,
            "name": row.name,
            "option_value": row.option_value,
            "status": row.status,
        }
        for row in rows
    ]


class ProductDetailBody(BaseModel):
    product_id: str
    specification: str | None = None
    usage: str | None = None
    installation_method: str | None = None
    usage_conditions: str | None = None
    cautions: str | None = None


@router.put("/product-detail")
def upsert_product_detail(
    body: ProductDetailBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    product = db.scalar(
        select(Product).where(
            Product.id == body.product_id,
            Product.tenant_id == tenant_id,
        )
    )
    if product is None:
        raise HTTPException(status_code=404, detail="product not found")

    row = db.scalar(
        select(ProductDetail).where(
            ProductDetail.product_id == body.product_id,
            ProductDetail.tenant_id == tenant_id,
        )
    )

    if row is None:
        row = ProductDetail(
            tenant_id=tenant_id,
            product_id=body.product_id,
        )
        db.add(row)

    row.specification = body.specification
    row.usage = body.usage
    row.installation_method = body.installation_method
    row.usage_conditions = body.usage_conditions
    row.cautions = body.cautions

    db.commit()
    db.refresh(row)

    return {
        "id": row.id,
        "product_id": row.product_id,
        "specification": row.specification,
        "usage": row.usage,
        "installation_method": row.installation_method,
        "usage_conditions": row.usage_conditions,
        "cautions": row.cautions,
    }


@router.get("/product-detail")
def get_product_detail(
    product_id: str = Query(...),
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    row = db.scalar(
        select(ProductDetail).where(
            ProductDetail.product_id == product_id,
            ProductDetail.tenant_id == tenant_id,
        )
    )

    if row is None:
        raise HTTPException(status_code=404, detail="product detail not found")

    return {
        "id": row.id,
        "product_id": row.product_id,
        "specification": row.specification,
        "usage": row.usage,
        "installation_method": row.installation_method,
        "usage_conditions": row.usage_conditions,
        "cautions": row.cautions,
    }


class ProductComponentBody(BaseModel):
    product_id: str
    sku_id: str
    component_code: str
    name: str
    quantity: int
    unit: str
    notes: str | None = None
    status: str = "active"


@router.post("/components")
def create_component(
    body: ProductComponentBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    sku = db.scalar(
        select(ProductSKU).where(
            ProductSKU.id == body.sku_id,
            ProductSKU.product_id == body.product_id,
            ProductSKU.tenant_id == tenant_id,
        )
    )

    if sku is None:
        raise HTTPException(
            status_code=404,
            detail="sku not found",
        )

    existing = db.scalar(
        select(ProductComponent).where(
            ProductComponent.sku_id == body.sku_id,
            ProductComponent.component_code == body.component_code,
        )
    )

    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="component already exists",
        )

    row = ProductComponent(
        tenant_id=tenant_id,
        product_id=body.product_id,
        sku_id=body.sku_id,
        component_code=body.component_code,
        name=body.name,
        quantity=body.quantity,
        unit=body.unit,
        notes=body.notes,
        status=body.status,
    )

    db.add(row)
    db.commit()
    db.refresh(row)

    return {
        "id": row.id,
        "sku_id": row.sku_id,
        "component_code": row.component_code,
        "name": row.name,
        "quantity": row.quantity,
        "unit": row.unit,
        "notes": row.notes,
        "status": row.status,
    }


@router.get("/components")
def list_components(
    sku_id: str = Query(...),
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(ProductComponent).where(
            ProductComponent.tenant_id == tenant_id,
            ProductComponent.sku_id == sku_id,
        )
    ).all()

    return [
        {
            "id": row.id,
            "component_code": row.component_code,
            "name": row.name,
            "quantity": row.quantity,
            "unit": row.unit,
            "notes": row.notes,
            "status": row.status,
        }
        for row in rows
    ]
