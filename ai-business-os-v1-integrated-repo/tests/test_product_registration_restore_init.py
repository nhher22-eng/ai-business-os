from app.product_registration_async_restore_ui_patch import inject_async_restore_ui


def test_restore_boot_replaces_original_init_before_script_injection():
    html = "<html><script>\ninit();\n</script></html>"

    patched = inject_async_restore_ui(html)

    assert "function restoreRecentRegistration()" in patched
    assert "async function initWithRegistrationRestore()" in patched
    assert "initWithRegistrationRestore();\n</script>" in patched
    assert "\ninit();\n</script>" not in patched
