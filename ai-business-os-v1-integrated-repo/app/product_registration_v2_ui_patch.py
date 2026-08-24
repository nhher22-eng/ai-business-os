from __future__ import annotations


PROGRESS = r'''
<div class="flow-progress" id="registrationFlow">
  <div class="flow-step active" role="button" tabindex="0" data-target="factCard"><b>1</b><span>상품 식별정보</span></div>
  <div class="flow-step" role="button" tabindex="0" data-target="objectiveFactCard"><b>2</b><span>객관적 상품 FACT</span></div>
  <div class="flow-step" role="button" tabindex="0" data-target="operationsCard"><b>3</b><span>옵션·규격·구성품</span></div>
  <div class="flow-step" role="button" tabindex="0" data-target="sourceMaterialCard"><b>4</b><span>원본 자료 등록</span></div>
  <div class="flow-step" role="button" tabindex="0" data-target="finalFactCard"><b>5</b><span>FACT 확인·완료</span></div>
</div>
'''

FACT_CARD = r'''
<section class="card" id="objectiveFactCard">
  <div class="step">2 · 객관적 상품 FACT</div><h2>짧고 확인 가능한 사실</h2>
  <div class="guide">광고 문장 없이 확인된 사실만 입력합니다. 자연스러운 판매 표현은 콘텐츠 문안 생성기에서 만듭니다.</div>
  <div class="grid" id="objectiveFactGrid">
    <div class="field"><label>상품군</label><input id="productGroup" placeholder="예: 화분·플랜터"></div>
    <div class="field"><label>실제 사용 용도</label><input id="verifiedUsage" placeholder="예: 내화분을 넣어 사용하는 가림 화분"></div>
    <div class="field full"><label>확인된 주의사항</label><textarea id="verifiedCautions" placeholder="확인된 내용만 입력"></textarea></div>
  </div>
  <div class="actions"><button type="button" id="saveObjectiveFacts">객관적 FACT 저장</button></div><div id="objectiveStatus" class="status"></div>
</section>
'''

SOURCE_CARD = r'''
<section class="card" id="sourceMaterialCard">
  <div class="step">4 · 원본 자료 등록</div><h2>가공하지 않은 이미지와 문서</h2>
  <div class="guide">여기서는 활용 역할·배경 제거·톤·예산을 정하지 않습니다. 이미지는 촬영 종류만 기록하고, 활용 계획은 이미지 요소 자산 생성기에서 정합니다.</div>
  <div class="source-current-head"><strong>현재 등록 원본 <span id="currentSourceCount">0장</span></strong><span class="status">마지막으로 확정 저장한 묶음</span></div>
  <div id="currentSourceImages" class="current-source-grid"><div class="source-queue-empty">등록된 원본 이미지가 없습니다.</div></div>
  <hr style="border:0;border-top:1px solid #e5eaf1;margin:18px 0">
  <h3>새 원본 추가·교체</h3>
  <div class="grid">
    <div class="field"><label>원본 이미지 추가</label><input type="file" accept="image/*" id="sourceImages" multiple></div>
    <div class="field"><label>새 파일 기본 촬영 분류</label><select id="sourceClassification"><option value="unknown">알 수 없음</option><option value="front">정면 촬영</option><option value="right_45">45도 우측 촬영</option><option value="left_45">45도 좌측 촬영</option><option value="side">측면 촬영</option><option value="top">상단 촬영</option><option value="bottom">하단 촬영</option><option value="detail">부분 상세 촬영</option><option value="usage_original">사용 모습 원본</option><option value="components">구성품 모음 촬영</option><option value="group">제품군·모음 촬영</option><option value="installation">설치·사용과정 촬영</option></select></div>
  </div>
  <div class="source-queue-head"><strong>저장 대기 원본 <span id="sourceQueueCount">0장</span></strong><button type="button" class="secondary" id="clearSourceQueue" disabled>전체 선택 취소</button></div>
  <div id="sourceQueueEmpty" class="source-queue-empty">선택된 이미지가 없습니다.</div><div id="sourceImageQueue" class="source-queue"></div>
  <div class="actions"><button type="button" id="uploadSourceImages" disabled>선택한 원본 이미지 저장</button></div><div id="sourceImageStatus" class="status"></div>
  <hr style="border:0;border-top:1px solid #e5eaf1;margin:18px 0">
  <div class="grid">
    <div class="field"><label>원본 문서</label><input type="file" id="sourceDocument" accept=".pdf,.doc,.docx,.xls,.xlsx,.csv,.txt,.zip"></div>
    <div class="field"><label>자료 종류</label><select id="sourceKind"><option value="manufacturer">제조사 제공 자료</option><option value="manual">설명서</option><option value="specification">규격서</option><option value="certificate">인증서</option><option value="other">기타 원본</option></select></div>
    <div class="field full"><label>자료 메모</label><input id="sourceNote" placeholder="선택사항"></div>
  </div><div class="actions"><button type="button" id="uploadSourceDocument">원본 문서 저장</button></div><div id="sourceDocumentStatus" class="status"></div><div id="sourceDocumentList" class="status"></div>
</section>
'''

