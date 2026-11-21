(() => {
  const clean = value => typeof value === "string" ? value.replace(/\s+/g, " ").trim() : null;
  const first = (...values) => values.map(clean).find(value => value) || null;
  const meta = selector => document.querySelector(selector)?.getAttribute("content") || null;
  const text = selector => document.querySelector(selector)?.textContent || null;

  function productIdFromUrl(url = location.href) {
    if (!/aliexpress\.com$/i.test(location.hostname) && !/\.aliexpress\.com$/i.test(location.hostname)) return null;
    return url.match(/\/item\/(?:[^/]+\/)?(\d+)(?:\.html)?(?:[/?#]|$)/i)?.[1] || null;
  }

  function flattenJson(value, output = []) {
    if (!value || typeof value !== "object") return output;
    if (Array.isArray(value)) value.forEach(item => flattenJson(item, output));
    else {
      output.push(value);
      if (value["@graph"]) flattenJson(value["@graph"], output);
      if (value.itemListElement) flattenJson(value.itemListElement, output);
    }
    return output;
  }

  function readProductJsonLd() {
    for (const script of document.querySelectorAll('script[type="application/ld+json"]')) {
      try {
        const nodes = flattenJson(JSON.parse(script.textContent));
        const found = nodes.find(node => {
          const type = node?.["@type"];
          return type === "Product" || (Array.isArray(type) && type.includes("Product"));
        });
        if (found) return found;
      } catch (_) { /* bloco estruturado inválido: tenta o próximo */ }
    }
    return null;
  }

  function findEmbeddedProduct() {
    // Alguns layouts expõem dados estruturados em scripts de estado. Só aceitamos
    // propriedades com nomes claros; não tentamos executar scripts da página.
    const scripts = [...document.scripts].filter(s => s.textContent && s.textContent.length < 2_000_000);
    for (const script of scripts) {
      const source = script.textContent;
      if (!source.includes('"title"') && !source.includes('"subject"')) continue;
      const title = source.match(/"(?:title|subject)"\s*:\s*"((?:\\.|[^"\\]){8,500})"/);
      const price = source.match(/"(?:act商品价格|minPrice|salePrice|formattedActivityPrice)"\s*:\s*"?([0-9]+(?:\.[0-9]+)?)/i);
      if (title || price) return { title: title?.[1]?.replace(/\\u([\da-f]{4})/gi, (_, h) => String.fromCharCode(parseInt(h, 16))).replace(/\\"/g, '"'), price: price?.[1] };
    }
    return null;
  }

  function toNumber(value) {
    if (value == null) return null;
    let raw = String(value).replace(/[^\d,.-]/g, "");
    if (!raw) return null;
    if (raw.includes(",") && raw.includes(".")) raw = raw.lastIndexOf(",") > raw.lastIndexOf(".") ? raw.replace(/\./g, "").replace(",", ".") : raw.replace(/,/g, "");
    else if (raw.includes(",")) raw = raw.replace(",", ".");
    const number = Number(raw);
    return Number.isFinite(number) ? number : null;
  }

  function categoryData() {
    const nodes = [...document.querySelectorAll('nav a, [class*="breadcrumb"] a, [class*="Breadcrumb"] a')]
      .map(node => clean(node.textContent)).filter(Boolean)
      .filter(label => !/^(home|início|aliexpress)$/i.test(label));
    const unique = [...new Set(nodes)].slice(-12);
    return { category: unique.at(-1) || null, category_path: unique };
  }

  function captureProduct() {
    const sourceProductId = productIdFromUrl();
    if (!sourceProductId) throw new Error("Esta não é uma página individual de produto. Abra um endereço /item/ID.html.");

    const json = readProductJsonLd();
    const embedded = findEmbeddedProduct();
    const offer = Array.isArray(json?.offers) ? json.offers[0] : json?.offers;
    const title = first(
      meta('meta[property="og:title"]'), meta('meta[name="title"]'),
      text('h1[data-pl="product-title"]'), text('h1'), json?.name, embedded?.title
    );
    if (!title || title.length < 3 || /comprar eletrônicos|aliexpress\.com/i.test(title)) {
      throw new Error("Não foi possível confirmar o título do produto nesta página. Atualize-a e tente novamente.");
    }

    const priceRaw = first(
      meta('meta[property="product:price:amount"]'), meta('meta[itemprop="price"]'),
      offer?.price != null ? String(offer.price) : null, embedded?.price,
      text('[class*="price--current"]'), text('[class*="price-current"]'), text('[data-pl="product-price"]')
    );
    const price = toNumber(priceRaw);
    const currencyRaw = first(meta('meta[property="product:price:currency"]'), offer?.priceCurrency);
    const visiblePriceText = first(
      text('[class*="price--current"]'), text('[class*="price-current"]'),
      text('[data-pl="product-price"]'), text('[class*="uniform-banner-box-price"]')
    ) || "";
    const currencyContext = `${visiblePriceText} ${priceRaw || ""} ${document.documentElement.lang || ""}`;
    const currency = currencyRaw?.toUpperCase() ||
      (/R\$|BRL/i.test(currencyContext) ? "BRL" :
       /US\$|USD/i.test(currencyContext) ? "USD" :
       /€|EUR/i.test(currencyContext) ? "EUR" :
       /£|GBP/i.test(currencyContext) ? "GBP" :
       /CNY|CN¥|RMB/i.test(currencyContext) ? "CNY" : null);

    const rating = toNumber(first(meta('meta[itemprop="ratingValue"]'), json?.aggregateRating?.ratingValue, text('[class*="overview-rating-average"]')));
    const reviewCount = toNumber(first(meta('meta[itemprop="reviewCount"]'), json?.aggregateRating?.reviewCount, text('[class*="review-count"]')));
    const bodyText = document.body?.innerText || "";
    const ordersMatch = bodyText.match(/([\d.,]+\s*(?:mil|mil\+|k|K|\+)?)[^\n]{0,35}(?:vendidos|pedidos|orders|sold)/i)
      || bodyText.match(/(?:vendidos|pedidos|orders|sold)[^\d\n]{0,20}([\d.,]+\s*(?:mil|k|K|\+)?)/i);
    let ordersCount = null;
    if (ordersMatch) {
      const token = ordersMatch[1].toLowerCase().replace(/\s/g, "");
      const multiplier = /mil|k/.test(token) ? 1000 : 1;
      ordersCount = Math.round((toNumber(token.replace(/mil|k|\+/g, "")) || 0) * multiplier) || null;
    }

    const seller = first(
      text('[class*="store-name"]'), text('[class*="seller-name"]'),
      text('[class*="shop-name"]'), text('[data-pl="store-name"]')
    );
    const image = first(meta('meta[property="og:image"]'), json?.image?.url, Array.isArray(json?.image) ? json.image[0] : json?.image);
    const category = categoryData();
    const description = first(meta('meta[property="og:description"]'), meta('meta[name="description"]'), json?.description);

    return {
      source: "aliexpress", title, url: location.href, source_product_id: sourceProductId,
      image_url: image, price, currency, rating,
      review_count: reviewCount != null ? Math.round(reviewCount) : null,
      orders_count: ordersCount, seller_name: seller, description,
      category: category.category, category_path: category.category_path,
      collected_at: new Date().toISOString()
    };
  }

  browser.runtime.onMessage.addListener(message => {
    if (message?.action === "DSI_CAPTURE_PRODUCT") {
      try { return Promise.resolve(captureProduct()); }
      catch (error) { return Promise.resolve({ error: error.message }); }
    }
  });
})();
