from __future__ import annotations


IMAGE_PLAN_CARD = r'''
  <section class="card hidden" id="imagePlanCard">
    <div class="step">4 · AI 이미지 제안 · 확장 상품정보</div>
    <h2>무엇을 만들지 먼저 확정합니다</h2>
    <div class="muted">
      확정된 기본 FACT · 상품 이미지 FACT · 사용자가 확정한 텍스트 정보를 함께 참고합니다.
      여기서는 이미지를 생성하지 않고, 상품에 필요한 이미지 기획만 확정합니다.
    </div>
    <div style="margin-top:12px;padding:12px;border:1px solid #35445a;border-radius:12px;background:#0b1220">
      <strong>공통 원칙</strong>
      <div class="muted" style="margin-top:6px;line-height:1.7">
        제품 형태·색상·부품·재질·치수·수량은 Product Image FACT와 확정 FACT를 기준으로 합니다.<br>
        기준 자료가 부족하면 AI가 추측하지 않고 추가 기준 사진이 필요하다고 표시합니다.<br>
        복잡한 조립·설치 설명은 상품등록에서 만들지 않고 이후 콘텐츠 제작에서 다룹니다.
      </div>
    </div>
    <div class="actions"><button id="getImagePlans">AI 이미지 제안 받기</button></div>
    <div id="imagePlanStatus" class="status"></div>
    <div id="imagePlanView" style="margin-top:12px"></div>
    <div class="actions hidden" id="imagePlanActions">
      <button id="confirmImagePlans">선택한 이미지 기획 확정</button>
    </div>
  </section>
'''