FINAL_CARD = r'''
<section class="card" id="finalFactCard"><div class="step">5 · FACT 확인·등록 완료</div><h2>사실과 원본만 등록되었는지 확인</h2>
<div id="finalFactSummary" class="guide">현재 상태를 점검해 주세요.</div><div class="actions"><button type="button" id="reviewFinalFacts">FACT 상태 점검</button><button type="button" id="completeRegistration" class="secondary">확인하고 등록 완료</button></div></section>
'''

CSS = r'''.flow-progress{display:grid;grid-template-columns:repeat(5,1fr);gap:7px;margin-bottom:16px}.flow-step{background:#fff;border:1px solid #dfe5ee;border-top:4px solid #cfd8e5;border-radius:9px;padding:10px 7px;font-size:12px;color:#65748a;cursor:pointer;user-select:none}.flow-step:hover,.flow-step:focus{outline:2px solid #b9cdf5;background:#f7faff}.flow-step b{display:inline-flex;width:20px;height:20px;border-radius:50%;background:#eef2f7;align-items:center;justify-content:center}.flow-step span{display:block;margin-top:5px}.flow-step.active{border-top-color:#2763dc;color:#1f55b5}.flow-step.done{border-top-color:#2e9b69;color:#226746}.registration-stage-hidden{display:none!important}#doneCard:not(.v2-registration-complete){display:none!important}.source-current-head,.source-queue-head{display:flex;justify-content:space-between;align-items:center;gap:10px;margin:14px 0 8px}.current-source-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px}.current-source-card{border:1px solid #dce3ed;border-radius:10px;padding:8px;background:#fff}.current-source-card img{width:100%;height:110px;object-fit:contain;background:#f4f6fa;border-radius:7px;cursor:zoom-in}.current-source-card strong{display:block;margin-top:7px;font-size:12px}.current-source-card .status{overflow-wrap:anywhere;font-size:10px}.source-queue{display:grid;gap:8px}.source-queue-empty{padding:20px;text-align:center;color:#65748a;background:#f8fafc;border:1px dashed #cbd5e1;border-radius:9px;margin-bottom:10px}.source-queue-row{display:grid;grid-template-columns:72px minmax(140px,1fr) minmax(180px,1fr) auto;align-items:center;gap:10px;padding:9px 0;border-bottom:1px solid #e5eaf1}.source-queue-row img{width:72px;height:62px;object-fit:contain;background:#f4f6fa;border-radius:7px}.source-queue-name{overflow-wrap:anywhere;font-size:13px}.source-queue-row select{margin:0}.next-tools{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:14px}@media(max-width:900px){.flow-progress,.next-tools{grid-template-columns:1fr}.source-queue-row{grid-template-columns:64px 1fr}.source-queue-row img{width:64px;height:56px}}'''

FOOTER = r'''
<div id="registrationStageFooter" style="display:flex;align-items:center;justify-content:space-between;gap:10px;margin:14px 0;background:#fff;border:1px solid #dfe5ee;border-radius:12px;padding:12px">
  <button type="button" class="secondary" id="registrationPrev">← 이전 단계</button>
  <span class="status" id="registrationStageStatus">1 / 5</span>
  <button type="button" id="registrationNext">다음 단계 →</button>
</div>
'''

