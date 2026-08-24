from __future__ import annotations


PATCH_SCRIPT = r'''

function setFieldValue(id,value){const el=document.getElementById(id);if(el&&value!==null&&value!==undefined)el.value=value}
function restoreRegistrationForm(reg){
  if(!reg||!reg.product)return false;
  const p=reg.product,f=reg.facts||{},dims=f.dimensions||{},pack=f.packaging||{};
  productId=p.id;
  setFieldValue('workspace',p.workspace_id);setFieldValue('name',p.name);setFieldValue('productCode',p.product_code);
  setFieldValue('modelName',f.model_name||'');setFieldValue('manufacturer',f.manufacturer||'');
  setFieldValue('primaryMaterial',f.primary_material||'');setFieldValue('secondaryMaterial',f.secondary_material||'');
  setFieldValue('weight',f.weight||'');setFieldValue('origin',f.country_of_origin||'');
  setFieldValue('length',dims.length||'');setFieldValue('width',dims.width||'');setFieldValue('height',dims.height||'');
  setFieldValue('certifications',Array.isArray(f.certifications)?f.certifications.join(', '):'');
  setFieldValue('individualPackaging',pack.individual||'');setFieldValue('boxPackaging',pack.box||'');setFieldValue('factNotes',f.fact_notes||'');
  const factStatus=document.getElementById('factStatus');if(factStatus)factStatus.innerHTML='<span class="ok">최근 작업 자동 복원 완료 · 저장된 FACT를 불러왔습니다.</span>';
  const imageFactCard=document.getElementById('imageFactCard');if(imageFactCard)imageFactCard.classList.remove('hidden');
  const aiCard=document.getElementById('aiCard');if(aiCard)aiCard.classList.add('hidden');
  return true;
}
async function restoreRegistrationProgress(){
  if(!productId)return;
  try{
    const r=await api(`/api/v1/product-registration/products/${productId}/readiness?tenant_id=${tenant}`);
    if(r.ready){const aiCard=document.getElementById('aiCard');if(aiCard)aiCard.classList.remove('hidden');}
    if(r.content_basis_saved){
      const imagePlanCard=document.getElementById('imagePlanCard');if(imagePlanCard)imagePlanCard.classList.remove('hidden');
      const s=document.getElementById('imagePlanStatus');if(s&&!r.image_plans_saved)s.textContent='저장된 텍스트 확장정보가 있습니다. 이미지 기획 단계부터 이어서 진행하세요.';
    }
    if(r.image_plans_saved&&typeof restoreConfirmedImagePlans==='function')await restoreConfirmedImagePlans();
    if(typeof renderRegistrationReadiness==='function')renderRegistrationReadiness(r);
  }catch(e){console.warn('registration progress restore skipped',e)}
}
async function restoreRecentRegistration(){
  try{
    const stored=localStorage.getItem('aios.productRegistration.activeProductId');
    let reg=null;
    if(stored){try{reg=await api(`/api/v1/product-registration/products/${stored}?tenant_id=${tenant}`)}catch(_){localStorage.removeItem('aios.productRegistration.activeProductId')}}
    if(!reg){const d=await api(`/api/v1/product-registration/recent?tenant_id=${tenant}`);reg=d.registration||null}
    if(reg&&restoreRegistrationForm(reg)){
      localStorage.setItem('aios.productRegistration.activeProductId',reg.product.id);
      await loadImageFacts();
      await restoreRegistrationProgress();
    }
  }catch(e){console.warn('registration restore skipped',e)}
}
async function initWithRegistrationRestore(){await init()}
'''


def inject_async_restore_ui(html: str) -> str:
    html = html.replace(
        "fd.append('auto_process','true');\n    s.textContent=`${files.length}장 업로드·분류·처리 중...`;\n    const data=await api(`/api/v1/product-image-facts/products/${productId}/batch?tenant_id=${tenant}`,{method:'POST',body:fd});\n    s.innerHTML=`<span class=\"ok\">${data.uploaded}장 등록 완료 · 분류가 틀리면 항목만 수정하세요.</span>`;",
        "s.textContent=`${files.length}장 업로드 접수 중...`;\n    const data=await api(`/api/v1/product-image-facts/products/${productId}/batch-async?tenant_id=${tenant}`,{method:'POST',body:fd});\n    localStorage.setItem('aios.productRegistration.activeProductId',productId);\n    s.innerHTML=`<span class=\"ok\">${data.accepted}장 접수 완료 · 뒤에서 자동 분류·배경제거 중입니다.</span>`;",
        1,
    )

    html = html.replace(
        "const bgText=item.slot_type==='LIFESTYLE'?'배경 보존':(item.background_removed?'배경제거 완료':'배경제거 대기');",
        "const processing=['processing_queued','processing'].includes(item.status);const bgText=processing?'자동 처리 중...':(item.slot_type==='LIFESTYLE'?'배경 보존':(item.background_removed?'배경제거 완료':'배경제거 대기'));",
        1,
    )
    html = html.replace(
        "renderImageFacts(data);s.textContent='';",
        "renderImageFacts(data);const busy=(data.images||[]).some(x=>['processing_queued','processing'].includes(x.status));if(busy){s.textContent='자동 분류·배경제거 처리 중...';setTimeout(loadImageFacts,2000)}else{s.textContent=''};",
        1,
    )

    if 'initWithRegistrationRestore();' not in html:
        boot_marker = 'init();'
        boot_pos = html.rfind(boot_marker)
        if boot_pos < 0:
            raise RuntimeError('product registration init marker not found')
        html = html[:boot_pos] + 'initWithRegistrationRestore();' + html[boot_pos + len(boot_marker):]

    if 'function restoreRecentRegistration()' not in html:
        html = html.replace('</script>', PATCH_SCRIPT + '\n</script>', 1)
    return html
