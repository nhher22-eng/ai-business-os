from fastapi import APIRouter
from fastapi.responses import HTMLResponse


router = APIRouter()


HTML = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta
  name="viewport"
  content="width=device-width,initial-scale=1"
>
<title>AI Business OS — Operations</title>

<style>
:root {
  font-family:
    Inter,
    ui-sans-serif,
    system-ui,
    -apple-system,
    BlinkMacSystemFont,
    "Segoe UI",
    sans-serif;
  color: #e5e7eb;
  background: #090d14;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-height: 100vh;
  background:
    radial-gradient(
      circle at top right,
      #172033,
      #090d14 42%
    );
}

.shell {
  width: min(1040px, calc(100% - 32px));
  margin: 0 auto;
  padding: 42px 0 70px;
}

.eyebrow {
  color: #8fa5c4;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: .14em;
  text-transform: uppercase;
}

h1 {
  margin: 7px 0 5px;
  font-size: clamp(28px, 5vw, 45px);
  letter-spacing: -.04em;
}

.subtitle {
  margin: 0 0 26px;
  color: #94a3b8;
}

.grid {
  display: grid;
  grid-template-columns:
    repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
}

.card {
  background: rgba(15, 23, 42, .88);
  border: 1px solid #263247;
  border-radius: 18px;
  padding: 20px;
  box-shadow:
    0 18px 50px rgba(0, 0, 0, .25);
}

.card h2 {
  margin: 0 0 16px;
  font-size: 16px;
}

.field {
  margin-bottom: 13px;
}

label {
  display: block;
  margin-bottom: 6px;
  color: #9fb0c7;
  font-size: 12px;
  font-weight: 700;
}

input {
  width: 100%;
  border: 1px solid #334155;
  border-radius: 10px;
  padding: 11px 12px;
  background: #0b1220;
  color: #f8fafc;
  outline: none;
}

input:focus {
  border-color: #64748b;
}

.status {
  display: grid;
  gap: 10px;
}

.status-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  border-bottom: 1px solid #263247;
  padding-bottom: 10px;
}

.status-row:last-child {
  border-bottom: 0;
  padding-bottom: 0;
}

.k {
  color: #8fa5c4;
  font-size: 12px;
}

.v {
  font-weight: 800;
  text-align: right;
}

.badge {
  display: inline-flex;
  align-items: center;
  min-width: 76px;
  justify-content: center;
  border: 1px solid #3b4c64;
  border-radius: 999px;
  padding: 6px 10px;
  background: #131d2d;
  font-size: 12px;
  font-weight: 900;
}

.actions {
  display: grid;
  grid-template-columns:
    repeat(3, minmax(0, 1fr));
  gap: 9px;
}

.actions.two {
  grid-template-columns:
    repeat(2, minmax(0, 1fr));
}

button {
  border: 1px solid #3b4c64;
  border-radius: 11px;
  padding: 11px 10px;
  cursor: pointer;
  background: #182235;
  color: #f8fafc;
  font-weight: 800;
}

button:hover {
  background: #22304a;
}

button.primary {
  background: #e2e8f0;
  color: #111827;
}

button.primary:hover {
  background: #f8fafc;
}

button.danger {
  border-color: #7f1d1d;
  background: #451a1a;
}

button.danger:hover {
  background: #621b1b;
}

button:disabled {
  cursor: wait;
  opacity: .55;
}

.log {
  min-height: 96px;
  margin-top: 16px;
  border-radius: 12px;
  background: #070b11;
  border: 1px solid #202b3d;
  padding: 13px;
  color: #aebdd1;
  font: 12px/1.55
    ui-monospace,
    SFMono-Regular,
    Menlo,
    Consolas,
    monospace;
  white-space: pre-wrap;
  word-break: break-word;
}

.note {
  margin-top: 12px;
  color: #718096;
  font-size: 11px;
}

@media (max-width: 620px) {
  .actions {
    grid-template-columns: 1fr;
  }

  .actions.two {
    grid-template-columns: 1fr;
  }
}
</style>
</head>

