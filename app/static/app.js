const $ = (sel) => document.querySelector(sel);
const state = { search: "", category: "", status: "", items: [], editing: null, stockFor: null, deleting: null };

const STATUS_LABEL = {
  ok: "In stock",
  low_stock: "Low stock",
  expiring: "Expiring soon",
  expired: "Expired",
};

const money = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

async function api(path, options = {}) {
  const res = await fetch("/api" + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
      else if (Array.isArray(body.detail)) {
        message = body.detail.map((e) => `${e.loc[e.loc.length - 1]}: ${e.msg}`).join(". ");
      }
    } catch (_) { /* keep default message */ }
    throw new Error(message);
  }
  return res.status === 204 ? null : res.json();
}

let toastTimer;
function toast(message, isError = false) {
  const el = $("#toast");
  el.textContent = message;
  el.className = "toast" + (isError ? " error" : "");
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.hidden = true), 3200);
}

function daysUntil(dateStr) {
  const today = new Date(new Date().toDateString());
  const target = new Date(dateStr + "T00:00:00");
  return Math.round((target - today) / 86400000);
}

function expiryText(dateStr) {
  const d = daysUntil(dateStr);
  if (d < 0) return `${-d} day${d === -1 ? "" : "s"} ago`;
  if (d === 0) return "Today";
  if (d <= 60) return `In ${d} day${d === 1 ? "" : "s"}`;
  return `In ${Math.round(d / 30)} months`;
}

function formatDate(dateStr) {
  return new Date(dateStr + "T00:00:00").toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

/* ---------- Loading ---------- */

async function loadStats() {
  const s = await api("/stats");
  const set = (id, n, warn) => {
    const el = $(id);
    el.textContent = n;
    el.classList.toggle("has", warn && n > 0);
  };
  set("#n-total", s.total, false);
  set("#n-low", s.low_stock, true);
  set("#n-expiring", s.expiring, true);
  set("#n-expired", s.expired, true);
  $("#stock-value").textContent = s.total ? `Stock on hand worth ${money.format(s.stock_value)}` : "";
}

async function loadCategories() {
  const cats = await api("/categories");
  const select = $("#category");
  select.innerHTML = '<option value="">All categories</option>' +
    cats.map((c) => `<option value="${esc(c)}">${esc(c)}</option>`).join("");
  select.value = cats.includes(state.category) ? state.category : "";
  state.category = select.value;
  $("#category-list").innerHTML = cats.map((c) => `<option value="${esc(c)}">`).join("");
}

async function loadMedicines() {
  const params = new URLSearchParams();
  if (state.search) params.set("search", state.search);
  if (state.category) params.set("category", state.category);
  if (state.status) params.set("status", state.status);
  const data = await api("/medicines?" + params);
  state.items = data.items;
  renderRows(data.total);
}

async function refresh() {
  try {
    await Promise.all([loadStats(), loadCategories()]);
    await loadMedicines();
  } catch (err) {
    toast("Could not load medicines. " + err.message, true);
  }
}

/* ---------- Rendering ---------- */

function renderRows(total) {
  const rows = $("#rows");
  rows.innerHTML = state.items.map((m) => `
    <tr class="st-${m.status}" data-id="${m.id}">
      <td>
        <div class="med-name">${esc(m.name)}</div>
        <div class="sub">${esc(m.generic_name || "")}${m.manufacturer ? (m.generic_name ? " · " : "") + esc(m.manufacturer) : ""}</div>
      </td>
      <td>${esc(m.category)}</td>
      <td>${esc(m.batch_number || "–")}</td>
      <td class="r"><span class="qty">${m.quantity}</span><div class="sub">reorder at ${m.reorder_level}</div></td>
      <td>${formatDate(m.expiry_date)}<div class="sub">${expiryText(m.expiry_date)}</div></td>
      <td><span class="pill ${m.status}">${STATUS_LABEL[m.status]}</span></td>
      <td>
        <div class="row-actions">
          <button class="btn small" data-act="stock" type="button">Stock</button>
          <button class="btn small" data-act="edit" type="button">Edit</button>
          <button class="btn small" data-act="delete" type="button">Delete</button>
        </div>
      </td>
    </tr>`).join("");

  const filtered = state.search || state.category || state.status;
  const empty = $("#empty");
  empty.hidden = state.items.length > 0;
  $("#empty-text").textContent = filtered
    ? "No medicines match these filters. Clear the search or pick another status."
    : "No medicines yet. Add one to start tracking stock and expiry dates.";
  $("#btn-empty-add").hidden = !!filtered;
  $(".table-wrap table").hidden = state.items.length === 0;
  $("#count").textContent = state.items.length ? `Showing ${state.items.length} of ${total} medicine${total === 1 ? "" : "s"}` : "";
}

/* ---------- Add / edit ---------- */

function openForm(medicine = null) {
  state.editing = medicine;
  const form = $("#form");
  form.reset();
  $("#form-error").hidden = true;
  $("#form-title").textContent = medicine ? "Edit medicine" : "Add medicine";
  $("#form-submit").textContent = "Save medicine";
  if (medicine) {
    for (const [key, value] of Object.entries(medicine)) {
      if (form.elements[key]) form.elements[key].value = value ?? "";
    }
  } else {
    form.elements.category.value = "General";
  }
  $("#dlg-form").showModal();
}

$("#form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.target;
  const data = Object.fromEntries(new FormData(form));
  for (const key of ["quantity", "reorder_level"]) data[key] = parseInt(data[key], 10) || 0;
  data.unit_price = parseFloat(data.unit_price) || 0;
  for (const key of ["generic_name", "manufacturer", "batch_number", "storage_notes"]) {
    data[key] = data[key].trim() || null;
  }
  const button = $("#form-submit");
  button.disabled = true;
  try {
    if (state.editing) {
      await api(`/medicines/${state.editing.id}`, { method: "PUT", body: JSON.stringify(data) });
      toast("Medicine updated");
    } else {
      await api("/medicines", { method: "POST", body: JSON.stringify(data) });
      toast("Medicine added");
    }
    $("#dlg-form").close();
    await refresh();
  } catch (err) {
    const box = $("#form-error");
    box.textContent = err.message;
    box.hidden = false;
  } finally {
    button.disabled = false;
  }
});