SCRIPT = r'''
const sourceClassificationOptions=[['unknown','미지정'],['front','정면 촬영'],['back','후면 촬영'],['right_45','45도 우측 촬영'],['left_45','45도 좌측 촬영'],['side','측면 촬영'],['top','상단 촬영'],['bottom','하단 촬영'],['detail','부분 상세 촬영'],['usage_original','사용 모습 원본'],['components','구성품'],['group','제품군·모음 촬영'],['installation','인포그래픽']];let sourceImageQueue=[];
function moveField(id,target){const x=document.getElementById(id)?.closest('.field');if(x)target.appendChild(x)}
function markFlow(n,state){const x=document.querySelectorAll('#registrationFlow .flow-step')[n-1];if(x){x.classList.remove('active','done');x.classList.add(state);if(state==='active')navigateRegistrationStep(x)}}
function syncRegistrationStageFooter(){const steps=[...document.querySelectorAll('#registrationFlow .flow-step')],current=steps.findIndex(x=>x.classList.contains('active'));registrationPrev.disabled=current<=0;registrationNext.disabled=current<0||current>=steps.length-1;registrationStageStatus.textContent=`${current+1} / ${steps.length}`}
function navigateRegistrationStep(step){const target=document.getElementById(step.dataset.target);if(!target)return;['factCard','objectiveFactCard','operationsCard','sourceMaterialCard','finalFactCard'].forEach(id=>{const panel=document.getElementById(id);if(panel)panel.classList.add('registration-stage-hidden')});target.classList.remove('hidden','registration-stage-hidden');document.querySelectorAll('#registrationFlow .flow-step').forEach(x=>x.classList.remove('active'));step.classList.add('active');syncRegistrationStageFooter();if(step.dataset.target==='sourceMaterialCard')loadCurrentSourceImages();target.scrollIntoView({behavior:'smooth',block:'start'})}
function moveRegistrationStage(delta){const steps=[...document.querySelectorAll('#registrationFlow .flow-step')],current=steps.findIndex(x=>x.classList.contains('active')),next=Math.max(0,Math.min(steps.length-1,current+delta));navigateRegistrationStep(steps[next])}
async function saveObjectiveFacts(){const s=document.getElementById('objectiveStatus');try{if(!productId)throw new Error('먼저 1단계 상품 식별정보를 저장하세요.');const f=factsPayload();delete f.workspace_id;delete f.product_code;delete f.name;await api(`/api/v1/product-registration/products/${productId}/facts?tenant_id=${tenant}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(f)});await api(`/api/v1/product-registration/products/${productId}/apply-suggestions?tenant_id=${tenant}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operating_info:{category:v('productGroup')||null,usage:v('verifiedUsage')?[v('verifiedUsage')]:[],cautions:v('verifiedCautions')||null,source_type:'user_verified_fact'}})});s.innerHTML='<span class="ok">객관적 FACT 저장 완료</span>';markFlow(2,'done');markFlow(3,'active')}catch(e){s.textContent=String(e)}}
async function ensureProductIdentityForSourceUpload(status){if(productId)return;status.textContent='상품 식별정보 자동 저장 중...';await window.saveFacts();if(!productId)throw new Error('상품 식별정보 자동 저장에 실패했습니다. 1단계의 품명과 상품코드를 확인해 주세요.')}
function sourceFileKey(file){return `${file.name}:${file.size}:${file.lastModified}`}
function renderSourceImageQueue(){const box=document.getElementById('sourceImageQueue'),empty=document.getElementById('sourceQueueEmpty'),count=document.getElementById('sourceQueueCount'),clear=document.getElementById('clearSourceQueue'),save=document.getElementById('uploadSourceImages');box.innerHTML=sourceImageQueue.map((item,i)=>`<div class="source-queue-row"><img src="${item.preview}" alt="${item.file.name} 미리보기"><div class="source-queue-name">${item.file.name}<br><span class="status">${Math.max(1,Math.round(item.file.size/1024))} KB</span></div><select data-source-classification="${i}">${sourceClassificationOptions.map(x=>`<option value="${x[0]}" ${item.classification===x[0]?'selected':''}>${x[1]}</option>`).join('')}</select><button type="button" class="secondary" data-source-remove="${i}">삭제</button></div>`).join('');empty.style.display=sourceImageQueue.length?'none':'block';count.textContent=`${sourceImageQueue.length}장`;clear.disabled=!sourceImageQueue.length;save.disabled=!sourceImageQueue.length;box.querySelectorAll('[data-source-classification]').forEach(x=>x.onchange=()=>{sourceImageQueue[+x.dataset.sourceClassification].classification=x.value});box.querySelectorAll('[data-source-remove]').forEach(x=>x.onclick=()=>{const item=sourceImageQueue.splice(+x.dataset.sourceRemove,1)[0];if(item)URL.revokeObjectURL(item.preview);renderSourceImageQueue()})}
function appendSourceImages(){const input=document.getElementById('sourceImages'),classification=document.getElementById('sourceClassification').value;[...input.files].forEach(file=>{const key=sourceFileKey(file);if(!sourceImageQueue.some(x=>x.key===key))sourceImageQueue.push({key,file,classification,preview:URL.createObjectURL(file)})});input.value='';renderSourceImageQueue()}
function clearSourceImages(){sourceImageQueue.forEach(x=>URL.revokeObjectURL(x.preview));sourceImageQueue=[];renderSourceImageQueue()}
function sourceEsc(value){return String(value||'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]))}
async function updateRegisteredSourceClassification(assetId,value,status){status.textContent='분류 저장 중...';try{await api(`/api/v1/product-registration/products/${productId}/images/${assetId}/classification?tenant_id=${tenant}`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({source_classification:value})});status.textContent='분류 저장 완료'}catch(e){status.textContent=String(e);await loadCurrentSourceImages()}}
async function loadCurrentSourceImages(){const box=document.getElementById('currentSourceImages'),count=document.getElementById('currentSourceCount');if(!box||!productId){if(count)count.textContent='0장';return}try{const d=await api(`/api/v1/product-registration/products/${productId}/images?tenant_id=${tenant}`),rows=d.assets||[];count.textContent=`${rows.length}장`;box.innerHTML=rows.length?rows.map(x=>{const label=(sourceClassificationOptions.find(v=>v[0]===x.source_classification)||['','미지정'])[1],url=`/api/v1/product-registration-assets/references/${encodeURIComponent(x.id)}/content?tenant_id=${tenant}`;return `<div class="current-source-card"><img src="${url}" alt="${sourceEsc(x.filename||label)}" onclick="window.open('${url}','_blank')"><select data-current-source-classification="${x.id}">${sourceClassificationOptions.map(v=>`<option value="${v[0]}" ${v[0]===x.source_classification?'selected':''}>${v[1]}</option>`).join('')}</select><div class="status" data-current-source-status="${x.id}">${sourceEsc(x.filename||'등록 이미지')}</div></div>`}).join(''):'<div class="source-queue-empty">등록된 원본 이미지가 없습니다.</div>';box.querySelectorAll('[data-current-source-classification]').forEach(el=>el.onchange=()=>updateRegisteredSourceClassification(el.dataset.currentSourceClassification,el.value,box.querySelector(`[data-current-source-status="${el.dataset.currentSourceClassification}"]`)))}catch(e){box.innerHTML=`<div class="source-queue-empty">기존 원본 조회 실패: ${sourceEsc(String(e))}</div>`}}
async function uploadSourceImages(){const s=document.getElementById('sourceImageStatus');try{if(!sourceImageQueue.length)throw new Error('이미지를 선택하세요.');await ensureProductIdentityForSourceUpload(s);s.textContent=`원본 ${sourceImageQueue.length}장 저장 중...`;for(let i=0;i<sourceImageQueue.length;i++){const item=sourceImageQueue[i],f=new FormData();f.append('role',i===0?'primary':'additional');f.append('source_classification',item.classification);f.append('file',item.file);await api(`/api/v1/product-registration/products/${productId}/images/upload?tenant_id=${tenant}`,{method:'POST',body:f})}const saved=sourceImageQueue.length;clearSourceImages();await loadCurrentSourceImages();s.innerHTML=`<span class="ok">원본 이미지 ${saved}장 저장 완료</span>`;markFlow(4,'done');markFlow(5,'active')}catch(e){s.textContent=String(e)}}
async function loadSourceDocuments(){if(!productId)return;const rows=await api(`/api/v1/product-registration/products/${productId}/sources?tenant_id=${tenant}`);sourceDocumentList.innerHTML=rows.length?rows.map(x=>`<div><a href="${x.content_url}">${x.original_filename}</a> · ${x.source_kind}</div>`).join(''):'등록된 원본 문서 없음'}
async function uploadSourceDocument(){const s=document.getElementById('sourceDocumentStatus');try{if(!productId)throw new Error('먼저 상품 식별정보를 저장하세요.');const file=document.getElementById('sourceDocument').files[0];if(!file)throw new Error('문서를 선택하세요.');const f=new FormData();f.append('source_kind',sourceKind.value);f.append('note',sourceNote.value);f.append('file',file);await api(`/api/v1/product-registration/products/${productId}/sources/upload?tenant_id=${tenant}`,{method:'POST',body:f});s.innerHTML='<span class="ok">원본 문서 저장 완료</span>';await loadSourceDocuments()}catch(e){s.textContent=String(e)}}
async function reviewFinalFacts(){try{if(!productId)throw new Error('먼저 상품을 저장하세요.');const d=await api(`/api/v1/product-registration/products/${productId}/readiness?tenant_id=${tenant}`);finalFactSummary.innerHTML=`<strong>객관적 FACT:</strong> ${d.facts_confirmed?'확정':'확인 필요'}<br><strong>원본 이미지:</strong> ${d.primary_asset_linked?'1개 이상 등록':'최소 1개 필요'}<br><strong>원본 문서:</strong> 선택 등록<br><strong>분리 확인:</strong> 판매 문안·이미지 활용계획·AI 제안은 상품정보에 포함하지 않음`}catch(e){finalFactSummary.textContent=String(e)}}
function completeV2Registration(){if(!productId)return alert('먼저 상품을 저장하세요.');doneCard.classList.add('v2-registration-complete');doneCard.classList.remove('hidden');doneCard.innerHTML=`<div class="step">등록 완료</div><h2>상품 FACT와 원본 등록 완료</h2><div class="muted">이후 도구는 저장된 FACT와 원본을 불러옵니다.</div><div class="next-tools"><a class="secondary" href="/image-assets" style="padding:12px;text-align:center;border-radius:9px">이미지 요소 자산 만들기</a><a class="secondary" href="/content-copy-studio" style="padding:12px;text-align:center;border-radius:9px">콘텐츠 문안 만들기</a><a class="secondary" href="/business-home" style="padding:12px;text-align:center;border-radius:9px">홈으로 이동</a></div>`;markFlow(5,'done');doneCard.scrollIntoView({behavior:'smooth'})}
function activateRegistrationV2(){const fact=factCard,obj=objectiveFactCard,ops=operationsCard,source=sourceMaterialCard,final=finalFactCard,done=doneCard;fact.querySelector('.step').textContent='1 · 상품 식별정보';fact.querySelector('h2').textContent='상품을 구분하는 기본값';fact.after(obj);obj.after(ops);ops.after(source);source.after(final);final.after(done);ops.classList.remove('hidden');['primaryMaterial','secondaryMaterial','weight','origin','length','width','height','certifications','factNotes'].forEach(id=>moveField(id,objectiveFactGrid));['individualPackaging','boxPackaging'].forEach(id=>moveField(id,ops.querySelector('.grid')));ops.querySelector('.step').textContent='3 · 옵션·규격·구성품';ops.querySelector('h2').textContent='판매 구성과 SKU 옵션';imageCard.style.display='none';imageFactCard.style.display='none';aiCard.style.display='none';imagePlanCard.style.display='none';document.querySelectorAll('#registrationFlow .flow-step').forEach(step=>{step.onclick=()=>navigateRegistrationStep(step);step.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();navigateRegistrationStep(step)}}});const old=window.saveFacts;window.saveFacts=async function(){await old();if(productId){markFlow(1,'done');markFlow(2,'active');await loadSourceDocuments()}};document.getElementById('saveFacts').onclick=window.saveFacts;document.getElementById('saveObjectiveFacts').onclick=saveObjectiveFacts;document.getElementById('sourceImages').onchange=appendSourceImages;document.getElementById('clearSourceQueue').onclick=clearSourceImages;document.getElementById('uploadSourceImages').onclick=uploadSourceImages;document.getElementById('uploadSourceDocument').onclick=uploadSourceDocument;document.getElementById('reviewFinalFacts').onclick=reviewFinalFacts;document.getElementById('completeRegistration').onclick=completeV2Registration;renderSourceImageQueue()}
activateRegistrationV2();
'''


SCRIPT = SCRIPT.replace(
    'activateRegistrationV2();',
    "activateRegistrationV2();registrationPrev.onclick=()=>moveRegistrationStage(-1);registrationNext.onclick=()=>moveRegistrationStage(1);const initialRegistrationStep=document.querySelector('#registrationFlow .flow-step.active');if(initialRegistrationStep)navigateRegistrationStep(initialRegistrationStep);",
    1,
)


def inject_product_registration_v2(html: str) -> str:
    if 'registrationFlow' in html:
        return html
    html = html.replace('</style>', CSS + '</style>', 1)
    html = html.replace('<section class="card" id="factCard">', PROGRESS + '<section class="card" id="factCard">', 1)
    html = html.replace('<section class="card hidden" id="imageCard">', FACT_CARD + '<section class="card hidden" id="imageCard">', 1)
    html = html.replace('<section class="card hidden" id="doneCard">', SOURCE_CARD + FINAL_CARD + FOOTER + '<section class="card hidden" id="doneCard">', 1)
    html = html.replace('</script>', SCRIPT + '</script>', 1)
    return html
