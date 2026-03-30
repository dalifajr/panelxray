const shell = document.getElementById("workspace-shell");
const initialDataNode = document.getElementById("workspace-initial-data");

if (!shell || !initialDataNode) {
  throw new Error("Workspace root node tidak ditemukan.");
}

const protocolGroups = {
  xray: ["vmess", "vless", "trojan", "shadowsocks"],
  ssh: ["ssh"],
  vmess: ["vmess"],
  vless: ["vless"],
  trojan: ["trojan"],
  shadowsocks: ["shadowsocks"],
};

const refs = {
  shell,
  menuToggle: document.getElementById("menu-toggle"),
  backdrop: document.getElementById("sidebar-backdrop"),
  serviceNav: document.getElementById("service-nav"),
  servicePicker: document.getElementById("service-picker"),
  workspaceTitle: document.getElementById("workspace-title"),
  quickActionGrid: document.getElementById("quick-action-grid"),
  metricGrid: document.getElementById("metric-grid"),
  serviceStatusGrid: document.getElementById("service-status-grid"),
  healthState: document.getElementById("health-state"),
  healthTime: document.getElementById("health-time"),
  healthBadge: document.getElementById("health-badge"),
  accountSearch: document.getElementById("account-search"),
  accountTableWrap: document.getElementById("account-table-wrap"),
  accountTableBody: document.getElementById("account-table-body"),
  accountCardGrid: document.getElementById("account-card-grid"),
  operationChipGrid: document.getElementById("operation-chip-grid"),
  mutationEmpty: document.getElementById("mutation-empty"),
  operationForm: document.getElementById("operation-form"),
  operationFormTitle: document.getElementById("operation-form-title"),
  operationFormFields: document.getElementById("operation-form-fields"),
  operationSubmit: document.getElementById("operation-submit"),
  operationReset: document.getElementById("operation-reset"),
  mutationResult: document.getElementById("mutation-result"),
  viewButtons: Array.from(document.querySelectorAll(".view-btn")),
  toastStack: document.getElementById("toast-stack"),
  legacyDashboardLink: document.getElementById("legacy-dashboard-link"),
  legacyManageLink: document.getElementById("legacy-manage-link"),
};

const initial = parseInitialData(initialDataNode.textContent || "{}");
const apiBase = deriveApiBase(shell.dataset.healthUrl || "/api/health");

const routes = {
  health: `${apiBase}/health`,
  stats: `${apiBase}/stats`,
  services: `${apiBase}/services`,
  serviceAccounts: (serviceKey) =>
    `${apiBase}/services/${encodeURIComponent(serviceKey)}/accounts`,
  serviceActionTemplate:
    shell.dataset.serviceActionUrlTemplate ||
    `${apiBase}/services/__service__/actions/__operation__`,
  workspaceTemplate: shell.dataset.workspaceUrlTemplate || "/workspace/__service__",
  dashboardTemplate: shell.dataset.dashboardUrlTemplate || "/dashboard/__service__",
  manageTemplate: shell.dataset.manageUrlTemplate || "/dashboard/__service__/accounts",
};

const state = {
  activeService:
    shell.dataset.activeService || initial.active_service_key || "xray",
  serviceCatalog: normalizeServiceCatalog(initial.service_catalog || []),
  accounts: Array.isArray(initial.accounts) ? initial.accounts : [],
  services: isObject(initial.services) ? initial.services : {},
  summary: isObject(initial.summary) ? initial.summary : {},
  checkedAt: String(initial.checked_at || ""),
  searchTerm: "",
  viewMode: "table",
  selectedOperation: "",
  prefillUsername: "",
  mutationBusy: false,
};

let refreshBusy = false;

init();

async function init() {
  wireSidebar();
  wireViewSwitch();
  wireSearch();
  wireServicePicker();
  wireOperationForm();

  renderServiceNav();
  renderServicePicker();
  renderQuickActions();
  renderMutationStudio();
  renderServiceStatuses();
  renderMetrics();
  renderAccounts();
  renderHealthStatus("loading", "Memuat status dari API...");

  await hydrateCatalog();
  await refreshWorkspace(true);

  window.setInterval(async () => {
    await refreshWorkspace(false);
  }, 30000);
}

function parseInitialData(raw) {
  try {
    return JSON.parse(raw);
  } catch (_error) {
    return {};
  }
}

