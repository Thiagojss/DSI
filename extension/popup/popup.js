const API_BASE = "http://127.0.0.1:8000";
let pairingToken = "";
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
let listingCandidates = [];
const BATCH_SIZE = 40;
const PAIR_STORAGE_KEY = "dsiPairingToken";
const validPairingToken = value => typeof value === "string" && /^[a-f0-9]{64}$/.test(value);

// Firefox pode rejeitar storage.local em certos perfis/ambientes de extensão.
// A segunda cópia permanece no armazenamento da ORIGEM DA EXTENSÃO (não da página).
// Nunca guardar tokens em páginas do AliExpress ou enviá-los para domínios externos.
function backupTokenRead() {
  try { return { token: globalThis.localStorage?.getItem(PAIR_STORAGE_KEY) || "", available: true }; }
  catch (error) { return { token: "", available: false, error }; }
}
function backupTokenSave(token) {
  try {
    if (!globalThis.localStorage) return false;
    globalThis.localStorage.setItem(PAIR_STORAGE_KEY, token);
    return globalThis.localStorage.getItem(PAIR_STORAGE_KEY) === token;
  } catch (_) { return false; }
}
function backupTokenRemove() {
  try { globalThis.localStorage?.removeItem(PAIR_STORAGE_KEY); return true; }
  catch (_) { return false; }
}
async function savePairingToken(token) {
  // Grava em ambos os armazenamentos, se possível; qualquer um deles basta.
  let nativeSaved = false;
  try {
    if (browser?.storage?.local?.set) {
      await browser.storage.local.set({ [PAIR_STORAGE_KEY]: token });
      const restored = await browser.storage.local.get(PAIR_STORAGE_KEY);
      nativeSaved = restored?.[PAIR_STORAGE_KEY] === token;
    }
  } catch (_) { /* aciona o armazenamento alternativo */ }
  const fallbackSaved = backupTokenSave(token);
  if (!nativeSaved && !fallbackSaved) {
    throw new Error("O Firefox não permitiu salvar a chave. Verifique permissões e armazenamento do perfil.");
  }
  return nativeSaved ? "Firefox" : "alternativo";
}
async function readPairingToken() {
  let nativeError = null;
  let nativeToken = "";
  try {
    if (!browser?.storage?.local?.get) throw new Error("browser.storage.local indisponível");
    const saved = await browser.storage.local.get(PAIR_STORAGE_KEY);
    nativeToken = saved?.[PAIR_STORAGE_KEY] || "";
  } catch (error) { nativeError = error; }
  if (validPairingToken(nativeToken)) {
    backupTokenSave(nativeToken);
    return { token: nativeToken, location: "Firefox" };
  }
  const fallback = backupTokenRead();
  if (validPairingToken(fallback.token)) {
    // Não bloqueia o usuário se a restauração do armazenamento nativo falhar.
    try { await browser?.storage?.local?.set?.({ [PAIR_STORAGE_KEY]: fallback.token }); }
    catch (_) { /* segue conectado via armazenamento alternativo */ }
    return { token: fallback.token, location: "alternativo" };
  }
  if (nativeError && !fallback.available) {
    return { token: "", error: "Armazenamento da extensão indisponível. Teste em uma janela normal do Firefox e confira about:debugging." };
  }
  if (nativeToken || fallback.token) return { token: "", error: "A chave armazenada está em formato inválido. Cole uma nova chave." };
  return { token: "" };
}
async function removePairingToken() {
  let nativeRemoved = false;
  try {
    if (browser?.storage?.local?.remove) {
      await browser.storage.local.remove(PAIR_STORAGE_KEY);
      nativeRemoved = true;
    }
  } catch (_) { /* ainda tenta apagar a cópia alternativa */ }
  const fallbackRemoved = backupTokenRemove();
  if (!nativeRemoved && !fallbackRemoved) throw new Error("Não foi possível remover a chave salva.");
}


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
      headers: { ...(options.body ? { "Content-Type": "application/json" } : {}), ...(options.headers || {}), "X-DSI-Token": pairingToken }
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
  if (!pairingToken) {
    backendAvailable = false;
    apiStatus.textContent = "Não conectado · informe a chave local uma vez";
    apiStatus.className = "status status-error";
    $("pair-status").textContent = "Não pareado";
    $("connection-help").hidden = false;
    updateCaptureState(); updateListingState();
    return false;
  }
  try {
    const data = await api("/health");
    await api("/monitoring/summary");
    apiStatus.textContent = `API conectada · v${data.version || "?"}`;
    apiStatus.className = "status status-ok";
    backendAvailable = true;
    $("pair-status").textContent = "Conectado";
    $("connection-help").hidden = true;
  } catch (error) {
    // Falhas de rede, reinicialização da API ou alteração da chave NÃO apagam
    // o pareamento salvo pelo usuário. Somente Desconectar pode removê-lo.
    backendAvailable = false;
    const invalid = /401|pareamento necessário/i.test(error.message || "");
    apiStatus.textContent = invalid
      ? "Chave salva · não aceita pela API atual"
      : "Chave salva · aplicativo local indisponível";
    apiStatus.className = "status status-error";
    $("pair-status").textContent = invalid ? "Verificar chave" : "Conexão pendente";
    $("connection-help").hidden = false;
  }
  updateCaptureState(); updateListingState();
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
  if (product.image_urls?.length > 1) {
    const photos = document.createElement('span');
    photos.textContent = `${product.image_urls.length} imagens do anúncio`;
    details.append(photos);
  }
  if (product.seller_rating != null || product.seller_positive_feedback_pct != null) {
    const sellerQuality = document.createElement('span');
    sellerQuality.textContent = [product.seller_rating != null ? `Nota da loja: ${product.seller_rating}/5` : null,
      product.seller_positive_feedback_pct != null ? `Feedback positivo: ${product.seller_positive_feedback_pct}%` : null].filter(Boolean).join(' · ');
    details.append(sellerQuality);
  }
  container.append(title, details);
}

