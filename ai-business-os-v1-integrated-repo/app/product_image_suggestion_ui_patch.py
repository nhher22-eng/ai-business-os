from __future__ import annotations


def inject_product_image_suggestion_ui(html: str) -> str:
    if "product-image-suggestion-ui-v1" in html:
        return html

    marker = "document.getElementById('saveFacts').onclick=saveFacts;"
    if marker not in html:
        return html

    script = r'''
// product-image-suggestion-ui-v1
const productImageSuggestionState={pollTimer:null};

function ensureImageSuggestionPanel(){
  if(document.getElementById('imageSuggestionView')) return;
  const aiCard=document.getElementById('aiCard');
  const applyActions=document.getElementById('applyActions');
  const box=document.createElement('div');
  box.id='imageSuggestionBlock';
  box.style.marginTop='20px';
  box.innerHTML=`
    <div style="border-top:1px solid #253044;padding-top:16px">
      <h2 style="font-size:18px">이미지 AI 제안</h2>
      <div class="muted">저장된 확정 FACT와 실제 상품 기준 이미지를 함께 읽어 후보 이미지를 만듭니다. 제품보존(HARD LOCK)은 자동 적용됩니다.</div>
      <div id="imageSuggestionView" style="margin-top:12px"></div>
      <div id="imageSuggestionStatus" class="status"></div>
    </div>`;
  aiCard.insertBefore(box,applyActions);
}

function imageSuggestionStatusLabel(job){
  const map={
    suggestion_queued:'생성 대기',
    suggestion_generating:'생성 중',
    suggestion_review:'검토 필요',
    suggestion_on_hold:'보류',
    suggestion_adopted:'채택 완료',
    failed:'생성 실패'
  };
  return map[job.status]||job.status||'-';
}

function renderImageSuggestionJobs(jobs){
  ensureImageSuggestionPanel();
  const view=document.getElementById('imageSuggestionView');
  if(!jobs||!jobs.length){
    view.innerHTML='<div class="muted">아직 이미지 제안이 없습니다.</div>';
    return;
  }
  view.innerHTML=jobs.map(job=>{
    const asset=job.asset;
    const image=asset
      ? `<img src="${asset.content_url}" alt="${job.title}" style="width:100%;max-height:340px;object-fit:contain;background:#0b1220;border-radius:12px;border:1px solid #35445a">`
      : `<div style="height:220px;display:grid;place-items:center;background:#0b1220;border:1px dashed #35445a;border-radius:12px" class="muted">${job.status==='failed'?'생성 실패':'AI 이미지 생성 중...'}</div>`;
    const actions=asset && job.status!=='suggestion_adopted'
      ? `<div class="actions" style="margin-top:10px">
           <button onclick="adoptImageSuggestion('${asset.id}','${job.role}')">채택</button>
           <button class="secondary" onclick="editImageSuggestion('${job.id}','${asset.id}','${job.role}')">편집 후 채택</button>
           <button class="secondary" onclick="decideImageSuggestion('${job.id}','hold')">보류</button>
           <button class="secondary" onclick="decideImageSuggestion('${job.id}','dismiss')">삭제</button>
         </div>`
      : job.status==='suggestion_on_hold'
        ? `<div class="actions"><button class="secondary" onclick="editImageSuggestion('${job.id}','${asset?asset.id:''}','${job.role}')">다시 열기</button><button class="secondary" onclick="decideImageSuggestion('${job.id}','dismiss')">삭제</button></div>`
        : '';
    return `<div class="suggestion" style="padding:14px;border:1px solid #253044;border-radius:14px;margin-bottom:12px">
      <div style="display:flex;justify-content:space-between;gap:10px;margin-bottom:10px"><strong>${job.title}</strong><span class="muted">${imageSuggestionStatusLabel(job)}</span></div>
      ${image}
      <div class="muted" style="margin-top:8px">${job.image_type} · ${job.usage_context} · ${job.protection_mode}</div>
      ${actions}
    </div>`;
  }).join('');
}

async function loadImageSuggestions(){
  if(!productId) return [];
  const d=await api(`/api/v1/product-image-suggestions/products/${productId}?tenant_id=${tenant}`);
  renderImageSuggestionJobs(d.jobs||[]);
  return d.jobs||[];
}

function stopImageSuggestionPolling(){
  if(productImageSuggestionState.pollTimer){clearTimeout(productImageSuggestionState.pollTimer);productImageSuggestionState.pollTimer=null;}
}

async function pollImageSuggestions(){
  stopImageSuggestionPolling();
  try{
    const jobs=await loadImageSuggestions();
    const pending=jobs.some(j=>['suggestion_queued','suggestion_generating','preview_generating'].includes(j.status));
    if(pending){
      document.getElementById('imageSuggestionStatus').textContent='이미지 후보를 생성하고 있습니다. 완료되는 순서대로 카드에 표시됩니다.';
      productImageSuggestionState.pollTimer=setTimeout(pollImageSuggestions,2500);
    }else{
      document.getElementById('imageSuggestionStatus').textContent=jobs.length?'이미지 제안 준비 완료':'이미지 제안 없음';
    }
  }catch(e){
    document.getElementById('imageSuggestionStatus').textContent=String(e);
  }
}

async function startImageSuggestions(){
  ensureImageSuggestionPanel();
  if(!productId) throw new Error('먼저 FACT를 저장하세요.');
  document.getElementById('imageSuggestionStatus').textContent='이미지 제안 작업을 준비 중...';
  try{
    const d=await api(`/api/v1/product-image-suggestions/products/${productId}/start?tenant_id=${tenant}`,{
      method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({force:false})
    });
    renderImageSuggestionJobs(d.jobs||[]);
    await pollImageSuggestions();
  }catch(e){
    document.getElementById('imageSuggestionStatus').textContent=`이미지 제안 보류 · ${e}`;
  }
}

async function adoptImageSuggestion(assetId,role){
  try{
    await api(`/api/v1/product-image-suggestions/assets/${assetId}/adopt?tenant_id=${tenant}`,{
      method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({role,approved_by:'dashboard-user'})
    });
    document.getElementById('imageSuggestionStatus').innerHTML='<span class="ok">제안 이미지를 상품 이미지로 채택했습니다.</span>';
    await loadImageSuggestions();
  }catch(e){alert(`채택 실패: ${e}`)}
}

async function decideImageSuggestion(jobId,decision){
  try{
    await api(`/api/v1/product-image-suggestions/jobs/${jobId}/decision?tenant_id=${tenant}`,{
      method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({decision})
    });
    await loadImageSuggestions();
  }catch(e){alert(`처리 실패: ${e}`)}
}

function editImageSuggestion(jobId,assetId,role){
  const back=`/product-registration?product_id=${encodeURIComponent(productId)}`;
  const params=new URLSearchParams({mode:'suggestion-edit',job_id:jobId,product_id:productId,asset_id:assetId||'',role:role||'additional',return_to:back});
  window.location.href=`/image-studio?${params.toString()}`;
}

const originalGetSuggestions=getSuggestions;
getSuggestions=async function(){
  await originalGetSuggestions();
  await startImageSuggestions();
};

const originalInit=init;
init=async function(){
  await originalInit();
  ensureImageSuggestionPanel();
  const requestedProduct=new URLSearchParams(window.location.search).get('product_id');
  if(requestedProduct){
    try{
      const d=await api(`/api/v1/product-registration/products/${requestedProduct}?tenant_id=${tenant}`);
      productId=d.product.id;
      document.getElementById('name').value=d.product.name||'';
      document.getElementById('productCode').value=d.product.product_code||'';
      const f=d.facts||{};
      document.getElementById('modelName').value=f.model_name||'';
      document.getElementById('manufacturer').value=f.manufacturer||'';
      document.getElementById('primaryMaterial').value=f.primary_material||'';
      document.getElementById('secondaryMaterial').value=f.secondary_material||'';
      document.getElementById('weight').value=f.weight||'';
      document.getElementById('origin').value=f.country_of_origin||'';
      document.getElementById('length').value=(f.dimensions||{}).length||'';
      document.getElementById('width').value=(f.dimensions||{}).width||'';
      document.getElementById('height').value=(f.dimensions||{}).height||'';
      document.getElementById('certifications').value=(f.certifications||[]).join(', ');
      document.getElementById('individualPackaging').value=(f.packaging||{}).individual||'';
      document.getElementById('boxPackaging').value=(f.packaging||{}).box||'';
      document.getElementById('factNotes').value=f.fact_notes||'';
      document.getElementById('imageCard').classList.remove('hidden');
      document.getElementById('aiCard').classList.remove('hidden');
      currentSuggestions=d.ai_suggestions||null;
      if(currentSuggestions && Object.keys(currentSuggestions).length){showSuggestions(currentSuggestions);}
      await loadImageSuggestions();
    }catch(e){document.getElementById('factStatus').textContent=`기존 상품 불러오기 실패: ${e}`;}
  }
};

setTimeout(()=>{
  document.getElementById('getSuggestions').onclick=getSuggestions;
},0);
'''

    return html.replace(marker, script + "\n" + marker, 1)


