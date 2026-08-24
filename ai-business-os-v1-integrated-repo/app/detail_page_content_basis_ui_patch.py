from __future__ import annotations


PANEL_MARKER = '<div class="label">자연어 수정 요청</div>'
PANEL = r'''
<div style="margin-top:16px;padding-top:14px;border-top:1px solid #e1e6ee">
  <h3 style="margin-bottom:4px">페이지 콘텐츠 기준정보</h3>
  <div class="muted">상품 Master 값을 기본으로 불러옵니다. 여기서 수정하면 기본적으로 이 상세페이지 버전에만 적용됩니다.</div>
  <div class="label">카테고리 <span class="muted">· 선택사항</span></div>
  <input id="basisCategory" placeholder="비워둘 수 있습니다">
  <div class="label">용도 <span class="muted">· 한 줄에 하나</span></div>
  <textarea id="basisUsage" placeholder="필요 없으면 비워두세요"></textarea>
  <div class="label">특징 <span class="muted">· 한 줄에 하나</span></div>
  <textarea id="basisFeatures"></textarea>
  <div class="label">판매 포인트 <span class="muted">· 한 줄에 하나</span></div>
  <textarea id="basisSelling"></textarea>
  <div class="label">타깃 <span class="muted">· 한 줄에 하나</span></div>
  <textarea id="basisTarget"></textarea>
  <div class="label">콘텐츠 방향 <span class="muted">· 선택사항</span></div>
  <textarea id="basisDirection"></textarea>
  <div id="basisSource" class="muted" style="margin-top:6px"></div>
  <div class="actions">
    <button class="btn ghost" onclick="savePageBasis(false)">이 페이지에만 저장</button>
    <button class="btn soft" onclick="savePageBasis(true)">상품 Master에도 반영</button>
  </div>
  <div id="basisStatus" class="muted" style="margin-top:7px"></div>
</div>
'''

OPEN_OLD = "async function openJob(id){if(!id)return;current=await jf(`/api/v1/detail-pages/jobs/${id}?tenant_id=${tenant}`);render()}"
OPEN_NEW = "async function openJob(id){if(!id)return;current=await jf(`/api/v1/detail-pages/jobs/${id}?tenant_id=${tenant}`);render();await loadPageBasis()}"

CREATE_OLD = "current=await jf(`/api/v1/detail-pages/jobs/${created.id}/prepare?tenant_id=${tenant}`,{method:'POST',body:JSON.stringify({template_code:template.value,visual_style:visualStyle.value,page_strategy:strategy.value,brand_style_sheet_id:brandStyle.value||null})});render();await loadJobs()}"
CREATE_NEW = "current=await jf(`/api/v1/detail-pages/jobs/${created.id}/prepare?tenant_id=${tenant}`,{method:'POST',body:JSON.stringify({template_code:template.value,visual_style:visualStyle.value,page_strategy:strategy.value,brand_style_sheet_id:brandStyle.value||null})});render();await loadPageBasis();await loadJobs()}"

SCRIPT_MARKER = "async function sessionOK()"
SCRIPT_INSERT = r'''
function basisLines(id){return document.getElementById(id).value.split(/\n/).map(x=>x.trim()).filter(Boolean)}
function setBasisField(id,value){document.getElementById(id).value=value||''}
async function loadPageBasis(){
  if(!current?.id){
    const productId=document.getElementById('product')?.value;
    if(!productId)return;
    try{
      const d=await jf(`/api/v1/product-registration/products/${productId}?tenant_id=${tenant}`);
      const op=d.operating_info||{};
      const mk=d.marketing_info||{};
      setBasisField('basisCategory',op.category||mk.category||'');
      setBasisField('basisUsage',(op.usage||[]).join('\n'));
      setBasisField('basisFeatures',(mk.features||[]).join('\n'));
      setBasisField('basisSelling',(mk.selling_points||[]).join('\n'));
      setBasisField('basisTarget',(mk.target_customer||[]).join('\n'));
      setBasisField('basisDirection',mk.content_direction||'');
      basisSource.textContent='현재 기준: 상품 Master 확정값';
      basisStatus.textContent='';
    }catch(e){
      basisStatus.textContent=`상품 Master 기준정보 불러오기 실패: ${e.message||e}`;
    }
    return;
  }
  try{
    const d=await jf(`/api/v1/detail-page-content-basis/jobs/${current.id}?tenant_id=${tenant}`);
    const b=d.basis||{};
    setBasisField('basisCategory',b.category);
    setBasisField('basisUsage',(b.usage||[]).join('\n'));
    setBasisField('basisFeatures',(b.features||[]).join('\n'));
    setBasisField('basisSelling',(b.selling_points||[]).join('\n'));
    setBasisField('basisTarget',(b.target_customer||[]).join('\n'));
    setBasisField('basisDirection',b.content_direction);
    const label=d.source==='product_master'?'상품 Master 기본값':'이 상세페이지에서 수정한 값';
    basisSource.textContent=`현재 기준: ${label}`;
    basisStatus.textContent='';
  }catch(e){basisStatus.textContent=`기준정보 불러오기 실패: ${e.message||e}`}
}
async function savePageBasis(syncMaster){
  if(!current?.id){basisStatus.textContent='먼저 상세페이지 작업을 선택하세요.';return}
  const payload={
    category:basisCategory.value.trim()||null,
    usage:basisLines('basisUsage'),
    features:basisLines('basisFeatures'),
    selling_points:basisLines('basisSelling'),
    target_customer:basisLines('basisTarget'),
    content_direction:basisDirection.value.trim()||null,
    sync_product_master:!!syncMaster
  };
  basisStatus.textContent='저장 중...';
  try{
    const saved=await jf(`/api/v1/detail-page-content-basis/jobs/${current.id}?tenant_id=${tenant}`,{method:'POST',body:JSON.stringify(payload)});
    current=await jf(`/api/v1/detail-pages/jobs/${current.id}?tenant_id=${tenant}`);
    render();
    await loadPageBasis();
    await loadJobs();
    basisStatus.textContent=syncMaster?'페이지와 상품 Master에 반영했습니다.':'이 상세페이지 버전에만 저장했습니다.';
  }catch(e){basisStatus.textContent=`저장 실패: ${e.message||e}`}
}
'''


def inject_detail_page_content_basis_editor(html: str) -> str:
    if "savePageBasis" in html:
        return html
    if PANEL_MARKER not in html:
        raise RuntimeError("detail page content basis panel marker not found")
    html = html.replace(PANEL_MARKER, PANEL + PANEL_MARKER, 1)
    if OPEN_OLD not in html:
        raise RuntimeError("detail page openJob marker not found")
    html = html.replace(OPEN_OLD, OPEN_NEW, 1)
    if CREATE_OLD not in html:
        raise RuntimeError("detail page createAndPrepare marker not found")
    html = html.replace(CREATE_OLD, CREATE_NEW, 1)
    if SCRIPT_MARKER not in html:
        raise RuntimeError("detail page script marker not found")
    return html.replace(SCRIPT_MARKER, SCRIPT_INSERT + "\n" + SCRIPT_MARKER, 1)