function deriveApiBase(healthUrl) {
  return healthUrl.replace(/\/health\/?$/, "");
}

function isObject(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function normalizeServiceCatalog(catalog) {
  if (!Array.isArray(catalog)) {
    return [];
  }

  return catalog
    .filter((row) => row && row.key)
    .map((row) => ({
      key: String(row.key),
      label: String(row.label || row.key.toUpperCase()),
      description: String(row.description || ""),
      operation_count: Number(row.operation_count || 0),
      operations: Array.isArray(row.operations) ? row.operations : [],
      workspace_links: Array.isArray(row.workspace_links) ? row.workspace_links : [],
    }));
}

async function hydrateCatalog() {
  try {
    const rows = await fetchJson(routes.services);
    const normalized = normalizeServiceCatalog(rows);
    if (normalized.length) {
      state.serviceCatalog = normalized;
      if (!findService(state.activeService)) {
        state.activeService = normalized[0].key;
      }
      renderServiceNav();
      renderServicePicker();
      renderQuickActions();
      renderMutationStudio();
    }
  } catch (_error) {
    showToast("Catalog service memakai data lokal karena API belum siap.", "error");
  }
}

function wireSidebar() {
  const closeSidebar = () => {
    refs.shell.classList.remove("sidebar-open");
  };

  refs.menuToggle?.addEventListener("click", () => {
    refs.shell.classList.toggle("sidebar-open");
  });

  refs.backdrop?.addEventListener("click", closeSidebar);

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeSidebar();
    }
  });
}

function wireViewSwitch() {
  for (const button of refs.viewButtons) {
    button.addEventListener("click", () => {
      state.viewMode = button.dataset.view === "cards" ? "cards" : "table";
      for (const item of refs.viewButtons) {
        item.classList.toggle("active", item === button);
      }
      renderAccounts();
    });
  }
}

function wireSearch() {
  refs.accountSearch?.addEventListener("input", () => {
    state.searchTerm = String(refs.accountSearch.value || "").toLowerCase();
    renderAccounts();
  });
}

function wireServicePicker() {
  refs.servicePicker?.addEventListener("change", async () => {
    const selected = String(refs.servicePicker.value || "");
    if (selected && selected !== state.activeService) {
      await switchService(selected);
    }
  });
}

async function switchService(serviceKey) {
  state.activeService = serviceKey;
  state.selectedOperation = "";
  state.prefillUsername = "";
  refs.shell.dataset.activeService = serviceKey;
  clearMutationResult();

  updateWorkspaceHeading();
  renderServiceNav();
  renderServicePicker();
  renderQuickActions();
  renderMutationStudio();

  syncLegacyLinks();
  updateUrl(serviceKey);

  await refreshWorkspace(true);
}

function updateUrl(serviceKey) {
  const url = formatRoute(routes.workspaceTemplate, serviceKey);
  window.history.replaceState({}, "", url);
}

function formatRoute(template, serviceKey) {
  return template.replace("__service__", encodeURIComponent(serviceKey));
}

function formatServiceActionRoute(serviceKey, operationName) {
  return routes.serviceActionTemplate
    .replace("__service__", encodeURIComponent(serviceKey))
    .replace("__operation__", encodeURIComponent(operationName));
}

function findService(serviceKey) {
  return state.serviceCatalog.find((row) => row.key === serviceKey) || null;
}

function updateWorkspaceHeading() {
  const profile = findService(state.activeService);
  const label = profile ? profile.label : state.activeService.toUpperCase();
  if (refs.workspaceTitle) {
    refs.workspaceTitle.textContent = `Workspace ${label}`;
  }
}

function renderServiceNav() {
  if (!refs.serviceNav) {
    return;
  }

  refs.serviceNav.innerHTML = "";
  for (const row of state.serviceCatalog) {
    const link = document.createElement("a");
    link.href = formatRoute(routes.workspaceTemplate, row.key);
    link.className = "service-link";
    if (row.key === state.activeService) {
      link.classList.add("active");
    }
    link.innerHTML = `
      <span class="service-badge">${escapeHtml(row.key.slice(0, 2).toUpperCase())}</span>
      <span class="service-copy">
        <strong>${escapeHtml(row.label)}</strong>
        <small>${escapeHtml(String(row.operation_count))} aksi</small>
      </span>
    `;
    link.addEventListener("click", async (event) => {
      event.preventDefault();
      if (row.key !== state.activeService) {
        await switchService(row.key);
      }
      refs.shell.classList.remove("sidebar-open");
    });
    refs.serviceNav.appendChild(link);
  }
}

