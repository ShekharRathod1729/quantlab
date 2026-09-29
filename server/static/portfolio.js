// Selected tickers set
const selected = new Map(); // ticker -> display label

const stockSearch = document.querySelector('#stock-search');
const selectedDiv = document.querySelector('#selected-stocks');
const reqReturnSlider = document.querySelector('#req-return');
const reqReturnOutput = document.querySelector('#req-return-output');

loadStocks();

reqReturnSlider.addEventListener('input', () => {
  reqReturnOutput.value = `${reqReturnSlider.value}%`;
});

document.querySelector('#add-stock').addEventListener('click', () => {
  const raw = stockSearch.value.trim();
  if (!raw) return;
  const ticker = raw.split(' – ')[0].trim().toUpperCase();
  const label = raw.includes(' – ') ? raw : ticker;
  if (!ticker) return;
  if (selected.has(ticker)) { stockSearch.value = ''; return; }
  selected.set(ticker, label);
  renderChips();
  stockSearch.value = '';
});

// Also allow pressing Enter in the search box to add
stockSearch.addEventListener('keydown', e => {
  if (e.key === 'Enter') { e.preventDefault(); document.querySelector('#add-stock').click(); }
});

function renderChips() {
  selectedDiv.innerHTML = [...selected.entries()].map(([ticker, label]) =>
    `<span class="chip" style="background:#091527;border:1px solid var(--line);border-radius:20px;padding:6px 12px;font-size:.85rem;display:inline-flex;align-items:center;gap:6px">
      ${label}
      <button type="button" data-ticker="${ticker}" aria-label="Remove ${ticker}"
        style="background:none;border:none;color:var(--muted);cursor:pointer;padding:0;font-size:1rem;min-height:unset">✕</button>
    </span>`
  ).join('');
  selectedDiv.querySelectorAll('button[data-ticker]').forEach(btn => {
    btn.addEventListener('click', () => { selected.delete(btn.dataset.ticker); renderChips(); });
  });
}

document.querySelector('#portfolio-form').addEventListener('submit', async event => {
  event.preventDefault();
  if (selected.size === 0) { message('Add at least one stock.', 'error'); return; }
  const button = event.submitter; button.disabled = true;
  message('Optimising portfolio…', 'pending');
  try {
    const data = await post('/api/portfolio/optimise', {
      tickers: [...selected.keys()],
      reqReturn: parseFloat(reqReturnSlider.value) / 100,
      budget: parseFloat(document.querySelector('#budget').value),
      allowShort: document.querySelector('#allow-short').checked,
    });
    renderAllocation(data);
    message('Optimisation complete.');
  } catch (error) {
    message(error.message, 'error');
  } finally {
    button.disabled = false;
  }
});

function renderAllocation(data) {
  const money = v => {
    const abs = Math.abs(v).toLocaleString('en-US', { style: 'currency', currency: 'USD' });
    return v < 0 ? `<span style="color:#ff9f9f">−${abs} (short)</span>` : abs;
  };
  document.querySelector('#allocation-grid').innerHTML = Object.entries(data.allocation)
    .map(([ticker, amount]) =>
      `<div class="stat"><span>${ticker}</span><strong>${money(amount)}</strong></div>`
    ).join('');
  document.querySelector('#results').hidden = false;
}
