from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

HTML = r'''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI 이미지 생성 | AI Business OS</title>
<style>
*{box-sizing:border-box}body{margin:0;font-family:Inter,Pretendard,system-ui,sans-serif;background:#f5f7fb;color:#142033}
.top{height:64px;background:#fff;border-bottom:1px solid #e6eaf0;display:flex;align-items:center;padding:0 24px;gap:18px;position:sticky;top:0;z-index:5}.brand{font-weight:900}.back{color:#64748b;text-decoration:none}.status{margin-left:auto;font-size:13px;color:#64748b}
.shell{display:grid;grid-template-columns:340px 1fr;min-height:calc(100vh - 64px)}.side{background:#fff;border-right:1px solid #e6eaf0;padding:20px;overflow:auto}.main{padding:24px;overflow:auto}
h1{font-size:24px;margin:0 0 6px}.muted{color:#718096;font-size:13px}.section{border-top:1px solid #edf0f4;padding-top:16px;margin-top:16px}.label{font-size:12px;font-weight:800;color:#64748b;margin-bottom:6px}
select,input,textarea{width:100%;border:1px solid #d9e0ea;border-radius:10px;padding:10px 11px;background:#fff;color:#142033}textarea{min-height:92px;resize:vertical}.grid2{display:grid;grid-template-columns:1fr 1fr;gap:8px}.btn{border:0;border-radius:10px;padding:11px 14px;font-weight:800;cursor:pointer}.primary{background:#3559e0;color:#fff}.ghost{background:#eef2ff;color:#273c9f}.danger{background:#fff0f0;color:#b42318}.btn:disabled{opacity:.45;cursor:not-allowed}
.card{background:#fff;border:1px solid #e2e7ef;border-radius:16px;padding:18px;box-shadow:0 4px 18px rgba(30,45,70,.04)}.preview{min-height:560px;display:grid;place-items:center;background:#f8fafc;border:1px dashed #cbd5e1;border-radius:14px;overflow:hidden}.preview img{max-width:100%;max-height:72vh;display:block}.empty{text-align:center;color:#94a3b8}.pills{display:flex;gap:8px;flex-wrap:wrap}.pill{font-size:12px;padding:6px 9px;border-radius:999px;background:#eef2ff;color:#3347a0}.lock{background:#e8f7ee;color:#1b6b3a}.jobs{display:grid;gap:8px}.job{border:1px solid #e1e6ee;border-radius:12px;padding:11px;cursor:pointer;background:#fff}.job.active{border-color:#3559e0;background:#f3f6ff}.job strong{display:block}.actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}.qa{margin-top:14px}.qa div{padding:8px 0;border-bottom:1px solid #edf0f4;font-size:13px}.revision-history{display:grid;gap:7px;margin-top:9px}.asset-versions{display:flex;gap:7px;flex-wrap:wrap;margin:10px 0}.version-btn{border:1px solid #d8dfeb;background:#fff;color:#44516a;border-radius:9px;padding:7px 10px;font-size:12px;font-weight:800;cursor:pointer}.version-btn.active{border-color:#3559e0;background:#eef2ff;color:#273c9f}.revision-item{background:#f8fafc;border:1px solid #e2e8f0;border-radius:9px;padding:9px;font-size:12px;line-height:1.45}.ok{color:#16803a}.warn{color:#a15c00}.bad{color:#b42318}.login{display:flex;gap:8px;margin-bottom:14px}.login input{max-width:330px}@media(max-width:900px){.shell{grid-template-columns:1fr}.side{border-right:0;border-bottom:1px solid #e6eaf0}.preview{min-height:380px}}
</style></head>
<body>
<div class="top"><a class="back" href="/dashboard">← 대시보드</a><div class="brand">AI Business OS · AI 이미지 생성</div><div class="status" id="sessionStatus">연결 확인 중</div></div>
<div class="shell">
<aside class="side">
  <div class="login" id="loginBox"><input id="token" type="password" placeholder="처음 접속 시 Bearer token"><button class="btn primary" onclick="connect()">연결</button></div>
  <h1>새 이미지 만들기</h1><div class="muted">상품 기준사진을 보호하면서 P0 → P1 → FINAL 순서로 생성합니다.</div>
  <div class="section"><div class="label">상품</div><select id="product" onchange="loadSkus()"></select><div class="label" style="margin-top:9px">SKU</div><select id="sku"><option value="">전체 상품</option></select></div>
  <div class="section grid2"><div><div class="label">이미지 유형</div><select id="imageType"><option value="HERO">대표 이미지</option><option value="LIFESTYLE" selected>라이프스타일</option><option value="EXPLANATION">설명 이미지</option><option value="BANNER">배너</option><option value="SPEC_SIZE">스펙·사이즈</option></select></div><div><div class="label">스타일</div><select id="style"><option value="PRODUCT_PHOTO">제품 실사</option><option value="LIFESTYLE_PHOTO" selected>라이프스타일 실사</option><option value="ADVERTISING">광고컷</option><option value="WHITE_BACKGROUND">누끼/화이트</option><option value="THREE_D">3D</option><option value="TECHNICAL_LINE_DRAWING">프로덕트 라인드로잉</option></select></div></div>
  <div class="section grid2"><div><div class="label">사용 용도</div><select id="usage"><option value="DETAIL_PAGE" selected>상세페이지</option><option value="SMARTSTORE">스마트스토어</option><option value="SNS">SNS</option><option value="AD_BANNER">광고/배너</option><option value="BROCHURE">브로슈어</option><option value="CATALOG">카탈로그</option><option value="LEAFLET">리플릿</option><option value="USER_MANUAL">사용설명서</option><option value="PRODUCT_GUIDE">제품소개서</option><option value="PACKAGE_INSERT">패키지 삽입물</option></select></div><div><div class="label">이미지 비율</div><select id="ratio"><option>1:1</option><option selected>4:3</option><option>3:4</option><option>16:9</option><option>9:16</option><option value="ORIGINAL">원본 유지</option><option value="CUSTOM">사용자 지정</option></select></div></div>
  <div class="section"><div class="label">제품보존</div><select id="protection"><option value="hard_lock" selected>🔒 HARD LOCK — 기본</option><option value="guided">GUIDED — 제한적 변형</option><option value="creative">CREATIVE — 예외</option></select><div class="muted" style="margin-top:6px">판매상품은 HARD LOCK을 기본으로 사용합니다.</div></div>
  <div class="section"><div class="label">요청사항</div><textarea id="request">일반적인 아파트 베란다 환경에서 실제 상품 형태와 부속품 구조를 유지한 자연스러운 사용 장면. 제품 구성과 연결 방식은 기준사진과 동일하게 유지.</textarea></div>
  <div class="section"><button class="btn primary" style="width:100%" onclick="createJob()">작업 만들기</button></div>
  <div class="section"><div class="label">최근 작업</div><div class="jobs" id="jobs"></div></div>
</aside>
<main class="main">
  <div class="card">
    <div style="display:flex;justify-content:space-between;gap:12px;align-items:start"><div><h1 id="title">P1 Preview</h1><div class="muted" id="meta">작업을 만들고 기준사진을 추가하세요.</div></div><div class="pills"><span class="pill lock">🔒 제품보존</span><span class="pill" id="statusPill">DRAFT</span></div></div>
    <div class="section" id="p0Box" style="display:none"><div class="label">P0 설정 미리보기</div><div id="p0" style="white-space:pre-wrap;line-height:1.6"></div></div>
    <div class="section"><div class="label">상품 기준사진 / 부속품 기준사진</div><input id="refFiles" type="file" accept="image/*" multiple onchange="onRefFilesChanged()"><div class="grid2" style="margin-top:8px"><select id="refRole"><option value="PRODUCT_REFERENCE">자사 상품사진</option><option value="COMPONENT_REFERENCE">부속품 기준사진</option><option value="MANUFACTURER_REFERENCE">제조사 자료</option><option value="STYLE_REFERENCE">스타일 참고</option><option value="EXTERNAL_REFERENCE">타사/외부 참고</option></select><button class="btn ghost" id="uploadRefsBtn" onclick="uploadRefs()">선택 파일 업로드</button></div><div class="muted" id="refStatus" style="margin-top:7px"></div></div>
    <div class="asset-versions" id="assetVersions" style="display:none"></div>
    <div class="section preview" id="preview"><div class="empty"><strong>아직 생성된 이미지가 없습니다.</strong><br><br>P0 설정 확인 후 P1 Preview를 생성하세요.</div></div>
    <div class="actions"><button id="prepareBtn" class="btn ghost" onclick="prepare()">P0 설정 확인</button><button id="previewBtn" class="btn primary" onclick="generatePreview()">P1 프리뷰 생성</button><button id="approveBtn" class="btn ghost" onclick="approveCurrent()">현재 이미지 승인</button><button id="finalBtn" class="btn primary" onclick="finalize()">이 구성으로 FINAL 생성</button><span id="finalStatus" class="muted"></span></div>
    <div class="section"><div class="label">최초 요청사항</div><div id="originalBrief" style="white-space:pre-wrap;line-height:1.5;font-size:13px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:9px;padding:10px"></div></div>
    <div class="section"><div class="label">수정 요청</div><div style="display:flex;gap:8px"><input id="revision" placeholder="예: 기준사진에 없는 연결구는 제거하고 실제 T형 연결구만 유지"><button class="btn ghost" onclick="revise()">수정 요청 저장</button></div><div class="muted" id="revisionStatus" style="margin-top:7px">원래 요청은 유지되고 수정 요청만 버전별로 누적됩니다.</div><div class="revision-history" id="revisionHistory"></div></div>
    <div class="qa" id="qa"></div>
  </div>
</main></div>
<script>
const tenant="__legacy__";
let workspace=null, products=[], currentJob=null, currentAsset=null, selectedAssetId=null, busy=false, finalPollJobId=null, finalPollTimer=null;
const el=(id)=>document.getElementById(id);
function escapeHtml(v){return String(v??'').replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]||c))}

async function readResponse(r){
  const text=await r.text();
  if(!text) return {};
  try{return JSON.parse(text)}catch{return {detail:text}}
}
async function jsonFetch(url,opts={}){
  const r=await fetch(url,{credentials:"same-origin",...opts,headers:{"Content-Type":"application/json",...(opts.headers||{})}});
  const d=await readResponse(r);
  if(!r.ok) throw new Error(d.detail||d.message||`HTTP ${r.status}`);
  return d;
}
function setBusy(v,msg=''){
  busy=v;
  if(msg) el('refStatus').textContent=msg;
  updateControls();
}
function fileSummary(){
  const files=[...el('refFiles').files];
  if(!files.length) return '';
  const total=files.reduce((n,f)=>n+f.size,0)/(1024*1024);
  return `${files.length}개 선택 · 총 ${total.toFixed(1)}MB`;
}
function onRefFilesChanged(){
  const summary=fileSummary();
  el('refStatus').textContent=summary ? `${summary} · 업로드 버튼을 누르세요.` : '파일을 선택해 주세요.';
  updateControls();
}
function updateControls(){
  const hasFiles=el('refFiles').files && el('refFiles').files.length>0;
  el('uploadRefsBtn').disabled=busy || !hasFiles || !workspace || !el('product').value;
  const status=currentJob?.status||'';
  const finalBusy=['final_queued','final_generating'].includes(status);
  const hasApprovedPreview=(currentJob?.assets||[]).some(a=>a.stage==='preview'&&a.status==='approved');
  const hasFinal=(currentJob?.assets||[]).some(a=>a.stage==='final');
  if(el('finalBtn')) el('finalBtn').disabled=busy || finalBusy || !hasApprovedPreview || hasFinal;
  if(el('previewBtn')) el('previewBtn').disabled=busy || finalBusy;
  if(el('approveBtn')) el('approveBtn').disabled=busy || finalBusy || !currentAsset;
  if(el('finalStatus')){
    el('finalStatus').textContent=status==='final_queued'?'FINAL 생성 대기 중…':status==='final_generating'?'FINAL 생성 중… 다른 작업을 하셔도 됩니다.':'';
  }
}
async function sessionOK(){
  try{return (await fetch('/api/v1/dashboard/session',{credentials:'same-origin'})).ok}catch{return false}
}
async function connect(){
  try{
    const token=el('token').value.trim();
    if(token){
      const r=await fetch('/api/v1/dashboard/session',{method:'POST',credentials:'same-origin',headers:{Authorization:`Bearer ${token}`}});
      if(!r.ok){alert('인증 실패');return}
    }
    await init();
  }catch(e){alert(`연결 실패: ${e.message||e}`)}
}
async function init(){
  if(!(await sessionOK())){el('sessionStatus').textContent='로그인 필요';return}
  el('loginBox').style.display='none';
  el('sessionStatus').textContent='Connected';
  const ws=await jsonFetch(`/api/v1/business/workspaces?tenant_id=${tenant}`);
  workspace=ws.find(x=>x.slug==='commerce-ai')||ws[0];
  if(!workspace){el('meta').textContent='사용 가능한 Workspace가 없습니다.';return}
  products=await jsonFetch(`/api/v1/business/products?tenant_id=${tenant}&workspace_id=${workspace.id}`);
  el('product').innerHTML=products.map(x=>`<option value="${x.id}">${x.name}</option>`).join('');
  if(!products.length){el('meta').textContent='등록된 상품이 없습니다.';return}
  const requestedProduct=new URLSearchParams(location.search).get('product_id');
  if(requestedProduct&&products.some(x=>x.id===requestedProduct)){
    el('product').value=requestedProduct;
  }
  el('product').onchange=()=>{
    const selected=el('product').value;
    location.href=`/image-studio?product_id=${encodeURIComponent(selected)}`;
  };
  await loadSkus();
  await loadConfirmedImagePlans();
  const rows=await loadJobs();
  if(!currentJob && rows && rows.length){await openJob(rows[0].id);}
  updateControls();
}
async function loadSkus(){
  const pid=el('product').value;
  if(!pid)return;
  const rows=await jsonFetch(`/api/v1/business/skus?tenant_id=${tenant}&product_id=${pid}`);
  el('sku').innerHTML='<option value="">전체 상품</option>'+rows.map(x=>`<option value="${x.id}">${x.option_value||x.name}</option>`).join('');
}

let confirmedImagePlans=[];

function ensureImagePlanPanel(){
  if(el('confirmedPlanPanel'))return;
  const createButton=document.querySelector('button[onclick="createJob()"]');
  const createSection=createButton?.closest('.section');
  if(!createSection)return;

  const panel=document.createElement('div');
  panel.id='confirmedPlanPanel';
  panel.className='section';
  panel.innerHTML=`
    <div class="label">확정 이미지 기획</div>
    <select id="confirmedPlanSelect" onchange="applyConfirmedImagePlan(this.value)">
      <option value="">기획을 선택하세요</option>
    </select>
    <div id="confirmedPlanStatus" class="muted" style="margin-top:7px;line-height:1.5">
      상품등록에서 확정한 이미지 기획을 불러옵니다.
    </div>`;
  createSection.parentNode.insertBefore(panel,createSection);
}

function applyConfirmedImagePlan(indexValue){
  if(indexValue==='')return;
  const item=confirmedImagePlans[Number(indexValue)];
  if(!item)return;

  const typeMap={
    hero:'HERO',
    use_scene:'LIFESTYLE',
    feature_focus:'FEATURE',
    detail:'DETAIL',
    simple_usage_flow:'EXPLANATION',
    line_drawing:'SPEC_SIZE',
    components:'COMPONENTS',
    extra:'LIFESTYLE'
  };

  const wantedType=typeMap[item.category]||'LIFESTYLE';
  const imageType=el('imageType');
  if(imageType&&[...imageType.options].some(option=>option.value===wantedType)){
    imageType.value=wantedType;
  }

  const protection=el('protection');
  if(protection&&[...protection.options].some(option=>option.value==='hard_lock')){
    protection.value='hard_lock';
  }

  const basis=(item.basis||[]).join(' · ');
  const request=[
    item.title,
    item.purpose?`목적: ${item.purpose}`:'',
    basis?`확정 근거: ${basis}`:'',
    item.execution?`실행 방식: ${item.execution}`:'',
    item.required_reference?`추가 기준 이미지 필요: ${item.required_reference}`:'',
    '상품 외형·재질·색상·부품은 Product Image FACT를 변경하지 않습니다.'
  ].filter(Boolean).join('\n');

  el('request').value=request;
  el('confirmedPlanStatus').innerHTML=
    `<strong>${escapeHtml(item.category_label||item.category)}</strong><br>`+
    `${escapeHtml(item.title||'')}<br>`+
    `<span class="muted">기획 내용을 작업 요청에 적용했습니다. 기준사진을 확인한 뒤 작업을 만드세요.</span>`;
}

async function loadConfirmedImagePlans(){
  ensureImagePlanPanel();
  const productId=el('product').value;
  if(!productId)return;

  const select=el('confirmedPlanSelect');
  const status=el('confirmedPlanStatus');

  try{
    const data=await jsonFetch(
      `/api/v1/product-registration/products/${productId}/image-plans?tenant_id=${tenant}`
    );
    confirmedImagePlans=data.plans||[];
    select.innerHTML='<option value="">기획을 선택하세요</option>'+
      confirmedImagePlans.map((item,index)=>
        `<option value="${index}">${escapeHtml(item.category_label||item.category)} · ${escapeHtml(item.title||'')}</option>`
      ).join('');

    status.textContent=confirmedImagePlans.length
      ? `확정 이미지 기획 ${confirmedImagePlans.length}개 · 제작할 기획을 선택하세요.`
      : '이 상품에 확정된 이미지 기획이 없습니다. 상품등록에서 먼저 기획을 확정하세요.';
  }catch(error){
    confirmedImagePlans=[];
    select.innerHTML='<option value="">기획을 선택하세요</option>';
    status.textContent=`이미지 기획 불러오기 실패: ${error.message||error}`;
  }
}

async function loadJobs(){
  const productId=el('product').value;
  if(!productId){el('jobs').innerHTML='';return []}
  const rows=await jsonFetch(`/api/v1/images/jobs?tenant_id=${tenant}&product_id=${encodeURIComponent(productId)}`);
  el('jobs').innerHTML=rows.length
    ? rows.slice(0,12).map(x=>`<div class="job ${currentJob&&x.id===currentJob.id?'active':''}" onclick="openJob('${x.id}')"><strong>${products.find(p=>p.id===x.product_id)?.name||x.product_id}</strong><span class="muted">${x.image_type} · ${x.aspect_ratio} · ${x.status}</span></div>`).join('')
    : '<div class="muted" style="padding:10px">이 상품의 이미지 작업이 아직 없습니다.</div>';
  return rows;
}
async function createJob({silent=false}={}){
  if(!workspace||!el('product').value){
    if(!silent) alert('상품을 먼저 선택해 주세요.');
    return null;
  }
  try{
    const body={workspace_id:workspace.id,product_id:el('product').value,sku_id:el('sku').value||null,image_type:el('imageType').value,style_preset:el('style').value,usage_context:el('usage').value,aspect_ratio:el('ratio').value,protection_mode:el('protection').value,request_text:el('request').value};
    currentJob=await jsonFetch(`/api/v1/images/jobs?tenant_id=${tenant}`,{method:'POST',body:JSON.stringify(body)});
    renderJob(currentJob);
    await loadJobs();
    if(!silent) el('refStatus').textContent='작업이 생성되었습니다. 기준사진을 선택해 업로드해 주세요.';
    return currentJob;
  }catch(e){
    alert(`작업 생성 실패: ${e.message||e}`);
    return null;
  }
}
async function ensureJob(){
  if(currentJob&&currentJob.product_id===el('product').value)return currentJob;
  currentJob=null;
  currentAsset=null;
  selectedAssetId=null;
  return await createJob({silent:true});
}
async function openJob(id){
  const opened=await jsonFetch(`/api/v1/images/jobs/${id}?tenant_id=${tenant}`);
  if(opened.product_id!==el('product').value){
    alert('현재 선택한 상품과 다른 이미지 작업은 열 수 없습니다.');
    return;
  }
  if(!currentJob||currentJob.id!==id)selectedAssetId=null;
  currentJob=opened;
  renderJob(currentJob);
  await loadJobs();
}
function assetLabel(a){return `${a.stage==='final'?'FINAL':'P1'} V${a.version_no}`}
function renderAssetVersions(assets){
  const box=el('assetVersions');
  if(!assets.length){box.style.display='none';box.innerHTML='';return}
  box.style.display='flex';
  box.innerHTML=assets.map(a=>`<button class="version-btn ${currentAsset&&a.id===currentAsset.id?'active':''}" onclick="selectAsset('${a.id}')">${assetLabel(a)} · ${escapeHtml(a.status)}</button>`).join('');
}
function selectAsset(assetId){
  if(!currentJob)return;
  const asset=(currentJob.assets||[]).find(a=>a.id===assetId);
  if(!asset)return;
  selectedAssetId=asset.id; currentAsset=asset;
  renderAssetVersions(currentJob.assets||[]);
  el('title').textContent=`${assetLabel(asset)} · ${asset.status==='approved'?'승인됨':'검토'}`;
  el('preview').innerHTML=`<img src="${asset.content_url}" alt="${assetLabel(asset)}">`;
  runQA(asset.id);
}
function renderJob(j){
  el('statusPill').textContent=j.status.toUpperCase();
  el('meta').textContent=`${j.image_type} · ${j.style_preset} · ${j.usage_context} · ${j.aspect_ratio}`;
  el('p0Box').style.display=j.p0_summary?'block':'none';
  el('p0').textContent=j.p0_summary||'';
  el('originalBrief').textContent=j.original_request_text||j.request_text||'(최초 요청사항 없음)';
  const revisions=j.revisions||[];
  el('revisionHistory').innerHTML=revisions.length?revisions.map((r,i)=>`<div class="revision-item"><strong>수정 V${i+2}</strong><br>${escapeHtml(r.instruction||'')}</div>`).join(''):'<div class="muted">아직 수정 요청이 없습니다.</div>';
  const assets=j.assets||[];
  let chosen=selectedAssetId?assets.find(a=>a.id===selectedAssetId):null;
  if(!chosen) chosen=[...assets].reverse().find(a=>a.stage==='final')||[...assets].reverse().find(a=>a.stage==='preview');
  currentAsset=chosen||null; selectedAssetId=currentAsset?.id||null;
  renderAssetVersions(assets);
  if(currentAsset){
    el('title').textContent=`${assetLabel(currentAsset)} · ${currentAsset.status==='approved'?'승인됨':'검토'}`;
    el('preview').innerHTML=`<img src="${currentAsset.content_url}" alt="${assetLabel(currentAsset)}">`;
    runQA(currentAsset.id);
  }else{
    el('title').textContent=j.p0_summary?'P1 Preview 준비':'P0 설정 확인';
    el('preview').innerHTML='<div class="empty"><strong>아직 생성된 이미지가 없습니다.</strong><br><br>기준사진 업로드 → P0 설정 확인 → P1 Preview 순서로 진행하세요.</div>';
  }
  const count=j.references?.length||0;
  if(!el('refFiles').files.length) el('refStatus').textContent=`등록된 기준/참고 이미지 ${count}장`;
  updateControls();
  if(['final_queued','final_generating'].includes(j.status)) startFinalPolling(j.id);
}
async function uploadRefs(){
  if(busy)return;
  const files=[...el('refFiles').files];
  if(!files.length){
    el('refStatus').textContent='먼저 [파일 선택]에서 사진을 선택해 주세요.';
    alert('업로드할 사진을 먼저 선택해 주세요.');
    return;
  }
  for(const f of files){
    if(!f.type.startsWith('image/')){alert(`${f.name}: 이미지 파일만 업로드할 수 있습니다.`);return}
    if(f.size>45*1024*1024){alert(`${f.name}: 파일이 너무 큽니다. 45MB 이하 이미지를 사용해 주세요.`);return}
  }
  const job=await ensureJob();
  if(!job){return}
  setBusy(true,`업로드 준비 중 · ${fileSummary()}`);
  try{
    let done=0;
    for(const f of files){
      el('refStatus').textContent=`업로드 중 ${done+1}/${files.length} · ${f.name} (${(f.size/1024/1024).toFixed(1)}MB)`;
      const fd=new FormData();
      fd.append('product_id',currentJob.product_id);
      fd.append('asset_role',el('refRole').value);
      fd.append('lock_level',el('refRole').value==='EXTERNAL_REFERENCE'?'creative':'hard_lock');
      fd.append('internal_reference_only',el('refRole').value==='EXTERNAL_REFERENCE'?'true':'false');
      fd.append('file',f);
      let r;
      try{
        r=await fetch(`/api/v1/images/jobs/${currentJob.id}/references/upload?tenant_id=${tenant}`,{method:'POST',credentials:'same-origin',body:fd});
      }catch(networkErr){
        throw new Error(`네트워크 업로드 실패: ${networkErr.message||networkErr}`);
      }
      const d=await readResponse(r);
      if(!r.ok){
        const hint=r.status===413?'서버 업로드 용량 제한을 초과했습니다.':r.status===401||r.status===403?'로그인 세션이 만료되었습니다. 다시 연결해 주세요.':'';
        throw new Error(`${d.detail||`HTTP ${r.status}`} ${hint}`.trim());
      }
      done++;
    }
    el('refFiles').value='';
    await openJob(currentJob.id);
    el('refStatus').textContent=`업로드 완료 · ${files.length}장 추가됨 · 총 ${currentJob.references?.length||0}장`;
  }catch(e){
    el('refStatus').textContent=`업로드 실패 · ${e.message||e}`;
    alert(`기준사진 업로드 실패\n\n${e.message||e}`);
  }finally{
    setBusy(false);
  }
}
async function prepare(){
  try{
    const job=await ensureJob();
    if(!job)return;
    currentJob=await jsonFetch(`/api/v1/images/jobs/${currentJob.id}/prepare?tenant_id=${tenant}`,{method:'POST',body:'{}'});
    renderJob(currentJob);
  }catch(e){alert(`P0 설정 확인 실패: ${e.message||e}`)}
}
async function generatePreview(){
  try{
    const job=await ensureJob();
    if(!job)return;
    if(!currentJob.p0_summary){await prepare();if(!currentJob?.p0_summary)return}
    if(currentJob.protection_mode==='hard_lock' && !(currentJob.references||[]).some(r=>['PRODUCT_REFERENCE','COMPONENT_REFERENCE'].includes(r.asset_role))){
      alert('HARD LOCK 상품은 자사 상품사진 또는 부속품 기준사진을 먼저 업로드해 주세요.');
      return;
    }
    const d=await jsonFetch(`/api/v1/images/jobs/${currentJob.id}/preview?tenant_id=${tenant}`,{method:'POST',body:'{}'});
    currentJob=d.job; selectedAssetId=d.asset_id||null; renderJob(currentJob); await loadJobs();
  }catch(e){alert(`P1 프리뷰 생성 실패: ${e.message||e}`)}
}
async function runQA(assetId){
  try{
    const rows=await jsonFetch(`/api/v1/images/assets/${assetId}/qa?tenant_id=${tenant}`,{method:'POST',body:'{}'});
    el('qa').innerHTML='<div class="label">Image QA</div>'+rows.map(x=>`<div class="${x.status==='PASS'?'ok':x.status==='FAIL'?'bad':'warn'}"><strong>${x.status}</strong> · ${x.message}</div>`).join('');
  }catch(e){el('qa').innerHTML=''}
}
async function approveCurrent(){
  if(!currentAsset){alert('승인할 이미지가 없습니다.');return}
  try{currentJob=await jsonFetch(`/api/v1/images/assets/${currentAsset.id}/approve?tenant_id=${tenant}`,{method:'POST',body:JSON.stringify({acknowledge_review:true})});renderJob(currentJob);await loadJobs()}catch(e){alert(e.message)}
}
function stopFinalPolling(){
  if(finalPollTimer){clearTimeout(finalPollTimer);finalPollTimer=null}
  finalPollJobId=null;
}
function startFinalPolling(jobId){
  if(finalPollJobId===jobId && finalPollTimer)return;
  stopFinalPolling();
  finalPollJobId=jobId;
  const tick=async()=>{
    try{
      const job=await jsonFetch(`/api/v1/images/jobs/${jobId}?tenant_id=${tenant}`);
      if(currentJob?.id===jobId){currentJob=job;renderJob(job);await loadJobs()}
      if(['final_review','approved'].includes(job.status)){
        stopFinalPolling();
        const finals=(job.assets||[]).filter(a=>a.stage==='final');
        if(finals.length && currentJob?.id===jobId){selectAsset(finals[finals.length-1].id)}
        return;
      }
      if(job.status==='failed'){stopFinalPolling();alert('FINAL 생성이 실패했습니다. 작업 상태와 서버 로그를 확인해 주세요.');return}
    }catch(e){console.warn('FINAL status poll failed',e)}
    finalPollTimer=setTimeout(tick,2500);
  };
  finalPollTimer=setTimeout(tick,800);
}
async function finalize(){
  if(!currentJob){alert('먼저 작업을 만들어 주세요.');return}
  if(['final_queued','final_generating'].includes(currentJob.status)){startFinalPolling(currentJob.id);return}
  if((currentJob.assets||[]).some(a=>a.stage==='final')){alert('이미 FINAL 결과가 있습니다. 새 FINAL을 중복 생성하지 않습니다.');return}
  try{
    const d=await jsonFetch(`/api/v1/images/jobs/${currentJob.id}/finalize?tenant_id=${tenant}`,{method:'POST',body:'{}'});
    currentJob=d.job;renderJob(currentJob);await loadJobs();
    if(d.already_exists && d.asset_id){selectAsset(d.asset_id);return}
    startFinalPolling(currentJob.id);
  }catch(e){alert(`FINAL 생성 요청 실패: ${e.message||e}`)}
}
async function revise(){
  if(!currentJob||!el('revision').value.trim()){alert('수정 요청 내용을 입력해 주세요.');return}
  const instruction=el('revision').value.trim();
  try{
    currentJob=await jsonFetch(`/api/v1/images/jobs/${currentJob.id}/revision?tenant_id=${tenant}`,{method:'POST',body:JSON.stringify({instruction})});
    el('revision').value='';
    el('revisionStatus').textContent='수정 요청이 저장되었습니다. 원래 요청은 유지됩니다. [P1 프리뷰 생성]을 눌러 다음 버전을 만드세요.';
    renderJob(currentJob);
    await loadJobs();
  }catch(e){alert(`수정 요청 실패: ${e.message||e}`)}
}
init().catch(e=>{el('sessionStatus').textContent='연결 오류';console.error(e)});
</script></body></html>'''

@router.get("/image-studio", response_class=HTMLResponse)
def image_studio():
    return HTMLResponse(HTML)
