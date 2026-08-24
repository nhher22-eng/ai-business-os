from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

HTML = r'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Google Drive 연결</title><style>body{font-family:system-ui;background:#f5f7fb;margin:0}.card{max-width:620px;margin:70px auto;background:white;padding:32px;border-radius:18px;box-shadow:0 10px 30px #0001}button{background:#1769e0;color:white;border:0;padding:14px 20px;border-radius:10px;font-weight:700}#status{margin-top:18px;white-space:pre-wrap}</style></head><body><main class="card"><h1>Google Drive 연결</h1><p>Google Drive에서 사용자가 만든 <b>AI Business OS</b> 폴더 하나만 선택해 주세요. 하위 폴더는 시스템이 자동 생성합니다.</p><button id="pick" disabled>AI Business OS 폴더 선택</button><div id="status">연결 준비 중…</div></main><script src="https://apis.google.com/js/api.js"></script><script>
const ticket=new URLSearchParams(location.search).get('ticket');let cfg;
async function init(){const r=await fetch('/api/v1/integrations/google-drive/picker-session?ticket='+encodeURIComponent(ticket));if(!r.ok)throw Error(await r.text());cfg=await r.json();gapi.load('picker',()=>{pick.disabled=false;status.textContent='폴더를 선택할 준비가 됐습니다.'})}
pick.onclick=()=>{const view=new google.picker.DocsView(google.picker.ViewId.FOLDERS).setIncludeFolders(true).setSelectFolderEnabled(true);new google.picker.PickerBuilder().setDeveloperKey(cfg.developer_key).setAppId(cfg.app_id).setOAuthToken(cfg.access_token).addView(view).setCallback(async data=>{if(data.action!==google.picker.Action.PICKED)return;status.textContent='하위 폴더를 만드는 중…';const folder=data.docs[0];const r=await fetch('/api/v1/integrations/google-drive/picker-folder?ticket='+encodeURIComponent(ticket),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({folder_id:folder.id})});if(!r.ok){status.textContent='연결 실패: '+await r.text();return}const out=await r.json();status.textContent='연결 완료\n'+Object.keys(out.folders).join(' · ');pick.disabled=true}).build().setVisible(true)};
init().catch(e=>status.textContent='연결 준비 실패: '+e.message);
</script></body></html>'''


@router.get("/google-drive-setup", response_class=HTMLResponse)
def setup_page():
    return HTML
