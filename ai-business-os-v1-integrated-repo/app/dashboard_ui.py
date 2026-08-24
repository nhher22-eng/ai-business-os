from fastapi import APIRouter
from fastapi.responses import HTMLResponse


router = APIRouter()


HTML = r"""
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Business OS</title>

<style>
*{box-sizing:border-box}
body{
  margin:0;
  font-family:Inter,system-ui,sans-serif;
  background:#0b0f17;
  color:#e5e7eb;
}
.shell{
  display:grid;
  grid-template-columns:210px 1fr;
  min-height:100vh;
}
.sidebar{
  border-right:1px solid #243044;
  padding:24px 16px;
  background:#0d1320;
}
.brand{
  font-size:18px;
  font-weight:800;
  margin-bottom:28px;
}
.nav button,.nav a{
  width:100%;
  display:block;
  margin:5px 0;
  padding:11px 12px;
  border:0;
  border-radius:10px;
  background:transparent;
  color:#a9b7ca;
  text-align:left;
  cursor:pointer;
  text-decoration:none;
}
.nav button.active,
.nav button:hover,
.nav a:hover{
  background:#182337;
  color:#fff;
}
.main{
  padding:30px;
}
.top{
  display:flex;
  justify-content:space-between;
  align-items:center;
  gap:16px;
  margin-bottom:24px;
}
h1{
  margin:0;
  font-size:27px;
}
.muted{
  color:#8ea0b7;
  font-size:13px;
}
.badge{
  display:inline-block;
  padding:6px 10px;
  border:1px solid #35445a;
  border-radius:999px;
  font-size:12px;
  font-weight:800;
}
.cards{
  display:grid;
  grid-template-columns:repeat(4,1fr);
  gap:14px;
  margin-bottom:20px;
}
.card{
  background:#111827;
  border:1px solid #263247;
  border-radius:15px;
  padding:18px;
}
.metric{
  font-size:26px;
  font-weight:800;
  margin-top:8px;
}
.panel{
  display:none;
}
.panel.active{
  display:block;
}
.row{
  display:flex;
  justify-content:space-between;
  gap:16px;
  padding:11px 0;
  border-bottom:1px solid #253044;
}
.row:last-child{
  border-bottom:0;
}
@media(max-width:800px){
  .shell{grid-template-columns:1fr}
  .sidebar{display:none}
  .cards{grid-template-columns:1fr 1fr}
}
</style>
</head>
<body>
"""
HTML += r"""
<div class="shell">

  <aside class="sidebar">
    <div class="brand">AI Business OS</div>

    <div class="nav">
      <a href="/business-home">새 업무 홈</a>
      <button class="active" data-panel="home">홈</button>
      <button data-panel="products">상품 업무</button>
      <button data-panel="approvals">승인함</button>
      <button data-panel="workflow">Workflow</button>
      <button data-panel="runs">실행 기록</button>
      <a href="/image-studio">AI 이미지 생성</a>
      <a href="/detail-pages">상세페이지 생성</a>
    </div>
  </aside>

  <main class="main">

    <div class="top">
      <div>
        <h1 id="pageTitle">운영 대시보드</h1>
        <div class="muted">
          실제 업무와 AI 실행 상태를 한 화면에서 관리합니다.
        </div>
      </div>

      <span class="badge" id="systemMode">
        SHADOW MODE
      </span>
    </div>

    <section id="home" class="panel active">

      <div class="cards">
        <div class="card">
          <div class="muted">Workspace</div>
          <div class="metric" id="workspaceCount">-</div>
        </div>

        <div class="card">
          <div class="muted">상품</div>
          <div class="metric" id="productCount">-</div>
        </div>

        <div class="card">
          <div class="muted">SKU</div>
          <div class="metric" id="skuCount">-</div>
        </div>

        <div class="card">
          <div class="muted">승인 대기</div>
          <div class="metric">0</div>
        </div>
      </div>

      <div class="card">
        <h2>현재 실제 업무</h2>

        <div class="row">
          <span class="muted">Workspace</span>
          <strong id="homeWorkspace">Loading...</strong>
        </div>

        <div class="row">
          <span class="muted">Product</span>
          <strong id="homeProduct">Loading...</strong>
        </div>

        <div class="row">
          <span class="muted">Sales Channel</span>
          <strong id="homeChannel">-</strong>
        </div>

        <div class="row">
          <span class="muted">SKU</span>
          <strong id="homeSkus">-</strong>
        </div>
      </div>

    </section>

    <section id="products" class="panel">
      <div class="card">
        <h2>상품 업무</h2>
        <div id="productView" class="muted">
          실제 상품 데이터를 불러오는 중입니다.
        </div>

        <div
          id="productDetail"
          style="display:none;margin-top:18px"
        ></div>
      </div>
    </section>

    <section id="approvals" class="panel">
      <div class="card">
        <h2>승인함</h2>
        <div class="muted">
          아직 승인 대기 업무가 없습니다.
        </div>
      </div>
    </section>

    <section id="workflow" class="panel">
      <div class="card">
        <h2>Workflow</h2>

        <div class="row">
          <span>1. 상품정보</span>
          <strong>완료</strong>
        </div>

        <div class="row">
          <span>2. SKU 구성</span>
          <strong>완료</strong>
        </div>

        <div class="row">
          <span>3. 콘텐츠 생성</span>
          <strong>대기</strong>
        </div>

        <div class="row">
          <span>4. QA</span>
          <strong>대기</strong>
        </div>

        <div class="row">
          <span>5. 사용자 승인</span>
          <strong>대기</strong>
        </div>
      </div>
    </section>

    <section id="runs" class="panel">
      <div class="card">
        <h2>실행 기록</h2>
        <div class="muted">
          실제 Workflow 실행 기록이 이곳에 표시됩니다.
        </div>
      </div>
    </section>

  </main>
</div>

"""