async function refreshListingCandidates() {
  const result = await browser.tabs.sendMessage(currentTab.id, { action: "DSI_COLLECT_LISTING" });
  if (result?.error) throw new Error(result.error);
  listingCandidates = Array.isArray(result?.products) ? result.products : [];
  // Consultas paginadas evitam limite do endpoint; processa toda a lista presente no DOM.
  const blockedIds = new Set();
  if (backendAvailable) {
    for (let i = 0; i < listingCandidates.length; i += 1500) {
      const slice = listingCandidates.slice(i, i + 1500);
      const response = await api("/collection-eligibility", {
        method: "POST", body: JSON.stringify({ product_ids: slice.map(p => p.source_product_id).filter(Boolean) })
      });
      (response.blocked_ids || []).forEach(id => blockedIds.add(id));
    }
  }
  const eligible = listingCandidates.filter(p => p.source_product_id && !blockedIds.has(p.source_product_id));
  listingProducts = eligible.slice(0, BATCH_SIZE);
  const listingStatus = $("listing-status"), listingBadge = $("listing-badge"), listingPreview = $("listing-preview");
  listingStatus.textContent = `${listingCandidates.length} itens carregados · ${blockedIds.size} bloqueados por 24h · ${eligible.length} elegíveis · próximo lote: ${listingProducts.length}.` +
    (eligible.length === 0 ? " Role a página para carregar mais anúncios e clique em Atualizar lista." : "");
  listingBadge.textContent = `${eligible.length} disponíveis`;
  listingPreview.hidden = !listingProducts.length;
  listingPreview.textContent = listingProducts.slice(0, 5).map((p, i) => `${i+1}. ${p.title}`).join("\n") +
    (listingProducts.length > 5 ? `\n… e mais ${listingProducts.length-5} neste lote` : "");
  updateListingState();
}

