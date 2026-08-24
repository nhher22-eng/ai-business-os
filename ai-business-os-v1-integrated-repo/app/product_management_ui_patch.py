from __future__ import annotations


INIT_OLD = "async function init(){try{const ws=await api(`/api/v1/business/workspaces?tenant_id=${tenant}`);const sel=document.getElementById('workspace');sel.innerHTML=ws.map(x=>`<option value=\"${x.id}\">${x.name}</option>`).join('');if(!ws.length)document.getElementById('factStatus').textContent='Workspace가 없습니다.'}catch(e){document.getElementById('factStatus').textContent='대시보드 로그인 후 다시 열어주세요. '+e}}"

INIT_NEW = r'''function setInput(id,value){const el=document.getElementById(id);if(el)el.value=value??''}
function csvValue(value){if(Array.isArray(value))return value.join(', ');if(value&&typeof value==='object')return Object.values(value).filter(Boolean).join(', ');return value||''}
async function loadExistingProductFromUrl(){
  const id=new URLSearchParams(location.search).get('product_id');
  if(!id)return false;
  const d=await api(`/api/v1/product-registration/products/${encodeURIComponent(id)}?tenant_id=${tenant}`);
  productId=d.product.id;
  document.getElementById('workspace').value=d.product.workspace_id;
  setInput('name',d.product.name);setInput('productCode',d.product.product_code);
  const f=d.facts||{},dims=f.dimensions||{},pack=f.packaging||{};
  setInput('modelName',f.model_name);setInput('manufacturer',f.manufacturer);setInput('primaryMaterial',f.primary_material);setInput('secondaryMaterial',f.secondary_material);setInput('weight',f.weight);setInput('origin',f.country_of_origin);setInput('length',dims.length);setInput('width',dims.width);setInput('height',dims.height);setInput('certifications',csvValue(f.certifications));setInput('individualPackaging',pack.individual);setInput('boxPackaging',pack.box);setInput('factNotes',f.fact_notes);
  document.querySelector('.top h1').textContent='상품 정보 관리';
  document.querySelector('.top .muted').textContent='등록된 Product Master를 확인하고 필요한 내용을 수정합니다.';
  document.getElementById('workspace').disabled=true;
  document.getElementById('productCode').readOnly=true;
  document.getElementById('name').readOnly=true;
  document.getElementById('factStatus').innerHTML='<span class="ok">기존 상품을 불러왔습니다. FACT 변경은 저장 시 다시 확정됩니다.</span>';
  openNextSteps();
  if((d.operating_info&&Object.keys(d.operating_info).length)||(d.marketing_info&&Object.keys(d.marketing_info).length))showSavedContentBasis(d);
  history.replaceState(null,'',`/product-registration?product_id=${encodeURIComponent(productId)}`);
  return true;
}
function savedCandidate(value,source='user'){return {value,source,status:source==='fact'?'confirmed':'suggested',reason:source==='fact'?'확정 FACT에서 가져왔습니다.':'현재 Product Master에 저장된 콘텐츠 기준정보입니다.'}}
function showSavedContentBasis(d){
  const op=d.operating_info||{},mk=d.marketing_info||{};
  const editor={category:op.category?savedCandidate(op.category):null,usage:(op.usage||[]).map(x=>savedCandidate(x)),features:(mk.features||[]).map(x=>savedCandidate(x)),selling_points:(mk.selling_points||[]).map(x=>savedCandidate(x)),target_customer:(mk.target_customer||[]).map(x=>savedCandidate(x)),content_direction:mk.content_direction?savedCandidate(mk.content_direction):null};
  currentSuggestions={editor,warnings:[]};
  showSuggestions(currentSuggestions);
  const noteBox=document.getElementById('basis-product_notes');
  if(noteBox&&Array.isArray(mk.product_notes)){noteBox.innerHTML=mk.product_notes.map((x,i)=>basisRow(savedCandidate(x),'product_notes',i)).join('')}
  document.getElementById('aiStatus').textContent='현재 저장된 콘텐츠 기준정보';
}
async function init(){try{const ws=await api(`/api/v1/business/workspaces?tenant_id=${tenant}`);const sel=document.getElementById('workspace');sel.innerHTML=ws.map(x=>`<option value="${x.id}">${x.name}</option>`).join('');if(!ws.length){document.getElementById('factStatus').textContent='Workspace가 없습니다.';return}await loadExistingProductFromUrl()}catch(e){document.getElementById('factStatus').textContent='대시보드 로그인 후 다시 열어주세요. '+e}}'''

SAVE_MARKER = "async function saveFacts(){"
SAVE_EXISTING = r'''async function saveExistingFacts(){const s=document.getElementById('factStatus');s.textContent='저장 중...';await api(`/api/v1/product-registration/products/${productId}/facts?tenant_id=${tenant}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(factsUpdatePayload())});s.innerHTML='<span class="ok">FACT 수정 저장 완료 · 다시 확정됨</span>';openNextSteps()}
'''

SAVE_GUARD_OLD = "async function saveFacts(){const s=document.getElementById('factStatus');try{if(!v('name')||!v('productCode'))throw new Error('품명과 상품코드는 필수입니다.');"
SAVE_GUARD_NEW = "async function saveFacts(){const s=document.getElementById('factStatus');try{if(productId&&new URLSearchParams(location.search).get('product_id')){await saveExistingFacts();return}if(!v('name')||!v('productCode'))throw new Error('품명과 상품코드는 필수입니다.');"
SAVE_GUARD_CATALOG_OLD = "async function saveFacts(){const s=document.getElementById('factStatus');try{if(!v('name'))throw new Error('품명은 필수입니다.');"
SAVE_GUARD_CATALOG_NEW = "async function saveFacts(){const s=document.getElementById('factStatus');try{if(productId&&new URLSearchParams(location.search).get('product_id')){await saveExistingFacts();return}if(!v('name'))throw new Error('품명은 필수입니다.');"


def inject_product_management_mode(html: str) -> str:
    if 'loadExistingProductFromUrl' in html:
        return html
    if INIT_OLD not in html:
        raise RuntimeError('product registration init marker not found')
    html = html.replace(INIT_OLD, INIT_NEW, 1)
    if SAVE_GUARD_CATALOG_OLD in html:
        html = html.replace(SAVE_GUARD_CATALOG_OLD, SAVE_GUARD_CATALOG_NEW, 1)
    elif SAVE_GUARD_OLD in html:
        html = html.replace(SAVE_GUARD_OLD, SAVE_GUARD_NEW, 1)
    else:
        raise RuntimeError('product registration save guard marker not found')
    if SAVE_MARKER not in html:
        raise RuntimeError('product registration save marker not found')
    return html.replace(SAVE_MARKER, SAVE_EXISTING + '\n' + SAVE_MARKER, 1)
