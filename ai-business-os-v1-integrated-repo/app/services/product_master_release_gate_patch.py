from __future__ import annotations

from app.services import detail_page_autogen as detail_autogen
from app.services import detail_page_studio as detail_studio
from app.services.product_image_fact import readiness as image_readiness


_INSTALLED = False


def apply_product_master_release_gate(base_readiness: dict, registration: dict) -> dict:
    """Combine existing content readiness with Product Master core readiness."""
    result = dict(base_readiness)
    images = registration.get("image_readiness") or {}
    facts_confirmed = bool(registration.get("facts_confirmed"))
    primary_linked = bool(registration.get("primary_asset_linked"))
    images_ready = bool(images.get("ready"))
    master_ready = facts_confirmed and images_ready and primary_linked

    master_missing: list[str] = []
    if not facts_confirmed:
        master_missing.append("Product Master FACT 사용자 확정")
    master_missing.extend(images.get("missing_labels") or [])
    if images_ready and not primary_linked:
        master_missing.append("대표 이미지 Product Master 연결")

    existing_missing = list(result.get("missing") or [])
    existing_labels = list(result.get("missing_labels") or [])
    if not master_ready and "product_master_core" not in existing_missing:
        existing_missing.append("product_master_core")
    for label in master_missing:
        if label not in existing_labels:
            existing_labels.append(label)

    result["missing"] = existing_missing
    result["missing_labels"] = existing_labels
    result["product_master_ready"] = master_ready
    result["product_master_missing_labels"] = master_missing
    result["images_ready"] = images_ready
    result["primary_asset_linked"] = primary_linked
    result["ready"] = bool(result.get("ready")) and master_ready
    return result


def install_product_master_release_gate() -> None:
    """Allow drafting, but block selling-page release until Product Master is complete.

    This installer intentionally runs after product_master_integration_patch so it
    wraps the already-enriched snapshot/readiness functions rather than replacing
    their FACT grounding behavior.
    """
    global _INSTALLED
    if _INSTALLED:
        return

    current_snapshot = detail_studio.product_snapshot
    current_readiness = detail_autogen.fact_readiness

    def release_aware_snapshot(db, *, tenant_id: str, product_id: str) -> dict:
        snapshot = current_snapshot(db, tenant_id=tenant_id, product_id=product_id)
        registration = snapshot.setdefault("registration", {})
        images = image_readiness(db, tenant_id=tenant_id, product_id=product_id)
        primary_linked = bool(registration.get("primary_image_asset_id"))
        facts_confirmed = bool(registration.get("facts_confirmed"))
        registration["image_readiness"] = images
        registration["primary_asset_linked"] = primary_linked
        registration["core_ready"] = (
            facts_confirmed and bool(images.get("ready")) and primary_linked
        )
        return snapshot

    def release_aware_fact_readiness(snapshot: dict) -> dict:
        base = current_readiness(snapshot)
        return apply_product_master_release_gate(
            base,
            snapshot.get("registration") or {},
        )

    detail_studio.product_snapshot = release_aware_snapshot
    detail_autogen.product_snapshot = release_aware_snapshot
    detail_autogen.fact_readiness = release_aware_fact_readiness
    _INSTALLED = True
