async function loadStocks() {
  try {
    const stocks = await (await fetch('/api/stocks')).json();
    document.querySelectorAll('.stock-datalist').forEach(dl => {
      dl.innerHTML = stocks
        .map(s => `<option value="${s.symbol} – ${s.name} (${s.index})"></option>`)
        .join('');
    });
    return stocks;
  } catch (_) { return []; }
}

/**
 * Wire a stock search input so the datalist dropdown only appears after the
 * user starts typing — prevents the full 500-item list showing on click.
 */
function initStockSearch(inputSelector = '#stock-search') {
  const input = document.querySelector(inputSelector);
  if (!input) return;
  // No list on initial focus/click — only when typing.
  input.removeAttribute('list');
  input.addEventListener('input', () => {
    input.setAttribute('list', input.value.trim() ? 'stocks' : '');
  });
}

function message(text, kind = '') {
  const node = document.querySelector('#message');
  node.className = `message ${kind}`;
  node.textContent = text;
}

async function post(url, body) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Request failed.');
  return data;
}

function stat(label, value) {
  return `<div class="stat"><span>${label}</span><strong>${value}</strong></div>`;
}

/** Try to show the company logo; fall back to a styled ticker badge. */
function renderLogo(ticker, containerSelector) {
  const el = document.querySelector(containerSelector);
  if (!el) return;
  const clean = ticker.split('.')[0]; // strip .NS, .BO, etc.
  const img = new Image();
  img.src = `https://assets.parqet.com/logos/symbol/${clean}?format=png`;
  img.alt = ticker;
  img.style.cssText = 'width:48px;height:48px;border-radius:10px;object-fit:contain;background:#fff;padding:4px';
  img.onload = () => { el.innerHTML = ''; el.appendChild(img); };
  img.onerror = () => {
    // Coloured badge using the ticker's first char as a seed
    const palette = ['#56d4bb','#75a7ff','#fdba74','#f0abfc','#a3e635','#fca5a5','#67e8f9'];
    const bg = palette[clean.charCodeAt(0) % palette.length];
    el.innerHTML = `<div style="width:48px;height:48px;border-radius:10px;background:${bg};
      display:flex;align-items:center;justify-content:center;
      font-weight:800;font-size:.75rem;color:#07111f;letter-spacing:.02em">${clean.slice(0,4)}</div>`;
  };
}