HTML += r"""
<script>
const titles = {
  home: "운영 대시보드",
  products: "상품 업무",
  approvals: "승인함",
  workflow: "Workflow",
  runs: "실행 기록"
};

document.querySelector(".top").insertAdjacentHTML(
  "afterend",
  `
  <div class="card" style="margin-bottom:16px">
    <div style="display:flex;gap:10px;align-items:end;flex-wrap:wrap">
      <div style="flex:1;min-width:220px">
        <div class="muted" style="margin-bottom:6px">Secure session</div>
        <input
          id="dashboardToken"
          type="password"
          placeholder="Bearer token"
          style="width:100%;padding:10px;border-radius:9px;
                 border:1px solid #35445a;background:#0b1220;color:#fff"
        >
      </div>

      <button
        id="loadDashboard"
        style="padding:10px 16px;border-radius:9px;
               border:1px solid #35445a;background:#e5e7eb;
               color:#111827;font-weight:800;cursor:pointer"
      >
        Connect / Refresh
      </button>

      <span id="dataStatus" class="muted">Not connected</span>
    </div>
  </div>
  `
);

document.querySelectorAll(".nav button").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".nav button").forEach(
      (x) => x.classList.remove("active")
    );
    document.querySelectorAll(".panel").forEach(
      (x) => x.classList.remove("active")
    );

    button.classList.add("active");

    const panel = button.dataset.panel;
    document.getElementById(panel).classList.add("active");
    document.getElementById("pageTitle").textContent =
      titles[panel] || "AI Business OS";
  });
});

async function api(path) {
  const response = await fetch(path, {
    credentials: "same-origin"
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      `HTTP ${response.status}: ${JSON.stringify(data)}`
    );
  }

  return data;
}

async function dashboardSessionValid() {
  const response = await fetch(
    "/api/v1/dashboard/session",
    { credentials: "same-origin" }
  );

  return response.ok;
}

function setDashboardConnected() {
  const tokenInput =
    document.getElementById("dashboardToken");
  const button =
    document.getElementById("loadDashboard");

  tokenInput.value = "";
  tokenInput.style.display = "none";
  button.textContent = "Refresh";
  document.getElementById("dataStatus").textContent =
    "Connected";
}

async function createDashboardSession() {
  const token =
    document.getElementById("dashboardToken").value.trim();

  if (!token) {
    throw new Error("Bearer token is required for first login.");
  }

  const response = await fetch(
    "/api/v1/dashboard/session",
    {
      method: "POST",
      credentials: "same-origin",
      headers: {
        Authorization: `Bearer ${token}`
      }
    }
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      `HTTP ${response.status}: ${JSON.stringify(data)}`
    );
  }

  setDashboardConnected();
}

async function connectDashboard() {
  const status =
    document.getElementById("dataStatus");

  try {
    status.textContent = "Connecting...";

    if (!(await dashboardSessionValid())) {
      await createDashboardSession();
    } else {
      setDashboardConnected();
    }

    await loadDashboardData();
  } catch (error) {
    status.textContent = String(error);
  }
}

async function restoreDashboardSession() {
  try {
    if (await dashboardSessionValid()) {
      setDashboardConnected();
      await loadDashboardData();
    }
  } catch (_) {
    // First visit: user logs in manually.
  }
}

async function loadDashboardData() {
  const status = document.getElementById("dataStatus");

  try {
    status.textContent = "Loading...";

    const tenant = "__legacy__";

    const workspaces = await api(
      `/api/v1/business/workspaces?tenant_id=${tenant}`
    );

    const workspace =
      workspaces.find((x) => x.slug === "commerce-ai")
      || workspaces[0];

    if (!workspace) {
      throw new Error("Workspace not found.");
    }

    const products = await api(
      `/api/v1/business/products?tenant_id=${tenant}` +
      `&workspace_id=${encodeURIComponent(workspace.id)}`
    );

    const product =
      products.find(
        (x) => x.product_code === "IRRIGATION-8MM-KIT"
      )
      || products[0];

    if (!product) {
      throw new Error("Product not found.");
    }

    const skus = await api(
      `/api/v1/business/skus?tenant_id=${tenant}` +
      `&product_id=${encodeURIComponent(product.id)}`
    );

    document.getElementById("workspaceCount").textContent =
      workspaces.length;
    document.getElementById("productCount").textContent =
      products.length;
    document.getElementById("skuCount").textContent =
      skus.length;

    document.getElementById("systemMode").textContent =
      `${String(workspace.mode).toUpperCase()} MODE`;

    document.getElementById("homeWorkspace").textContent =
      workspace.name;
    document.getElementById("homeProduct").textContent =
      product.name;
    document.getElementById("homeChannel").textContent =
      product.sales_channel || "-";
    document.getElementById("homeSkus").textContent =
      skus.map((x) => x.option_value || x.name).join(" / ");

    document.getElementById("productView").innerHTML = `
      <button
        id="openProductDetail"
        style="
          width:100%;
          padding:16px;
          text-align:left;
          border:1px solid #35445a;
          border-radius:12px;
          background:#0f172a;
          color:#e5e7eb;
          cursor:pointer;
        "
      >
        <strong style="font-size:16px">
          ${product.name}
        </strong>
        <div class="muted" style="margin-top:7px">
          ${product.product_code}
          · ${product.status}
          · ${product.sales_channel || "-"}
        </div>
        <div class="muted" style="margin-top:7px">
          SKU ${skus.length}개
          · ${skus.map(
            (x) => x.option_value || x.name
          ).join(" / ")}
        </div>
        <div style="margin-top:10px">
          상품 상세 열기 →
        </div>
      </button>
    `;

    document
      .getElementById("openProductDetail")
      .addEventListener("click", () => {
        const detail =
          document.getElementById("productDetail");

        if (detail.style.display === "block") {
          detail.style.display = "none";
          return;
        }

        detail.innerHTML = `
          <div class="card">
            <h2>${product.name}</h2>

            <div class="row">
              <span class="muted">상품코드</span>
              <strong>${product.product_code}</strong>
            </div>

            <div class="row">
              <span class="muted">상태</span>
              <strong>${product.status}</strong>
            </div>

            <div class="row">
              <span class="muted">판매채널</span>
              <strong>${product.sales_channel || "-"}</strong>
            </div>

            <div class="row">
              <span class="muted">설명</span>
              <strong>${product.description || "-"}</strong>
            </div>

            <h2 style="margin-top:24px">SKU / 옵션</h2>

            ${skus.map(
              (x) => `
                <div class="row">
                  <span>
                    <strong>${x.option_value || x.name}</strong>
                    <div class="muted">
                      ${x.sku_code}
                    </div>
                  </span>
                  <strong>${x.status}</strong>
                </div>
              `
            ).join("")}
          </div>
        `;

        detail.style.display = "block";
      });

    document
      .getElementById("openProductDetail")
      .addEventListener("click", async () => {
        const detailPanel =
          document.getElementById("productDetail");

        if (detailPanel.style.display !== "block") {
          return;
        }

        try {
          const productDetail = await api(
            `/api/v1/business/product-detail?tenant_id=__legacy__` +
            `&product_id=${encodeURIComponent(product.id)}`
          );

          const componentGroups = await Promise.all(
            skus.map(async (sku) => ({
              sku,
              components: await api(
                `/api/v1/business/components?tenant_id=__legacy__` +
                `&sku_id=${encodeURIComponent(sku.id)}`
              )
            }))
          );

          const extra = document.createElement("div");
          extra.style.marginTop = "18px";

          extra.innerHTML = `
            <div class="card">
              <h2>상품 스펙</h2>

              <div class="row">
                <span class="muted">규격</span>
                <strong>${productDetail.specification || "-"}</strong>
              </div>

              <div class="row">
                <span class="muted">용도</span>
                <strong>${productDetail.usage || "-"}</strong>
              </div>

              <div class="row">
                <span class="muted">설치 방식</span>
                <strong>${productDetail.installation_method || "-"}</strong>
              </div>

              <div class="row">
                <span class="muted">사용 조건</span>
                <strong>${productDetail.usage_conditions || "-"}</strong>
              </div>

              <div class="row">
                <span class="muted">주의사항</span>
                <strong>${productDetail.cautions || "-"}</strong>
              </div>
            </div>

            <div class="card" style="margin-top:18px">
              <h2>SKU별 구성품</h2>

              ${componentGroups.map(({sku, components}) => `
                <div style="
                  margin-top:16px;
                  padding-top:16px;
                  border-top:1px solid #253044
                ">
                  <strong>
                    ${sku.option_value || sku.name}
                  </strong>

                  ${components.map((item) => `
                    <div class="row">
                      <span>${item.name}</span>
                      <strong>
                        ${item.quantity} ${item.unit}
                      </strong>
                    </div>
                  `).join("")}
                </div>
              `).join("")}
            </div>
          `;

          detailPanel.appendChild(extra);

        } catch (error) {
          console.error(error);
        }
      });


    status.textContent = "Connected";
  } catch (error) {
    status.textContent = String(error);
  }
}

document
  .getElementById("loadDashboard")
  .addEventListener("click", connectDashboard);

restoreDashboardSession();
</script>

</body>
</html>
"""


@router.get(
    "/dashboard",
    response_class=HTMLResponse,
    include_in_schema=False,
)
def dashboard_page():
    return HTMLResponse(
        content=HTML,
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
