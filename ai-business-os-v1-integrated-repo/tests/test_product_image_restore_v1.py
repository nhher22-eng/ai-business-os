from app.product_registration_image_restore_ui_patch import inject_product_image_restore
from app.product_registration_resume_ui_patch import inject_product_registration_resume
from app.product_registration_ui import HTML


def test_image_restore_ui_is_injected_after_resume_patch():
    html = inject_product_registration_resume(HTML)
    html = inject_product_image_restore(html)

    assert 'id="currentImages"' in html
    assert "loadExistingImages" in html
    assert "product-registration-assets/references" in html
    assert "await loadExistingImages();" in html


def test_image_restore_patch_is_idempotent():
    html = inject_product_registration_resume(HTML)
    once = inject_product_image_restore(html)
    twice = inject_product_image_restore(once)
    assert once == twice


def test_open_next_steps_restores_images():
    html = inject_product_registration_resume(HTML)
    html = inject_product_image_restore(html)
    assert "if(productId)loadExistingImages()" in html
