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
    const nodes = [...document.querySelectorAll('[class*="breadcrumb" i] a, [aria-label*="breadcrumb" i] a, nav[aria-label*="breadcrumb" i] a')]
      .map(node => clean(node.textContent)).filter(Boolean)
      .filter(label => !/^(home|início|aliexpress)$/i.test(label));
    // Não usar todos os links de <nav>: menus globais geram categorias falsas.
    const unique = [...new Set(nodes)].slice(-12);
    return { category: unique.at(-1) || null, category_path: unique };
  }

  // Somente imagens vinculadas ao produto: galeria/miniaturas e metadados.
  // Nunca coleta imagens de recomendações ou da página inteira.
  function safeImage(raw) {
    if (!raw || typeof raw !== 'string') return null;
    try {
      const url = new URL(raw.trim(), location.href);
      if (!['https:', 'http:'].includes(url.protocol)) return null;
      if (/^(?:localhost|127\.|0\.0\.0\.0)/i.test(url.hostname)) return null;
      return url.href;
    } catch (_) { return null; }
  }

  function productImages(json) {
    const pool = [];
    const add = raw => {
      const url = safeImage(typeof raw === 'object' ? raw?.url : raw);
      if (url && !pool.includes(url) && pool.length < 16) pool.push(url);
    };
    add(meta('meta[property="og:image"]'));
    const images = Array.isArray(json?.image) ? json.image : (json?.image ? [json.image] : []);
    images.forEach(add);
    const selectors = [
      '[class*="image-view" i] img', '[class*="image-gallery" i] img',
      '[class*="slider--img" i] img', '[class*="magnifier" i] img',
      '[data-pl*="product-image" i] img', '[class*="product-image" i] img',
      '[class*="thumbnail" i] img'
    ];
    for (const node of document.querySelectorAll(selectors.join(','))) {
      if (pool.length >= 16) break;
      const srcset = node.getAttribute('data-src') || node.getAttribute('data-lazy-src') || node.currentSrc || node.getAttribute('src');
      add(srcset);
    }
    return pool;
  }

  function supplierInfo(json) {
    const root = document.querySelector('[class*="store-header" i], [class*="shop-header" i], [data-pl*="store" i]');
    const links = [
      ...document.querySelectorAll('a[href*="/store/"], a[href*="/store/index"], a[href*="/store/storeHome"], a[href*="/store/home"]')
    ];
    if (root) links.unshift(...root.querySelectorAll('a[href]'));
    const sellerUrl = links.map(node => {
      try {
        const u = new URL(node.href, location.href);
        return (u.protocol === 'https:' && /(^|\.)aliexpress\.com$/i.test(u.hostname) && /\/store\//i.test(u.pathname)) ? u.href : null;
      } catch (_) { return null; }
    }).find(Boolean) || null;
    // Notas do vendedor nunca são inferidas da nota do produto.
    const specific = document.querySelector('[class*="store-rating" i], [class*="seller-rating" i], [data-pl*="seller-rating" i]');
    const ratingText = [specific?.getAttribute('aria-label'), specific?.textContent].filter(Boolean).join(' ');
    const numeric = ratingText.match(/(?:rating|nota|avaliação)?\s*[:：]?\s*([0-5](?:[.,]\d{1,2})?)\s*(?:\/\s*5|stars?|estrelas?)/i);
    const sellerRating = numeric ? toNumber(numeric[1]) : null;
    const feedbackNode = document.querySelector('[class*="positive-feedback" i], [class*="positive-rate" i], [data-pl*="positive-feedback" i]');
    const feedback = (feedbackNode?.textContent || '').match(/(\d{1,3}(?:[.,]\d{1,2})?)\s*%/);
    const positive = feedback ? toNumber(feedback[1]) : null;
    return { seller_url: sellerUrl,
      seller_rating: sellerRating != null && sellerRating <= 5 ? sellerRating : null,
      seller_positive_feedback_pct: positive != null && positive <= 100 ? positive : null };
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
    const gallery = productImages(json);
    const supplier = supplierInfo(json);
    const category = categoryData();
    const description = first(meta('meta[property="og:description"]'), meta('meta[name="description"]'), json?.description);
    const discountBadge = (document.body?.innerText || "").match(/(?:-\s*)?(\d{1,3})\s*%\s*(?:OFF|desconto|de desconto)/i);
    const discountPercent = discountBadge && Number(discountBadge[1]) <= 100 ? Number(discountBadge[1]) : null;
    const shippingText = (document.body?.innerText || "").match(/(?:frete gr[aá]tis|envio gr[aá]tis|free shipping)/i)?.[0] || null;
    const deliveryText = first(text('[class*="delivery-time"]'), text('[class*="estimated-delivery"]'))?.slice(0,160) || null;

    return {
      source: "aliexpress", title, url: location.href, source_product_id: sourceProductId,
      image_url: safeImage(image) || gallery[0] || null, image_urls: gallery, ...supplier, price, currency, rating,
      review_count: reviewCount != null ? Math.round(reviewCount) : null,
      orders_count: ordersCount, seller_name: seller, description,
      discount_percent: discountPercent, shipping_text: shippingText, delivery_text: deliveryText,
      category: category.category, category_path: category.category_path,
      collected_at: new Date().toISOString()
    };
  }



  // Métricas dos cartões: aceita sinal explícito; não tenta inferir avaliações a partir de números soltos.
  function scaledCount(raw) {
    if (!raw) return null;
    const compact = String(raw).replace(/\s/g, "").toLowerCase();
    const suffix = compact.match(/(mil|milhão|milhões|k|m)\+?$/i)?.[1];
    let numeric = compact.replace(/(milhões|milhão|mil|k|m)\+?$/i, "").replace(/\+$/, "");
    if (!numeric) return null;
    let value;
    if (suffix) value = Number(numeric.replace(",", "."));
    else value = Number(numeric.replace(/[.,](?=\d{3}(?:[.,]|$))/g, "").replace(",", "."));
    if (!Number.isFinite(value) || value < 0) return null;
    const multiplier = /mil|k/i.test(suffix || "") ? 1000 : /milh|^m$/i.test(suffix || "") ? 1000000 : 1;
    return Math.round(value * multiplier);
  }

  function listingMetrics(card) {
    const fullText = card.innerText || card.textContent || "";
    const cleaned = fullText.replace(/\u00a0/g, " ");
    const explicitRating = cleaned.match(/(?:★|⭐|rating|nota|avaliação(?:\s+média)?|classificação)\s*[:：]?\s*([0-5](?:[.,]\d{1,2})?)(?!\d)/i)
      || cleaned.match(/\b([0-5][.,]\d{1,2})\s*(?:\/\s*5|★|⭐|estrelas?|stars?)/i);
    let rating = explicitRating ? toNumber(explicitRating[1]) : null;
    const ratingNode = card.querySelector('[aria-label*="star" i], [aria-label*="estrela" i], [class*="rating" i], [class*="star" i]');
    const ratingLabel = [ratingNode?.getAttribute("aria-label"), ratingNode?.getAttribute("title"), ratingNode?.textContent].filter(Boolean).join(" ");
    if (rating == null) {
      const fromElement = ratingLabel.match(/\b([0-5](?:[.,]\d{1,2})?)(?:\s*\/\s*5|\s*(?:stars?|estrelas?))\b/i)
        || ratingLabel.match(/^\s*([0-5][.,]\d{1,2})\s*$/);
      rating = fromElement ? toNumber(fromElement[1]) : null;
    }
    if (rating != null && (rating < 0 || rating > 5)) rating = null;
    const countLabel = '(?:avaliações|avaliação|reviews?|ratings?|classificações|opiniões)';
    const countToken = '(\\d+(?:[.,]\\d+)*(?:\\s*(?:milhões|milhão|mil|k|m))?\\+?)';
    // Regexes deliberadamente restritas à proximidade do rótulo e da contagem.
    const beforeReview = cleaned.match(new RegExp(countToken + '\\s*' + countLabel, 'i'));
    const afterReview = cleaned.match(new RegExp(countLabel + '\\s*[:：]?\\s*' + countToken, 'i'));
    const nearRatingCount = rating != null ? cleaned.match(/(?:★|⭐|rating|nota)\s*[:：]?\s*[0-5](?:[.,]\d{1,2})?\s*\(\s*(\d+(?:[.,]\d+)*(?:\s*(?:mil|k|m))?\+?)\s*\)/i) : null;
    const reviewToken = beforeReview?.[1] || afterReview?.[1] || nearRatingCount?.[1];
    const reviewCount = reviewToken && !/^[0-5][.,]\d{1,2}$/.test(reviewToken.trim()) ? scaledCount(reviewToken) : null;
    const countOrders = '(?:vendidos?|vendas?|pedidos?|orders?|sold)';
    const beforeOrders = cleaned.match(new RegExp(countToken + '\\s*' + countOrders, 'i'));
    const afterOrders = cleaned.match(new RegExp(countOrders + '\\s*[:：]?\\s*' + countToken, 'i'));
    const ordersCount = scaledCount(beforeOrders?.[1] || afterOrders?.[1]);
    return { rating, review_count: reviewCount, orders_count: ordersCount };
  }

  function listingProductCards() {
    const links = [...document.querySelectorAll('a[href*="/item/"]')];
    const found = new Map();
    const category = categoryData();
    for (const link of links) {
      const href = link.href;
      const id = href.match(/\/item\/(?:[^/]+\/)?(\d+)(?:\.html)?(?:[/?#]|$)/i)?.[1];
      if (!id) continue;
      let card = link;
      for (let depth = 0; depth < 5 && card.parentElement; depth++) {
        const parent = card.parentElement;
        const candidate = (parent.innerText || "").trim();
        if (candidate.length >= 18 && candidate.length <= 2000 && parent.querySelector("img")) { card = parent; break; }
        card = parent;
      }
      const cardText = card.innerText || link.innerText || "";
      const imageNode = card.querySelector("img");
      const title = first(link.getAttribute("title"), link.getAttribute("aria-label"), imageNode?.getAttribute("alt"),
        [...card.querySelectorAll("[title]")].map(n => n.getAttribute("title")).find(v => v && v.length > 8),
        link.innerText, cardText.split(/\n/).find(line => line.length > 12 && !/[R$€£]/.test(line)));
      if (!title || title.length < 6 || /^aliexpress$/i.test(title)) continue;
      // Não atribuir um valor ao produto sem símbolo de moeda (impede usar preço parcelado ou desconto por engano).
      const priceMatch = cardText.match(/(?:R\$|US\$|[$€£¥])\s*[\d.,]+|[\d.,]+\s*(?:BRL|USD|EUR|CNY)/i);
      const priceRaw = priceMatch?.[0] || null;
      const price = toNumber(priceRaw);
      const currency = priceRaw ? (/R\$/i.test(priceRaw) ? "BRL" : /US\$|USD/i.test(priceRaw) ? "USD" : /€/i.test(priceRaw) ? "EUR" : /£/i.test(priceRaw) ? "GBP" : /¥|CNY/i.test(priceRaw) ? "CNY" : null) : null;
      const image = imageNode?.currentSrc || imageNode?.src || null;
      const metrics = listingMetrics(card);
      const seller = first(card.querySelector('[class*="store-name" i], [class*="seller-name" i], [class*="shop-name" i]')?.textContent);
      const badgeMatch = cardText.match(/(?:-\s*)?(\d{1,3})\s*%\s*(?:OFF|desconto|de desconto)/i);
      const discountPercent = badgeMatch && Number(badgeMatch[1]) <= 100 ? Number(badgeMatch[1]) : null;
      const originalNode = card.querySelector('del, s, [class*="original-price" i], [class*="price--original" i], [style*="line-through"]');
      const originalText = clean(originalNode?.textContent);
      const originalValue = originalText?.match(/(?:R\$|US\$|[$€£¥])\s*[\d.,]+|[\d.,]+\s*(?:BRL|USD|EUR|CNY)/i);
      const originalCurrency = originalValue ? (/R\$/i.test(originalValue[0]) ? "BRL" : /US\$|USD/i.test(originalValue[0]) ? "USD" : /€/i.test(originalValue[0]) ? "EUR" : /£/i.test(originalValue[0]) ? "GBP" : /¥|CNY/i.test(originalValue[0]) ? "CNY" : null) : null;
      const originalPrice = originalCurrency && originalCurrency === currency ? toNumber(originalValue[0]) : null;
      const shippingText = cardText.match(/(?:frete gr[aá]tis|envio gr[aá]tis|free shipping|shipping free|frete de\s*(?:R\$|US\$)\s*[\d.,]+)/i)?.[0] || null;
      const deliveryText = clean(card.querySelector('[class*="delivery-time" i], [class*="estimated-delivery" i], [data-pl*="delivery"]')?.textContent)?.slice(0,160) || null;
      const sellerRatingNode = card.querySelector('[class*="store-rating" i], [class*="seller-rating" i]');
      const sellerRatingLabel = [sellerRatingNode?.getAttribute('aria-label'), sellerRatingNode?.getAttribute('title'), sellerRatingNode?.textContent].filter(Boolean).join(' ');
      const sellerRatingMatch = sellerRatingLabel.match(/([0-5](?:[.,]\d{1,2})?)\s*(?:\/\s*5|stars?|estrelas?)/i);
      const sellerRating = sellerRatingMatch ? toNumber(sellerRatingMatch[1]) : null;
      const positiveFeedbackNode = card.querySelector('[class*="positive-feedback" i], [class*="positive-rate" i]');
      const positiveFeedbackMatch = (positiveFeedbackNode?.textContent || '').match(/(\d{1,3}(?:[.,]\d{1,2})?)\s*%/);
      const positiveFeedback = positiveFeedbackMatch ? toNumber(positiveFeedbackMatch[1]) : null;
      const sellerLinkNode = card.querySelector('a[href*="/store/"]');
      let sellerUrl = null;
      try { const u = new URL(sellerLinkNode?.href || '', location.href);
        if (u.protocol === 'https:' && /(^|\.)aliexpress\.com$/i.test(u.hostname) && /\/store\//.test(u.pathname)) sellerUrl = u.href;
      } catch (_) { /* link não disponível */ }
      const result = { source: "aliexpress", source_product_id: id, title: title.slice(0, 1000), url: `https://www.aliexpress.com/item/${id}.html`,
        image_url: safeImage(image), image_urls: safeImage(image) ? [safeImage(image)] : [], seller_url: sellerUrl,
        seller_rating: sellerRating, seller_positive_feedback_pct: positiveFeedback, price, currency,
        ...metrics, seller_name: seller, original_price: originalPrice, discount_percent: discountPercent,
        shipping_text: shippingText, delivery_text: deliveryText,
        category: category.category, category_path: category.category_path,
        collected_at: new Date().toISOString() };
      // Links duplicados de um mesmo card: preferir a captura com mais campos disponíveis.
      const previous = found.get(id);
      const completeness = item => ["price", "rating", "review_count", "orders_count", "image_url"].filter(k => item[k] != null).length;
      if (!previous || completeness(result) > completeness(previous)) found.set(id, result);
      // Sem limite de 40 na descoberta: o limite passa a ser apenas no envio de cada lote.
    }
    return [...found.values()];
  }

  browser.runtime.onMessage.addListener(message => {
    if (message?.action === "DSI_COLLECT_LISTING") {
      try { return Promise.resolve({ products: listingProductCards(), page_url: location.href }); }
      catch (error) { return Promise.resolve({ error: error.message }); }
    }
    if (message?.action === "DSI_CAPTURE_PRODUCT" || message?.action === "DSI_PREVIEW_PRODUCT") {
      try { return Promise.resolve(captureProduct()); }
      catch (error) { return Promise.resolve({ error: error.message }); }
    }
  });
})();