<body>
<div class="shell">

  <div class="eyebrow">
    AI Business OS / Operations Control
  </div>

  <h1>Agent Control</h1>

  <p class="subtitle">
    Authenticated manual runtime control for tenant automation
    and individual agents.
  </p>

  <div class="grid">

    <section class="card">
      <h2>Operator Session</h2>

      <div class="field">
        <label for="token">
          Bearer token
        </label>
        <input
          id="token"
          type="password"
          autocomplete="off"
          placeholder="AGENT_CONTROL_API_TOKEN"
        >
      </div>

      <div class="field">
        <label for="operator">
          Operator ID
        </label>
        <input
          id="operator"
          value="operations-dashboard"
          maxlength="128"
        >
      </div>

      <div class="field">
        <label for="tenant">
          Tenant ID
        </label>
        <input
          id="tenant"
          value="__legacy__"
          maxlength="128"
        >
      </div>

      <div class="field">
        <label for="agent">
          Agent ID
        </label>
        <input
          id="agent"
          value="__legacy_default_agent__"
          maxlength="128"
        >
      </div>

      <button
        class="primary"
        style="width:100%"
        onclick="refreshStatus()"
      >
        Authenticate / Refresh
      </button>

      <div class="note">
        The token is kept only in this page's password field.
        It is not embedded by the server.
      </div>
    </section>

    <section class="card">
      <h2>Runtime State</h2>

      <div class="status">
        <div class="status-row">
          <div class="k">Tenant automation</div>
          <div
            class="v badge"
            id="tenantState"
          >
            UNKNOWN
          </div>
        </div>

        <div class="status-row">
          <div class="k">Agent desired state</div>
          <div
            class="v badge"
            id="agentState"
          >
            UNKNOWN
          </div>
        </div>

        <div class="status-row">
          <div class="k">Effective state</div>
          <div
            class="v badge"
            id="effectiveState"
          >
            UNKNOWN
          </div>
        </div>

        <div class="status-row">
          <div class="k">Agent version</div>
          <div
            class="v"
            id="agentVersion"
          >
            -
          </div>
        </div>

        <div class="status-row">
          <div class="k">Tenant version</div>
          <div
            class="v"
            id="tenantVersion"
          >
            -
          </div>
        </div>
      </div>
    </section>

    <section class="card">
      <h2>Agent ON / PAUSE / OFF</h2>

      <div class="actions">
        <button onclick="setAgent('on')">
          ON
        </button>

        <button onclick="setAgent('paused')">
          PAUSE
        </button>

        <button
          class="danger"
          onclick="setAgent('off')"
        >
          OFF
        </button>
      </div>
    </section>

    <section class="card">
      <h2>Tenant Automation</h2>

      <div class="actions two">
        <button
          class="danger"
          onclick="setTenant(true)"
        >
          PAUSE ALL
        </button>

        <button onclick="setTenant(false)">
          RESUME ALL
        </button>
      </div>
    </section>

  </div>

  <section class="card" style="margin-top:16px">
    <h2>Real Business Workspace</h2>

    <div class="status">
      <div class="status-row">
        <div class="k">Workspace</div>
        <div class="v" id="workspaceName">-</div>
      </div>

      <div class="status-row">
        <div class="k">Mode</div>
        <div class="v badge" id="workspaceMode">UNKNOWN</div>
      </div>

      <div class="status-row">
        <div class="k">Product</div>
        <div class="v" id="productName">-</div>
      </div>

      <div class="status-row">
        <div class="k">Sales channel</div>
        <div class="v" id="salesChannel">-</div>
      </div>

      <div class="status-row">
        <div class="k">SKU</div>
        <div class="v" id="skuList">-</div>
      </div>
    </div>

    <button
      class="primary"
      style="width:100%;margin-top:16px"
      onclick="loadBusinessData()"
    >
      Load Business Data
    </button>
  </section>

  <div
    id="log"
    class="log"
  >
Ready.
  </div>
</div>

<script>
const $ = (id) => document.getElementById(id);

function values() {
  return {
    token: $("token").value.trim(),
    operator: $("operator").value.trim()
      || "operations-dashboard",
    tenant: $("tenant").value.trim(),
    agent: $("agent").value.trim()
  };
}

function headers(json = false) {
  const v = values();

  if (!v.token) {
    throw new Error("Bearer token is required.");
  }

  const h = {
    "Authorization": `Bearer ${v.token}`,
    "X-Operator-ID": v.operator
  };

  if (json) {
    h["Content-Type"] = "application/json";
  }

  return h;
}

