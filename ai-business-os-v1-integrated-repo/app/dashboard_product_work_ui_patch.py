from __future__ import annotations


def inject_dashboard_product_work(html: str) -> str:
    """Turn the dashboard's single demo-product view into a readiness-first work view."""
    html = html.replace(
        '<div class="muted">승인 대기</div>\n          <div class="metric">0</div>',
        '<div class="muted">상품 보완 필요</div>\n          <div class="metric" id="needsAttentionCount">-</div>',
        1,
    )

    old_fetch = '''    const products = await api(
      `/api/v1/business/products?tenant_id=${tenant}` +
      `&workspace_id=${encodeURIComponent(workspace.id)}`
    );'''
    new_fetch = '''    const products = await api(
      `/api/v1/product-overview/products?tenant_id=${tenant}` +
      `&workspace_id=${encodeURIComponent(workspace.id)}`
    );'''
    if old_fetch not in html:
        raise RuntimeError("dashboard product fetch marker not found")
    html = html.replace(old_fetch, new_fetch, 1)

    old_select = '''    const product =
      products.find(
        (x) => x.product_code === "IRRIGATION-8MM-KIT"
      )
      || products[0];'''
    new_select = '''    const product =
      products.find((x) => !x.master_ready)
      || products[0];'''
    if old_select not in html:
        raise RuntimeError("dashboard demo product selection marker not found")
    html = html.replace(old_select, new_select, 1)

    old_counts = '''    document.getElementById("productCount").textContent =
      products.length;
    document.getElementById("skuCount").textContent =
      skus.length;'''
    new_counts = '''    document.getElementById("productCount").textContent =
      products.length;
    document.getElementById("needsAttentionCount").textContent =
      products.filter((x) => !x.master_ready).length;
    document.getElementById("skuCount").textContent =
      skus.length;'''
    if old_counts not in html:
        raise RuntimeError("dashboard metric marker not found")
    html = html.replace(old_counts, new_counts, 1)

    old_meta = '''          · ${product.status}
          · ${product.sales_channel || "-"}'''
    new_meta = '''          · ${product.status}
          · ${product.sales_channel || "-"}
          · ${product.master_ready ? "Master 완료" : "보완 필요"}'''
    html = html.replace(old_meta, new_meta, 1)

    old_sku_block = '''        <div class="muted" style="margin-top:7px">
          SKU ${skus.length}개
          · ${skus.map(
            (x) => x.option_value || x.name
          ).join(" / ")}
        </div>'''
    new_sku_block = '''        <div class="muted" style="margin-top:7px">
          SKU ${skus.length}개
          · ${skus.map(
            (x) => x.option_value || x.name
          ).join(" / ") || "-"}
        </div>
        ${product.master_ready ? "" : `
          <div style="margin-top:9px;color:#fde68a;font-size:13px">
            보완: ${(product.master_missing_labels || []).join(" · ") || "필수 상품정보"}
          </div>
        `}'''
    if old_sku_block not in html:
        raise RuntimeError("dashboard SKU display marker not found")
    html = html.replace(old_sku_block, new_sku_block, 1)

    old_action = '''        <div style="margin-top:10px">
          상품 상세 열기 →
        </div>'''
    new_action = '''        <div style="margin-top:10px">
          ${product.master_ready ? "상품 상세 열기 →" : "등록 보완 계속하기 →"}
        </div>'''
    html = html.replace(old_action, new_action, 1)

    old_click = '''      .addEventListener("click", () => {
        const detail ='''
    new_click = '''      .addEventListener("click", () => {
        if (!product.master_ready) {
          window.location.href = `/product-registration?product_id=${encodeURIComponent(product.id)}`;
          return;
        }
        const detail ='''
    if old_click not in html:
        raise RuntimeError("dashboard product click marker not found")
    html = html.replace(old_click, new_click, 1)

    # The second listener enriches the expanded detail. Do not run it for an
    # incomplete product because the first listener navigates to registration.
    second_listener = '''      .addEventListener("click", async () => {
        const detailPanel ='''
    second_replacement = '''      .addEventListener("click", async () => {
        if (!product.master_ready) return;
        const detailPanel ='''
    if second_listener in html:
        html = html.replace(second_listener, second_replacement, 1)

    # Product Overview already provides description so the existing detail UI
    # continues to work without a second product fetch.
    return html
