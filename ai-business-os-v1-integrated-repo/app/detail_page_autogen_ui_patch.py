from __future__ import annotations


_AUTOGEN_BUTTON_MARKER = '<button class="btn primary full" style="margin-top:12px" onclick="createAndPrepare()">새 상세페이지 만들기</button>'
_AUTOGEN_SCRIPT_MARKER = 'init();\n</script></body></html>'

_AUTOGEN_BUTTON = r'''
<div style="margin-top:12px;padding:12px;border:1px solid #dbe5ff;border-radius:12px;background:#f6f8ff">
  <div style="font-size:12px;font-weight:900;color:#3047a2;margin-bottom:6px">M06 자동생성 v1</div>
  <button id="autogenBtn" class="btn primary full" onclick="autoGenerateRC()">⚡ 상세페이지 자동생성</button>
  <div id="autogenStatus" class="muted" style="margin-top:7px;line-height:1.5">상품 FACT와 승인 이미지를 기준으로 필요한 페이지만 선택하고 QA까지 실행합니다.</div>
</div>
<button class="btn ghost full" style="margin-top:8px" onclick="createAndPrepare()">수동 제작으로 시작</button>
'''.strip()

_AUTOGEN_SCRIPT = r'''
let autogenBusy=false;
function factReadinessHtml(d){
  const f=d.fact_readiness||{};
  if(f.ready){
    return '<span style="color:#16803a;font-weight:900">FACT 준비 완료</span>';
  }
  const missing=(f.missing_labels||[]).join(', ')||'확정 상품정보';
  return `<span style="color:#b42318;font-weight:900">FACT 보완 필요</span><br>부족 항목: ${esc(missing)}<br><span class="muted">미확정 값은 AI가 추정하지 않습니다. 상품정보를 보완한 뒤 다시 생성하세요.</span>`;
}
async function autoGenerateRC(){
  if(autogenBusy||!workspace||!product.value)return;
  autogenBusy=true;
  const btn=document.getElementById('autogenBtn'),status=document.getElementById('autogenStatus');
  btn.disabled=true;btn.textContent='자동생성 중...';
  status.textContent='FACT 확인 → 조건부 페이지 선택 → 승인 이미지 연결 → QA 실행 중';
  try{
    const d=await jf(`/api/v1/detail-page-autogen/generate?tenant_id=${tenant}`,{
      method:'POST',
      body:JSON.stringify({
        workspace_id:workspace.id,
        product_id:product.value,
        channel:channel.value,
        page_length:pageLength.value,
        template_code:template.value||'A_PRACTICAL_TRUST',
        visual_style:visualStyle.value||'natural',
        page_strategy:strategy.value||'standard',
        brand_style_sheet_id:brandStyle.value||null
      })
    });
    current=await jf(`/api/v1/detail-pages/jobs/${d.job_id}?tenant_id=${tenant}`);
    selected=null;render();await loadJobs();jobs.value=current.id;
    const hidden=(d.hidden_sections||[]).join(', ')||'없음';
    if(d.fact_readiness && !d.fact_readiness.ready){
      status.innerHTML=`${factReadinessHtml(d)}<br>QA <strong>${esc(d.qa_summary)}</strong> · 자동 제외: ${esc(hidden)}`;
    }else{
      status.innerHTML=`${factReadinessHtml(d)} · Release Candidate 생성 완료<br>QA <strong>${esc(d.qa_summary)}</strong> · 자동 제외: ${esc(hidden)} · 다음: 검토 후 최종 승인`;
    }
  }catch(e){
    status.textContent=`자동생성 실패: ${e.message}`;
    alert(e.message);
  }finally{
    autogenBusy=false;btn.disabled=false;btn.textContent='⚡ 상세페이지 자동생성';
  }
}
'''.strip()


def inject_autogen_ui(html: str) -> str:
    """Inject the M06 RC generator without rewriting the existing editor UI."""
    if 'id="autogenBtn"' in html:
        return html
    if _AUTOGEN_BUTTON_MARKER not in html or _AUTOGEN_SCRIPT_MARKER not in html:
        raise RuntimeError("detail-page UI markers changed; autogen injection aborted")
    html = html.replace(_AUTOGEN_BUTTON_MARKER, _AUTOGEN_BUTTON, 1)
    html = html.replace(
        _AUTOGEN_SCRIPT_MARKER,
        f"{_AUTOGEN_SCRIPT}\ninit();\n</script></body></html>",
        1,
    )
    return html