function endpoint(path) {
  const v = values();

  if (!v.tenant || !v.agent) {
    throw new Error(
      "Tenant ID and Agent ID are required."
    );
  }

  return (
    "/api/v1/operations/control/" +
    path +
    "?tenant_id=" +
    encodeURIComponent(v.tenant) +
    "&agent_id=" +
    encodeURIComponent(v.agent)
  );
}

function showLog(message) {
  $("log").textContent = message;
}

function render(data) {
  $("tenantState").textContent =
    data.tenant_paused ? "PAUSED" : "RUNNING";

  $("agentState").textContent =
    String(data.desired_state).toUpperCase();

  $("effectiveState").textContent =
    String(data.effective_state).toUpperCase();

  $("agentVersion").textContent =
    data.agent.version;

  $("tenantVersion").textContent =
    data.tenant.version;
}

async function request(url, options = {}) {
  const response = await fetch(url, options);

  let data;

  try {
    data = await response.json();
  } catch (_) {
    data = {
      detail: "Non-JSON response"
    };
  }

  if (!response.ok) {
    throw new Error(
      `HTTP ${response.status}: ` +
      JSON.stringify(data)
    );
  }

  return data;
}

async function refreshStatus() {
  try {
    showLog("Refreshing control state...");

    const data = await request(
      endpoint("status"),
      {
        headers: headers(false)
      }
    );

    render(data);
    showLog(
      "Authenticated.\n" +
      JSON.stringify(data, null, 2)
    );
  } catch (error) {
    showLog(String(error));
  }
}

async function setAgent(state) {
  try {
    showLog(
      `Changing agent desired_state -> ${state} ...`
    );

    const data = await request(
      endpoint("agent"),
      {
        method: "PUT",
        headers: headers(true),
        body: JSON.stringify({
          desired_state: state
        })
      }
    );

    render(data);
    showLog(
      "Agent control updated.\n" +
      JSON.stringify(data, null, 2)
    );
  } catch (error) {
    showLog(String(error));
  }
}

async function setTenant(paused) {
  try {
    showLog(
      `Changing tenant paused -> ${paused} ...`
    );

    const data = await request(
      endpoint("tenant"),
      {
        method: "PUT",
        headers: headers(true),
        body: JSON.stringify({
          paused: paused
        })
      }
    );

    render(data);
    showLog(
      "Tenant control updated.\n" +
      JSON.stringify(data, null, 2)
    );
  } catch (error) {
    showLog(String(error));
  }
}

async function loadBusinessData() {
  try {
    showLog("Loading real business data...");

    const v = values();

    const workspaces = await request(
      "/api/v1/business/workspaces?tenant_id=" +
      encodeURIComponent(v.tenant),
      { headers: headers(false) }
    );

    const workspace = workspaces.find(
      (x) => x.slug === "commerce-ai"
    ) || workspaces[0];

    if (!workspace) {
      throw new Error("No business workspace found.");
    }

    const products = await request(
      "/api/v1/business/products?tenant_id=" +
      encodeURIComponent(v.tenant) +
      "&workspace_id=" +
      encodeURIComponent(workspace.id),
      { headers: headers(false) }
    );

    const product = products.find(
      (x) => x.product_code === "IRRIGATION-8MM-KIT"
    ) || products[0];

    if (!product) {
      throw new Error("No product found.");
    }

    const skus = await request(
      "/api/v1/business/skus?tenant_id=" +
      encodeURIComponent(v.tenant) +
      "&product_id=" +
      encodeURIComponent(product.id),
      { headers: headers(false) }
    );

    $("workspaceName").textContent = workspace.name;
    $("workspaceMode").textContent =
      String(workspace.mode).toUpperCase();
    $("productName").textContent = product.name;
    $("salesChannel").textContent =
      product.sales_channel || "-";
    $("skuList").textContent =
      skus.map((x) => x.option_value || x.name).join(" / ");

    showLog(
      "Business data loaded.\n" +
      JSON.stringify(
        { workspace, product, skus },
        null,
        2
      )
    );
  } catch (error) {
    showLog(String(error));
  }
}

</script>

</body>
</html>
"""


@router.get(
    "/operations",
    response_class=HTMLResponse,
    include_in_schema=False,
)
def operations_page():
    return HTMLResponse(
        content=HTML,
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
