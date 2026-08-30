from pathlib import Path


def test_oom_patch_is_installed_and_isolated():
    main = Path("app/main.py").read_text()
    patch = Path("app/services/product_image_fact_oom_patch.py").read_text()

    assert "install_product_image_fact_oom_patch" in main
    assert "subprocess.run" in patch
    assert '"u2netp"' in patch
    assert "new_session(model)" in patch
    assert "remove(content, session=session)" in patch
    assert "PRODUCT_IMAGE_FACT_REMBG_TIMEOUT_SECONDS" in patch
    assert "U2NET_HOME" in patch