function renderServicePicker() {
  if (!refs.servicePicker) {
    return;
  }

  refs.servicePicker.innerHTML = "";
  for (const row of state.serviceCatalog) {
    const option = document.createElement("option");
    option.value = row.key;
    option.textContent = row.label;
    option.selected = row.key === state.activeService;
    refs.servicePicker.appendChild(option);
  }
}

function syncLegacyLinks() {
  if (refs.legacyDashboardLink) {
    refs.legacyDashboardLink.href = formatRoute(routes.dashboardTemplate, state.activeService);
  }
  if (refs.legacyManageLink) {
    refs.legacyManageLink.href = formatRoute(routes.manageTemplate, state.activeService);
  }
}

function renderQuickActions() {
  if (!refs.quickActionGrid) {
    return;
  }

  refs.quickActionGrid.innerHTML = "";

  const profile = findService(state.activeService);
  if (!profile) {
    return;
  }

  if (profile.operations.length > 0) {
    for (const operation of profile.operations.slice(0, 6)) {
      const action = document.createElement("button");
      action.type = "button";
      action.className = "quick-chip quick-button";
      action.textContent = String(operation.label || operation.name || "Aksi");
      action.addEventListener("click", () => {
        setSelectedOperation(String(operation.name || ""), { scroll: true });
      });
      refs.quickActionGrid.appendChild(action);
    }
    return;
  }

  if (profile.workspace_links.length > 0) {
    for (const item of profile.workspace_links.slice(0, 6)) {
      const target = String(item.service || "").trim().toLowerCase();
      if (!target) {
        continue;
      }

      const link = document.createElement("a");
      link.className = "quick-chip";
      link.href = formatRoute(routes.workspaceTemplate, target);
      link.textContent = String(item.label || target.toUpperCase());
      link.addEventListener("click", async (event) => {
        event.preventDefault();
        await switchService(target);
      });
      refs.quickActionGrid.appendChild(link);
    }
    return;
  }

  const fallback = document.createElement("a");
  fallback.className = "quick-chip";
  fallback.href = formatRoute(routes.manageTemplate, state.activeService);
  fallback.textContent = "Buka manajemen akun";
  refs.quickActionGrid.appendChild(fallback);
}

function wireOperationForm() {
  refs.operationForm?.addEventListener("submit", handleOperationSubmit);
  refs.operationReset?.addEventListener("click", () => {
    clearMutationResult();
    renderMutationStudio();
  });
}

function clearMutationResult() {
  if (!refs.mutationResult) {
    return;
  }
  refs.mutationResult.classList.add("hidden");
  refs.mutationResult.innerHTML = "";
}

function renderMutationStudio() {
  if (!refs.operationChipGrid || !refs.operationForm || !refs.mutationEmpty) {
    return;
  }

  refs.operationChipGrid.innerHTML = "";

  const profile = findService(state.activeService);
  const operations = Array.isArray(profile?.operations) ? profile.operations : [];
  if (!operations.length) {
    refs.operationForm.classList.add("hidden");
    refs.mutationEmpty.classList.remove("hidden");

    if (profile?.workspace_links?.length) {
      refs.mutationEmpty.textContent =
        "Workspace ini adalah hub. Pilih VMESS/VLESS/TROJAN/SHADOWSOCKS untuk menjalankan mutasi langsung.";
    } else {
      refs.mutationEmpty.textContent =
        "Service aktif belum memiliki operasi mutasi yang tersedia.";
    }
    return;
  }

  refs.mutationEmpty.classList.add("hidden");

  if (!operations.some((item) => String(item.name) === state.selectedOperation)) {
    state.selectedOperation = String(operations[0].name || "");
  }

  for (const operation of operations) {
    const name = String(operation.name || "");
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "operation-chip";
    if (name === state.selectedOperation) {
      chip.classList.add("active");
    }
    chip.textContent = String(operation.label || name || "Operation");
    chip.addEventListener("click", () => {
      setSelectedOperation(name);
    });
    refs.operationChipGrid.appendChild(chip);
  }

  const selected = operations.find(
    (item) => String(item.name || "") === state.selectedOperation
  );
  if (!selected) {
    refs.operationForm.classList.add("hidden");
    return;
  }

  refs.operationForm.classList.remove("hidden");
  renderOperationForm(selected);
}

