from fastapi import APIRouter
from fastapi.responses import HTMLResponse


router = APIRouter()


HTML = r'''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>상세페이지 템플릿 설정 | AI Business OS</title>
<style>
*{box-sizing:border-box}body{margin:0;font-family:Inter,Pretendard,system-ui,sans-serif;background:#f4f6fa;color:#172033}
.top{height:64px;background:#fff;border-bottom:1px solid #e1e6ee;display:flex;align-items:center;padding:0 22px;gap:18px;position:sticky;top:0;z-index:20}
.top a{text-decoration:none;color:#526174;font-size:14px}.brand{font-weight:900;font-size:17px}.session{margin-left:auto;color:#64748b;font-size:13px}
.shell{display:grid;grid-template-columns:310px minmax(700px,1fr);min-height:calc(100vh - 64px)}.side{background:#fff;border-right:1px solid #e1e6ee;padding:18px;overflow:auto}.main{padding:22px;overflow:auto}
.muted{font-size:12px;color:#718096;line-height:1.55}.label{font-size:12px;font-weight:800;color:#667085;margin:12px 0 6px}
button,input,textarea,select{font:inherit}input,textarea,select{width:100%;padding:10px;border:1px solid #d5dce7;border-radius:9px;background:#fff}textarea{min-height:78px;resize:vertical}
.btn{border:0;border-radius:9px;padding:10px 13px;font-weight:800;cursor:pointer}.btn:disabled{opacity:.5}.primary{background:#3559e0;color:#fff}.secondary{background:#edf2ff;color:#3047a2}.soft{background:#f2f4f7;color:#344054}.danger{background:#fff1f0;color:#b42318}.full{width:100%}
.template-list{display:grid;gap:8px;margin-top:14px}.template-card{border:1px solid #dde3ec;border-radius:12px;padding:12px;cursor:pointer;background:#fff}.template-card.selected{border:2px solid #5b72df;background:#f6f8ff}.template-title{font-weight:850}.meta{font-size:11px;color:#6b778c;margin-top:5px}
.badge{display:inline-flex;padding:4px 8px;border-radius:999px;font-size:11px;font-weight:800}.draft{background:#f2f4f7;color:#475467}.testing{background:#fff4d6;color:#8a5b00}.active-status{background:#e8f7ed;color:#137333}.retired{background:#fdecec;color:#b42318}
.card{background:#fff;border:1px solid #dfe5ed;border-radius:15px;padding:18px;margin-bottom:14px}.header{display:flex;gap:12px;align-items:flex-start}.header h2{margin:0 0 5px;flex:1}.actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}
.step-title{display:flex;align-items:center;gap:9px;margin-bottom:12px}.step-no{width:28px;height:28px;border-radius:50%;background:#3559e0;color:#fff;display:grid;place-items:center;font-weight:900}.step-title h3{margin:0}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:12px}.section-row{display:grid;grid-template-columns:38px minmax(150px,1fr) 105px 210px 76px;gap:8px;align-items:center;padding:9px;border:1px solid #e2e7ef;border-radius:10px;margin-bottom:7px}.section-row.off{opacity:.5}.section-row input[type=checkbox]{width:auto}.section-name strong,.section-name small{display:block}.section-name small{color:#778396}.move{display:flex;gap:4px}.move button{border:0;background:#eef2f7;border-radius:7px;padding:6px}
.binding-row{display:grid;grid-template-columns:minmax(180px,1fr) 34px minmax(220px,1fr) 40px;gap:8px;align-items:center;margin-bottom:7px}.arrow{text-align:center;color:#697386;font-weight:900}
.preview{background:#f8fafc;border:1px dashed #cdd5e1;border-radius:13px;padding:14px;display:grid;gap:8px}.preview-block{background:#fff;border:1px solid #e3e7ed;border-radius:10px;padding:11px;display:flex;justify-content:space-between}.preview-block span{font-size:11px;color:#6f7b8d}
.validation{padding:12px;border-radius:10px;background:#f8fafc;min-height:50px}.ok{color:#16803a}.warn{color:#9a6700}.fail{color:#b42318}.hidden{display:none!important}.lock-note{background:#eef7ff;color:#245b82;padding:11px;border-radius:10px;margin-top:10px}
.guide{background:#f7f9ff;border:1px solid #dce4ff;border-radius:11px;padding:12px;margin:8px 0 14px;color:#405174;font-size:12px;line-height:1.6}
.guide strong{color:#263d89}.guide details{margin-top:7px}.guide summary{cursor:pointer;font-weight:800;color:#3559b8}.guide ul{margin:7px 0 2px;padding-left:19px}
.field-label{display:flex;align-items:center;gap:6px}.field-tag{font-size:10px;border-radius:999px;padding:2px 6px;font-weight:800}.required{background:#fff0ee;color:#b42318}.optional{background:#eef4ff;color:#3559b8}.fixed{background:#f2f4f7;color:#596579}
.field-note{font-size:11px;color:#748096;line-height:1.5;margin-top:5px}.field-note b{color:#50607a}
.field-error{font-size:11px;color:#b42318;min-height:16px;margin-top:3px}.input-invalid{border-color:#e5484d!important;background:#fff8f7!important}
.example{background:#fff;border-left:3px solid #8aa2ff;padding:7px 9px;margin-top:7px;color:#526174}

@media(max-width:950px){.shell{display:block}.side{border:0;border-bottom:1px solid #ddd}.grid2{grid-template-columns:1fr}.section-row,.binding-row{grid-template-columns:1fr}.arrow{display:none}}
</style>
</head>
<body>
<div class="top"><a href="/dashboard">← 대시보드</a><a href="/detail-pages">상품 상세페이지 생성</a><div class="brand">상세페이지 템플릿 설정</div><div class="session" id="sessionStatus">연결 확인 중</div></div>
<div class="shell">
<aside class="side">
<h3 style="margin:0">템플릿</h3>
<div class="muted">상세페이지의 내용 구성, Canva 디자인, 상품 요소 연결을 설정합니다. 확정된 템플릿은 상품 제작 화면에서 변경할 수 없습니다.</div>
<button class="btn primary full" style="margin-top:14px" onclick="createTemplate()">+ 새 템플릿 만들기</button>
<div class="template-list" id="templateList"></div>
</aside>
<main class="main">
<div id="emptyState" class="card"><h2 style="margin-top:0">템플릿을 선택하거나 새로 만들어 주세요.</h2><div class="muted">① 기본정보·Canva 연결 → ② 섹션 구성 → ③ 요소 연결 → ④ 시험·확정</div></div>
<div id="editor" class="hidden">
<div class="card">
<div class="header"><div style="flex:1"><h2 id="title">-</h2><div id="templateMeta" class="muted"></div></div><span id="statusBadge" class="badge draft">작성 중</span></div>
<div id="lockNote" class="lock-note hidden">확정된 템플릿은 직접 수정할 수 없습니다. 변경하려면 새 버전을 만드세요.</div>
<div class="actions">
<button id="saveBtn" class="btn primary" onclick="saveDraft()">임시저장</button>
<button id="validateBtn" class="btn secondary" onclick="validateTemplate()">템플릿 시험</button>
<button id="publishBtn" class="btn primary" onclick="publishTemplate()">검증 후 확정</button>
<button id="newVersionBtn" class="btn secondary hidden" onclick="newVersion()">새 버전 만들기</button>
<button id="retireBtn" class="btn danger hidden" onclick="retireTemplate()">사용 중지</button>
<button class="btn soft" onclick="openCanva()">Canva 원본 열기</button>
</div></div>

<section class="card">
<div class="step-title"><span class="step-no">1</span><h3>기본정보와 Canva 원본 연결</h3></div>
<div class="guide"><strong>무엇을 설정하나요?</strong> 템플릿의 이름과 사용범위를 정하고, 사용자가 Canva에서 만든 원본 디자인을 연결합니다.
<details><summary>입력 순서와 주의사항 보기</summary><ul><li>Canva 원본이 없다면 Canva 관련 항목은 비워두어도 됩니다.</li><li>먼저 임시저장과 템플릿 시험을 하고 마지막에 확정하세요.</li><li>확정된 템플릿은 이 화면에서 직접 덮어쓰지 않고 새 버전으로 수정합니다.</li></ul></details></div>

<div class="grid2">
<div>
<div class="label field-label">템플릿 이름 <span class="field-tag required">필수</span></div>
<input id="name" placeholder="예: 화분 기본 상세페이지" oninput="validateGuideFields()">
<div class="field-note">자동·수동 생성 화면에서 사용자가 보고 선택하는 이름입니다.</div>
<div class="example">예: 화분 기본 상세페이지</div>
<div class="field-error" id="nameError"></div>
</div>
<div>
<div class="label field-label">템플릿 코드 <span class="field-tag fixed">자동·고정</span></div>
<input id="code" disabled>
<div class="field-note">시스템이 템플릿을 구분하는 고유 코드입니다. 생성 후에는 직접 변경하지 않습니다.</div>
<div class="example">예: FLOWERPOT_STANDARD</div>
</div>
</div>

<div class="label field-label">설명 <span class="field-tag optional">권장</span></div>
<textarea id="description" placeholder="템플릿의 목적, 대상 상품과 디자인 방향"></textarea>
<div class="field-note">템플릿이 여러 개일 때 어떤 템플릿을 선택할지 판단하는 안내입니다.</div>
<div class="example">예: 화분 상품용 기본 상세페이지. 확정 FACT와 승인 이미지를 자동 연결합니다.</div>

<div class="grid2">
<div>
<div class="label field-label">Canva 디자인 ID <span class="field-tag optional">선택</span></div>
<input id="canvaDesignId" placeholder="예: DAGxxxxxxx" oninput="validateGuideFields()">
<div class="field-note">Canva 주소에서 <b>design/</b> 다음에 있는 값입니다. 아직 연결하지 않으면 비워두세요.</div>
<div class="field-error" id="canvaIdError"></div>
</div>
<div>
<div class="label field-label">Canva 브랜드 템플릿 ID <span class="field-tag optional">선택</span></div>
<input id="canvaBrandTemplateId" placeholder="브랜드 템플릿을 사용할 때만 입력">
<div class="field-note">일반 Canva 디자인만 사용하면 비워둡니다.</div>
</div>
</div>

<div class="label field-label">Canva 편집 링크 <span class="field-tag optional">선택</span></div>
<input id="canvaEditUrl" placeholder="https://www.canva.com/design/..." oninput="validateGuideFields()">
<div class="field-note">개별 상품 복사본이 아니라 원본 템플릿 디자인의 전체 주소를 입력합니다.</div>
<div class="example">예: https://www.canva.com/design/DAGxxxxxxx/edit</div>
<div class="field-error" id="canvaUrlError"></div>

<div class="grid2">
<div>
<div class="label field-label">적용 카테고리 <span class="field-tag optional">선택</span></div>
<input id="categoryScope" placeholder="화분, 플랜터 · 비워두면 전체">
<div class="field-note">쉼표로 구분합니다. 비워두면 모든 상품 카테고리에 사용할 수 있습니다.</div>
</div>
<div>
<div class="label field-label">적용 판매채널 <span class="field-tag required">필수</span></div>
<input id="channelScope" value="naver-smartstore" oninput="validateGuideFields()">
<div class="field-note">사용할 판매채널을 쉼표로 구분합니다.</div>
<div class="example">예: naver-smartstore</div>
<div class="field-error" id="channelError"></div>
</div>
</div>
</section>

<section class="card">
<div class="step-title"><span class="step-no">2</span><h3>상세페이지 섹션 구성</h3></div>
<div class="guide"><strong>무엇을 설정하나요?</strong> 상세페이지에 들어갈 내용의 종류와 순서를 정합니다.
<details><summary>활성화·필수·표시 조건의 차이 보기</summary><ul><li><b>활성화:</b> 이 템플릿에서 해당 섹션을 사용합니다.</li><li><b>필수:</b> 데이터가 없으면 QA가 실패합니다. 반드시 존재해야 할 섹션에만 사용하세요.</li><li><b>표시 조건:</b> FACT나 승인 이미지가 있을 때만 자동으로 표시합니다.</li><li>실제 리뷰가 없으면 리뷰 섹션과 임의 리뷰를 만들지 않습니다.</li></ul></details></div>
<div id="sectionRows"></div><button id="addSectionBtn" class="btn secondary" onclick="addSection()">+ 섹션 추가</button>
</section>

<section class="card">
<div class="step-title"><span class="step-no">3</span><h3>Canva 자리와 상품 요소 연결</h3></div>
<div class="guide"><strong>무엇을 설정하나요?</strong> Canva 디자인의 입력 자리와 시스템의 확정 상품정보를 연결합니다.
<details><summary>연결 예시와 작성 방법 보기</summary><ul><li>왼쪽: Canva에서 정한 자리 이름입니다. 예: <b>hero.title</b></li><li>오른쪽: 해당 자리에 자동 입력할 확정 데이터입니다. 예: <b>product.name</b></li><li>예: <b>hero.image ← approved_image.HERO</b></li><li>이 연결을 저장하면 상품마다 같은 내용을 손으로 다시 입력하지 않습니다.</li></ul></details></div>
<datalist id="dataSources">
<option value="product.name"><option value="product.description"><option value="content_basis.headline"><option value="content_basis.features"><option value="content_basis.selling_points">
<option value="approved_image.HERO"><option value="approved_image.LIFESTYLE"><option value="approved_image.SPEC_SIZE"><option value="registration_fact.dimensions"><option value="registration_fact.primary_material">
<option value="product_detail.usage"><option value="product_detail.installation_method"><option value="product_detail.usage_conditions"><option value="product_detail.cautions">
<option value="product_skus.options"><option value="product_components.items"><option value="fact_based_faq.items">
</datalist>
<div id="bindingRows"></div><button id="addBindingBtn" class="btn secondary" onclick="addBinding()">+ 요소 연결 추가</button>
</section>

<section class="card">
<div class="step-title"><span class="step-no">4</span><h3>미리보기·시험·확정</h3></div>
<div class="guide"><strong>마지막 확인 단계입니다.</strong> 임시저장 → 템플릿 시험 → 오류 수정 → 확정 순서로 진행합니다.
<details><summary>확정하면 어떻게 되나요?</summary><ul><li>확정된 템플릿은 상품 상세페이지 자동생성에서 사용할 수 있습니다.</li><li>확정 후 원본은 잠기며, 변경하려면 새 버전을 만듭니다.</li><li>개별 상품 상세페이지에서는 원본 템플릿을 수정할 수 없습니다.</li></ul></details></div>
<div class="grid2"><div><div class="label">현재 섹션 구성</div><div class="preview" id="templatePreview"></div></div><div><div class="label">검증 결과</div><div class="validation" id="validationResult">아직 시험하지 않았습니다.</div></div></div>
</section>
</div></main></div>

<script>
const tenant='__legacy__';let workspace=null,catalog=null,templates=[],current=null,sections=[],bindings={};
const statusText={draft:'작성 중',testing:'시험 필요',active:'사용 중',retired:'사용 중지'};
const conditionText={always:'항상 표시',confirmed_fact_exists:'확정 FACT가 있을 때',approved_lifestyle_image_exists:'승인 사용장면 이미지가 있을 때',installation_or_usage_exists:'사용·설치방법이 있을 때',caution_exists:'주의사항이 있을 때',faq_fact_source_exists:'FAQ 근거가 있을 때',options_exist:'옵션이 있을 때',components_exist:'구성품이 있을 때',relations_exist:'연결 상품이 있을 때'};
function esc(v){return String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
async function api(url,opts={}){const r=await fetch(url,{credentials:'same-origin',...opts,headers:{'Content-Type':'application/json',...(opts.headers||{})}});let d={};try{d=await r.json()}catch{}if(!r.ok){const x=d.detail;throw new Error(typeof x==='string'?x:(x?.message||JSON.stringify(x)||`HTTP ${r.status}`))}return d}
async function sessionOK(){return (await fetch('/api/v1/dashboard/session',{credentials:'same-origin'})).ok}
async function init(){if(!(await sessionOK())){sessionStatus.textContent='대시보드 로그인 필요';return}sessionStatus.textContent='연결됨';const rows=await api(`/api/v1/business/workspaces?tenant_id=${tenant}`);workspace=rows.find(x=>x.slug==='commerce-ai')||rows[0];if(!workspace)return;catalog=await api('/api/v1/detail-page-template-settings/catalog');await loadTemplates()}
async function loadTemplates(selectId=null){templates=await api(`/api/v1/detail-page-template-settings?tenant_id=${tenant}&workspace_id=${encodeURIComponent(workspace.id)}&include_retired=true`);templateList.innerHTML=templates.map(t=>`<div class="template-card ${current?.id===t.id?'selected':''}" onclick="selectTemplate('${t.id}')"><div style="display:flex;gap:8px"><div class="template-title" style="flex:1">${esc(t.name)}</div><span class="badge ${t.status==='active'?'active-status':t.status}">${esc(statusText[t.status]||t.status)}</span></div><div class="meta">${esc(t.code)} · v${t.version_no}${t.workspace_id?'':' · 기존 기본 템플릿'}</div></div>`).join('')||'<div class="muted">등록된 템플릿이 없습니다.</div>';const id=selectId||(current&&templates.some(x=>x.id===current.id)?current.id:null);if(id)await selectTemplate(id)}
async function createTemplate(){const value=prompt('새 템플릿 이름을 입력하세요.','화분 기본 상세페이지');if(!value?.trim())return;const row=await api(`/api/v1/detail-page-template-settings?tenant_id=${tenant}`,{method:'POST',body:JSON.stringify({workspace_id:workspace.id,name:value.trim()})});await loadTemplates(row.id)}
async function selectTemplate(id){current=await api(`/api/v1/detail-page-template-settings/${id}?tenant_id=${tenant}`);sections=Array.isArray(current.content_rules?.sections)?structuredClone(current.content_rules.sections):[];bindings=structuredClone(current.field_bindings||{});render();templateList.querySelectorAll('.template-card').forEach((el,i)=>el.classList.toggle('selected',templates[i]?.id===id))}
function locked(){return !!current?.locked}
function render(){emptyState.classList.add('hidden');editor.classList.remove('hidden');title.textContent=current.name;templateMeta.textContent=`${current.code} · 버전 ${current.version_no} · ${statusText[current.status]||current.status}`;statusBadge.textContent=statusText[current.status]||current.status;statusBadge.className=`badge ${current.status==='active'?'active-status':current.status}`;lockNote.classList.toggle('hidden',!locked());name.value=current.name||'';code.value=current.code||'';description.value=current.description||'';canvaDesignId.value=current.canva_design_id||'';canvaBrandTemplateId.value=current.canva_brand_template_id||'';canvaEditUrl.value=current.canva_edit_url||'';categoryScope.value=(current.category_scope?.values||[]).join(', ');channelScope.value=(current.channel_scope?.values||['naver-smartstore']).join(', ');document.querySelectorAll('#editor input,#editor textarea,#editor select').forEach(x=>x.disabled=locked());saveBtn.classList.toggle('hidden',locked());validateBtn.classList.toggle('hidden',locked());publishBtn.classList.toggle('hidden',locked());newVersionBtn.classList.toggle('hidden',!locked());retireBtn.classList.toggle('hidden',current.status!=='active');addSectionBtn.classList.toggle('hidden',locked());addBindingBtn.classList.toggle('hidden',locked());renderSections();renderBindings();renderPreview()}
function renderSections(){sections.sort((a,b)=>(a.sort_order||0)-(b.sort_order||0));sectionRows.innerHTML=sections.map((s,i)=>`<div class="section-row ${s.enabled===false?'off':''}"><input type="checkbox" ${s.enabled!==false?'checked':''} ${locked()?'disabled':''} onchange="setSection(${i},'enabled',this.checked)"><div class="section-name"><strong>${esc(s.name||s.type)}</strong><small>${esc(s.type)}</small></div><label><input type="checkbox" ${s.required?'checked':''} ${locked()?'disabled':''} onchange="setSection(${i},'required',this.checked)"> 필수</label><select ${locked()?'disabled':''} onchange="setSection(${i},'condition',this.value)">${Object.entries(conditionText).map(([k,v])=>`<option value="${k}" ${s.condition===k?'selected':''}>${v}</option>`).join('')}</select><div class="move"><button ${locked()||i===0?'disabled':''} onclick="moveSection(${i},-1)">↑</button><button ${locked()||i===sections.length-1?'disabled':''} onclick="moveSection(${i},1)">↓</button></div></div>`).join('')}
function setSection(i,key,value){sections[i][key]=value;renderSections();renderPreview()}
function moveSection(i,d){const j=i+d;if(j<0||j>=sections.length)return;[sections[i],sections[j]]=[sections[j],sections[i]];sections.forEach((s,n)=>s.sort_order=(n+1)*10);renderSections();renderPreview()}
function addSection(){const used=new Set(sections.map(s=>s.type)),choices=(catalog.sections||[]).filter(x=>!used.has(x.type));if(!choices.length)return alert('추가할 섹션이 없습니다.');const answer=prompt('섹션 코드를 입력하세요.\n'+choices.map(x=>`${x.type} = ${x.name}`).join('\n'),choices[0].type);const item=choices.find(x=>x.type===String(answer||'').trim().toUpperCase());if(!item)return;sections.push({type:item.type,name:item.name,enabled:true,required:item.default_required,condition:'always',sort_order:(sections.length+1)*10});renderSections();renderPreview()}
function renderBindings(){bindingRows.innerHTML=Object.entries(bindings).map(([key,value],i)=>`<div class="binding-row"><input value="${esc(key)}" ${locked()?'disabled':''} onchange="changeBindingKey(${i},this.value)"><div class="arrow">←</div><input list="dataSources" value="${esc(value)}" ${locked()?'disabled':''} onchange="changeBindingValue('${esc(key)}',this.value)"><button class="btn danger" ${locked()?'disabled':''} onclick="removeBinding('${esc(key)}')">×</button></div>`).join('')}
function changeBindingKey(i,newKey){const entries=Object.entries(bindings),[oldKey,value]=entries[i];newKey=newKey.trim();if(!newKey||newKey===oldKey)return;delete bindings[oldKey];bindings[newKey]=value;renderBindings();renderPreview()}
function changeBindingValue(key,value){bindings[key]=value.trim();renderPreview()}function removeBinding(key){delete bindings[key];renderBindings();renderPreview()}
function addBinding(){const key=prompt('Canva 입력 자리 이름을 입력하세요.','faq.items');if(!key?.trim())return;if(bindings[key.trim()]!==undefined)return alert('이미 존재합니다.');bindings[key.trim()]='';renderBindings();renderPreview()}
function renderPreview(){const enabled=sections.filter(s=>s.enabled!==false).sort((a,b)=>(a.sort_order||0)-(b.sort_order||0));templatePreview.innerHTML=enabled.map(s=>{const count=Object.keys(bindings).filter(k=>k.toLowerCase().startsWith(String(s.type).toLowerCase()+'.')).length;return `<div class="preview-block"><strong>${esc(s.name||s.type)}</strong><span>${s.required?'필수':'선택'} · 연결 ${count}개</span></div>`}).join('')||'<div class="muted">활성화된 섹션이 없습니다.</div>'}
function validateGuideFields(){
  if(!current)return true;
  const checks=[
    [name,nameError,!name.value.trim(),'템플릿 이름을 입력하세요.'],
    [channelScope,channelError,!channelScope.value.trim(),'판매채널을 하나 이상 입력하세요.'],
    [canvaEditUrl,canvaUrlError,!!canvaEditUrl.value.trim()&&!/^https:\/\/(www\.)?canva\.com\//i.test(canvaEditUrl.value.trim()),'Canva의 https 주소를 입력하세요.'],
    [canvaDesignId,canvaIdError,/\s/.test(canvaDesignId.value.trim()),'Canva 디자인 ID에는 공백을 넣을 수 없습니다.']
  ];
  let valid=true;
  checks.forEach(([input,error,bad,message])=>{
    input.classList.toggle('input-invalid',bad);
    error.textContent=bad?message:'';
    if(bad)valid=false;
  });
  return valid;
}
function csvValues(v){return v.split(',').map(x=>x.trim()).filter(Boolean)}
function draftPayload(){const rules=structuredClone(current.content_rules||{});rules.sections=sections.map((s,i)=>({...s,sort_order:(i+1)*10}));rules.review_policy='exclude_without_verified_source';rules.faq_policy='fact_based_guidance_only';return{name:name.value.trim(),description:description.value.trim()||null,canva_design_id:canvaDesignId.value.trim()||null,canva_brand_template_id:canvaBrandTemplateId.value.trim()||null,canva_edit_url:canvaEditUrl.value.trim()||null,content_rules:rules,field_bindings:bindings,category_scope:{mode:categoryScope.value.trim()?'selected':'all',values:csvValues(categoryScope.value)},channel_scope:{mode:'selected',values:csvValues(channelScope.value)}}}
async function saveDraft(){if(!validateGuideFields())return alert('빨간색으로 표시된 입력항목을 먼저 확인하세요.');try{saveBtn.disabled=true;saveBtn.textContent='저장 중...';current=await api(`/api/v1/detail-page-template-settings/${current.id}?tenant_id=${tenant}`,{method:'PUT',body:JSON.stringify(draftPayload())});validationResult.innerHTML='<span class="ok">임시저장 완료</span>';await loadTemplates(current.id)}catch(e){alert(e.message)}finally{saveBtn.disabled=false;saveBtn.textContent='임시저장'}}
async function validateTemplate(){try{await saveDraft();const d=await api(`/api/v1/detail-page-template-settings/${current.id}/validate?tenant_id=${tenant}`,{method:'POST',body:'{}'});validationResult.innerHTML=`<div class="${d.valid?'ok':'fail'}"><strong>${d.valid?'통과':'수정 필요'}</strong></div>`+(d.errors||[]).map(x=>`<div class="fail">• ${esc(x)}</div>`).join('')+(d.warnings||[]).map(x=>`<div class="warn">• ${esc(x)}</div>`).join('')+`<div class="muted">활성 섹션 ${d.enabled_section_count}개 · 요소 연결 ${d.binding_count}개</div>`;current=await api(`/api/v1/detail-page-template-settings/${current.id}?tenant_id=${tenant}`);render()}catch(e){alert(e.message)}}
async function publishTemplate(){if(!confirm('이 템플릿을 확정하시겠습니까?\n확정 후에는 새 버전으로만 수정할 수 있습니다.'))return;try{await saveDraft();current=await api(`/api/v1/detail-page-template-settings/${current.id}/publish?tenant_id=${tenant}`,{method:'POST',body:'{}'});validationResult.innerHTML='<span class="ok"><strong>템플릿 확정 완료</strong></span>';await loadTemplates(current.id)}catch(e){alert(e.message)}}
async function newVersion(){const row=await api(`/api/v1/detail-page-template-settings/${current.id}/new-version?tenant_id=${tenant}`,{method:'POST',body:'{}'});await loadTemplates(row.id)}
async function retireTemplate(){if(!confirm('이 템플릿을 사용 중지하시겠습니까?'))return;current=await api(`/api/v1/detail-page-template-settings/${current.id}/retire?tenant_id=${tenant}`,{method:'POST',body:'{}'});await loadTemplates(current.id)}
function openCanva(){const url=canvaEditUrl.value.trim();if(!url)return alert('Canva 편집 링크가 없습니다.');window.open(url,'_blank','noopener')}
init().catch(e=>{sessionStatus.textContent='오류';alert(e.message)});
</script>
</body>
</html>'''


@router.get("/detail-page-templates", response_class=HTMLResponse)
def detail_page_template_settings_ui():
    return HTMLResponse(HTML)
