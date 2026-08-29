from __future__ import annotations

import hashlib
import json
import re
import secrets
import shutil
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import redis
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import (
    DetailPageJob,
    ImageReferenceAsset,
    Product,
    ProductSKU,
    SalesChannelListing,
)
from app.db.product_registration import ProductRegistrationProfile
from app.services.commerce_codes import create_sku
from app.services.image_studio import media_root, save_reference_upload


TOOL_PROTOCOL = "agent-tool-v1"
STAGE_SECONDS = 30 * 60
STAGE_PREFIX = "agent-stage:"
MAX_STAGE_FILES = 10
MAX_STAGE_BYTES = 50 * 1024 * 1024

TOOL_REGISTRY = {
    "product_price": {"risk": "read", "approval": False, "label": "판매가 조회"},
    "shipping_fee": {"risk": "read", "approval": False, "label": "배송비 조회"},
    "sku_list": {"risk": "read", "approval": False, "label": "SKU 구성 조회"},
    "primary_image": {"risk": "read", "approval": False, "label": "대표이미지 조회"},
    "image_list": {"risk": "read", "approval": False, "label": "등록 이미지 조회"},
    "detail_page": {"risk": "read", "approval": False, "label": "상세페이지 조회"},
    "category_products": {"risk": "read", "approval": False, "label": "카테고리 상품 조회"},
    "channel_status": {"risk": "read", "approval": False, "label": "판매채널 상태 조회"},
    "product_image_add": {"risk": "internal_write", "approval": True, "label": "상품 이미지 추가"},
    "sku_add": {"risk": "internal_write", "approval": True, "label": "SKU 추가"},
}


def _redis():
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


def normalize(value: str | None) -> str:
    return re.sub(r"[^0-9a-z가-힣]+", "", (value or "").lower())


def infer_action(request_text: str, *, attachment_count: int = 0) -> str | None:
    text = normalize(request_text)
    if "sku" in text and any(word in text for word in ("추가", "만들", "생성")):
        return "sku_add"
    if attachment_count and any(word in text for word in ("사진추가", "이미지추가", "사진등록", "이미지등록")):
        return "product_image_add"
    if "카테고리" in text or ("모든상품" in text and "등록" in text):
        return "category_products"
    if "네이버" in text and any(word in text for word in ("등록", "연결", "판매")):
        return "channel_status"
    if "배송비" in text:
        return "shipping_fee"
    if "판매가" in text or "판매금액" in text or "가격" in text:
        return "product_price"
    if "sku" in text and any(word in text for word in ("구성", "목록", "알려", "보여")):
        return "sku_list"
    if "대표이미지" in text or "대표사진" in text:
        return "primary_image"
    if any(word in text for word in ("등록이미지", "등록사진", "이미지모두", "사진모두")):
        return "image_list"
    if "상세페이지" in text:
        return "detail_page"
    if attachment_count:
        return "product_image_add"
    return None


def _intent_noise(action: str | None) -> set[str]:
    common = {"상품", "알려줘", "보여줘", "확인해줘", "해줘", "등록된", "모두", "추가"}
    by_action = {
        "product_price": {"판매가", "판매금액", "가격"},
        "shipping_fee": {"배송비"},
        "sku_list": {"sku", "구성"},
        "primary_image": {"대표이미지", "대표사진"},
        "image_list": {"등록이미지", "등록사진", "이미지", "사진"},
        "detail_page": {"상세페이지"},
        "channel_status": {"네이버", "상품등록", "등록"},
        "product_image_add": {"이미지", "사진", "추가", "등록"},
        "sku_add": {"sku", "추가", "판매금액", "판매가"},
    }
    return common | by_action.get(action or "", set())


def product_candidates(db: Session, *, tenant_id: str, query: str,
                       action: str | None, limit: int = 5) -> list[dict[str, Any]]:
    products = list(db.scalars(select(Product).where(
        Product.tenant_id == tenant_id,
    ).order_by(Product.updated_at.desc())).all())
    query_normal = normalize(query)
    for word in _intent_noise(action):
        query_normal = query_normal.replace(normalize(word), "")
    scored = []
    for product in products:
        name = normalize(product.name)
        code = normalize(product.product_code)
        category = normalize(product.category)
        score = SequenceMatcher(None, query_normal, name).ratio() if query_normal else 0
        if query_normal and (query_normal in name or name in query_normal):
            score += 0.8
        query_chunks = set(re.findall(r"[가-힣]{2,}|[a-z0-9]{2,}", query.lower()))
        matched = sum(1 for chunk in query_chunks if normalize(chunk) in name)
        score += matched * 0.22
        if code and code in normalize(query):
            score += 1.2
        if category and category in query_normal:
            score += 0.15
        if score > 0.18:
            scored.append((score, product))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [{
        "id": product.id,
        "product_code": product.product_code,
        "name": product.name,
        "category": product.category,
        "score": round(score, 3),
        "management_url": f"/commerce-catalog/product/{product.id}",
    } for score, product in scored[:limit]]