async function inspectPage() {
  currentTab = await getActiveTab().catch(() => null);
  previewProduct = null; listingProducts = []; listingCandidates = [];
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
      await refreshListingCandidates();
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
  if (isCapturing || !backendAvailable || !currentTab?.url) return;
  isCapturing = true; collectListingButton.textContent = "Coletando..."; updateCaptureState(); updateListingState();
  $("collection-feedback").textContent = "Enviando lote para validação e deduplicação no DSI...";
  try {
    // Reconsulta no clique para evitar enviar um lote obsoleto após a rolagem.
    await refreshListingCandidates();
    if (!listingProducts.length) {
      $("collection-feedback").textContent = "Nenhum produto elegível neste momento. Role a página e atualize a lista.";
      return;
    }
    const result = await api("/collection-sessions", { method: "POST", body: JSON.stringify({ source_url: currentTab.url, products: listingProducts }) });
    $("collection-feedback").textContent = `Sessão #${result.session_id}: ${result.saved_new} novos, ${result.updated} atualizados, ${result.cooldown_skipped || 0} bloqueados por 24h e ${result.skipped} ignorados no total.`;
    $("collection-feedback").className = "feedback success";
    await loadMonitoring();
    try { await refreshListingCandidates(); } // próximo lote sem reabrir o popup
    catch (refreshError) { $("listing-status").textContent = "Lote salvo. Atualize a lista para continuar."; }
  } catch (error) {
    $("collection-feedback").textContent = error.message || "Não foi possível concluir a sessão.";
    $("collection-feedback").className = "feedback error";
  } finally { isCapturing = false; collectListingButton.textContent = "Coletar produtos desta página"; updateCaptureState(); updateListingState(); }
});

$("refresh-listing-button").addEventListener("click", async () => {
  if (isCapturing || !currentTab?.id || isAliExpressProduct(currentTab.url || "")) return;
  $("refresh-listing-button").disabled = true;
  try { await refreshListingCandidates(); }
  catch (error) { $("listing-status").textContent = error.message || "Erro ao reler os itens."; }
  finally { $("refresh-listing-button").disabled = false; }
});
$("refresh-button").addEventListener("click", refreshAll);
$("retry-button").addEventListener("click", refreshAll);

// A chave é persistida ANTES da tentativa de conexão: fechar o popup ou
// ficar offline jamais deve exigir colá-la novamente.
$("pair-save").addEventListener("click", async () => {
  const token = $("pair-token").value.trim().toLowerCase();
  if (!validPairingToken(token)) {
    $("pair-feedback").textContent = "Chave inválida. Copie os 64 caracteres em Configurações.";
    return;
  }
  const saveButton = $("pair-save");
  saveButton.disabled = true;
  try {
    const location = await savePairingToken(token);
    pairingToken = token;
    $("pair-token").value = "";
    $("pair-feedback").textContent = "Chave salva. Verificando a conexão...";
    const connected = await checkBackend();
    $("pair-feedback").textContent = connected
      ? `Conectado. Chave persistida no armazenamento ${location}.`
      : `Chave persistida no armazenamento ${location}. Inicie a API e clique em Reconectar.`;
    if (connected) await Promise.allSettled([loadMonitoring(), loadAlerts()]);
  } catch (error) {
    // Caso o perfil impeça persistência, ainda permite USAR a chave nesta sessão.
    pairingToken = token;
    $("pair-feedback").textContent = `${error.message} A conexão nesta sessão ainda pode funcionar.`;
    await checkBackend();
  } finally { saveButton.disabled = false; }
});
$("pair-remove").addEventListener("click", async () => {
  try {
    await removePairingToken();
    pairingToken = "";
    $("pair-token").value = "";
    $("pair-feedback").textContent = "Pareamento removido deste Firefox.";
    await checkBackend();
  } catch (error) {
    $("pair-feedback").textContent = error.message;
  }
});
async function restorePairing() {
  const saveButton = $("pair-save");
  saveButton.disabled = true;
  try {
    const result = await readPairingToken();
    pairingToken = result.token;
    if (pairingToken) $("pair-feedback").textContent = `Chave recuperada do armazenamento ${result.location}.`;
    else if (result.error) $("pair-feedback").textContent = result.error;
  } catch (error) {
    $("pair-feedback").textContent = `Não foi possível restaurar a chave: ${error.message}`;
  } finally { saveButton.disabled = false; }
  await Promise.allSettled([refreshAll(), inspectPage()]);
}
void restorePairing();
