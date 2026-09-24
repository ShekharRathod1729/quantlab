async function loadStocks() {
  const status = document.querySelector('#catalog-status');
  try {
    const stocks = await (await fetch('/api/stocks')).json();
    document.querySelector('#stocks').innerHTML = stocks.map(stock => `<option value="${stock.symbol}" label="${stock.name} (${stock.index})"></option>`).join('');
    status.textContent = `${stocks.length} index constituents available. Enter a ticker or search by company name.`;
    return stocks;
  } catch (_) { status.textContent = 'Catalogue unavailable. You can still enter a Yahoo Finance ticker.'; return []; }
}
function message(text, kind = '') { const node = document.querySelector('#message'); node.className = `message ${kind}`; node.textContent = text; }
async function post(url, body) { const response = await fetch(url, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)}); const data = await response.json(); if (!response.ok) throw new Error(data.error || 'Request failed.'); return data; }
function stat(label, value) { return `<div class="stat"><span>${label}</span><strong>${value}</strong></div>`; }
