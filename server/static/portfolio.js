// ============================================================
// QUANTLAB — PORTFOLIO MANAGEMENT & OPTIMISATION
// ============================================================

let currentHoldings = [];
let lastMarkowitzAllocation = null;

// Currency & number formatting helpers
function formatUSD(val) {
  if (val === null || val === undefined || isNaN(val)) return '—';
  const abs = Math.abs(val).toLocaleString('en-US', { style: 'currency', currency: 'USD' });
  return val < 0 ? `−${abs}` : abs;
}

function formatPnl(amount, pct) {
  if (amount === null || isNaN(amount)) return '—';
  const sign = amount > 0 ? '+' : amount < 0 ? '−' : '';
  const absAmt = Math.abs(amount).toLocaleString('en-US', { style: 'currency', currency: 'USD' });
  const absPct = Math.abs(pct || 0).toFixed(2);
  const cls = amount > 0 ? 'pnl-pos' : amount < 0 ? 'pnl-neg' : '';
  return `<span class="${cls}">${sign}${absAmt} (${sign}${absPct}%)</span>`;
}

// ------------------------------------------------------------
// 1. FETCH & RENDER HOLDINGS
// ------------------------------------------------------------
async function fetchHoldings() {
  const statusMsg = document.querySelector('#portfolio-status-msg');
  const tbody = document.querySelector('#holdings-tbody');
  try {
    const res = await fetch('/api/portfolio/holdings');
    if (!res.ok) throw new Error('Failed to load portfolio holdings.');
    const data = await res.json();
    currentHoldings = data.holdings || [];

    // Update KPI summary cards
    document.querySelector('#kpi-total-value').textContent = formatUSD(data.totalValue);
    document.querySelector('#kpi-total-cost').textContent = formatUSD(data.totalCost);
    document.querySelector('#kpi-total-pnl').innerHTML = formatPnl(data.totalPnl, data.totalPnlPct);
    document.querySelector('#kpi-holdings-count').textContent = data.count || 0;

    // Render table rows
    if (currentHoldings.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="8" style="text-align:center;padding:var(--gap-lg);color:var(--text-dim)">
            No stock positions in your portfolio yet. Add positions above or run Markowitz optimisation below to build your basket.
          </td>
        </tr>`;
      return;
    }

    tbody.innerHTML = currentHoldings.map(h => {
      const pnlHtml = formatPnl(h.pnl, h.pnlPct);
      const weight = h.weight || 0;
      return `
        <tr data-id="${h.id}">
          <td>
            <div class="asset-cell">
              <div class="asset-info">
                <span class="asset-symbol">${h.ticker}</span>
                <span class="asset-name">${h.name || h.ticker}</span>
              </div>
            </div>
          </td>
          <td class="num-cell">${Number(h.shares).toLocaleString('en-US', { maximumFractionDigits: 4 })}</td>
          <td class="num-cell">${formatUSD(h.buyPrice)}</td>
          <td class="num-cell">${formatUSD(h.currentPrice)}</td>
          <td class="num-cell" style="font-weight:600">${formatUSD(h.currentValue)}</td>
          <td class="num-cell">
            <div class="weight-cell">
              <span>${weight.toFixed(1)}%</span>
              <div class="weight-bar-bg"><div class="weight-bar-fill" style="width:${Math.min(100, Math.max(0, weight))}%"></div></div>
            </div>
          </td>
          <td class="num-cell">${pnlHtml}</td>
          <td style="text-align:center">
            <div class="action-btns">
              <button type="button" class="btn-icon edit-btn" data-id="${h.id}" title="Edit shares / cost basis">Edit</button>
              <button type="button" class="btn-icon btn-icon-del del-btn" data-id="${h.id}" title="Remove position">✕</button>
            </div>
          </td>
        </tr>
      `;
    }).join('');

    // Wire edit & delete buttons
    tbody.querySelectorAll('.edit-btn').forEach(b => {
      b.addEventListener('click', () => openEditModal(parseInt(b.dataset.id, 10)));
    });
    tbody.querySelectorAll('.del-btn').forEach(b => {
      b.addEventListener('click', () => deleteHolding(parseInt(b.dataset.id, 10)));
    });

  } catch (err) {
    if (statusMsg) statusMsg.textContent = err.message;
  }
}

// ------------------------------------------------------------
// 2. ADD POSITION
// ------------------------------------------------------------
const toggleAddBtn = document.querySelector('#toggle-add-btn');
const addHoldingPanel = document.querySelector('#add-holding-panel');
const addHoldingForm = document.querySelector('#add-holding-form');
const addHoldingMsg = document.querySelector('#add-holding-msg');

if (toggleAddBtn && addHoldingPanel) {
  toggleAddBtn.addEventListener('click', () => {
    const isHidden = addHoldingPanel.style.display === 'none';
    addHoldingPanel.style.display = isHidden ? 'block' : 'none';
    toggleAddBtn.textContent = isHidden ? '− Hide add form' : '+ Add position';
    if (isHidden) document.querySelector('#holding-stock-search').focus();
  });
}

if (addHoldingForm) {
  addHoldingForm.addEventListener('submit', async e => {
    e.preventDefault();
    const rawTicker = document.querySelector('#holding-stock-search').value.trim();
    const ticker = rawTicker.split(' – ')[0].trim().toUpperCase();
    const shares = parseFloat(document.querySelector('#holding-shares').value);
    const rawBuyPrice = document.querySelector('#holding-buy-price').value.trim();
    const buyPrice = rawBuyPrice ? parseFloat(rawBuyPrice) : null;

    if (!ticker) {
      addHoldingMsg.className = 'message error';
      addHoldingMsg.textContent = 'Please select a valid stock ticker.';
      return;
    }
    if (isNaN(shares) || shares <= 0) {
      addHoldingMsg.className = 'message error';
      addHoldingMsg.textContent = 'Shares must be greater than zero.';
      return;
    }

    addHoldingMsg.className = 'message pending';
    addHoldingMsg.textContent = `Adding ${ticker} to your portfolio…`;

    try {
      const res = await post('/api/portfolio/holdings', { ticker, shares, buyPrice });
      addHoldingMsg.className = 'message';
      addHoldingMsg.textContent = `Added ${shares} shares of ${ticker}.`;
      addHoldingForm.reset();
      await fetchHoldings();
    } catch (err) {
      addHoldingMsg.className = 'message error';
      addHoldingMsg.textContent = err.message;
    }
  });
}

// Refresh button
const refreshBtn = document.querySelector('#refresh-holdings-btn');
if (refreshBtn) {
  refreshBtn.addEventListener('click', async () => {
    refreshBtn.disabled = true;
    refreshBtn.textContent = '↻ Updating…';
    await fetchHoldings();
    refreshBtn.textContent = '↻ Refresh';
    refreshBtn.disabled = false;
  });
}

// ------------------------------------------------------------
// 3. EDIT & DELETE POSITION
// ------------------------------------------------------------
const editModal = document.querySelector('#edit-modal');
const editHoldingForm = document.querySelector('#edit-holding-form');
const editMsg = document.querySelector('#edit-msg');

function openEditModal(holdingId) {
  const holding = currentHoldings.find(h => h.id === holdingId);
  if (!holding) return;
  document.querySelector('#edit-holding-id').value = holding.id;
  document.querySelector('#modal-ticker').textContent = holding.ticker;
  document.querySelector('#edit-shares').value = holding.shares;
  document.querySelector('#edit-buy-price').value = holding.buyPrice || '';
  editMsg.textContent = '';
  editModal.style.display = 'flex';
}

function closeEditModal() {
  editModal.style.display = 'none';
  editHoldingForm.reset();
}

document.querySelector('#close-modal-btn')?.addEventListener('click', closeEditModal);
document.querySelector('#cancel-edit-btn')?.addEventListener('click', closeEditModal);

if (editHoldingForm) {
  editHoldingForm.addEventListener('submit', async e => {
    e.preventDefault();
    const id = document.querySelector('#edit-holding-id').value;
    const shares = parseFloat(document.querySelector('#edit-shares').value);
    const buyPrice = parseFloat(document.querySelector('#edit-buy-price').value);

    editMsg.className = 'message pending';
    editMsg.textContent = 'Updating position…';

    try {
      const res = await fetch(`/api/portfolio/holdings/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ shares, buyPrice }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to update position.');
      closeEditModal();
      await fetchHoldings();
    } catch (err) {
      editMsg.className = 'message error';
      editMsg.textContent = err.message;
    }
  });
}

