from pathlib import Path


def test_async_image_fact_upload_and_restore_are_wired():
    main = Path("app/main.py").read_text()
    async_api = Path("app/api/product_image_fact_async.py").read_text()
    recent_api = Path("app/api/product_registration_recent.py").read_text()
    worker = Path("app/image_worker.py").read_text()
    ui = Path("app/product_registration_async_restore_ui_patch.py").read_text()

    assert "product_image_fact_async_router" in main
    assert "product_registration_recent_router" in main
    assert "inject_async_restore_ui" in main
    assert 'batch-async' in async_api
    assert 'status="processing_queued"' in async_api
    assert 'status == "processing_queued"' in worker
    assert "process_product_fact" in worker
    assert '@router.get("/recent")' in recent_api
    assert "restoreRecentRegistration" in ui
    assert "setTimeout(loadImageFacts,2000)" in ui
    assert "batch-async" in ui
