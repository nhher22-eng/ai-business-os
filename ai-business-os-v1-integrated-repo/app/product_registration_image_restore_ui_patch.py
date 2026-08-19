from __future__ import annotations


IMAGE_STATUS_MARKER = '<div id="imageStatus" class="status"></div>'
IMAGE_STATUS_REPLACEMENT = IMAGE_STATUS_MARKER + '''
    <div id="currentImages" style="margin-top:14px"></div>'''

OPEN_NEXT_OLD = "function openNextSteps(){document.getElementById('imageCard').classList.remove('hidden');document.getElementById('aiCard').classList.remove('hidden')}"
OPEN_NEXT_NEW = "function openNextSteps(){document.getElementById('imageCard').classList.remove('hidden');document.getElementById('aiCard').classList.remove('hidden');if(productId)loadExistingImages()}"

UPLOAD_OLD = "s.innerHTML=`<span class=\"ok\">이미지 저장 완료 · 대표 ${p?1:0} / 추가 ${adds.length}</span>`;"
UPLOAD_NEW = UPLOAD_OLD + "await loadExistingImages();"

SCRIPT_MARKER = "document.getElementById('saveFacts').onclick=saveFacts;"
SCRIPT_INSERT = r'''
function escapeHtml(value){return String(value||'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]))}
function assetContentUrl(id){return `/api/v1/product-registration-assets/references/${encodeURIComponent(id)}/content?tenant_id=${tenant}`}
async function loadExistingImages(){
  const box=document.getElementById('currentImages');
  if(!box||!productId)return;
  try{
    const d=await api(`/api/v1/product-registration/products/${productId}/images?tenant_id=${tenant}`);
    const byId=new Map((d.assets||[]).map(x=>[x.id,x]));
    const primary=d.primary_asset_id?byId.get(d.primary_asset_id):null;
    const additional=(d.additional_asset_ids||[]).map(id=>byId.get(id)).filter(Boolean);
    const card=(asset,label)=>`<div style="border:1px solid #35445a;border-radius:10px;padding:10px;background:#0b1220"><div class="muted" style="margin-bottom:7px">${label}</div><img src="${assetContentUrl(asset.id)}" alt="${escapeHtml(asset.filename||label)}" style="width:100%;max-height:180px;object-fit:contain;border-radius:8px;background:#070b12"><div class="muted" style="margin-top:7px;overflow-wrap:anywhere">${escapeHtml(asset.filename||'등록 이미지')}</div></div>`;
    if(!primary&&!additional.length){box.innerHTML='<div class="muted">현재 등록된 상품 이미지가 없습니다.</div>';return;}
    box.innerHTML=`<div class="muted" style="margin-bottom:8px">현재 저장된 이미지</div><div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px">${primary?card(primary,'대표 이미지'):''}${additional.map((x,i)=>card(x,`추가 이미지 ${i+1}`)).join('')}</div>`;
  }catch(e){box.innerHTML=`<div class="warn">기존 이미지 조회 실패: ${escapeHtml(String(e))}</div>`}
}
'''


def inject_product_image_restore(html: str) -> str:
    if "loadExistingImages" in html:
        return html
    if IMAGE_STATUS_MARKER not in html:
        raise RuntimeError("product image status marker not found")
    html = html.replace(IMAGE_STATUS_MARKER, IMAGE_STATUS_REPLACEMENT, 1)
    if OPEN_NEXT_OLD not in html:
        raise RuntimeError("product registration openNextSteps marker not found")
    html = html.replace(OPEN_NEXT_OLD, OPEN_NEXT_NEW, 1)
    if UPLOAD_OLD not in html:
        raise RuntimeError("product registration upload status marker not found")
    html = html.replace(UPLOAD_OLD, UPLOAD_NEW, 1)
    if SCRIPT_MARKER not in html:
        raise RuntimeError("product registration script marker not found")
    return html.replace(SCRIPT_MARKER, SCRIPT_INSERT + "\n" + SCRIPT_MARKER, 1)
