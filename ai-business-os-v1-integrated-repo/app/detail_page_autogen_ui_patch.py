from __future__ import annotations


_AUTOGEN_BUTTON_MARKER = '<button class="btn primary full" style="margin-top:12px" onclick="createAndPrepare()">새 상세페이지 만들기</button>'
_AUTOGEN_SCRIPT_MARKER = 'init();\n</script></body></html>'

_AUTOGEN_BUTTON = r'''
<div style="margin-top:12px;padding:12px;border:1px solid #dbe5ff;border-radius:12px;background:#f6f8ff">
  <div style="font-size:12px;font-weight:900;color:#3047a2;margin-bottom:6px">M06 자동생성 v1</div>
  <button id="autogenBtn" class="btn primary full" onclick="autoGenerateRC()">⚡ 상세페이지 자동생성</button>
  <div id="autogenStatus" class="muted" style="margin-top:7px;line-height:1.5">상품 FACT와 승인 이미지를 기준으로 필요한 페이지만 선택하고 QA까지 실행합니다.</div>
</div>
<div style="margin-top:10px;padding:12px;border:1px solid #d8e9dd;border-radius:12px;background:#f7fbf8">
  <div style="font-size:12px;font-weight:900;color:#1f6b4f;margin-bottom:6px">상품 FACT 편집</div>
  <div id="factEditorProductLabel" style="padding:9px 10px;margin-bottom:8px;border-radius:9px;background:#eaf5ee;font-size:13px;font-weight:900;color:#14532d">현재 편집 상품: 선택 없음</div>
  <button id="repottingSetupBtn" class="btn ghost full" style="display:none" onclick="ensureRepottingMatProduct()">분갈이 매트 테스트 상품 준비</button>
  <div id="factEditorStatus" class="muted" style="margin-top:7px;line-height:1.5">현재 선택 상품의 확정 FACT만 입력합니다. 모르는 값은 비워두세요.</div>
  <div id="factEditor" style="display:none;margin-top:10px">
    <div class="label">확정 사양</div><textarea id="factSpecification" placeholder="예: 실제 확인된 크기·소재·구조만 입력"></textarea>
    <div class="label">사용 정보</div><textarea id="factUsage" placeholder="실제 확인된 사용 용도만 입력"></textarea>
    <div class="label">사용/설치 방법</div><textarea id="factInstallation" placeholder="실제 확인된 사용 순서만 입력"></textarea>
    <div class="label">사용 조건</div><textarea id="factConditions" placeholder="확인된 조건이 없으면 비워두세요"></textarea>
    <div class="label">주의사항</div><textarea id="factCautions" placeholder="확인된 주의사항이 없으면 비워두세요"></textarea>
    <button id="saveFactsBtn" class="btn primary full" style="margin-top:8px" onclick="saveProductFacts()">확정 FACT 저장</button>
    <div class="muted" style="margin-top:7px">저장 후 상세페이지 자동생성을 다시 실행하면 FACT 준비상태가 재평가됩니다.</div>
  </div>
</div>
<button class="btn ghost full" style="margin-top:8px" onclick="createAndPrepare()">수동 제작으로 시작</button>
'''.strip()