IMAGE_PLAN_SCRIPT = r'''

const imagePlanCategoryOrder=['hero','use_scene','feature_focus','detail','simple_usage_flow','line_drawing','components','extra'];
const imagePlanCategoryLabels={
  hero:'① 메인 / 히어로',use_scene:'② 사용 장면',feature_focus:'③ 특징 강조',detail:'④ 부분 상세',
  simple_usage_flow:'⑤ 간단 사용 / 활용 순서',line_drawing:'⑥ 라인드로잉 기본 2종',components:'⑦ 구성품 / 세트',extra:'⑧ 추가 이미지 아이디어'
};
const imagePlanCategoryHelp={
  hero:'상품을 대표하는 판매·콘텐츠용 이미지',
  use_scene:'어디서·어떻게 쓰는지 보여주는 장면',
  feature_focus:'구매자가 자세히 볼 핵심 특징',
  detail:'실제 DETAIL FACT를 활용한 세부 확인',
  simple_usage_flow:'누구나 이해할 수 있는 짧고 일반적인 활용 순서',
  line_drawing:'정면 규격용 + 45도 설명·주의 재사용용 기본 도면',
  components:'실제로 포함되는 본품·구성품·세트 확인',
  extra:'1~7번으로 다루지 못한 상품 특화 이미지'
};
let currentImagePlans=[];

function imagePlanBadge(item){
  if(item.status==='fact')return '<span style="color:#a7f3d0;font-size:12px;font-weight:800">✓ FACT 기반</span>';
  return '<span style="color:#fde68a;font-size:12px;font-weight:800">⚠ 확인 필요</span>';
}
function imagePlanRow(item,category,index){
  const basis=(item.basis||[]).join(' · ');
  const checked=item.status==='fact'?'checked':'';
  const needsRef=item.required_reference?`<div class="warn" style="margin-top:7px">추가 기준 이미지 필요: ${escapeHtml(item.required_reference)}</div>`:'';
  const note=item.note?`<div class="muted" style="margin-top:7px">${escapeHtml(item.note)}</div>`:'';
  return `<div class="image-plan-row" data-category="${category}" data-index="${index}" style="border:1px solid #35445a;border-radius:12px;padding:12px;margin-top:9px;background:${item.status==='fact'?'#0b1c1a':'#211c10'}">
    <div style="display:flex;gap:8px;align-items:center">
      <input class="image-plan-use" type="checkbox" ${checked} style="width:auto">
      <input class="image-plan-title" value="${escapeHtml(item.title||'')}" style="flex:1;font-weight:800">
      <button type="button" class="secondary" style="padding:7px 9px" onclick="this.closest('.image-plan-row').remove();refreshImagePlanCount()">삭제</button>
    </div>
    <div class="grid" style="margin-top:9px">
      <div class="field full"><label class="muted">목적</label><input class="image-plan-purpose" value="${escapeHtml(item.purpose||'')}"></div>
      <div class="field"><label class="muted">근거</label><input class="image-plan-basis" value="${escapeHtml(basis)}"></div>
      <div class="field"><label class="muted">실행 방식</label><input class="image-plan-execution" value="${escapeHtml(item.execution||'')}"></div>
    </div>
    <input type="hidden" class="image-plan-status" value="${escapeHtml(item.status||'review')}">
    <input type="hidden" class="image-plan-required-reference" value="${escapeHtml(item.required_reference||'')}">
    <div style="display:flex;justify-content:space-between;gap:10px;margin-top:8px">${imagePlanBadge(item)}<span class="muted">제품 외형은 Product Image FACT 기준</span></div>
    ${needsRef}${note}
  </div>`;
}
function imagePlanGroup(category,items){
  const rows=(items||[]).map((x,i)=>imagePlanRow(x,category,i)).join('');
  return `<div class="suggestion"><strong>${imagePlanCategoryLabels[category]}</strong><div class="muted" style="margin-top:4px">${imagePlanCategoryHelp[category]}</div><div id="image-plan-${category}">${rows||'<div class="muted image-plan-empty" style="margin-top:9px">현재 AI 제안 없음</div>'}</div><button type="button" class="secondary" style="margin-top:8px;padding:7px 9px" onclick="addImagePlanRow('${category}')">+ 직접 추가</button></div>`;
}
function addImagePlanRow(category){
  const box=document.getElementById(`image-plan-${category}`);if(!box)return;
  const empty=box.querySelector('.image-plan-empty');if(empty)empty.remove();
  const wrap=document.createElement('div');
  wrap.innerHTML=imagePlanRow({category,title:'',purpose:'',basis:['사용자 직접 추가'],execution:'추후 이미지 제작',status:'review',note:null,required_reference:null},category,Date.now());
  box.appendChild(wrap.firstElementChild);refreshImagePlanCount();
}
function renderImagePlans(data){
  currentImagePlans=data.plans||[];
  const grouped={};imagePlanCategoryOrder.forEach(k=>grouped[k]=[]);
  currentImagePlans.forEach(x=>{if(grouped[x.category])grouped[x.category].push(x)});
  document.getElementById('imagePlanView').innerHTML=`<div class="notice" style="margin-bottom:10px">체크·수정·삭제·직접 추가 후 필요한 기획만 확정하세요. 확정은 이미지 생성이 아니라 상품 확장정보 저장입니다.</div>${imagePlanCategoryOrder.map(k=>imagePlanGroup(k,grouped[k])).join('')}<div id="imagePlanCount" class="status"></div>`;
  document.getElementById('imagePlanActions').classList.remove('hidden');refreshImagePlanCount();
}
function refreshImagePlanCount(){
  const all=[...document.querySelectorAll('.image-plan-row')];const selected=all.filter(x=>x.querySelector('.image-plan-use')?.checked);
  const needRef=selected.filter(x=>x.querySelector('.image-plan-required-reference')?.value.trim());
  const el=document.getElementById('imagePlanCount');if(el)el.innerHTML=`이미지 기획 ${all.length}개 · 선택 ${selected.length}개${needRef.length?` · <span class="warn">추가 기준사진 필요 ${needRef.length}개</span>`:''}`;
}
function collectImagePlans(){
  return [...document.querySelectorAll('.image-plan-row')].filter(row=>row.querySelector('.image-plan-use')?.checked).map(row=>{
    const category=row.dataset.category;const basis=row.querySelector('.image-plan-basis')?.value.split('·').map(x=>x.trim()).filter(Boolean)||[];
    return {category,category_label:imagePlanCategoryLabels[category]?.replace(/^[①-⑧]\s*/,''),title:row.querySelector('.image-plan-title')?.value.trim(),purpose:row.querySelector('.image-plan-purpose')?.value.trim()||null,basis,execution:row.querySelector('.image-plan-execution')?.value.trim()||null,status:row.querySelector('.image-plan-status')?.value||'review',note:null,required_reference:row.querySelector('.image-plan-required-reference')?.value.trim()||null};
  }).filter(x=>x.title);
}
async function getImagePlans(){
  const s=document.getElementById('imagePlanStatus');try{
    if(!productId)throw new Error('먼저 기본 FACT를 저장하세요.');
    s.textContent='확정 FACT와 이미지 FACT, 확정 텍스트 정보를 참고해 이미지 기획 제안 중...';
    const data=await api(`/api/v1/product-registration/products/${productId}/image-plan-suggestions?tenant_id=${tenant}`,{method:'POST'});
    renderImagePlans(data);s.innerHTML=`<span class="ok">이미지 기획 제안 완료 · ${data.metadata?.provider||'planner'}</span>`;
  }catch(e){s.textContent=String(e)}
}
async function confirmImagePlans(){
  const s=document.getElementById('imagePlanStatus');try{
    const plans=collectImagePlans();
    s.textContent='확장 상품정보 저장 중...';
    const data=await api(`/api/v1/product-registration/products/${productId}/image-plans/confirm?tenant_id=${tenant}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({plans})});
    s.innerHTML=`<span class="ok">확장 상품정보 저장 완료 · 이미지 기획 ${data.confirmed_count}개 확정 · 실제 이미지 생성은 등록 완료 조건이 아닙니다.</span>`;
    document.getElementById('imagePlanActions').classList.add('hidden');
    await checkRegistrationReadiness();
  }catch(e){s.textContent=String(e)}
}
async function restoreConfirmedImagePlans(){
  if(!productId)return;try{
    const data=await api(`/api/v1/product-registration/products/${productId}/image-plans?tenant_id=${tenant}`);
    if(data.policy?.plans_confirmed){document.getElementById('imagePlanCard').classList.remove('hidden');renderImagePlans({plans:data.plans||[]});document.getElementById('imagePlanActions').classList.add('hidden');document.getElementById('imagePlanStatus').innerHTML='<span class="ok">저장된 확장 이미지 기획을 불러왔습니다.</span>';}
  }catch(_){ }
}

const _imagePlanApplySuggestions=applySuggestions;
applySuggestions=async function(){
  const applied=await _imagePlanApplySuggestions();
  if(applied===false)return false;
  const card=document.getElementById('imagePlanCard');if(card)card.classList.remove('hidden');
  const s=document.getElementById('imagePlanStatus');if(s)s.textContent='텍스트 확장정보가 확정되었습니다. 이제 필요한 이미지 기획을 검토하세요.';
  return true;
};
document.getElementById('getImagePlans').onclick=getImagePlans;
document.getElementById('confirmImagePlans').onclick=confirmImagePlans;
document.addEventListener('change',e=>{if(e.target?.classList?.contains('image-plan-use'))refreshImagePlanCount()});
'''


def inject_product_image_planning_ui(html: str) -> str:
    if 'id="imagePlanCard"' not in html:
        marker = '<section class="card hidden" id="doneCard">'
        if marker not in html:
            raise RuntimeError("product registration done card marker not found")
        html = html.replace(marker, IMAGE_PLAN_CARD + "\n" + marker, 1)

    html = html.replace(
        '<a href="/image-studio" class="secondary" style="padding:11px 16px;border-radius:10px">AI 이미지 생성 열기</a>',
        '',
        1,
    )

    html = html.replace(
        '이제 이 상품의 확정 FACT와 이미지를 이미지 생성·상세페이지 생성에서 다시 입력하지 않고 재사용할 수 있습니다.',
        '기본 FACT와 상품 이미지 FACT, 확정된 확장 상품정보가 Product Master에 저장되었습니다. 추가·보완 이미지는 등록 후 별도 이미지 제작에서 만들 수 있습니다.',
        1,
    )

    if 'function renderImagePlans(data)' not in html:
        html = html.replace('</script>', IMAGE_PLAN_SCRIPT + '\n</script>', 1)
    return html
