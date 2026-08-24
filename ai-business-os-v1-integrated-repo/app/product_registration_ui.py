from fastapi import APIRouter
from fastapi.responses import HTMLResponse


router = APIRouter()


HTML = r"""
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>새 상품 등록 · AI Business OS</title>
<style>
*{box-sizing:border-box} body{margin:0;font-family:Inter,Pretendard,"Noto Sans KR",system-ui,sans-serif;background:#f4f6fa;color:#172033}
.side{position:fixed;inset:0 auto 0 0;width:220px;background:#14243b;color:#dbe5f2;padding:22px 14px;z-index:5}.brand{font-size:18px;font-weight:800;padding:0 10px 22px}.side a{display:block;color:#dbe5f2;padding:10px;border-radius:9px;margin:3px 0}.side a:hover,.side a.active{background:#2763dc;color:#fff}.nav-label{font-size:11px;color:#8498b4;padding:18px 10px 6px}
.wrap{max-width:1280px;margin-left:220px;padding:28px}.top{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:20px}
a{color:#52637a;text-decoration:none}.card{background:#fff;border:1px solid #dfe5ee;border-radius:14px;padding:20px;margin-bottom:16px;box-shadow:0 2px 8px rgba(23,32,51,.035)}
h1,h2{margin:0 0 12px}.muted{color:#8ea0b7;font-size:13px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.field{display:flex;flex-direction:column;gap:6px}.full{grid-column:1/-1}
input,textarea,select{width:100%;padding:11px 12px;border-radius:9px;border:1px solid #cbd5e1;background:#fff;color:#172033}textarea{min-height:84px;resize:vertical}
button{padding:11px 16px;border-radius:9px;border:1px solid #2763dc;background:#2763dc;color:#fff;font-weight:800;cursor:pointer}.secondary{background:#edf3ff;color:#1f55b5;border:1px solid #cfddfa}.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}.step{display:inline-block;padding:5px 9px;background:#edf3ff;color:#1f55b5;border-radius:999px;font-size:12px;font-weight:800;margin-bottom:10px}.hidden{display:none}.status{margin-top:10px;font-size:13px;color:#65748a}.suggestion{padding:12px 0;border-bottom:1px solid #e5eaf1}.suggestion:last-child{border-bottom:0}.ok{color:#226746}.warn{color:#8a6111}.guide{margin:10px 0;padding:11px;border-radius:9px;background:#fff8e8;color:#74530d;border:1px solid #f1ddb1;font-size:13px}
@media(max-width:900px){.side{display:none}.wrap{margin:0;padding:18px}.grid{grid-template-columns:1fr}.full{grid-column:auto}}
</style>
</head>
<body>
<aside class="side"><div class="brand">AI Business OS</div><a href="/business-home">홈</a><div class="nav-label">공통 제작도구</div><a class="active" href="/product-registration">상품 기본정보 등록</a><a href="/image-assets">이미지 요소 자산</a><a href="/content-copy-studio">콘텐츠 문안</a><a href="/template-maker">템플릿 제작</a><a href="/detail-page-builder">상세페이지 생성</a><div class="nav-label">보조·관리</div><a href="/image-studio">기존 이미지 생성기</a><a href="/dashboard">기존 운영화면</a></aside>
<div class="wrap">
  <div class="top">
    <div><h1>새 상품 등록</h1><div class="muted">사용자는 확정 FACT만 입력하고, 나머지는 AI가 제안합니다.</div></div>
    <a href="/business-home">← 전체 홈</a>
  </div>

  <section class="card" id="factCard">
    <div class="step">1 · 기본 FACT</div>
    <h2>상품 자체의 확정값</h2>
    <div class="muted">모르는 값은 비워둘 수 있습니다. AI가 물리적 사실을 임의로 채우지 않습니다.</div>
    <div class="guide">직접 확인한 값만 입력하세요. 빈 항목은 오류가 아니며, AI 제안으로 채운 내용은 별도의 2차 FACT 후보로 관리됩니다.</div>
    <div class="grid" style="margin-top:16px">
      <div class="field full"><label>Workspace</label><select id="workspace"></select></div>
      <div class="field"><label>품명 *</label><input id="name" placeholder="예: 8mm 자동 관수키트"></div>
      <div class="field"><label>상품코드 *</label><input id="productCode" placeholder="예: IRRIGATION-8MM-KIT"></div>
      <div class="field"><label>모델명</label><input id="modelName"></div>
      <div class="field"><label>제조사</label><input id="manufacturer"></div>
      <div class="field"><label>주재질</label><input id="primaryMaterial"></div>
      <div class="field"><label>보조재질</label><input id="secondaryMaterial"></div>
      <div class="field"><label>중량</label><input id="weight" placeholder="예: 1.2 kg"></div>
      <div class="field"><label>원산지</label><input id="origin"></div>
      <div class="field"><label>길이</label><input id="length" placeholder="단위 포함 가능"></div>
      <div class="field"><label>폭</label><input id="width"></div>
      <div class="field"><label>높이</label><input id="height"></div>
      <div class="field"><label>인증 관련</label><input id="certifications" placeholder="여러 개면 쉼표로 구분"></div>
      <div class="field"><label>개별 포장</label><input id="individualPackaging"></div>
      <div class="field"><label>박스 단위 포장</label><input id="boxPackaging"></div>
      <div class="field full"><label>추가 FACT 메모</label><textarea id="factNotes"></textarea></div>
    </div>
    <div class="actions"><button id="saveFacts">FACT 저장</button></div>
    <div id="factStatus" class="status"></div>
  </section>

  <section class="card hidden" id="imageCard">
    <div class="step">2 · 원본 이미지 FACT</div>
    <h2>직접 촬영·확보한 원본 등록</h2>
    <div class="muted">여기에는 가공 결과가 아니라 원본을 등록합니다. 역할이 아직 없는 사진도 추가 이미지로 보관할 수 있습니다.</div>
    <div class="grid" style="margin-top:16px">
      <div class="field"><label>대표 이미지</label><input type="file" accept="image/*" id="primaryImage"></div>
      <div class="field"><label>추가 이미지</label><input type="file" accept="image/*" id="additionalImage" multiple></div>
    </div>
    <div class="actions"><button id="uploadImages">이미지 저장</button><a href="/image-studio" class="secondary" style="padding:11px 16px;border-radius:10px">AI 이미지 생성 열기</a></div>
    <div id="imageStatus" class="status"></div>
  </section>

  <section class="card hidden" id="aiCard">
    <div class="step">3 · AI 제안</div>
    <h2>생각이 필요한 정보는 AI가 먼저 제안</h2>
    <div class="muted">카테고리·용도·특징·판매 포인트는 제안일 뿐이며, FACT를 변경하지 않습니다.</div>
    <div class="actions"><button id="getSuggestions">AI 제안 받기</button></div>
    <div id="suggestionView" style="margin-top:12px"></div>
    <div class="actions hidden" id="applyActions"><button id="applySuggestions">제안 적용</button></div>
    <div id="aiStatus" class="status"></div>
  </section>

  <section class="card hidden" id="doneCard">
    <div class="step">완료</div>
    <h2>상품 Master 등록 완료</h2>
    <div class="muted">이제 이 상품의 확정 FACT와 이미지를 이미지 생성·상세페이지 생성에서 다시 입력하지 않고 재사용할 수 있습니다.</div>
    <div class="actions"><a href="/dashboard" class="secondary" style="padding:11px 16px;border-radius:10px">대시보드로 돌아가기</a></div>
  </section>
</div>
<script>
const tenant='__legacy__'; let productId=null; let currentSuggestions=null;
async function api(path, options={}){const r=await fetch(path,{credentials:'same-origin',...options});let d={};try{d=await r.json()}catch(_){ }if(!r.ok)throw new Error(`HTTP ${r.status}: ${JSON.stringify(d)}`);return d}
function v(id){return document.getElementById(id).value.trim()}
function arr(id){return v(id)?v(id).split(',').map(x=>x.trim()).filter(Boolean):[]}
function factsPayload(){return {workspace_id:document.getElementById('workspace').value,product_code:v('productCode'),name:v('name'),model_name:v('modelName')||null,manufacturer:v('manufacturer')||null,primary_material:v('primaryMaterial')||null,secondary_material:v('secondaryMaterial')||null,weight:v('weight')||null,country_of_origin:v('origin')||null,dimensions:{length:v('length')||null,width:v('width')||null,height:v('height')||null},certifications:arr('certifications'),packaging:{individual:v('individualPackaging')||null,box:v('boxPackaging')||null},fact_notes:v('factNotes')||null,confirm:true,confirmed_by:'dashboard-user'}}
async function init(){try{const ws=await api(`/api/v1/business/workspaces?tenant_id=${tenant}`);const sel=document.getElementById('workspace');sel.innerHTML=ws.map(x=>`<option value="${x.id}">${x.name}</option>`).join('');if(!ws.length)document.getElementById('factStatus').textContent='Workspace가 없습니다.'}catch(e){document.getElementById('factStatus').textContent='대시보드 로그인 후 다시 열어주세요. '+e}}
async function saveFacts(){const s=document.getElementById('factStatus');try{if(!v('name')||!v('productCode'))throw new Error('품명과 상품코드는 필수입니다.');s.textContent='저장 중...';const d=await api(`/api/v1/product-registration/products?tenant_id=${tenant}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(factsPayload())});productId=d.product.id;s.innerHTML='<span class="ok">FACT 저장 완료 · AI 임의 수정 금지</span>';document.getElementById('imageCard').classList.remove('hidden');document.getElementById('aiCard').classList.remove('hidden');}catch(e){s.textContent=String(e)}}
async function uploadOne(file,role){const f=new FormData();f.append('role',role);f.append('file',file);return api(`/api/v1/product-registration/products/${productId}/images/upload?tenant_id=${tenant}`,{method:'POST',body:f})}
async function uploadImages(){const s=document.getElementById('imageStatus');try{if(!productId)throw new Error('먼저 FACT를 저장하세요.');const p=document.getElementById('primaryImage').files[0];const adds=[...document.getElementById('additionalImage').files];if(!p&&!adds.length)throw new Error('업로드할 이미지를 선택하세요.');s.textContent='업로드 중...';if(p)await uploadOne(p,'primary');for(const f of adds)await uploadOne(f,'additional');s.innerHTML=`<span class="ok">이미지 저장 완료 · 대표 ${p?1:0} / 추가 ${adds.length}</span>`;}catch(e){s.textContent=String(e)}}
function showSuggestions(d){const op=d.operating||{};const mk=d.marketing||{};const list=x=>(x||[]).map(i=>`<li>${i}</li>`).join('')||'<span class="muted">제안 없음</span>';document.getElementById('suggestionView').innerHTML=`<div class="suggestion"><strong>카테고리</strong><div>${d.category||op.category||'<span class="muted">제안 없음</span>'}</div></div><div class="suggestion"><strong>용도</strong><ul>${list(d.usage||op.usage)}</ul></div><div class="suggestion"><strong>특징</strong><ul>${list(mk.features)}</ul></div><div class="suggestion"><strong>판매 포인트</strong><ul>${list(mk.selling_points)}</ul></div><div class="suggestion"><strong>타깃</strong><ul>${list(mk.target_customer)}</ul></div><div class="suggestion"><strong>콘텐츠 방향</strong><div>${mk.content_direction||'<span class="muted">제안 없음</span>'}</div></div><div class="suggestion warn"><strong>주의</strong><ul>${list(d.warnings)}</ul></div>`;document.getElementById('applyActions').classList.remove('hidden')}
async function getSuggestions(){const s=document.getElementById('aiStatus');try{if(!productId)throw new Error('먼저 FACT를 저장하세요.');s.textContent='제안 생성 중...';const d=await api(`/api/v1/product-registration/products/${productId}/suggest?tenant_id=${tenant}`,{method:'POST'});currentSuggestions=d.suggestions;showSuggestions(currentSuggestions);s.textContent=`제안 생성 완료 · ${d.metadata.provider}`;}catch(e){s.textContent=String(e)}}
async function applySuggestions(){const s=document.getElementById('aiStatus');try{if(!currentSuggestions)throw new Error('먼저 AI 제안을 생성하세요.');await api(`/api/v1/product-registration/products/${productId}/apply-suggestions?tenant_id=${tenant}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operating_info:currentSuggestions.operating||{},marketing_info:currentSuggestions.marketing||{}})});s.innerHTML='<span class="ok">제안 적용 완료</span>';document.getElementById('doneCard').classList.remove('hidden');}catch(e){s.textContent=String(e)}}
document.getElementById('saveFacts').onclick=saveFacts;document.getElementById('uploadImages').onclick=uploadImages;document.getElementById('getSuggestions').onclick=getSuggestions;document.getElementById('applySuggestions').onclick=applySuggestions;init();
</script>
</body></html>
"""


def inject_product_registration_link(html: str) -> str:
    marker = '<button data-panel="products">상품 업무</button>'
    addition = marker + '\n      <a href="/product-registration">＋ 새 상품 등록</a>'
    if marker in html and '/product-registration' not in html:
        return html.replace(marker, addition, 1)
    return html


@router.get("/product-registration", response_class=HTMLResponse, include_in_schema=False)
def product_registration_page():
    return HTMLResponse(
        content=HTML,
        headers={"Cache-Control":"no-store","X-Content-Type-Options":"nosniff"},
    )
