import re

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.models import CommerceCodeCounter, Product, ProductSKU


PRODUCT_CODE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9._-]*$")


def normalize_product_code(value: str) -> str:
    code = value.strip().upper()
    if not code or not PRODUCT_CODE_PATTERN.fullmatch(code):
        raise ValueError("상품코드는 영문·숫자·점·밑줄·하이픈만 사용할 수 있습니다.")
    return code


def allocate_product_code(db: Session, workspace_id: str) -> str:
    """Allocate a permanent product code while holding a database row lock."""
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        # Also serializes the very first allocation, before the counter row exists.
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": workspace_id})
    counter = db.scalar(
        select(CommerceCodeCounter)
        .where(CommerceCodeCounter.workspace_id == workspace_id)
        .with_for_update()
    )
    if counter is None:
        # Preserve legacy codes and start after any already-issued automatic code.
        codes = db.scalars(select(Product.product_code).where(Product.workspace_id == workspace_id)).all()
        used = [int(code[4:]) for code in codes if code.startswith("PRD-") and code[4:].isdigit()]
        counter = CommerceCodeCounter(workspace_id=workspace_id, next_product_number=max(used, default=0) + 1)
        db.add(counter)
        db.flush()
    number = counter.next_product_number
    counter.next_product_number += 1
    return f"PRD-{number:06d}"


def next_sku_code(db: Session, product: Product) -> str:
    db.scalar(select(Product.id).where(Product.id == product.id).with_for_update())
    prefix = product.product_code.replace("PRD-", "SKU-", 1) if product.product_code.startswith("PRD-") else f"SKU-{product.product_code}"
    codes = db.scalars(select(ProductSKU.sku_code).where(ProductSKU.product_id == product.id)).all()
    used = []
    for code in codes:
        suffix = code.rsplit("-", 1)[-1]
        if code.startswith(prefix + "-") and suffix.isdigit():
            used.append(int(suffix))
    return f"{prefix}-{max(used, default=0) + 1:02d}"


def create_sku(db: Session, *, product: Product, name: str, option_value: str | None = None,
               barcode: str | None = None, sales_unit: str = "each") -> ProductSKU:
    row = ProductSKU(
        tenant_id=product.tenant_id,
        product_id=product.id,
        sku_code=next_sku_code(db, product),
        name=name,
        option_value=option_value,
        barcode=barcode or None,
        sales_unit=sales_unit,
        status="active",
    )
    db.add(row)
    db.flush()
    return row
