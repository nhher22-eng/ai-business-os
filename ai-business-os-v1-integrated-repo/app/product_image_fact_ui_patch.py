from __future__ import annotations


IMAGE_FACT_CARD = r'''
  <section class="card hidden" id="imageFactCard">
    <div class="step">2 · 상품 이미지 FACT</div>
    <h2>핸드폰 사진을 한 번에 올리세요</h2>
    <div class="muted">
      45도 우측(대표)과 정면은 필수입니다. 각도사진은 자동 분류·배경제거 후 확인하고,
      라이프스타일 사진은 실제 촬영 배경을 그대로 보존합니다.
    </div>
    <div style="margin-top:12px;padding:12px;border:1px solid #35445a;border-radius:12px;background:#0b1220">
      <strong>저장 원칙</strong>
      <div class="muted" style="margin-top:6px">
        각도/상세사진: 촬영 원본은 임시 → 누끼 FACT 확정 후 원본 자동 삭제 ·
        라이프스타일: 촬영 원본 자체를 FACT로 보관
      </div>
    </div>
    <div class="field" style="margin-top:16px">
      <label>사진 여러 장 일괄 업로드</label>
      <input type="file" accept="image/*" id="imageFactFiles" multiple>
    </div>
    <div class="actions">
      <button id="uploadImageFacts">일괄 업로드 · 자동 정리</button>
      <button id="refreshImageFacts" class="secondary">새로고침</button>
    </div>
    <div id="imageFactReadiness" class="status"></div>
    <div id="imageFactStatus" class="status"></div>
    <div id="imageFactGrid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin-top:16px"></div>
  </section>
'''