_AUTOGEN_SCRIPT = r'''
let autogenBusy=false;
let factEditorBusy=false;
let factEditorProductId=null;
let factLoadSerial=0;
function factReadinessHtml(d){
  const f=d.fact_readiness||{};
  if(f.ready){
    return '<span style="color:#16803a;font-weight:900">FACT 준비 완료</span>';
  }
  const missing=(f.missing_labels||[]).join(', ')||'확정 상품정보';
  return `<span style="color:#b42318;font-weight:900">FACT 보완 필요</span><br>부족 항목: ${esc(missing)}<br><span class="muted">미확정 값은 AI가 추정하지 않습니다. 상품정보를 보완한 뒤 다시 생성하세요.</span>`;
}
function selectedProductRow(){return (products||[]).find(p=>p.id===product.value)||null}
function showFactEditor(show){const box=document.getElementById('factEditor');if(box)box.style.display=show?'block':'none'}
function clearFactEditorFields(){
  factSpecification.value='';factUsage.value='';factInstallation.value='';factConditions.value='';factCautions.value='';
}
function repottingProductExists(){return (products||[]).some(p=>p.product_code==='REPOTTING-MAT'||p.name==='분갈이 매트')}
function updateFactEditorContext(){
  const row=selectedProductRow();
  const label=document.getElementById('factEditorProductLabel');
  const setup=document.getElementById('repottingSetupBtn');
  if(label){
    label.textContent=`현재 편집 상품: ${row?row.name:'선택 없음'}`;
    label.style.background=row?'#eaf5ee':'#f3f4f6';
    label.style.color=row?'#14532d':'#6b7280';
  }
  if(setup){setup.style.display=repottingProductExists()?'none':'block'}
}
async function refreshProducts(selectId=null){
  if(!workspace)return;
  products=await jf(`/api/v1/business/products?tenant_id=${tenant}&workspace_id=${workspace.id}`);
  product.innerHTML=products.map(p=>`<option value="${p.id}">${esc(p.name)}</option>`).join('');
  if(selectId && products.some(p=>p.id===selectId))product.value=selectId;
  updateFactEditorContext();
}
async function ensureRepottingMatProduct(){
  if(factEditorBusy||!workspace)return;
  factEditorBusy=true;
  const btn=document.getElementById('repottingSetupBtn'),status=document.getElementById('factEditorStatus');
  btn.disabled=true;status.textContent='분갈이 매트 테스트 상품 확인 중...';
  try{
    let row=(products||[]).find(p=>p.product_code==='REPOTTING-MAT'||p.name==='분갈이 매트');
    if(!row){
      row=await jf(`/api/v1/business/products?tenant_id=${tenant}`,{method:'POST',body:JSON.stringify({
        workspace_id:workspace.id,product_code:'REPOTTING-MAT',name:'분갈이 매트',status:'draft',sales_channel:'naver-smartstore',description:null,image_nonlocked_allowed:false
      })});
      await refreshProducts(row.id);
    }else{
      product.value=row.id;
      updateFactEditorContext();
    }
    await loadFactEditor();
    if(product.value===row.id){status.innerHTML='<strong style="color:#1f6b4f">분갈이 매트 테스트 상품 준비 완료</strong><br>확인된 FACT만 입력하고 저장하세요.'}
  }catch(e){status.textContent=`테스트 상품 준비 실패: ${e.message}`;alert(e.message)}
  finally{factEditorBusy=false;btn.disabled=false;updateFactEditorContext()}
}
async function loadFactEditor(){
  const row=selectedProductRow(),status=document.getElementById('factEditorStatus');
  const serial=++factLoadSerial;
  factEditorProductId=null;
  clearFactEditorFields();
  updateFactEditorContext();
  if(!row){showFactEditor(false);return}
  showFactEditor(true);
  status.innerHTML=`<strong>${esc(row.name)}</strong> FACT 불러오는 중...`;
  try{
    const d=await jf(`/api/v1/business/product-detail?tenant_id=${tenant}&product_id=${row.id}`);
    if(serial!==factLoadSerial||product.value!==row.id)return;
    factSpecification.value=d.specification||'';factUsage.value=d.usage||'';factInstallation.value=d.installation_method||'';factConditions.value=d.usage_conditions||'';factCautions.value=d.cautions||'';
    factEditorProductId=row.id;
    status.innerHTML=`<strong>${esc(row.name)}</strong> · 저장된 FACT를 불러왔습니다. 실제 확인된 값만 수정하세요.`;
  }catch(e){
    if(serial!==factLoadSerial||product.value!==row.id)return;
    factEditorProductId=row.id;
    if(String(e.message).includes('404')||String(e.message).includes('not found'))status.innerHTML=`<strong>${esc(row.name)}</strong> · 아직 확정 FACT가 없습니다. 모르는 값은 비워두고 확인된 값만 입력하세요.`;
    else status.textContent=`FACT 불러오기 실패: ${e.message}`;
  }
}
async function saveProductFacts(){
  const row=selectedProductRow();if(!row||factEditorBusy)return;
  const status=document.getElementById('factEditorStatus');
  if(factEditorProductId!==row.id){
    status.innerHTML='<strong style="color:#b42318">저장 차단</strong><br>선택 상품과 FACT 편집 대상이 다릅니다. 현재 상품 FACT를 다시 불러옵니다.';
    await loadFactEditor();
    alert('상품 선택이 변경되어 저장을 차단했습니다. 현재 선택 상품의 FACT를 다시 확인해 주세요.');
    return;
  }
  factEditorBusy=true;const btn=document.getElementById('saveFactsBtn');btn.disabled=true;status.innerHTML=`<strong>${esc(row.name)}</strong> FACT 저장 중...`;
  try{
    const payload={product_id:row.id,specification:factSpecification.value.trim()||null,usage:factUsage.value.trim()||null,installation_method:factInstallation.value.trim()||null,usage_conditions:factConditions.value.trim()||null,cautions:factCautions.value.trim()||null};
    await jf(`/api/v1/business/product-detail?tenant_id=${tenant}`,{method:'PUT',body:JSON.stringify(payload)});
    if(product.value!==row.id){await loadFactEditor();return}
    status.innerHTML=`<strong style="color:#16803a">${esc(row.name)} FACT 저장 완료</strong><br>이제 [상세페이지 자동생성]을 눌러 QA와 준비상태를 다시 확인하세요.`;
  }catch(e){status.textContent=`FACT 저장 실패: ${e.message}`;alert(e.message)}
  finally{factEditorBusy=false;btn.disabled=false}
}
async function autoGenerateRC(){
  if(autogenBusy||!workspace||!product.value)return;
  const row=selectedProductRow();
  if(!row)return;
  autogenBusy=true;
  const btn=document.getElementById('autogenBtn'),status=document.getElementById('autogenStatus');
  btn.disabled=true;btn.textContent='자동생성 중...';
  status.innerHTML=`<strong>${esc(row.name)}</strong> · FACT 확인 → 조건부 페이지 선택 → 승인 이미지 연결 → QA 실행 중`;
  try{
    const d=await jf(`/api/v1/detail-page-autogen/generate?tenant_id=${tenant}`,{
      method:'POST',
      body:JSON.stringify({workspace_id:workspace.id,product_id:row.id,channel:channel.value,page_length:pageLength.value,template_code:template.value||'A_PRACTICAL_TRUST',visual_style:visualStyle.value||'natural',page_strategy:strategy.value||'standard',brand_style_sheet_id:brandStyle.value||null})
    });
    current=await jf(`/api/v1/detail-pages/jobs/${d.job_id}?tenant_id=${tenant}`);
    selected=null;render();await loadJobs();jobs.value=current.id;
    const hidden=(d.hidden_sections||[]).join(', ')||'없음';
    if(d.fact_readiness && !d.fact_readiness.ready){status.innerHTML=`<strong>${esc(row.name)}</strong><br>${factReadinessHtml(d)}<br>QA <strong>${esc(d.qa_summary)}</strong> · 자동 제외: ${esc(hidden)}`}
    else{status.innerHTML=`<strong>${esc(row.name)}</strong><br>${factReadinessHtml(d)} · Release Candidate 생성 완료<br>QA <strong>${esc(d.qa_summary)}</strong> · 자동 제외: ${esc(hidden)} · 다음: 검토 후 최종 승인`}
  }catch(e){status.textContent=`자동생성 실패: ${e.message}`;alert(e.message)}
  finally{autogenBusy=false;btn.disabled=false;btn.textContent='⚡ 상세페이지 자동생성'}
}
const _baseInitForFactEditor=init;
init=async function(){
  await _baseInitForFactEditor();
  if(product){product.addEventListener('change',()=>loadFactEditor().catch(()=>{}));updateFactEditorContext();await loadFactEditor()}
}

async function loadProductMasterFactsBridge(){
  const productId=document.getElementById('product')?.value;
  const row=products.find(x=>x.id===productId);
  const status=document.getElementById('factEditorStatus');
  const label=document.getElementById('factEditorProductLabel');
  if(label)label.textContent=`현재 편집 상품: ${row?row.name:'선택 없음'}`;
  showFactEditor(!!row);
  clearFactEditorFields();
  if(!productId)return;
  try{
    const d=await jf(`/api/v1/product-registration/products/${productId}?tenant_id=${tenant}`);
    const f=d.facts||{};
    const op=d.operating_info||{};
    const mk=d.marketing_info||{};
    const dims=f.dimensions||{};
    const packaging=f.packaging||{};

    const specification=[
      f.model_name?`모델명: ${f.model_name}`:'',
      f.manufacturer?`제조사: ${f.manufacturer}`:'',
      f.main_material?`주재질: ${f.main_material}`:'',
      f.sub_material?`보조재질: ${f.sub_material}`:'',
      f.weight?`중량: ${f.weight}`:'',
      f.origin?`원산지: ${f.origin}`:'',
      dims.length?`길이: ${dims.length}`:'',
      dims.width?`폭: ${dims.width}`:'',
      dims.height?`높이: ${dims.height}`:'',
      f.certification?`인증: ${f.certification}`:'',
      packaging.individual?`개별 포장: ${packaging.individual}`:'',
      packaging.box_unit?`박스 단위 포장: ${packaging.box_unit}`:'',
      f.fact_notes||''
    ].filter(Boolean).join('\n');

    const setValue=(id,value)=>{
      const el=document.getElementById(id);
      if(el)el.value=value||'';
    };

    setValue('factSpecification',specification);
    setValue('factUsage',(op.usage||[]).join('\n'));
    setValue('factInstallation',op.installation_method||'');
    setValue('factConditions',op.usage_conditions||'');
    setValue('factCautions',(mk.product_notes||[]).join('\n'));

    if(status)status.innerHTML=`<strong>${esc(row?.name||d.product?.name||'상품')}</strong> · Product Master 확정 FACT를 불러왔습니다.`;
    if(typeof loadPageBasis==='function')await loadPageBasis();
  }catch(e){
    if(status)status.textContent=`Product Master FACT 불러오기 실패: ${e.message||e}`;
  }
}

loadFactEditor=loadProductMasterFactsBridge;

'''.strip()


def inject_autogen_ui(html: str) -> str:
    """Inject the M06 RC generator and safe Product FACT editor."""
    if 'id="autogenBtn"' in html:
        return html
    if _AUTOGEN_BUTTON_MARKER not in html or _AUTOGEN_SCRIPT_MARKER not in html:
        raise RuntimeError("detail-page UI markers changed; autogen injection aborted")
    html = html.replace(_AUTOGEN_BUTTON_MARKER, _AUTOGEN_BUTTON, 1)
    html = html.replace(_AUTOGEN_SCRIPT_MARKER, f"{_AUTOGEN_SCRIPT}\ninit();\n</script></body></html>", 1)
    return html
