const API_BASE = "http://127.0.0.1:8000";
const $ = id => document.getElementById(id);
const apiStatus = $("api-status");
const pageStatus = $("page-status");
const pageBadge = $("page-badge");
const captureButton = $("capture-button");
const collectListingButton = $("collect-listing-button");
const feedback = $("feedback");
let backendAvailable = false;
let currentTab = null;
let previewProduct = null;
let isCapturing = false;
let listingProducts = [];

function showFeedback(message, type = "") {
  feedback.textContent = message;
  feedback.className = `feedback ${type}`;
}

async function api(path, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8000);
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      signal: controller.signal,
      headers: { ...(options.body ? { "Content-Type": "application/json" } : {}), ...(options.headers || {}) }
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = typeof payload.detail === "string" ? payload.detail : `Erro HTTP ${response.status}`;
      throw new Error(detail);
    }
    return payload;
  } catch (error) {
    if (error.name === "AbortError") throw new Error("A API demorou para responder. Verifique se o servidor está ativo.");
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

async function checkBackend() {
  try {
    const data = await api("/health");
    apiStatus.textContent = `API conectada · v${data.version || "?"}`;
    apiStatus.className = "status status-ok";
    backendAvailable = true;
  } catch (_) {
    apiStatus.textContent = "API desconectada · inicie o servidor";
    apiStatus.className = "status status-error";
    backendAvailable = false;
  }
  updateCaptureState();
  updateListingState();
  return backendAvailable;
}

async function getActiveTab() {
  const tabs = await browser.tabs.query({ active: true, currentWindow: true });
  return tabs[0] || null;
}

function isAliExpressProduct(urlString) {
  try {
    const url = new URL(urlString);
    const host = url.hostname.toLowerCase();
    return (host === "aliexpress.com" || host.endsWith(".aliexpress.com")) &&
      /\/item\/(?:[^/]+\/)?\d+(?:\.html)?(?:[/?#]|$)/i.test(url.pathname);
  } catch (_) { return false; }
}

function updateCaptureState() {
  captureButton.disabled = !backendAvailable || !currentTab?.id || !previewProduct || isCapturing;
}

function updateListingState() {
  collectListingButton.disabled = !backendAvailable || !currentTab?.id || !listingProducts.length || isCapturing;
}

function formatPrice(value, currency) {
  if (value == null || !currency) return "Preço não identificado";
  try { return new Intl.NumberFormat("pt-BR", { style: "currency", currency }).format(value); }
  catch (_) { return `${value} ${currency}`; }
}

function formatDate(value) {
  if (!value) return "Data indisponível";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Data indisponível" : date.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

function renderPreview(product) {
  const container = $("product-preview");
  container.replaceChildren();
  const title = document.createElement("p");
  title.className = "product-title";
  title.textContent = product.title;
  const details = document.createElement("div");
  details.className = "product-details";
  const price = document.createElement("strong");
  price.textContent = formatPrice(product.price, product.currency);
  const seller = document.createElement("span");
  seller.textContent = product.seller_name ? `Vendedor: ${product.seller_name}` : "Vendedor não identificado";
  details.append(price, seller);
  container.append(title, details);
}

async function inspectPage() {
  currentTab = await getActiveTab().catch(() => null);
  previewProduct = null; listingProducts = [];
  const listingStatus = $("listing-status"), listingBadge = $("listing-badge"), listingPreview = $("listing-preview");
  listingPreview.hidden = true; listingPreview.textContent = "";
  if (!currentTab?.id || !/aliexpress\.com$/i.test(new URL(currentTab.url || "https://invalid/").hostname) && !/\.aliexpress\.com$/i.test(new URL(currentTab.url || "https://invalid/").hostname)) {
    pageStatus.textContent = "Abra uma página individual de produto do AliExpress para começar.";
    pageBadge.textContent = "Página não compatível"; pageBadge.className = "badge";
    listingStatus.textContent = "Abra uma página de busca ou categoria do AliExpress."; listingBadge.textContent = "Página não compatível";
    updateCaptureState(); updateListingState(); return;
  }
  const isProduct = isAliExpressProduct(currentTab.url || "");
  if (isProduct) {
    pageBadge.textContent = "Produto identificado"; pageBadge.className = "badge ready";
    pageStatus.textContent = "Lendo as informações disponíveis na página...";
    try {
      const result = await browser.tabs.sendMessage(currentTab.id, { action: "DSI_PREVIEW_PRODUCT" });
      if (result?.error) throw new Error(result.error);
      if (!result?.title || !result?.source_product_id) throw new Error("Não foi possível confirmar os dados do produto.");
      previewProduct = result; renderPreview(result); pageStatus.textContent = "Confira os dados e adicione o produto ao seu catálogo.";
    } catch (error) { pageStatus.textContent = error.message || "Atualize a aba do AliExpress e tente novamente."; }
    listingStatus.textContent = "Você está em uma página individual. Para garimpar em lote, abra uma busca ou categoria.";
  } else {
    pageStatus.textContent = "Esta é uma listagem. Use a sessão de garimpo abaixo para coletar os produtos visíveis.";
    pageBadge.textContent = "Página de listagem"; pageBadge.className = "badge ready";
    try {
      const result = await browser.tabs.sendMessage(currentTab.id, { action: "DSI_COLLECT_LISTING" });
      if (result?.error) throw new Error(result.error);
      listingProducts = Array.isArray(result?.products) ? result.products : [];
      listingStatus.textContent = listingProducts.length ? `${listingProducts.length} produto(s) identificados. A prévia inclui somente os itens carregados nesta página.` : "Nenhum produto reconhecido. Role a página para carregar mais itens ou tente outra listagem.";
      listingBadge.textContent = `${listingProducts.length} encontrados`;
      listingPreview.hidden = false;
      listingPreview.textContent = listingProducts.slice(0,5).map((item,i)=>`${i+1}. ${item.title}${item.price!=null?` · ${item.price} ${item.currency||""}`:""}`).join("\n") + (listingProducts.length>5?`\n… e mais ${listingProducts.length-5}`:"");
    } catch (error) { listingStatus.textContent = error.message || "Atualize a aba do AliExpress e tente novamente."; listingBadge.textContent = "Falha na leitura"; }
  }
  updateCaptureState(); updateListingState();
}

async function loadHistory(productId) {
  const panel = $("history-panel");
  const content = $("history-content");
  panel.hidden = false;
  content.textContent = "Carregando histórico...";
  try {
    const rows = await api(`/products/${productId}/history?limit=6`);
    $("history-count").textContent = `${rows.length} registro(s)`;
    content.replaceChildren();
    if (!rows.length) {
      const empty = document.createElement("p");
      empty.className = "empty";
      empty.textContent = "Ainda não há observações de preço.";
      content.append(empty);
      return;
    }
    [...rows].reverse().forEach(row => {
      const line = document.createElement("div");
      line.className = "history-row";
      const date = document.createElement("span");
      date.className = "history-date";
      date.textContent = formatDate(row.collected_at);
      const price = document.createElement("strong");
      price.className = "history-price";
      price.textContent = formatPrice(row.price ?? row.price_min, row.currency);
      line.append(date, price);
      content.append(line);
    });
  } catch (error) {
    content.textContent = `Histórico indisponível: ${error.message}`;
  }
}

async function loadMonitoring() {
  try {
    const summary = await api("/monitoring/summary");
    $("metric-products").textContent = summary.products_with_history ?? 0;
    $("metric-observations").textContent = summary.observations ?? 0;
    $("metric-alerts").textContent = summary.unread_alerts ?? 0;
    $("monitoring-note").textContent = summary.note || "O histórico é atualizado por novas capturas.";
  } catch (error) {
    $("monitoring-note").textContent = `Indicadores indisponíveis: ${error.message}`;
  }
}

async function loadAlerts() {
  const list = $("alerts-list");
  try {
    const alerts = await api("/alerts?limit=5&unread_only=true");
    $("alerts-caption").textContent = `${alerts.length} pendente(s)`;
    list.replaceChildren();
    if (!alerts.length) {
      const empty = document.createElement("p");
      empty.className = "empty";
      empty.textContent = "Tudo em dia. Nenhum alerta pendente.";
      list.append(empty);
      return;
    }
    alerts.forEach(alert => {
      const row = document.createElement("div");
      row.className = "alert-row";
      const main = document.createElement("div");
      main.className = "alert-main";
      const title = document.createElement("span");
      title.className = "alert-title";
      title.textContent = alert.product_title || `Produto #${alert.product_id}`;
      const message = document.createElement("span");
      message.className = "alert-message";
      message.textContent = `${alert.message} · ${formatDate(alert.created_at)}`;
      main.append(title, message);
      const read = document.createElement("button");
      read.type = "button";
      read.className = "read-button";
      read.textContent = "Marcar lido";
      read.addEventListener("click", async () => {
        read.disabled = true;
        try {
          await api(`/alerts/${alert.id}/read`, { method: "PUT" });
          await Promise.all([loadAlerts(), loadMonitoring()]);
        } catch (error) {
          read.disabled = false;
          showFeedback(`Falha ao atualizar alerta: ${error.message}`, "error");
        }
      });
      row.append(main, read);
      list.append(row);
    });
  } catch (error) {
    list.textContent = `Alertas indisponíveis: ${error.message}`;
  }
}

async function refreshAll() {
  const refresh = $("refresh-button");
  refresh.disabled = true;
  await checkBackend();
  if (backendAvailable) await Promise.all([loadMonitoring(), loadAlerts()]);
  refresh.disabled = false;
}

captureButton.addEventListener("click", async () => {
  if (isCapturing || !previewProduct || !backendAvailable) return;
  isCapturing = true;
  captureButton.textContent = "Adicionando...";
  updateCaptureState();
  showFeedback("Validando e salvando o produto e a observação de preço...");
  try {
    const result = await api("/products", { method: "POST", body: JSON.stringify(previewProduct) });
    showFeedback(`${result.message} Qualidade dos dados: ${result.data_quality}%.`, "success");
    await Promise.all([loadHistory(result.id), loadMonitoring(), loadAlerts()]);
  } catch (error) {
    showFeedback(error.message || "Não foi possível salvar o produto.", "error");
  } finally {
    isCapturing = false;
    captureButton.textContent = "Adicionar ao DSI";
    updateCaptureState();
  }
});

collectListingButton.addEventListener("click", async () => {
  if (isCapturing || !listingProducts.length || !backendAvailable || !currentTab?.url) return;
  isCapturing = true; collectListingButton.textContent = "Coletando..."; updateCaptureState(); updateListingState();
  $("collection-feedback").textContent = "Enviando lote para validação e deduplicação no DSI...";
  try {
    const result = await api("/collection-sessions", { method: "POST", body: JSON.stringify({ source_url: currentTab.url, products: listingProducts }) });
    $("collection-feedback").textContent = `Sessão #${result.session_id} concluída: ${result.saved_new} novos, ${result.updated} atualizados e ${result.skipped} ignorados.`;
    $("collection-feedback").className = "feedback success";
    await loadMonitoring();
  } catch (error) {
    $("collection-feedback").textContent = error.message || "Não foi possível concluir a sessão.";
    $("collection-feedback").className = "feedback error";
  } finally { isCapturing = false; collectListingButton.textContent = "Coletar produtos desta página"; updateCaptureState(); updateListingState(); }
});

$("refresh-button").addEventListener("click", refreshAll);
$("retry-button").addEventListener("click", refreshAll);

(async () => {
  await Promise.all([refreshAll(), inspectPage()]);
})();