async function deleteHolding(holdingId) {
  const holding = currentHoldings.find(h => h.id === holdingId);
  const name = holding ? holding.ticker : 'this position';
  if (!confirm(`Are you sure you want to remove ${name} from your portfolio?`)) return;

  try {
    const res = await fetch(`/api/portfolio/holdings/${holdingId}`, { method: 'DELETE' });
    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.error || 'Failed to remove position.');
    }
    await fetchHoldings();
  } catch (err) {
    alert(err.message);
  }
}

// ------------------------------------------------------------
// 4. CROSS-MODULE INTEGRATION (MARKOWITZ & RISK)
// ------------------------------------------------------------
function loadHoldingsIntoMarkowitz() {
  if (currentHoldings.length === 0) {
    alert('You have no holdings in your portfolio to import. Add some stocks first!');
    return;
  }
  selected.clear();
  currentHoldings.forEach(h => {
    const label = h.name && h.name !== h.ticker ? `${h.ticker} – ${h.name}` : h.ticker;
    selected.set(h.ticker, label);
  });
  renderChips();
  // Set budget equal to current portfolio value if greater than 0
  const totalVal = currentHoldings.reduce((sum, h) => sum + (h.currentValue || 0), 0);
  if (totalVal > 0) {
    document.querySelector('#budget').value = Math.round(totalVal);
  }
  document.querySelector('#optimiser-section').scrollIntoView({ behavior: 'smooth' });
}