IMAGE_FACT_SCRIPT = r'''

const imageFactSlotLabels={
  RIGHT_45:'45도 우측 ★ 대표·필수',LEFT_45:'45도 좌측',FRONT:'정면 ★ 필수',
  LEFT:'좌측',RIGHT:'우측',TOP:'상부',BOTTOM:'하부',DETAIL:'부분상세',
  LIFESTYLE:'라이프스타일',UNASSIGNED:'미분류'
};
const imageFactSlots=['RIGHT_45','LEFT_45','FRONT','LEFT','RIGHT','TOP','BOTTOM','DETAIL','LIFESTYLE'];

function imageFactOptions(selected){
  return imageFactSlots.map(x=>`<option value="${x}" ${x===selected?'selected':''}>${imageFactSlotLabels[x]}</option>`).join('');
}
function imageFactConfidence(item){
  if(item.classification_confidence===null||item.classification_confidence===undefined)return '';
  return ` · 신뢰도 ${Math.round(item.classification_confidence*100)}%`;
}
function renderImageFactReadiness(r){
  const el=document.getElementById('imageFactReadiness');
  if(!r){el.textContent='';return;}
  if(r.ready){el.innerHTML='<span class="ok">필수 이미지 FACT 완료 · 45도 우측 + 정면</span>';}
  else{el.innerHTML=`<span class="warn">필수 미완료: ${(r.missing_labels||[]).join(', ')}</span>`;}
}
function renderImageFacts(data){
  renderImageFactReadiness(data.readiness);
  const grid=document.getElementById('imageFactGrid');
  const rows=data.images||[];
  if(!rows.length){grid.innerHTML='<div class="muted">아직 등록된 이미지가 없습니다.</div>';return;}
  grid.innerHTML=rows.map(item=>{
    const src=item.fact_content_url||item.raw_content_url||'';
    const confirmed=item.status==='confirmed';
    const bgText=item.slot_type==='LIFESTYLE'?'배경 보존':(item.background_removed?'배경제거 완료':'배경제거 대기');
    const rawText=item.raw_available?'촬영 원본 임시보관':(item.raw_deleted_at?'촬영 원본 삭제 완료':'촬영 원본 없음');
    return `<div style="border:1px solid #35445a;border-radius:13px;padding:12px;background:#0f172a">
      ${src?`<img src="${src}" alt="상품 이미지" style="width:100%;height:180px;object-fit:contain;background:#fff;border-radius:9px">`:''}
      <div style="margin-top:10px"><strong>${imageFactSlotLabels[item.slot_type]||item.slot_type}</strong></div>
      <div class="muted" style="margin-top:4px">${item.filename||''}</div>
      <div class="muted">${item.classification_source||'-'}${imageFactConfidence(item)} · ${bgText}</div>
      <div class="muted">${rawText}</div>
      ${confirmed
        ? `<div class="ok" style="margin-top:10px">✓ 확정 FACT</div>`
        : `<div style="margin-top:10px">
            <select id="slot-${item.id}">${imageFactOptions(item.slot_type==='UNASSIGNED'?'RIGHT_45':item.slot_type)}</select>
            <div class="actions" style="margin-top:8px">
              <button class="secondary" onclick="saveImageFactSlot('${item.id}')">항목 저장·처리</button>
              ${item.fact_available?`<button onclick="confirmImageFact('${item.id}')">FACT 확정</button>`:''}
              <button class="secondary" onclick="deleteImageFact('${item.id}')">삭제</button>
            </div>
          </div>`}
    </div>`;
  }).join('');
}
async function loadImageFacts(){
  if(!productId)return;
  const s=document.getElementById('imageFactStatus');
  try{
    const data=await api(`/api/v1/product-image-facts/products/${productId}?tenant_id=${tenant}`);
    renderImageFacts(data);s.textContent='';
  }catch(e){s.textContent=String(e)}
}
async function uploadImageFacts(){
  const s=document.getElementById('imageFactStatus');
  try{
    if(!productId)throw new Error('먼저 기본 FACT를 저장하세요.');
    const files=[...document.getElementById('imageFactFiles').files];
    if(!files.length)throw new Error('업로드할 사진을 선택하세요.');
    const fd=new FormData();files.forEach(f=>fd.append('files',f));fd.append('auto_process','true');
    s.textContent=`${files.length}장 업로드·분류·처리 중...`;
    const data=await api(`/api/v1/product-image-facts/products/${productId}/batch?tenant_id=${tenant}`,{method:'POST',body:fd});
    s.innerHTML=`<span class="ok">${data.uploaded}장 등록 완료 · 분류가 틀리면 항목만 수정하세요.</span>`;
    document.getElementById('imageFactFiles').value='';
    await loadImageFacts();
  }catch(e){s.textContent=String(e)}
}
async function saveImageFactSlot(id){
  const s=document.getElementById('imageFactStatus');
  try{
    const slot=document.getElementById(`slot-${id}`).value;
    s.textContent='항목 저장 및 이미지 처리 중...';
    await api(`/api/v1/product-image-facts/images/${id}?tenant_id=${tenant}`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({slot_type:slot})});
    s.innerHTML='<span class="ok">항목 저장·처리 완료</span>';await loadImageFacts();
  }catch(e){s.textContent=String(e)}
}
async function confirmImageFact(id){
  const s=document.getElementById('imageFactStatus');
  try{
    s.textContent='FACT 확정 중...';
    await api(`/api/v1/product-image-facts/images/${id}/confirm?tenant_id=${tenant}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({confirmed_by:'dashboard-user'})});
    s.innerHTML='<span class="ok">이미지 FACT 확정 완료 · 정책에 따라 임시 원본 정리됨</span>';await loadImageFacts();
  }catch(e){s.textContent=String(e)}
}
async function deleteImageFact(id){
  const s=document.getElementById('imageFactStatus');
  try{
    await api(`/api/v1/product-image-facts/images/${id}?tenant_id=${tenant}`,{method:'DELETE'});
    s.textContent='미확정 이미지 삭제 완료';await loadImageFacts();
  }catch(e){s.textContent=String(e)}
}

const legacyImageCard=document.getElementById('imageCard');
if(legacyImageCard)legacyImageCard.style.display='none';
document.getElementById('uploadImageFacts').onclick=uploadImageFacts;
document.getElementById('refreshImageFacts').onclick=loadImageFacts;
'''


def inject_product_image_fact_ui(html: str) -> str:
    marker = '  <section class="card hidden" id="aiCard">'
    if 'id="imageFactCard"' not in html and marker in html:
        html = html.replace(marker, IMAGE_FACT_CARD + "\n" + marker, 1)

    # Existing saveFacts reveals the legacy image card. Reveal the new FACT card as well.
    old = "document.getElementById('imageCard').classList.remove('hidden');document.getElementById('aiCard').classList.remove('hidden');"
    new = "document.getElementById('imageCard').classList.remove('hidden');document.getElementById('imageFactCard').classList.remove('hidden');document.getElementById('aiCard').classList.remove('hidden');"
    if old in html:
        html = html.replace(old, new, 1)

    if 'function renderImageFacts(data)' not in html:
        html = html.replace('</script>', IMAGE_FACT_SCRIPT + '\n</script>', 1)
    return html
