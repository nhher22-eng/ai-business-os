from __future__ import annotations


OLD_SHOW = """function showSuggestions(d){const op=d.operating||{};const mk=d.marketing||{};const list=x=>(x||[]).map(i=>`<li>${i}</li>`).join('')||'<span class=\"muted\">제안 없음</span>';document.getElementById('suggestionView').innerHTML=`<div class=\"suggestion\"><strong>카테고리</strong><div>${d.category||op.category||'<span class=\"muted\">제안 없음</span>'}</div></div><div class=\"suggestion\"><strong>용도</strong><ul>${list(d.usage||op.usage)}</ul></div><div class=\"suggestion\"><strong>특징</strong><ul>${list(mk.features)}</ul></div><div class=\"suggestion\"><strong>판매 포인트</strong><ul>${list(mk.selling_points)}</ul></div><div class=\"suggestion\"><strong>타깃</strong><ul>${list(mk.target_customer)}</ul></div><div class=\"suggestion\"><strong>콘텐츠 방향</strong><div>${mk.content_direction||'<span class=\"muted\">제안 없음</span>'}</div></div><div class=\"suggestion warn\"><strong>주의</strong><ul>${list(d.warnings)}</ul></div>`;document.getElementById('applyActions').classList.remove('hidden')}"""

NEW_SHOW = r'''function basisBadge(item){if(item.source==='fact')return '<span style="color:#a7f3d0;font-size:12px;font-weight:800">✓ FACT</span>';if(item.status==='review')return '<span style="color:#fde68a;font-size:12px;font-weight:800">⚠ 확인 필요</span>';return '<span style="color:#bfdbfe;font-size:12px;font-weight:800">AI 제안</span>'}
function focusBasisInput(button){const row=button.closest('.basis-row');const input=row?.querySelector('.basis-value');if(!input)return;input.focus();input.select()}
function basisRow(item,group,index){const checked=item.source==='fact'||item.status==='suggested'?'checked':'';return `<div class="basis-row" data-group="${group}" data-index="${index}" style="border:1px solid #35445a;border-radius:10px;padding:10px;margin-top:8px;background:${item.status==='review'?'#211c10':'#0b1220'}"><div style="display:flex;gap:8px;align-items:center"><input class="basis-use" type="checkbox" ${checked} style="width:auto"><input class="basis-value" value="${escapeHtml(item.value||'')}" aria-label="직접 수정 가능한 제안 문장" style="flex:1"><button type="button" class="secondary basis-edit" style="padding:7px 9px;white-space:nowrap" onclick="focusBasisInput(this)">✎ 수정</button><button type="button" class="secondary" style="padding:7px 9px" onclick="this.closest('.basis-row').remove()">삭제</button></div><div style="display:flex;justify-content:space-between;gap:10px;margin-top:7px">${basisBadge(item)}<span class="muted" style="text-align:right">${escapeHtml(item.reason||'')}</span></div></div>`}
function basisGroup(title,key,items){const rows=(items||[]).map((x,i)=>basisRow(x,key,i)).join('');return `<div class="suggestion"><strong>${title}</strong><div id="basis-${key}">${rows||'<div class="muted" style="margin-top:8px">현재 제안 없음 · 필요하면 직접 추가할 수 있습니다.</div>'}</div><button type="button" class="secondary" style="margin-top:8px;padding:7px 9px" onclick="addBasisRow('${key}')">+ 직접 추가</button></div>`}
function addBasisRow(group){const box=document.getElementById(`basis-${group}`);if(!box)return;const placeholder=box.querySelector('.muted');if(placeholder)placeholder.remove();const wrap=document.createElement('div');wrap.innerHTML=basisRow({value:'',source:'user',status:'suggested',reason:'사용자가 직접 추가한 내용입니다.'},group,Date.now());box.appendChild(wrap.firstElementChild);const input=box.lastElementChild?.querySelector('.basis-value');if(input)input.focus()}
function isSystemGuidance(text){const x=String(text||'');return x.includes('AI 제안은 아이디어')||x.includes('AI 제안은 확정 FACT')||x.includes('FACT 항목')||x.includes('물리적 사실은 AI가 새로 만들지 않습니다')||x.includes('텍스트 AI가 연결되지 않아')||x.includes('AI 제안 호출 실패')||x.includes('상품 FACT를 먼저 사용자 확정')}
function editorGuidance(d){const runtime=(d.warnings||[]).filter(x=>isSystemGuidance(x));return `<div class="suggestion"><strong>AI 제안 편집 안내</strong><ul class="muted" style="line-height:1.7"><li>각 문장은 입력칸에서 바로 고칠 수 있고, <strong>✎ 수정</strong>을 누르면 해당 문장을 바로 선택합니다.</li><li>AI 제안은 확정 FACT를 바꾸지 않는 설명·마케팅 아이디어입니다. 실제 상품에 맞는 내용만 수정·삭제·채택합니다.</li><li>초록색은 확정 FACT에서 직접 가져온 항목입니다. 콘텐츠에서 쓰지 않을 경우 선택 해제할 수 있지만 원천 FACT는 바뀌지 않습니다.</li><li>체크된 항목만 텍스트 확장 상품정보로 저장됩니다. 필요 없는 항목은 비워둬도 됩니다.</li>${runtime.map(x=>`<li class="warn">${escapeHtml(x)}</li>`).join('')}</ul></div>`}
function showSuggestions(d){const e=d.editor||{};const directionItems=e.content_direction?[e.content_direction]:[];const notes=e.product_notes||[];document.getElementById('suggestionView').innerHTML=`<div class="notice" style="margin-bottom:10px">확정 FACT를 바탕으로 상품 설명에 필요한 텍스트 확장정보를 먼저 검토합니다. 물리적 사실을 새로 만들지 않으며, 맞는 내용만 체크·수정·확정하세요.</div>${basisGroup('용도','usage',e.usage)}${basisGroup('특징','features',e.features)}${basisGroup('판매 포인트','selling_points',e.selling_points)}${basisGroup('타깃','target_customer',e.target_customer)}${basisGroup('콘텐츠 방향','content_direction',directionItems)}${basisGroup('상품 관련 참고·주의','product_notes',notes)}${editorGuidance(d)}`;document.getElementById('applyActions').classList.remove('hidden')}
function collectBasis(group){return [...document.querySelectorAll(`#basis-${group} .basis-row`)].filter(row=>row.querySelector('.basis-use')?.checked).map(row=>row.querySelector('.basis-value')?.value.trim()).filter(Boolean)}
function editedBasisPayload(){const usage=collectBasis('usage');const features=collectBasis('features');const selling=collectBasis('selling_points');const targets=collectBasis('target_customer');const direction=collectBasis('content_direction')[0]||null;const productNotes=collectBasis('product_notes');return {operating_info:{usage},marketing_info:{features,selling_points:selling,target_customer:targets,content_direction:direction,product_notes:productNotes}}}'''