/* ---------- Stock ---------- */

async function openStock(medicine) {
  state.stockFor = medicine;
  const form = $("#stock-form");
  form.reset();
  $("#stock-error").hidden = true;
  $("#stock-sub").textContent = `${medicine.name}: ${medicine.quantity} in stock`;
  $("#history").innerHTML = "";
  $("#dlg-stock").showModal();
  try {
    const moves = await api(`/medicines/${medicine.id}/movements`);
    $("#history").innerHTML = moves.slice(0, 8).map((mv) => `
      <div><span>${esc(mv.reason || "No reason given")}</span><b>${mv.change > 0 ? "+" : ""}${mv.change}</b></div>`).join("");
  } catch (_) { /* history is optional */ }
}

$("#stock-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.target;
  const amount = parseInt(form.elements.amount.value, 10);
  const change = form.elements.dir.value === "remove" ? -amount : amount;
  try {
    await api(`/medicines/${state.stockFor.id}/stock`, {
      method: "POST",
      body: JSON.stringify({ change, reason: form.elements.reason.value.trim() || null }),
    });
    $("#dlg-stock").close();
    toast("Stock updated");
    await refresh();
  } catch (err) {
    const box = $("#stock-error");
    box.textContent = err.message;
    box.hidden = false;
  }
});

/* ---------- Delete ---------- */

function openDelete(medicine) {
  state.deleting = medicine;
  $("#delete-text").textContent = `${medicine.name} and its stock history will be removed permanently.`;
  $("#dlg-delete").showModal();
}

$("#dlg-delete form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await api(`/medicines/${state.deleting.id}`, { method: "DELETE" });
    $("#dlg-delete").close();
    toast("Medicine deleted");
    await refresh();
  } catch (err) {
    toast(err.message, true);
  }
});

/* ---------- Wiring ---------- */

document.querySelectorAll("[data-close]").forEach((btn) =>
  btn.addEventListener("click", () => btn.closest("dialog").close())
);

$("#btn-add").addEventListener("click", () => openForm());
$("#btn-empty-add").addEventListener("click", () => openForm());

$("#rows").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-act]");
  if (!button) return;
  const id = Number(button.closest("tr").dataset.id);
  const medicine = state.items.find((m) => m.id === id);
  if (!medicine) return;
  if (button.dataset.act === "edit") openForm(medicine);
  if (button.dataset.act === "stock") openStock(medicine);
  if (button.dataset.act === "delete") openDelete(medicine);
});

$("#shelf").addEventListener("click", (event) => {
  const item = event.target.closest(".shelf-item");
  if (!item) return;
  state.status = item.dataset.status;
  document.querySelectorAll(".shelf-item").forEach((el) => el.setAttribute("aria-pressed", String(el === item)));
  loadMedicines().catch((err) => toast(err.message, true));
});

let searchTimer;
$("#search").addEventListener("input", (event) => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    state.search = event.target.value.trim();
    loadMedicines().catch((err) => toast(err.message, true));
  }, 250);
});

$("#category").addEventListener("change", (event) => {
  state.category = event.target.value;
  loadMedicines().catch((err) => toast(err.message, true));
});

refresh();