function setSelectedOperation(operationName, options = {}) {
  const normalized = String(operationName || "").trim().toLowerCase();
  if (!normalized) {
    return;
  }

  state.selectedOperation = normalized;
  clearMutationResult();
  renderMutationStudio();

  if (options.scroll) {
    refs.operationForm?.scrollIntoView({ behavior: "smooth", block: "center" });
  }
}

function renderOperationForm(operation) {
  if (!refs.operationFormTitle || !refs.operationFormFields) {
    return;
  }

  refs.operationFormTitle.textContent = String(operation.label || "Form Mutasi");
  refs.operationFormFields.innerHTML = "";

  const fields = Array.isArray(operation.fields) ? operation.fields : [];
  if (!fields.length) {
    const text = document.createElement("p");
    text.className = "caption";
    text.textContent =
      "Operasi ini tidak membutuhkan input tambahan. Klik Jalankan Mutasi untuk proses.";
    refs.operationFormFields.appendChild(text);
    return;
  }

  for (const field of fields) {
    const fieldName = String(field.name || "").trim();
    if (!fieldName) {
      continue;
    }

    const wrapper = document.createElement("label");
    wrapper.className = "field-control";

    const label = document.createElement("span");
    label.textContent = String(field.label || fieldName);
    wrapper.appendChild(label);

    let value = "";
    if (fieldName === "username" && state.prefillUsername) {
      value = state.prefillUsername;
    } else if (field.value !== undefined && field.value !== null) {
      value = String(field.value);
    }

    const fieldType = String(field.type || "text").toLowerCase();
    if (fieldType === "select") {
      const select = document.createElement("select");
      select.name = fieldName;

      for (const option of field.options || []) {
        const optionNode = document.createElement("option");
        optionNode.value = String(option.value || "");
        optionNode.textContent = String(option.label || option.value || "");
        optionNode.selected = optionNode.value === value;
        select.appendChild(optionNode);
      }

      wrapper.appendChild(select);
    } else {
      const input = document.createElement("input");
      input.name = fieldName;
      input.type = fieldType === "number" ? "number" : "text";
      input.autocomplete = "off";
      input.value = value;

      if (field.placeholder) {
        input.placeholder = String(field.placeholder);
      }
      if (field.required) {
        input.required = true;
      }
      if (fieldType === "number" && field.min !== undefined) {
        input.min = String(field.min);
      }

      wrapper.appendChild(input);
    }

    refs.operationFormFields.appendChild(wrapper);
  }
}

function collectOperationPayload(operation) {
  const payload = {};
  const fields = Array.isArray(operation.fields) ? operation.fields : [];

  for (const field of fields) {
    const fieldName = String(field.name || "").trim();
    if (!fieldName) {
      continue;
    }

    const element = refs.operationForm?.elements.namedItem(fieldName);
    if (!element) {
      continue;
    }

    const rawValue = String(element.value || "").trim();
    const isRequired = Boolean(field.required);
    const fieldType = String(field.type || "text").toLowerCase();

    if (!rawValue) {
      if (isRequired) {
        throw new Error(`Field ${field.label || fieldName} wajib diisi.`);
      }
      continue;
    }

    if (fieldType === "number") {
      const numericValue = Number(rawValue);
      if (!Number.isFinite(numericValue)) {
        throw new Error(`Field ${field.label || fieldName} harus berupa angka.`);
      }

      if (field.min !== undefined && numericValue < Number(field.min)) {
        throw new Error(
          `Field ${field.label || fieldName} minimal ${String(field.min)}.`
        );
      }

      payload[fieldName] = Math.trunc(numericValue);
      continue;
    }

    payload[fieldName] = rawValue;
  }

  return payload;
}

function setMutationBusy(isBusy) {
  state.mutationBusy = isBusy;
  if (refs.operationSubmit) {
    refs.operationSubmit.disabled = isBusy;
    refs.operationSubmit.textContent = isBusy ? "Memproses..." : "Jalankan Mutasi";
  }
  if (refs.operationReset) {
    refs.operationReset.disabled = isBusy;
  }
}