OLD_APPLY = """async function applySuggestions(){const s=document.getElementById('aiStatus');try{if(!currentSuggestions)throw new Error('먼저 AI 제안을 생성하세요.');await api(`/api/v1/product-registration/products/${productId}/apply-suggestions?tenant_id=${tenant}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operating_info:currentSuggestions.operating||{},marketing_info:currentSuggestions.marketing||{}})});s.innerHTML='<span class=\"ok\">제안 적용 완료</span>';document.getElementById('doneCard').classList.remove('hidden');}catch(e){s.textContent=String(e)}}"""

NEW_APPLY = """async function applySuggestions(){const s=document.getElementById('aiStatus');try{if(!currentSuggestions)throw new Error('먼저 텍스트 AI 제안을 생성하세요.');const payload=editedBasisPayload();await api(`/api/v1/product-registration/products/${productId}/apply-suggestions?tenant_id=${tenant}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});s.innerHTML='<span class=\"ok\">텍스트 확장정보 확정 완료 · 다음 단계에서 이미지 기획을 검토합니다.</span>';return true;}catch(e){s.textContent=String(e);return false;}}"""

STYLE_MARKER = ".suggestion:last-child{border-bottom:0}.ok{color:#a7f3d0}.warn{color:#fde68a}"
STYLE_REPLACEMENT = STYLE_MARKER + ".basis-row input[type=text],.basis-row input:not([type]){min-width:0}.basis-row .basis-value{font-size:14px}.basis-row .basis-value:focus{outline:2px solid #93c5fd;outline-offset:1px}"


def inject_product_content_basis_editor(html: str) -> str:
    if "editedBasisPayload" in html:
        return html
    if OLD_SHOW not in html:
        raise RuntimeError("product suggestion renderer marker not found")
    html = html.replace(OLD_SHOW, NEW_SHOW, 1)
    if OLD_APPLY not in html:
        raise RuntimeError("product suggestion apply marker not found")
    html = html.replace(OLD_APPLY, NEW_APPLY, 1)

    html = html.replace('<div class="step">3 · AI 제안</div>', '<div class="step">3 · 텍스트 AI 제안 · 확장 상품정보</div>', 1)
    html = html.replace('생각이 필요한 정보는 AI가 먼저 제안', '상품을 설명하는 확장정보를 먼저 확정합니다', 1)
    html = html.replace('카테고리·용도·특징·판매 포인트는 제안일 뿐이며, FACT를 변경하지 않습니다.', '확정 FACT를 기준으로 용도·특징·판매 포인트·타깃·콘텐츠 방향·상품 관련 참고사항을 제안합니다. 물리적 사실은 새로 만들지 않습니다.', 1)
    html = html.replace('>AI 제안 받기</button>', '>텍스트 AI 제안 받기</button>', 1)
    html = html.replace('>제안 적용</button>', '>선택한 텍스트 정보 확정</button>', 1)

    if STYLE_MARKER in html:
        html = html.replace(STYLE_MARKER, STYLE_REPLACEMENT, 1)
    return html
