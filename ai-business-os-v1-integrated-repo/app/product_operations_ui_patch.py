from __future__ import annotations


DONE_MARKER = '<section class="card hidden" id="doneCard">'
OPERATIONS_CARD = r'''
  <section class="card hidden" id="operationsCard">
    <div class="step">4 · 상품 운영</div>
    <h2>상태 · SKU · 변경 이력</h2>
    <div class="muted">기존 상품의 운영 상태와 판매 옵션을 관리합니다. 변경 내용은 운영 이력으로 기록됩니다.</div>

    <div class="grid" style="margin-top:16px">
      <div class="field"><label>상품 상태</label><select id="operationProductStatus"><option value="draft">초안</option><option value="active">활성</option><option value="inactive">비활성</option></select></div>
      <div class="field" style="justify-content:flex-end"><button type="button" id="saveProductStatus">상태 저장</button></div>
    </div>
    <div id="operationStatus" class="status"></div>

    <div style="margin-top:22px"><strong>SKU</strong><div class="muted" style="margin-top:4px">옵션이 없는 단일 상품은 SKU를 만들지 않아도 됩니다.</div></div>
    <div id="skuList" style="margin-top:10px"></div>
    <div class="grid" style="margin-top:12px">
      <div class="field"><label>SKU 코드</label><input id="newSkuCode" placeholder="예: NET-60-120"></div>
      <div class="field"><label>SKU 이름</label><input id="newSkuName" placeholder="예: 1.2×1.5m"></div>
      <div class="field"><label>옵션값</label><input id="newSkuOption" placeholder="선택사항"></div>
      <div class="field"><label>상태</label><select id="newSkuStatus"><option value="active">활성</option><option value="inactive">비활성</option></select></div>
    </div>
    <div class="actions"><button type="button" id="addSku">＋ SKU 추가</button></div>

    <div style="margin-top:24px"><strong>최근 변경 이력</strong></div>
    <div id="productHistory" style="margin-top:8px"></div>
  </section>
'''