async function handleOperationSubmit(event) {
  event.preventDefault();
  if (state.mutationBusy) {
    return;
  }

  const profile = findService(state.activeService);
  const operation = (profile?.operations || []).find(
    (item) => String(item.name || "") === state.selectedOperation
  );
  if (!operation) {
    showToast("Pilih operasi mutasi terlebih dahulu.", "error");
    return;
  }

  let payload;
  try {
    payload = collectOperationPayload(operation);
  } catch (error) {
    showToast(String(error.message || "Validasi form gagal."), "error");
    return;
  }

  const operationName = String(operation.name || "").toLowerCase();
  if (["delete", "suspend"].includes(operationName)) {
    const allowed = window.confirm(
      `Lanjutkan operasi ${String(operation.label || operationName)}?`
    );
    if (!allowed) {
      return;
    }
  }

  setMutationBusy(true);
  try {
    const response = await fetchJson(
      formatServiceActionRoute(state.activeService, operationName),
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      }
    );

    renderMutationResult(response.result || {});

    const updatedUsername = String(response.result?.username || "").trim();
    if (updatedUsername) {
      state.prefillUsername = updatedUsername;
    }

    showToast(response.message || "Mutasi berhasil diproses.");
    await refreshWorkspace(false);
  } catch (error) {
    showToast(String(error.message || "Mutasi gagal diproses."), "error");
  } finally {
    setMutationBusy(false);
  }
}

function renderMutationResult(result) {
  if (!refs.mutationResult) {
    return;
  }

  const details = isObject(result.details) ? result.details : {};
  const fields = Array.isArray(details.fields) ? details.fields.slice(0, 8) : [];
  const links = Array.isArray(details.links) ? details.links.slice(0, 6) : [];
  const safety = isObject(details.safety) ? details.safety : {};

  const fieldsHtml = fields.length
    ? fields
        .map(
          (item) =>
            `<div class="result-block"><strong>${escapeHtml(item.label || item.key || "Field")}</strong><span>${escapeHtml(item.value || "-")}</span></div>`
        )
        .join("")
    : '<p class="caption">Tidak ada field output tambahan.</p>';

  const linksHtml = links.length
    ? `<div class="result-links">${links
        .map(
          (link) =>
            `<a href="${escapeHtml(link)}" target="_blank" rel="noopener noreferrer">${escapeHtml(link)}</a>`
        )
        .join("")}</div>`
    : '<p class="caption">Tidak ada link konfigurasi terdeteksi.</p>';

  const safetyHtml = !safety.enabled
    ? '<p class="caption">Safety layer tidak aktif.</p>'
    : `<div class="result-grid">
        <div class="result-block"><strong>Preflight</strong><span>${escapeHtml(String(safety.preflight_ok ? "OK" : "skip"))}</span></div>
        <div class="result-block"><strong>Postcheck</strong><span>${escapeHtml(String(safety.postcheck_ok ? "OK" : "pending"))}</span></div>
        <div class="result-block"><strong>Snapshot</strong><span>${escapeHtml(String(safety.snapshot_id || "-"))}</span></div>
        <div class="result-block"><strong>Rollback</strong><span>${escapeHtml(String(safety.rollback_status || "not-needed"))}</span></div>
      </div>`;

  refs.mutationResult.classList.remove("hidden");
  refs.mutationResult.innerHTML = `
    <h4>Mutasi ${escapeHtml(String(result.operation || state.selectedOperation || "operation"))} berhasil</h4>
    <p class="caption">Protocol: ${escapeHtml(String(result.protocol || state.activeService))} | Username: ${escapeHtml(String(result.username || "-"))}</p>

    <h5>Safety Layer</h5>
    ${safetyHtml}

    <h5>Output Fields</h5>
    <div class="result-grid">${fieldsHtml}</div>

    <h5>Link Konfigurasi</h5>
    ${linksHtml}

    <h5>Log Ringkas</h5>
    <div class="result-pre">${escapeHtml(String(result.stdout_tail || "Tidak ada stdout."))}</div>
    <div class="result-pre">${escapeHtml(String(result.stderr_tail || "stderr bersih."))}</div>
  `;
}

function applyAccountPrefill(username) {
  const normalized = String(username || "").trim();
  if (!normalized) {
    return;
  }

  state.prefillUsername = normalized;
  const usernameInput = refs.operationForm?.querySelector('input[name="username"]');
  if (usernameInput) {
    usernameInput.value = normalized;
  }

  if (!state.selectedOperation) {
    setSelectedOperation("create");
  }

  showToast(`Username ${normalized} disiapkan untuk form mutasi.`);
}