def _category_query(request_text: str) -> str:
    match = re.search(r"(?:카테고리(?:별)?\s*)?([가-힣A-Za-z0-9 _-]{2,30}?)(?:에\s*등록된|\s*카테고리|\s*상품)", request_text)
    return (match.group(1) if match else request_text).strip()


def parse_sku_args(request_text: str) -> dict[str, Any]:
    weight = re.search(r"(\d+(?:\.\d+)?)\s*(kg|g|m|cm|개)", request_text, re.I)
    price = re.search(r"(?:판매(?:금액|가)|가격)[^0-9]{0,15}([0-9][0-9,]*)\s*원?", request_text)
    shipping = re.search(r"배송비[^0-9]{0,15}([0-9][0-9,]*)\s*원?", request_text)
    stock = re.search(r"(?:초기\s*)?재고[^0-9]{0,15}([0-9]+)\s*개?", request_text)
    formulation = next((x for x in ("입제", "액상", "분말", "과립") if x in request_text), "")
    packaging = next((x for x in ("지퍼백", "봉투", "용기", "박스", "병") if x in request_text), "")
    option = f"{weight.group(1)}{weight.group(2)}" if weight else ""
    name = " ".join(x for x in (option, formulation, packaging) if x) or "새 SKU"
    return {
        "name": name,
        "option_value": " / ".join(x for x in (option, formulation, packaging) if x),
        "sale_price": int(price.group(1).replace(",", "")) if price else None,
        "shipping_fee": int(shipping.group(1).replace(",", "")) if shipping else None,
        "current_stock": int(stock.group(1)) if stock else 0,
        "available_stock": int(stock.group(1)) if stock else 0,
        "safety_stock": 0,
        "incoming_stock": 0,
        "sales_unit": "each",
        "status": "active",
    }


def stage_file(*, tenant_id: str, filename: str, content_type: str | None,
               content: bytes) -> dict[str, Any]:
    if not content or len(content) > MAX_STAGE_BYTES:
        raise ValueError("첨부 이미지는 파일당 50MB 이하여야 합니다.")
    if content_type and not content_type.startswith("image/"):
        raise ValueError("현재 실제 실행기는 이미지 첨부만 지원합니다.")
    stage_id = secrets.token_urlsafe(24)
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(filename).name)[:180] or "image"
    folder = media_root() / "agent_staging" / stage_id
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / safe_name
    path.write_bytes(content)
    meta = {
        "stage_id": stage_id, "tenant_id": tenant_id, "filename": filename,
        "content_type": content_type, "size": len(content), "path": str(path),
        "sha256": hashlib.sha256(content).hexdigest(),
    }
    _redis().setex(f"{STAGE_PREFIX}{stage_id}", STAGE_SECONDS, json.dumps(meta, ensure_ascii=False))
    return {key: meta[key] for key in ("stage_id", "filename", "content_type", "size", "sha256")}


def build_plan(db: Session, *, tenant_id: str, workflow: str,
               request_text: str, staged: list[dict[str, Any]],
               context_product_id: str | None = None) -> dict[str, Any]:
    action = infer_action(request_text, attachment_count=len(staged))
    if action is None:
        return {"supported": False, "message": "현재 등록된 공통 도구로 처리할 수 없는 요청입니다.",
                "available_tools": list(TOOL_REGISTRY)}
    tool = TOOL_REGISTRY[action]
    plan = {
        "supported": True, "protocol": TOOL_PROTOCOL, "action": action,
        "tool_label": tool["label"], "risk": tool["risk"],
        "approval_required": tool["approval"], "workflow": workflow,
        "request": request_text, "staged_attachments": staged,
    }
    if action == "category_products":
        plan["category_query"] = _category_query(request_text)
        plan["candidates"] = []
    else:
        plan["candidates"] = product_candidates(
            db, tenant_id=tenant_id, query=request_text, action=action,
        )
        if context_product_id:
            context_product = db.scalar(select(Product).where(
                Product.id == context_product_id,
                Product.tenant_id == tenant_id,
            ))
            if context_product is not None:
                exact = {
                    "id": context_product.id,
                    "product_code": context_product.product_code,
                    "name": context_product.name,
                    "category": context_product.category,
                    "score": 2.0,
                    "management_url": f"/commerce-catalog/product/{context_product.id}",
                    "context_selected": True,
                }
                plan["candidates"] = [exact] + [
                    row for row in plan["candidates"]
                    if row["id"] != context_product.id
                ]
    if action == "sku_add":
        plan["args"] = parse_sku_args(request_text)
    else:
        plan["args"] = {}
    return plan


