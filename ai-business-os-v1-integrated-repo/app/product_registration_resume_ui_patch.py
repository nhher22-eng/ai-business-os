from __future__ import annotations


OLD_SAVE = """async function saveFacts(){const s=document.getElementById('factStatus');try{if(!v('name')||!v('productCode'))throw new Error('품명과 상품코드는 필수입니다.');s.textContent='저장 중...';const d=await api(`/api/v1/product-registration/products?tenant_id=${tenant}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(factsPayload())});productId=d.product.id;s.innerHTML='<span class=\"ok\">FACT 저장 완료 · AI 임의 수정 금지</span>';document.getElementById('imageCard').classList.remove('hidden');document.getElementById('aiCard').classList.remove('hidden');}catch(e){s.textContent=String(e)}}"""

CATALOG_SAVE = """async function saveFacts(){const s=document.getElementById('factStatus');try{if(!v('name'))throw new Error('품명은 필수입니다.');s.textContent='저장 중...';const d=await api(`/api/v1/product-registration/products?tenant_id=${tenant}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(factsPayload())});productId=d.product.id;document.getElementById('productCode').value=d.product.product_code;s.innerHTML=`<span class=\"ok\">${d.product.product_code} · SKU ${d.skus.length}개 자동 생성 완료</span>`;document.getElementById('imageCard').classList.remove('hidden');document.getElementById('aiCard').classList.remove('hidden');}catch(e){s.textContent=String(e)}}"""

NEW_SAVE = """function factsUpdatePayload(){const p=factsPayload();delete p.workspace_id;delete p.product_code;delete p.name;return p}
function openNextSteps(){document.getElementById('imageCard').classList.remove('hidden');document.getElementById('aiCard').classList.remove('hidden')}
async function resumeExistingProduct(){const workspaceId=document.getElementById('workspace').value;const code=v('productCode');const products=await api(`/api/v1/business/products?tenant_id=${tenant}&workspace_id=${encodeURIComponent(workspaceId)}`);const existing=products.find(x=>x.product_code===code);if(!existing)throw new Error('같은 상품코드가 존재하지만 현재 Workspace에서 찾지 못했습니다.');productId=existing.id;await api(`/api/v1/product-registration/products/${productId}/facts?tenant_id=${tenant}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(factsUpdatePayload())});return api(`/api/v1/product-registration/products/${productId}?tenant_id=${tenant}`)}
async function saveFacts(){const s=document.getElementById('factStatus');try{if(!v('name')||!v('productCode'))throw new Error('품명과 상품코드는 필수입니다.');s.textContent='저장 중...';try{const d=await api(`/api/v1/product-registration/products?tenant_id=${tenant}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(factsPayload())});productId=d.product.id;s.innerHTML='<span class=\"ok\">FACT 저장 완료 · AI 임의 수정 금지</span>';}catch(e){if(!String(e).includes('HTTP 409')||!String(e).includes('product already exists'))throw e;await resumeExistingProduct();s.innerHTML='<span class=\"ok\">기존 상품을 불러와 FACT를 이어서 저장했습니다.</span>';}openNextSteps();}catch(e){s.textContent=String(e)}}"""

CATALOG_NEW_SAVE = """function factsUpdatePayload(){const p=factsPayload();delete p.workspace_id;delete p.product_code;delete p.name;delete p.options;return p}
function openNextSteps(){document.getElementById('imageCard').classList.remove('hidden');document.getElementById('aiCard').classList.remove('hidden')}
async function resumeExistingProduct(){const workspaceId=document.getElementById('workspace').value;const code=v('productCode');const products=await api(`/api/v1/business/products?tenant_id=${tenant}&workspace_id=${encodeURIComponent(workspaceId)}`);const existing=products.find(x=>x.product_code===code);if(!existing)throw new Error('같은 상품코드가 존재하지만 현재 Workspace에서 찾지 못했습니다.');productId=existing.id;await api(`/api/v1/product-registration/products/${productId}/facts?tenant_id=${tenant}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(factsUpdatePayload())});return api(`/api/v1/product-registration/products/${productId}?tenant_id=${tenant}`)}
async function saveFacts(){const s=document.getElementById('factStatus');try{if(!v('name'))throw new Error('품명은 필수입니다.');s.textContent='저장 중...';try{const d=await api(`/api/v1/product-registration/products?tenant_id=${tenant}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(factsPayload())});productId=d.product.id;document.getElementById('productCode').value=d.product.product_code;s.innerHTML=`<span class=\"ok\">${d.product.product_code} · SKU ${d.skus.length}개 자동 생성 완료</span>`;}catch(e){if(!v('productCode')||!String(e).includes('HTTP 409')||!String(e).includes('product already exists'))throw e;await resumeExistingProduct();s.innerHTML='<span class=\"ok\">기존 상품을 불러와 FACT를 이어서 저장했습니다.</span>';}openNextSteps();}catch(e){s.textContent=String(e)}}"""


def inject_product_registration_resume(html: str) -> str:
    """Turn duplicate-create after refresh into an edit/resume flow."""
    if "resumeExistingProduct" in html:
        return html
    if CATALOG_SAVE in html:
        return html.replace(CATALOG_SAVE, CATALOG_NEW_SAVE, 1)
    if OLD_SAVE in html:
        return html.replace(OLD_SAVE, NEW_SAVE, 1)
    raise RuntimeError("product registration saveFacts marker not found")