function renderHealthStatus(status, checkedAtText) {
  if (refs.healthState) {
    refs.healthState.textContent = status === "healthy" ? "Healthy" : status === "degraded" ? "Degraded" : "Unknown";
  }

  if (refs.healthTime) {
    refs.healthTime.textContent = checkedAtText || "Belum ada timestamp pemeriksaan.";
  }

  if (refs.healthBadge) {
    refs.healthBadge.textContent = status;
    refs.healthBadge.classList.remove("healthy", "degraded", "error");
    if (status === "healthy" || status === "degraded") {
      refs.healthBadge.classList.add(status);
    } else {
      refs.healthBadge.classList.add("error");
    }
  }
}

function renderMetrics() {
  if (!refs.metricGrid) {
    return;
  }

  refs.metricGrid.innerHTML = "";
  const counts = summarizeVisibleAccounts(getVisibleAccounts());
  const cards = [
    ["Total", counts.total],
    ["Active", counts.active],
    ["Suspended", counts.suspended],
    ["SSH", counts.ssh],
    ["VMESS", counts.vmess],
    ["VLESS", counts.vless],
    ["TROJAN", counts.trojan],
    ["SS", counts.shadowsocks],
  ];

  for (const [label, value] of cards) {
    const card = document.createElement("article");
    card.className = "metric-card";
    card.innerHTML = `<span>${escapeHtml(label)}</span><strong>${escapeHtml(String(value))}</strong>`;
    refs.metricGrid.appendChild(card);
  }
}

function renderServiceStatuses() {
  if (!refs.serviceStatusGrid) {
    return;
  }

  refs.serviceStatusGrid.innerHTML = "";
  const entries = Object.entries(state.services || {});
  if (!entries.length) {
    refs.serviceStatusGrid.innerHTML = '<div class="caption">Status service belum tersedia.</div>';
    return;
  }

  for (const [serviceName, status] of entries) {
    const card = document.createElement("div");
    card.className = "service-state";
    card.innerHTML = `
      <span>${escapeHtml(serviceName)}</span>
      <strong class="${escapeHtml(String(status).toLowerCase())}">${escapeHtml(String(status))}</strong>
    `;
    refs.serviceStatusGrid.appendChild(card);
  }
}

function renderAccounts() {
  const rows = getVisibleAccounts().filter((row) => matchesSearch(row, state.searchTerm));

  if (state.viewMode === "cards") {
    refs.accountTableWrap?.classList.add("hidden");
    refs.accountCardGrid?.classList.remove("hidden");
  } else {
    refs.accountTableWrap?.classList.remove("hidden");
    refs.accountCardGrid?.classList.add("hidden");
  }

  renderAccountTable(rows);
  renderAccountCards(rows);
}

