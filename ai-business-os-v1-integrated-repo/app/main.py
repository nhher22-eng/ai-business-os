from fastapi import FastAPI
from sqlalchemy import text
import redis

from app.core.config import settings
from app.db.session import engine
from app.api.runs import router as runs_router
from app.api.operations import router as operations_router
from app.api.business import router as business_router
from app.api.dashboard_session import router as dashboard_session_router
from app.api.images import router as images_router
from app.api.detail_pages import router as detail_pages_router
from app.api.detail_page_autogen import router as detail_page_autogen_router
from app.api.detail_page_content_basis import router as detail_page_content_basis_router
from app.api.canva_controlled_export import router as canva_controlled_export_router
from app.api.product_registration import router as product_registration_router
from app.api.product_registration_assets import router as product_registration_assets_router
from app.api.product_image_facts import router as product_image_facts_router
from app.api.product_overview import router as product_overview_router
from app.api.product_operations import router as product_operations_router
from app.dashboard_ui import router as dashboard_ui_router
from app.operations_ui import router as operations_ui_router
from app.image_studio_ui import router as image_studio_ui_router
from app.product_overview_ui import router as product_overview_ui_router, inject_product_overview_link
from app import dashboard_ui, detail_page_ui, product_registration_ui
from app.detail_page_autogen_ui_patch import inject_autogen_ui
from app.detail_page_content_basis_ui_patch import inject_detail_page_content_basis_editor
from app.detail_page_product_selection_ui_patch import inject_detail_page_product_selection
from app.product_registration_ui import (
    inject_product_registration_link,
    router as product_registration_ui_router,
)
from app.product_registration_resume_ui_patch import inject_product_registration_resume
from app.product_registration_image_restore_ui_patch import inject_product_image_restore
from app.product_content_basis_ui_patch import inject_product_content_basis_editor
from app.product_management_ui_patch import inject_product_management_mode
from app.product_operations_ui_patch import inject_product_operations_ui
from app.product_image_fact_ui_patch import inject_product_image_fact_ui
from app.services.fact_grounded_copy_patch import install_fact_grounded_copy_patch
from app.services.product_master_integration_patch import install_product_master_integration_patch
from app.services.product_registration_safety_patch import install_product_registration_safety_patch
from app.services.product_image_fact_oom_patch import install_product_image_fact_oom_patch
from app.services.queue import queue_depth


install_fact_grounded_copy_patch()
install_product_master_integration_patch()
install_product_registration_safety_patch()
install_product_image_fact_oom_patch()
detail_page_ui.HTML = inject_autogen_ui(detail_page_ui.HTML)
detail_page_ui.HTML = inject_detail_page_content_basis_editor(detail_page_ui.HTML)
detail_page_ui.HTML = inject_detail_page_product_selection(detail_page_ui.HTML)
dashboard_ui.HTML = inject_product_registration_link(dashboard_ui.HTML)
dashboard_ui.HTML = inject_product_overview_link(dashboard_ui.HTML)
product_registration_ui.HTML = inject_product_registration_resume(product_registration_ui.HTML)
product_registration_ui.HTML = inject_product_image_restore(product_registration_ui.HTML)
product_registration_ui.HTML = inject_product_content_basis_editor(product_registration_ui.HTML)
product_registration_ui.HTML = inject_product_management_mode(product_registration_ui.HTML)
product_registration_ui.HTML = inject_product_operations_ui(product_registration_ui.HTML)
product_registration_ui.HTML = inject_product_image_fact_ui(product_registration_ui.HTML)

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
)

app.include_router(runs_router)
app.include_router(operations_router)
app.include_router(dashboard_ui_router)
app.include_router(business_router)
app.include_router(product_registration_router)
app.include_router(product_registration_assets_router)
app.include_router(product_image_facts_router)
app.include_router(product_overview_router)
app.include_router(product_operations_router)
app.include_router(dashboard_session_router)
app.include_router(operations_ui_router)
app.include_router(images_router)
app.include_router(detail_pages_router)
app.include_router(detail_page_autogen_router)
app.include_router(detail_page_content_basis_router)
app.include_router(canva_controlled_export_router)
app.include_router(image_studio_ui_router)
app.include_router(product_overview_ui_router)
app.include_router(product_registration_ui_router)
app.include_router(detail_page_ui.router)


@app.get("/")
def root():
    return {
        "service": settings.app_name,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "operations": "/operations",
    }


@app.get("/health/live")
def live():
    return {"status": "ok"}


@app.get("/health/ready")
def ready():
    checks = {}

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as exc:
        checks["postgres"] = f"error: {type(exc).__name__}"

    try:
        r = redis.Redis.from_url(settings.redis_url)
        checks["redis"] = "ok" if r.ping() else "error"
    except Exception as exc:
        checks["redis"] = f"error: {type(exc).__name__}"

    status = "ok" if all(v == "ok" for v in checks.values()) else "degraded"

    return {
        "status": status,
        "checks": checks,
        "queue_depth": queue_depth() if checks.get("redis") == "ok" else None,
    }
