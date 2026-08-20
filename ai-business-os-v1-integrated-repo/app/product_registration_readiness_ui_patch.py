from __future__ import annotations


READINESS_SCRIPT = r'''

function setRegistrationNextActions(){
  if(!productId)return;
  const detail=document.getElementById('nextDetailPage');
  if(detail)detail.href=`/detail-pages?product_id=${encodeURIComponent(productId)}`;
}
function renderRegistrationReadiness(r){
  const el=document.getElementById('registrationReadinessStatus');
  const done=document.getElementById('doneCard');
  if(!r){if(el)el.textContent='';if(done)done.classList.add('hidden');return;}
  if(r.registration_flow_complete){
    if(el)el.innerHTML='<span class="ok">✓ 상품등록 완료 · 기본 Product Master + 확장 상품정보 확정</span>';
    setRegistrationNextActions();
    if(done)done.classList.remove('hidden');
  }else if(r.ready){
    const missing=(r.registration_missing_labels||[]).join(', ')||'확장 상품정보';
    if(el)el.innerHTML=`<span class="ok">✓ Product Master 핵심 등록 완료</span> · <span class="warn">등록 마무리 전: ${missing}</span>`;
    if(done)done.classList.add('hidden');
  }else{
    const missing=(r.missing_labels||[]).join(', ')||'필수 등록정보';
    if(el)el.innerHTML=`<span class="warn">Product Master 완료 전 보완: ${missing}</span>`;
    if(done)done.classList.add('hidden');
  }
}
async function checkRegistrationReadiness(){
  if(!productId){renderRegistrationReadiness(null);return null;}
  try{
    const r=await api(`/api/v1/product-registration/products/${productId}/readiness?tenant_id=${tenant}`);
    renderRegistrationReadiness(r);return r;
  }catch(e){
    const el=document.getElementById('registrationReadinessStatus');if(el)el.textContent=String(e);return null;
  }
}

const _readinessConfirmImageFact=confirmImageFact;
confirmImageFact=async function(id){await _readinessConfirmImageFact(id);await checkRegistrationReadiness()};
const _readinessApplySuggestions=applySuggestions;
applySuggestions=async function(){await _readinessApplySuggestions();await checkRegistrationReadiness()};
const _readinessLoadImageFacts=loadImageFacts;
loadImageFacts=async function(){const result=await _readinessLoadImageFacts();await checkRegistrationReadiness();return result};
const _readinessConfirmImagePlans=confirmImagePlans;
confirmImagePlans=async function(){await _readinessConfirmImagePlans();await checkRegistrationReadiness()};
'''


def inject_product_registration_readiness_ui(html: str) -> str:
    # Align visible policy copy with the final-only storage rule.
    html = html.replace(
        "45도 우측(대표)과 정면은 필수입니다. 각도사진은 자동 분류·배경제거 후 확인하고,\n      라이프스타일 사진은 실제 촬영 배경을 그대로 보존합니다.",
        "45도 우측(대표)과 정면은 필수입니다. 전체상품 사진은 자동 분류·누끼·표준 Fit 후 확인하고,\n      부분상세·라이프스타일은 업로드한 최종 사용본을 그대로 사용합니다.",
        1,
    )
    html = html.replace(
        "각도/상세사진: 촬영 원본은 임시 → 누끼 FACT 확정 후 원본 자동 삭제 ·\n        라이프스타일: 촬영 원본 자체를 FACT로 보관",
        "전체상품 사진: 촬영 원본은 임시 → 누끼 + 1000×1000 표준 Fit 확정 후 원본·중간본 삭제 ·\n        부분상세/라이프스타일: 최종 사용본 1개만 Product Master에 보존",
        1,
    )
    html = html.replace(
        '<div id="imageFactReadiness" class="status"></div>',
        '<div id="imageFactReadiness" class="status"></div>\n    <div id="registrationReadinessStatus" class="status"></div>',
        1,
    )

    # Async worker copy should describe the whole standardization pipeline, not only cutout.
    html = html.replace("뒤에서 자동 분류·배경제거 중입니다.", "뒤에서 자동 분류·상품 이미지 표준화 중입니다.")
    html = html.replace("자동 분류·배경제거 처리 중...", "자동 분류·상품 이미지 표준화 처리 중...")
    html = html.replace(
        "const processing=['processing_queued','processing'].includes(item.status);const bgText=processing?'자동 처리 중...':(item.slot_type==='LIFESTYLE'?'배경 보존':(item.background_removed?'배경제거 완료':'배경제거 대기'));",
        "const processing=['processing_queued','processing'].includes(item.status);const bgText=processing?'자동 처리 중...':(['DETAIL','LIFESTYLE'].includes(item.slot_type)?(item.slot_type==='LIFESTYLE'?'배경 유지 · 최종본':'부분상세 · 최종본'):(item.background_removed?'누끼 + 표준 Fit 완료':'표준화 대기'));",
        1,
    )
    html = html.replace(
        "const rawText=item.raw_available?'촬영 원본 임시보관':(item.raw_deleted_at?'촬영 원본 삭제 완료':'촬영 원본 없음');",
        "const rawText=item.raw_available?'촬영 원본 임시보관':(['DETAIL','LIFESTYLE'].includes(item.slot_type)&&item.fact_available?'최종본만 보존':(item.raw_deleted_at?'촬영 원본 삭제 완료':'촬영 원본 없음'));",
        1,
    )

    # Completion belongs to the full registration flow, not the text-suggestion step.
    html = html.replace(
        "document.getElementById('doneCard').classList.remove('hidden');",
        "await checkRegistrationReadiness();",
        1,
    )

    old_done_actions = '<div class="actions"><a href="/dashboard" class="secondary" style="padding:11px 16px;border-radius:10px">대시보드로 돌아가기</a></div>'
    new_done_actions = '''<div class="actions">
      <a id="nextDetailPage" href="/detail-pages" class="secondary" style="padding:11px 16px;border-radius:10px">상세페이지 만들기</a>
      <a href="/products" class="secondary" style="padding:11px 16px;border-radius:10px">전체 상품</a>
      <a href="/dashboard" class="secondary" style="padding:11px 16px;border-radius:10px">대시보드</a>
    </div>'''
    if old_done_actions in html:
        html = html.replace(old_done_actions, new_done_actions, 1)

    if 'function checkRegistrationReadiness()' not in html:
        html = html.replace('</script>', READINESS_SCRIPT + '\n</script>', 1)
    return html