SCRIPT_MARKER = "document.getElementById('saveFacts').onclick=saveFacts;"
SCRIPT_INSERT = r'''
function operationEsc(v){return escapeHtml(v??'')}
function operationTime(v){if(!v)return '';try{return new Date(v).toLocaleString('ko-KR')}catch(_){return v}}
async function loadProductOperations(){
  if(!productId)return;
  const card=document.getElementById('operationsCard');if(card)card.classList.remove('hidden');
  try{
    const d=await api(`/api/v1/product-operations/products/${encodeURIComponent(productId)}?tenant_id=${tenant}`);
    document.getElementById('operationProductStatus').value=d.product?.status||'draft';
    renderSkuList(d.skus||[]);renderProductHistory(d.history||[]);
  }catch(e){document.getElementById('operationStatus').textContent=String(e)}
}
function renderSkuList(items){
  const box=document.getElementById('skuList');if(!box)return;
  if(!items.length){box.innerHTML='<div class="muted">등록된 SKU가 없습니다.</div>';return}
  box.innerHTML=items.map(x=>`<div class="basis-row" data-sku-id="${operationEsc(x.id)}" style="border:1px solid #35445a;border-radius:10px;padding:10px;margin-top:8px;background:#0b1220"><div class="grid"><div class="field"><label>코드</label><input value="${operationEsc(x.sku_code)}" disabled></div><div class="field"><label>이름</label><input class="sku-name" value="${operationEsc(x.name)}"></div><div class="field"><label>옵션값</label><input class="sku-option" value="${operationEsc(x.option_value||'')}"></div><div class="field"><label>상태</label><select class="sku-status"><option value="active" ${x.status==='active'?'selected':''}>활성</option><option value="inactive" ${x.status==='inactive'?'selected':''}>비활성</option></select></div></div><div class="actions"><button type="button" class="secondary" onclick="saveSku('${operationEsc(x.id)}')">SKU 수정 저장</button></div></div>`).join('')
}
function renderProductHistory(items){
  const box=document.getElementById('productHistory');if(!box)return;
  box.innerHTML=items.length?items.map(x=>`<div style="padding:9px 0;border-bottom:1px solid #253044"><div>${operationEsc(x.summary)}</div><div class="muted">${operationEsc(operationTime(x.created_at))} · ${operationEsc(x.changed_by||'')}</div></div>`).join(''):'<div class="muted">아직 운영 변경 이력이 없습니다.</div>'
}
async function saveOperationStatus(){const s=document.getElementById('operationStatus');try{s.textContent='저장 중...';await api(`/api/v1/product-operations/products/${productId}/status?tenant_id=${tenant}`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({status:document.getElementById('operationProductStatus').value,changed_by:'dashboard-user'})});s.innerHTML='<span class="ok">상품 상태 저장 완료</span>';await loadProductOperations()}catch(e){s.textContent=String(e)}}
async function addOperationSku(){const s=document.getElementById('operationStatus');try{const code=v('newSkuCode'),name=v('newSkuName');if(!code||!name)throw new Error('SKU 코드와 이름은 필수입니다.');await api(`/api/v1/product-operations/products/${productId}/skus?tenant_id=${tenant}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sku_code:code,name,option_value:v('newSkuOption')||null,status:document.getElementById('newSkuStatus').value,changed_by:'dashboard-user'})});setInput('newSkuCode','');setInput('newSkuName','');setInput('newSkuOption','');s.innerHTML='<span class="ok">SKU 추가 완료</span>';await loadProductOperations()}catch(e){s.textContent=String(e)}}
async function saveSku(id){const s=document.getElementById('operationStatus');try{const row=document.querySelector(`[data-sku-id="${CSS.escape(id)}"]`);if(!row)throw new Error('SKU 행을 찾지 못했습니다.');await api(`/api/v1/product-operations/products/${productId}/skus/${encodeURIComponent(id)}?tenant_id=${tenant}`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:row.querySelector('.sku-name').value.trim(),option_value:row.querySelector('.sku-option').value.trim(),status:row.querySelector('.sku-status').value,changed_by:'dashboard-user'})});s.innerHTML='<span class="ok">SKU 수정 완료</span>';await loadProductOperations()}catch(e){s.textContent=String(e)}}
'''

LOAD_EXISTING_MARKER = "openNextSteps();\n  if((d.operating_info&&Object.keys(d.operating_info).length)||(d.marketing_info&&Object.keys(d.marketing_info).length))showSavedContentBasis(d);"
LOAD_EXISTING_REPLACEMENT = "openNextSteps();\n  await loadProductOperations();\n  if((d.operating_info&&Object.keys(d.operating_info).length)||(d.marketing_info&&Object.keys(d.marketing_info).length))showSavedContentBasis(d);"

BIND_MARKER = "document.getElementById('saveFacts').onclick=saveFacts;"
BIND_REPLACEMENT = "document.getElementById('saveProductStatus').onclick=saveOperationStatus;document.getElementById('addSku').onclick=addOperationSku;\n" + BIND_MARKER


def inject_product_operations_ui(html: str) -> str:
    if "loadProductOperations" in html:
        return html
    if DONE_MARKER not in html:
        raise RuntimeError("product done card marker not found")
    html = html.replace(DONE_MARKER, OPERATIONS_CARD + "\n" + DONE_MARKER, 1)
    if SCRIPT_MARKER not in html:
        raise RuntimeError("product script bind marker not found")
    html = html.replace(SCRIPT_MARKER, SCRIPT_INSERT + "\n" + SCRIPT_MARKER, 1)
    if LOAD_EXISTING_MARKER not in html:
        raise RuntimeError("product management load marker not found")
    html = html.replace(LOAD_EXISTING_MARKER, LOAD_EXISTING_REPLACEMENT, 1)
    if BIND_MARKER not in html:
        raise RuntimeError("product bind marker disappeared")
    html = html.replace(BIND_MARKER, BIND_REPLACEMENT, 1)
    return html