document.querySelector('#load-to-markowitz-btn')?.addEventListener('click', loadHoldingsIntoMarkowitz);
document.querySelector('#import-holdings-btn')?.addEventListener('click', loadHoldingsIntoMarkowitz);

// Send holdings to Risk analytics page via localStorage
document.querySelector('#analyze-risk-btn')?.addEventListener('click', () => {
  if (currentHoldings.length > 0) {
    const totalVal = currentHoldings.reduce((sum, h) => sum + (h.currentValue || 0), 0);
    const payload = {
      tickers: currentHoldings.map(h => h.ticker),
      weights: currentHoldings.map(h => totalVal > 0 ? (h.currentValue / totalVal) : (1 / currentHoldings.length)),
      portfolioValue: totalVal > 0 ? Math.round(totalVal) : 100000,
    };
    try {
      localStorage.setItem('quantlab_portfolio_risk', JSON.stringify(payload));
    } catch (_) {}
  }
});

// ------------------------------------------------------------
// 5. MARKOWITZ OPTIMISER
// ------------------------------------------------------------
const selected = new Map(); // ticker -> display label
const stockSearch = document.querySelector('#stock-search');
const selectedDiv = document.querySelector('#selected-stocks');
const reqReturnSlider = document.querySelector('#req-return');
const reqReturnOutput = document.querySelector('#req-return-output');

loadStocks().then(() => {
  initStockSearch('#stock-search');
  initStockSearch('#holding-stock-search');
});

reqReturnSlider?.addEventListener('input', () => {
  reqReturnOutput.value = `${reqReturnSlider.value}%`;
});

document.querySelector('#add-stock')?.addEventListener('click', () => {
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

stockSearch?.addEventListener('keydown', e => {
  if (e.key === 'Enter') { e.preventDefault(); document.querySelector('#add-stock').click(); }
});

function renderChips() {
  selectedDiv.innerHTML = [...selected.entries()].map(([ticker, label]) =>
    `<span class="chip">
       ${label}
       <button type="button" data-ticker="${ticker}" aria-label="Remove ${ticker}">✕</button>
     </span>`
  ).join('');
  selectedDiv.querySelectorAll('button[data-ticker]').forEach(btn => {
    btn.addEventListener('click', () => { selected.delete(btn.dataset.ticker); renderChips(); });
  });
}

document.querySelector('#portfolio-form')?.addEventListener('submit', async event => {
  event.preventDefault();
  if (selected.size === 0) { message('Add at least one stock to the basket.', 'error'); return; }
  const button = event.submitter; button.disabled = true;
  message('Optimising portfolio…', 'pending');
  try {
    const budgetVal = parseFloat(document.querySelector('#budget').value);
    const data = await post('/api/portfolio/optimise', {
      tickers: [...selected.keys()],
      reqReturn: parseFloat(reqReturnSlider.value) / 100,
      budget: budgetVal,
      allowShort: document.querySelector('#allow-short').checked,
    });
    lastMarkowitzAllocation = data.allocation;
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

// ------------------------------------------------------------
// 6. SAVE ALLOCATION AS USER PORTFOLIO
// ------------------------------------------------------------
async function saveAllocation(mode) {
  const saveMsg = document.querySelector('#save-allocation-msg');
  if (!lastMarkowitzAllocation) {
    saveMsg.className = 'message error';
    saveMsg.textContent = 'Please run the optimisation first.';
    return;
  }
  const modeText = mode === 'replace' ? 'replace your current portfolio with' : 'add';
  if (!confirm(`Save this allocation as your portfolio? This will ${modeText} these positions.`)) return;

  saveMsg.className = 'message pending';
  saveMsg.textContent = 'Saving allocation to your portfolio…';

  try {
    const res = await post('/api/portfolio/apply-allocation', {
      allocation: lastMarkowitzAllocation,
      mode: mode,
    });
    saveMsg.className = 'message';
    saveMsg.textContent = `Successfully saved ${res.saved} positions to your portfolio!`;
    await fetchHoldings();
    document.querySelector('#portfolio-manager').scrollIntoView({ behavior: 'smooth' });
  } catch (err) {
    saveMsg.className = 'message error';
    saveMsg.textContent = err.message;
  }
}

document.querySelector('#apply-replace-btn')?.addEventListener('click', () => saveAllocation('replace'));
document.querySelector('#apply-add-btn')?.addEventListener('click', () => saveAllocation('add'));

// Initial load
fetchHoldings();