def _product(db: Session, tenant_id: str, product_id: str) -> Product:
    product = db.scalar(select(Product).where(
        Product.id == product_id, Product.tenant_id == tenant_id,
    ))
    if product is None:
        raise ValueError("확정한 상품을 찾을 수 없습니다.")
    return product


def _skus(db: Session, tenant_id: str, product_id: str) -> list[ProductSKU]:
    return list(db.scalars(select(ProductSKU).where(
        ProductSKU.tenant_id == tenant_id,
        ProductSKU.product_id == product_id,
        ProductSKU.status != "inactive",
    ).order_by(ProductSKU.created_at)).all())


def _images(db: Session, tenant_id: str, product_id: str) -> tuple[ProductRegistrationProfile | None, list[ImageReferenceAsset]]:
    profile = db.scalar(select(ProductRegistrationProfile).where(
        ProductRegistrationProfile.tenant_id == tenant_id,
        ProductRegistrationProfile.product_id == product_id,
    ))
    ids = [] if profile is None else [
        value for value in [profile.primary_image_asset_id, *(profile.additional_image_asset_ids or [])] if value
    ]
    rows = list(db.scalars(select(ImageReferenceAsset).where(
        ImageReferenceAsset.tenant_id == tenant_id,
        ImageReferenceAsset.product_id == product_id,
        ImageReferenceAsset.id.in_(ids),
    )).all()) if ids else []
    by_id = {row.id: row for row in rows}
    return profile, [by_id[item] for item in ids if item in by_id]


def _query_result(db: Session, payload: dict[str, Any], product: Product | None) -> dict[str, Any]:
    action = payload["action"]
    tenant_id = payload["tenant_id"]
    if action == "category_products":
        query = normalize(payload.get("category_query"))
        rows = list(db.scalars(select(Product).where(Product.tenant_id == tenant_id)).all())
        matches = [row for row in rows if query and query in normalize(row.category)]
        return {"verified": True, "actual_change": False, "action": action, "category_query": payload.get("category_query"),
                "count": len(matches), "products": [{"id": row.id, "name": row.name,
                "product_code": row.product_code, "category": row.category,
                "management_url": f"/commerce-catalog/product/{row.id}"} for row in matches]}
    assert product is not None
    skus = _skus(db, tenant_id, product.id)
    base = {"verified": True, "actual_change": False, "action": action,
            "product": {"id": product.id, "name": product.name, "product_code": product.product_code}}
    if action == "product_price":
        base["skus"] = [{"sku_code": s.sku_code, "name": s.name, "sale_price": s.sale_price} for s in skus]
    elif action == "shipping_fee":
        base["skus"] = [{"sku_code": s.sku_code, "name": s.name, "shipping_fee": s.shipping_fee} for s in skus]
    elif action == "sku_list":
        base["skus"] = [{"sku_code": s.sku_code, "name": s.name, "option_value": s.option_value,
                         "sale_price": s.sale_price, "shipping_fee": s.shipping_fee,
                         "available_stock": s.available_stock, "status": s.status} for s in skus]
    elif action in {"primary_image", "image_list"}:
        profile, images = _images(db, tenant_id, product.id)
        if action == "primary_image" and profile:
            images = [row for row in images if row.id == profile.primary_image_asset_id]
        base["images"] = [{"id": row.id, "filename": row.original_filename,
                           "role": row.asset_role,
                           "content_url": f"/api/v1/product-registration-assets/references/{row.id}/content?tenant_id={tenant_id}"}
                          for row in images]
        base["count"] = len(images)
    elif action == "detail_page":
        job = db.scalar(select(DetailPageJob).where(
            DetailPageJob.tenant_id == tenant_id, DetailPageJob.product_id == product.id,
        ).order_by(DetailPageJob.updated_at.desc()))
        base["detail_page"] = None if job is None else {
            "job_id": job.id, "status": job.status, "approved_version_no": job.approved_version_no,
            "url": f"/detail-pages?product_id={product.id}",
        }
    elif action == "channel_status":
        listings = list(db.scalars(select(SalesChannelListing).where(
            SalesChannelListing.tenant_id == tenant_id,
            SalesChannelListing.product_id == product.id,
            SalesChannelListing.channel == "naver",
        )).all())
        base["channel"] = "naver"
        base["internal_records"] = [{"sku_id": row.sku_id, "status": row.status,
                                     "external_product_id": row.external_product_id,
                                     "last_synced_at": row.last_synced_at.isoformat() if row.last_synced_at else None}
                                    for row in listings]
        base["live_marketplace_verified"] = False
        base["notice"] = "내부 연결 기록입니다. 네이버의 현재 전시 상태는 API 연결 후 별도 확인해야 합니다."
    return base


