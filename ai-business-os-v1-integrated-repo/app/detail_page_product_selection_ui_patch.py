from __future__ import annotations


INIT_OLD = "async function init(){if(!(await sessionOK())){sessionStatus.textContent='로그인 필요';return}loginBox.style.display='none';sessionStatus.textContent='Connected';const ws=await jf(`/api/v1/business/workspaces?tenant_id=${tenant}`);workspace=ws.find(x=>x.slug==='commerce-ai')||ws[0];if(!workspace)return;products=await jf(`/api/v1/business/products?tenant_id=${tenant}&workspace_id=${workspace.id}`);product.innerHTML=products.map(p=>`<option value=\"${p.id}\">${p.name}</option>`).join('');await loadJobs();await loadStyles()}"

INIT_NEW = "async function init(){if(!(await sessionOK())){sessionStatus.textContent='로그인 필요';return}loginBox.style.display='none';sessionStatus.textContent='Connected';const ws=await jf(`/api/v1/business/workspaces?tenant_id=${tenant}`);workspace=ws.find(x=>x.slug==='commerce-ai')||ws[0];if(!workspace)return;products=await jf(`/api/v1/business/products?tenant_id=${tenant}&workspace_id=${workspace.id}`);product.innerHTML=products.map(p=>`<option value=\"${p.id}\">${p.name}</option>`).join('');const requestedProduct=new URLSearchParams(location.search).get('product_id');if(requestedProduct&&products.some(p=>p.id===requestedProduct))product.value=requestedProduct;await loadJobs();await loadStyles()}"


def inject_detail_page_product_selection(html: str) -> str:
    if "requestedProduct" in html:
        return html
    if INIT_OLD not in html:
        raise RuntimeError("detail page init marker not found")
    return html.replace(INIT_OLD, INIT_NEW, 1)