function renderAccountTable(rows) {
  if (!refs.accountTableBody) {
    return;
  }

  refs.accountTableBody.innerHTML = "";
  if (!rows.length) {
    refs.accountTableBody.innerHTML = '<tr><td colspan="5">Tidak ada akun yang cocok dengan filter saat ini.</td></tr>';
    return;
  }

  for (const row of rows) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHtml(row.protocol || "-")}</td>
      <td>${escapeHtml(row.username || "-")}</td>
      <td>${escapeHtml(row.expiry || "-")}</td>
      <td><span class="pill ${statusClass(row.status)}">${escapeHtml(row.status || "unknown")}</span></td>
      <td><button type="button" class="account-use-btn" data-username="${escapeHtml(row.username || "")}">Gunakan</button></td>
    `;

    const useButton = tr.querySelector(".account-use-btn");
    useButton?.addEventListener("click", () => {
      applyAccountPrefill(row.username || "");
    });

    refs.accountTableBody.appendChild(tr);
  }
}

function renderAccountCards(rows) {
  if (!refs.accountCardGrid) {
    return;
  }

  refs.accountCardGrid.innerHTML = "";
  if (!rows.length) {
    refs.accountCardGrid.innerHTML = '<div class="caption">Tidak ada akun pada mode card view.</div>';
    return;
  }

  for (const row of rows) {
    const card = document.createElement("article");
    card.className = "account-card";
    card.innerHTML = `
      <strong>${escapeHtml(row.username || "-")}</strong>
      <div class="account-meta">Protocol: ${escapeHtml(row.protocol || "-")}</div>
      <div class="account-meta">Expiry: ${escapeHtml(row.expiry || "-")}</div>
      <div><span class="pill ${statusClass(row.status)}">${escapeHtml(row.status || "unknown")}</span></div>
      <div><button type="button" class="account-use-btn">Gunakan Username</button></div>
    `;

    const useButton = card.querySelector(".account-use-btn");
    useButton?.addEventListener("click", () => {
      applyAccountPrefill(row.username || "");
    });

    refs.accountCardGrid.appendChild(card);
  }
}

function statusClass(status) {
  const normalized = String(status || "").toLowerCase();
  if (normalized === "active") {
    return "pill-active";
  }
  if (normalized === "suspended") {
    return "pill-suspended";
  }
  return "pill-unknown";
}

function matchesSearch(account, keyword) {
  if (!keyword) {
    return true;
  }

  const bucket = [account.protocol, account.username, account.expiry, account.status]
    .map((value) => String(value || "").toLowerCase())
    .join(" ");
  return bucket.includes(keyword);
}

function getVisibleAccounts() {
  const protocols = protocolGroups[state.activeService] || [state.activeService];
  return (state.accounts || []).filter((row) => protocols.includes(row.protocol));
}

function summarizeVisibleAccounts(rows) {
  const summary = {
    total: 0,
    active: 0,
    suspended: 0,
    ssh: 0,
    vmess: 0,
    vless: 0,
    trojan: 0,
    shadowsocks: 0,
  };

  for (const row of rows) {
    summary.total += 1;
    const protocol = String(row.protocol || "").toLowerCase();
    if (Object.prototype.hasOwnProperty.call(summary, protocol)) {
      summary[protocol] += 1;
    }

    const status = String(row.status || "").toLowerCase();
    if (status === "suspended") {
      summary.suspended += 1;
    } else {
      summary.active += 1;
    }
  }

  return summary;
}

async function refreshWorkspace(showErrorToast) {
  if (refreshBusy) {
    return;
  }

  refreshBusy = true;
  try {
    const [health, stats, accounts] = await Promise.all([
      fetchJson(routes.health),
      fetchJson(routes.stats),
      fetchJson(routes.serviceAccounts(state.activeService)),
    ]);

    state.services = isObject(health.services) ? health.services : state.services;
    state.checkedAt = String(health.checked_at || stats.checked_at || "");

    if (isObject(stats.services)) {
      state.services = stats.services;
    }

    state.summary = isObject(stats.accounts) ? stats.accounts : state.summary;
    state.accounts = Array.isArray(accounts) ? accounts : [];

    renderHealthStatus(String(health.status || "unknown"), formatTimestamp(state.checkedAt));
    renderServiceStatuses();
    renderMetrics();
    renderAccounts();
    syncLegacyLinks();
    updateWorkspaceHeading();
  } catch (error) {
    renderHealthStatus("error", "Gagal memuat API. Cek service web panel.");
    if (showErrorToast) {
      showToast(String(error.message || "Refresh workspace gagal."), "error");
    }
  } finally {
    refreshBusy = false;
  }
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    credentials: "same-origin",
    headers: {
      Accept: "application/json",
      ...(options.headers || {}),
    },
  });

  const contentType = String(response.headers.get("content-type") || "").toLowerCase();
  if (!contentType.includes("application/json")) {
    throw new Error("Respon API bukan JSON. Periksa konfigurasi reverse proxy /panel.");
  }

  const payload = await response.json();
  if (!response.ok || payload.ok === false) {
    throw new Error(payload.message || "Permintaan API gagal diproses.");
  }

  return payload;
}

function formatTimestamp(value) {
  if (!value) {
    return "Timestamp tidak tersedia.";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return `Terakhir dicek ${date.toLocaleString("id-ID")}`;
}

function showToast(message, mode = "info") {
  if (!refs.toastStack) {
    return;
  }

  const toast = document.createElement("div");
  toast.className = "toast";
  if (mode === "error") {
    toast.classList.add("error");
  }

  toast.textContent = message;
  refs.toastStack.appendChild(toast);

  window.setTimeout(() => {
    toast.remove();
  }, 3600);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