def inject_image_studio_suggestion_edit_mode(html: str) -> str:
    if "suggestion-edit-mode-v1" in html:
        return html

    marker = "init().catch(e=>{el('sessionStatus').textContent='연결 오류';console.error(e)});"
    if marker not in html:
        return html

    script = r'''
// suggestion-edit-mode-v1
const suggestionEditContext=(()=>{
  const p=new URLSearchParams(window.location.search);
  if(p.get('mode')!=='suggestion-edit') return null;
  return {
    jobId:p.get('job_id'),productId:p.get('product_id'),assetId:p.get('asset_id'),
    role:p.get('role')||'additional',returnTo:p.get('return_to')||'/product-registration'
  };
})();

function installSuggestionEditBanner(){
  if(!suggestionEditContext||document.getElementById('suggestionEditBanner')) return;
  const main=document.querySelector('.main .card');
  const banner=document.createElement('div');
  banner.id='suggestionEditBanner';
  banner.style='margin-bottom:14px;padding:14px;border:1px solid #c7d2fe;background:#eef2ff;border-radius:12px;color:#273c9f';
  banner.innerHTML=`<strong>AI 제안 이미지 편집 모드</strong><div style="font-size:13px;margin-top:5px">상품 FACT·기준사진·HARD LOCK·이미지 역할은 상품등록에서 자동으로 이어받았습니다. 바꾸고 싶은 부분만 수정 요청하세요.</div><div class="actions"><button class="btn primary" onclick="adoptSuggestionAndReturn()">현재 이미지 채택 후 상품정보로 돌아가기</button><button class="btn ghost" onclick="returnToProductRegistration()">저장하지 않고 돌아가기</button></div>`;
  main.insertBefore(banner,main.firstChild);
}

async function openSuggestionEditContext(){
  if(!suggestionEditContext) return;
  const idx=products.findIndex(p=>p.id===suggestionEditContext.productId);
  if(idx>=0){el('product').value=suggestionEditContext.productId;await loadSkus();}
  if(suggestionEditContext.jobId){await openJob(suggestionEditContext.jobId);}
  if(suggestionEditContext.assetId && currentJob){selectAsset(suggestionEditContext.assetId);}
  el('protection').value='hard_lock';
  el('protection').disabled=true;
  el('product').disabled=true;
  el('imageType').disabled=true;
  el('usage').disabled=true;
  installSuggestionEditBanner();
}

function returnToProductRegistration(){window.location.href=suggestionEditContext?.returnTo||'/product-registration';}

async function adoptSuggestionAndReturn(){
  if(!suggestionEditContext||!currentAsset){alert('채택할 이미지가 없습니다.');return;}
  try{
    await jsonFetch(`/api/v1/product-image-suggestions/assets/${currentAsset.id}/adopt?tenant_id=${tenant}`,{
      method:'POST',body:JSON.stringify({role:suggestionEditContext.role,approved_by:'dashboard-user'})
    });
    returnToProductRegistration();
  }catch(e){alert(`채택 실패: ${e.message||e}`)}
}

const baseStudioInit=init;
init=async function(){
  await baseStudioInit();
  await openSuggestionEditContext();
};
'''
    return html.replace(marker, script + "\n" + marker, 1)
