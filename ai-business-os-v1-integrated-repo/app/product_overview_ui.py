from fastapi import APIRouter
from fastapi.responses import HTMLResponse


router = APIRouter()


HTML = r'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>전체 상품 · AI Business OS</title>
<style>
*{box-sizing:border-box}body{margin:0;font-family:Inter,Pretendard,system-ui,sans-serif;background:#0b0f17;color:#e5e7eb}.wrap{max-width:1260px;margin:0 auto;padding:28px}.top{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:20px}.top h1{margin:0}.muted{color:#8ea0b7;font-size:13px}.btn,a.btn{display:inline-block;padding:10px 14px;border-radius:10px;border:1px solid #35445a;text-decoration:none;font-weight:800}.primary{background:#e5e7eb;color:#111827}.secondary{background:#182337;color:#fff}.card{background:#111827;border:1px solid #263247;border-radius:16px;overflow:hidden}.toolbar{display:flex;gap:10px;align-items:center;padding:16px;border-bottom:1px solid #263247}.toolbar input{flex:1;min-width:220px;padding:10px 12px;border-radius:10px;border:1px solid #35445a;background:#0b1220;color:#fff}.toolbar select{padding:10px 12px;border-radius:10px;border:1px solid #35445a;background:#0b1220;color:#fff}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;min-width:1080px}th,td{padding:14px 12px;border-bottom:1px solid #253044;text-align:left;font-size:13px}th{color:#8ea0b7;font-size:12px;background:#0d1421;position:sticky;top:0}.product a{color:#fff;font-weight:800;text-decoration:none}.code{color:#8ea0b7;font-size:12px;margin-top:3px}.pill{display:inline-block;border-radius:999px;padding:4px 8px;font-size:11px;font-weight:800;border:1px solid #35445a}.ok{color:#a7f3d0}.warn{color:#fde68a}.empty{color:#94a3b8}.missing{color:#fde68a;font-size:11px;margin-top:4px;max-width:190px}.actions{display:flex;gap:6px;flex-wrap:wrap}.actions a{font-size:12px;color:#bfdbfe;text-decoration:none}.summary{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px}.stat{background:#111827;border:1px solid #263247;border-radius:12px;padding:12px 14px;min-width:130px}.stat strong{font-size:20px;display:block}.empty-state{padding:40px;text-align:center;color:#8ea0b7}@media(max-width:700px){.wrap{padding:18px}.top{align-items:flex-start;flex-direction:column}.toolbar{align-items:stretch;flex-direction:column}}
</style></head><body><div class="wrap">
<div class="top"><div><h1>전체 상품</h1><div class="muted">등록된 Product Master를 한 곳에서 보고 관리합니다.</div></div><div><a class="btn secondary" href="/dashboard">← 대시보드</a> <a class="btn secondary" href="/commerce-catalog">통합 상품관리</a> <a class="btn primary" href="/product-registration">＋ 새 상품 등록</a></div></div>
<div class="summary"><div class="stat"><strong id="totalCount">-</strong><span class="muted">전체 상품</span></div><div class="stat"><strong id="masterCount">-</strong><span class="muted">등록 완료</span></div><div class="stat"><strong id="needsCount">-</strong><span class="muted">보완 필요</span></div><div class="stat"><strong id="contentCount">-</strong><span class="muted">콘텐츠정보 있음</span></div><div class="stat"><strong id="detailCount">-</strong><span class="muted">상세페이지 작업</span></div></div>
<div class="card"><div class="toolbar"><input id="search" placeholder="상품명 또는 상품코드 검색" oninput="render()"><select id="masterFilter" onchange="render()"><option value="">전체 등록상태</option><option value="ready">등록 완료</option><option value="needs">보완 필요</option></select><select id="statusFilter" onchange="render()"><option value="">전체 운영상태</option><option value="draft">초안</option><option value="active">활성</option><option value="inactive">비활성</option></select></div><div class="table-wrap"><table><thead><tr><th>상품</th><th>Product Master</th><th>운영상태</th><th>FACT</th><th>이미지</th><th>콘텐츠 기준정보</th><th>SKU</th><th>상세페이지</th><th>작업</th></tr></thead><tbody id="rows"></tbody></table></div><div id="empty" class="empty-state" style="display:none">등록된 상품이 없습니다.</div></div>
</div><script>
const tenant='__legacy__';let workspace=null,items=[];
async function api(path){const r=await fetch(path,{credentials:'same-origin'});let d={};try{d=await r.json()}catch{}if(!r.ok)throw new Error(d.detail||`HTTP ${r.status}`);return d}
function esc(v){return String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
function statusText(v){return ({draft:'초안',active:'활성',inactive:'비활성'})[v]||v||'-'}
function masterCell(x){if(x.master_ready)return '<span class="ok">✓ 등록 완료</span>';const missing=(x.master_missing_labels||[]).map(esc).join(', ');return `<span class="warn">보완 필요</span>${missing?`<div class="missing">${missing}</div>`:''}`}
function render(){const q=search.value.trim().toLowerCase(),sf=statusFilter.value,mf=masterFilter.value;const filtered=items.filter(x=>(!sf||x.status===sf)&&(!mf||(mf==='ready'?x.master_ready:!x.master_ready))&&(!q||`${x.name} ${x.product_code}`.toLowerCase().includes(q)));rows.innerHTML=filtered.map(x=>`<tr><td class="product"><a href="/product-registration?product_id=${encodeURIComponent(x.id)}">${esc(x.name)}</a><div class="code">${esc(x.product_code)}</div></td><td>${masterCell(x)}</td><td><span class="pill">${esc(statusText(x.status))}</span></td><td>${x.facts_confirmed?'<span class="ok">✓ 확정</span>':'<span class="warn">확인 필요</span>'}</td><td>${x.images_ready?'<span class="ok">✓ 필수 완료</span>':(x.image_count?`대표 ${x.has_primary_image?'1':'0'} · 추가 ${x.additional_image_count}`:'<span class="empty">없음</span>')}</td><td>${x.content_basis_status==='complete'?'<span class="ok">✓ 있음</span>':'<span class="empty">선택 · 미작성</span>'}</td><td>${x.sku_count}</td><td>${x.detail_page_count}${x.page_override_count?` <span class="muted">(편집 ${x.page_override_count})</span>`:''}</td><td><div class="actions"><a href="/product-registration?product_id=${encodeURIComponent(x.id)}">정보 관리</a><a href="/detail-pages?product_id=${encodeURIComponent(x.id)}">상세페이지</a><a href="/image-studio?product_id=${encodeURIComponent(x.id)}">이미지</a></div></td></tr>`).join('');empty.style.display=filtered.length?'none':'block'}
async function init(){try{const ws=await api(`/api/v1/business/workspaces?tenant_id=${tenant}`);workspace=ws.find(x=>x.slug==='commerce-ai')||ws[0];if(!workspace){empty.textContent='Workspace가 없습니다.';empty.style.display='block';return}items=await api(`/api/v1/product-overview/products?tenant_id=${tenant}&workspace_id=${encodeURIComponent(workspace.id)}`);totalCount.textContent=items.length;masterCount.textContent=items.filter(x=>x.master_ready).length;needsCount.textContent=items.filter(x=>!x.master_ready).length;contentCount.textContent=items.filter(x=>x.content_basis_status==='complete').length;detailCount.textContent=items.reduce((n,x)=>n+x.detail_page_count,0);render()}catch(e){empty.textContent='대시보드 로그인 후 다시 열어주세요. '+e;empty.style.display='block'}}
init();
</script></body></html>'''


def inject_product_overview_link(html: str) -> str:
    if 'href="/products"' in html:
        return html
    marker = '<button data-panel="products">상품 업무</button>'
    addition = marker + '\n      <a href="/products">전체 상품</a>'
    if marker in html:
        return html.replace(marker, addition, 1)
    return html


@router.get('/products', response_class=HTMLResponse, include_in_schema=False)
def products_page():
    return HTMLResponse(HTML, headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})
