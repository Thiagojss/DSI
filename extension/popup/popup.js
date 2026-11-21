const API_BASE = "http://127.0.0.1:8000";
const apiStatus = document.getElementById("api-status");
const pageStatus = document.getElementById("page-status");
const captureButton = document.getElementById("capture-button");
const feedback = document.getElementById("feedback");

function showFeedback(message, type = "") {
  feedback.textContent = message;
  feedback.className = `feedback ${type}`;
}

async function checkBackend() {
  try {
    const response = await fetch(`${API_BASE}/health`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    apiStatus.textContent = `Backend conectado · ${data.version}`;
    apiStatus.className = "status status-ok";
    return true;
  } catch (_) {
    apiStatus.textContent = "Backend offline · inicie o servidor Python";
    apiStatus.className = "status status-error";
    return false;
  }
}

async function getActiveTab() {
  const tabs = await browser.tabs.query({ active: true, currentWindow: true });
  return tabs[0];
}

async function inspectPage() {
  try {
    const tab = await getActiveTab();
    const url = new URL(tab?.url || "about:blank");
    const isAliExpress = url.hostname === "aliexpress.com" || url.hostname.endsWith(".aliexpress.com");
    const isProduct = isAliExpress && /\/item\/(?:[^/]+\/)?\d+(?:\.html)?(?:[/?#]|$)/i.test(url.pathname);
    if (!isProduct) {
      pageStatus.textContent = "Abra uma página individual de produto (/item/ID.html).";
      captureButton.disabled = true;
      return;
    }
    pageStatus.textContent = "Produto do AliExpress identificado. Pronto para capturar.";
    captureButton.disabled = false;
  } catch (_) {
    pageStatus.textContent = "Não foi possível verificar esta página.";
    captureButton.disabled = true;
  }
}

captureButton.addEventListener("click", async () => {
  captureButton.disabled = true;
  showFeedback("Extraindo e validando os dados...");
  try {
    const tab = await getActiveTab();
    if (!tab?.id) throw new Error("Aba ativa não encontrada.");
    let product;
    try { product = await browser.tabs.sendMessage(tab.id, { action: "DSI_CAPTURE_PRODUCT" }); }
    catch (_) { throw new Error("Content script indisponível. Atualize a página do produto e tente novamente."); }
    if (product?.error) throw new Error(product.error);
    if (!product?.title || !product?.source_product_id) throw new Error("Os dados não passaram pela validação de produto.");

    const response = await fetch(`${API_BASE}/products`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(product)
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.detail || `Falha ao salvar (HTTP ${response.status}).`);
    showFeedback(`${result.message} Qualidade dos dados: ${result.data_quality}%.`, "success");
  } catch (error) {
    showFeedback(error.message || "Erro inesperado na captura.", "error");
  } finally {
    await inspectPage();
  }
});

(async () => { await Promise.all([checkBackend(), inspectPage()]); })();