def execute_tool(db: Session, payload: dict[str, Any]) -> str:
    if payload.get("protocol") != TOOL_PROTOCOL or payload.get("action") not in TOOL_REGISTRY:
        return json.dumps({"verified": False, "actual_change": False,
                           "message": "요청 기록 완료 · 실제 상품 변경 없음"}, ensure_ascii=False)
    action = payload["action"]
    tenant_id = payload["tenant_id"]
    product = None if action == "category_products" else _product(db, tenant_id, payload.get("product_id") or "")
    if TOOL_REGISTRY[action]["risk"] == "read":
        return json.dumps(_query_result(db, payload, product), ensure_ascii=False)
    if not payload.get("approval_confirmed"):
        raise ValueError("내부 변경 실행에는 사용자 최종 승인이 필요합니다.")
    assert product is not None
    if action == "sku_add":
        args = payload.get("args") or {}
        if not args.get("name") or args.get("sale_price") is None:
            raise ValueError("SKU명과 판매가는 필수입니다.")
        sku = create_sku(db, product=product, name=str(args["name"]).strip(),
                         option_value=(str(args.get("option_value") or "").strip() or None),
                         sales_unit=args.get("sales_unit") or "each")
        for field in ("sale_price", "shipping_fee", "current_stock", "available_stock",
                      "safety_stock", "incoming_stock", "status"):
            if field in args:
                setattr(sku, field, args[field])
        db.commit()
        verified = db.scalar(select(ProductSKU).where(
            ProductSKU.id == sku.id, ProductSKU.product_id == product.id,
        ))
        if verified is None:
            raise RuntimeError("SKU 저장 후 검증에 실패했습니다.")
        return json.dumps({"verified": True, "actual_change": True, "action": action,
                           "product": {"id": product.id, "name": product.name},
                           "sku": {"id": verified.id, "sku_code": verified.sku_code,
                                   "name": verified.name, "option_value": verified.option_value,
                                   "sale_price": verified.sale_price,
                                   "shipping_fee": verified.shipping_fee}}, ensure_ascii=False)
    if action == "product_image_add":
        stage_ids = payload.get("staged_attachment_ids") or []
        if not stage_ids:
            raise ValueError("추가할 이미지가 없습니다.")
        profile = db.scalar(select(ProductRegistrationProfile).where(
            ProductRegistrationProfile.tenant_id == tenant_id,
            ProductRegistrationProfile.product_id == product.id,
        ))
        if profile is None:
            profile = ProductRegistrationProfile(tenant_id=tenant_id, product_id=product.id)
            db.add(profile)
            db.flush()
        additional = list(profile.additional_image_asset_ids or [])
        created = []
        staged_meta = []
        for stage_id in stage_ids:
            raw = _redis().get(f"{STAGE_PREFIX}{stage_id}")
            if not raw:
                raise ValueError("첨부 이미지가 만료되었거나 존재하지 않습니다.")
            meta = json.loads(raw)
            if meta.get("tenant_id") != tenant_id:
                raise ValueError("다른 작업공간의 첨부 이미지는 사용할 수 없습니다.")
            staged_meta.append(meta)
            content = Path(meta["path"]).read_bytes()
            uri = save_reference_upload(product_id=product.id, job_id=None,
                                        filename=meta["filename"], content=content)
            asset = ImageReferenceAsset(
                tenant_id=tenant_id, product_id=product.id, job_id=None,
                asset_role="SOURCE_UNKNOWN", asset_uri=uri,
                original_filename=meta["filename"], mime_type=meta.get("content_type"),
                internal_reference_only=False, lock_level="hard_lock",
                sort_order=len(additional) + 1,
            )
            db.add(asset)
            db.flush()
            additional.append(asset.id)
            created.append(asset)
        profile.additional_image_asset_ids = additional
        db.commit()
        verified_ids = set(db.scalars(select(ImageReferenceAsset.id).where(
            ImageReferenceAsset.id.in_([row.id for row in created]),
            ImageReferenceAsset.product_id == product.id,
        )).all())
        if len(verified_ids) != len(created):
            raise RuntimeError("이미지 저장 후 검증에 실패했습니다.")
        for stage_id, meta in zip(stage_ids, staged_meta):
            _redis().delete(f"{STAGE_PREFIX}{stage_id}")
            shutil.rmtree(Path(meta["path"]).parent, ignore_errors=True)
        return json.dumps({"verified": True, "actual_change": True, "action": action,
                           "product": {"id": product.id, "name": product.name},
                           "images": [{"id": row.id, "filename": row.original_filename,
                                       "content_url": f"/api/v1/product-registration-assets/references/{row.id}/content?tenant_id={tenant_id}"}
                                      for row in created], "count": len(created)}, ensure_ascii=False)
    raise ValueError("지원하지 않는 Agent 도구입니다.")
