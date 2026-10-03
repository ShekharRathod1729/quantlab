const selected = new Map(); // ticker -> display label

const stockSearch = document.querySelector('#stock-search');
const weightRows  = document.querySelector('#weight-rows');
const weightSumMsg = document.querySelector('#weight-sum-msg');

loadStocks().then(() => initStockSearch('#stock-search'));

// Add stock chip + weight row
document.querySelector('#add-stock').addEventListener('click', addStock);
stockSearch.addEventListener('keydown', e => {
  if (e.key === 'Enter') { e.preventDefault(); addStock(); }
});

function addStock() {
  const raw = stockSearch.value.trim();
  if (!raw) return;
  const ticker = raw.split(' – ')[0].trim().toUpperCase();
  if (!ticker || selected.has(ticker)) { stockSearch.value = ''; return; }
  selected.set(ticker, raw.includes(' – ') ? raw : ticker);
  stockSearch.value = '';
  renderWeightRows();
}

function renderWeightRows(customWeights = null) {
  const equal = selected.size ? (100 / selected.size).toFixed(1) : 0;
  weightRows.innerHTML = [...selected.entries()].map(([ticker, label]) => {
    const val = (customWeights && customWeights[ticker] != null) ? Number(customWeights[ticker]).toFixed(1) : equal;
    return `
    <label>
      ${ticker} weight (%)
      <div style="display:flex;gap:6px;align-items:center">
        <input class="weight-input" data-ticker="${ticker}" type="number"
               min="0" max="100" step="0.1" value="${val}" style="flex:1">
        <button type="button" class="remove-btn secondary"
                data-ticker="${ticker}"
                style="min-height:unset;padding:8px 10px">✕</button>
      </div>
    </label>`;
  }).join('');

  weightRows.querySelectorAll('.remove-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      selected.delete(btn.dataset.ticker);
      renderWeightRows();
    });
  });

  weightRows.querySelectorAll('.weight-input').forEach(inp => {
    inp.addEventListener('input', checkWeightSum);
  });

  checkWeightSum();
}

function applyPortfolioData(items, portfolioValue) {
  if (!items || items.length === 0) return;
  selected.clear();
  const weights = {};
  items.forEach(item => {
    selected.set(item.ticker, item.name ? `${item.ticker} – ${item.name}` : item.ticker);
    weights[item.ticker] = item.weight != null ? item.weight : (100 / items.length);
  });
  if (portfolioValue && portfolioValue > 0) {
    document.querySelector('#portfolio-value').value = Math.round(portfolioValue);
  }
  renderWeightRows(weights);
}

// Check localStorage from Portfolio navigation
try {
  const savedRisk = localStorage.getItem('quantlab_portfolio_risk');
  if (savedRisk) {
    localStorage.removeItem('quantlab_portfolio_risk');
    const parsed = JSON.parse(savedRisk);
    if (parsed.tickers && parsed.weights) {
      const items = parsed.tickers.map((t, idx) => ({
        ticker: t,
        weight: (parsed.weights[idx] || 0) * 100,
      }));
      applyPortfolioData(items, parsed.portfolioValue);
    }
  }
} catch (_) {}

// Wire Import my portfolio button
document.querySelector('#import-portfolio-risk-btn')?.addEventListener('click', async () => {
  const btn = document.querySelector('#import-portfolio-risk-btn');
  btn.disabled = true;
  btn.textContent = 'Importing…';
  try {
    const res = await fetch('/api/portfolio/holdings');
    if (!res.ok) throw new Error('Please log in or add holdings first.');
    const data = await res.json();
    if (!data.holdings || data.holdings.length === 0) {
      alert('You have no saved holdings in your portfolio yet.');
      return;
    }
    applyPortfolioData(data.holdings, data.totalValue);
  } catch (err) {
    alert(err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = '⚡ Import my portfolio';
  }
});

function getWeights() {
  return [...weightRows.querySelectorAll('.weight-input')].map(inp => parseFloat(inp.value) / 100);
}

function checkWeightSum() {
  if (selected.size === 0) { weightSumMsg.textContent = ''; return; }
  const total = getWeights().reduce((a, b) => a + b, 0);
  const pct = (total * 100).toFixed(1);
  if (Math.abs(total - 1) < 0.001) {
    weightSumMsg.className = 'message pending';
    weightSumMsg.textContent = `Weights sum to ${pct}% ✓`;
  } else {
    weightSumMsg.className = 'message error';
    weightSumMsg.textContent = `Weights sum to ${pct}% — must equal 100%.`;
  }
}

document.querySelector('#risk-form').addEventListener('submit', async event => {
  event.preventDefault();
  if (selected.size === 0) { message('Add at least one stock.', 'error'); return; }
  const weights = getWeights();
  const total = weights.reduce((a, b) => a + b, 0);
  if (Math.abs(total - 1) >= 0.001) {
    message(`Weights sum to ${(total * 100).toFixed(1)}% — they must equal 100%.`, 'error');
    return;
  }
  const button = event.submitter; button.disabled = true;
  message('Calculating risk measures…', 'pending');
  try {
    const data = await post('/api/risk', {
      tickers: [...selected.keys()],
      weights,
      period: document.querySelector('#period').value,
      portfolioValue: parseFloat(document.querySelector('#portfolio-value').value),
      confidence: parseInt(document.querySelector('#confidence').value),
    });
    renderResults(data);
    message('Risk calculation complete.');
  } catch (error) {
    message(error.message, 'error');
  } finally {
    button.disabled = false;
  }
});

function renderResults(d) {
  const pct  = v => v != null ? `${(v).toFixed(2)}%` : '—';
  const money = v => v != null ? `$${Math.abs(v).toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2})}` : '—';
  const num  = (v, dp=4) => v != null ? v.toFixed(dp) : '—';
  const red  = v => `<strong style="color:#ff9f9f">${v}</strong>`;

  document.querySelector('#ret-vol').innerHTML =
    stat('Expected annual return', pct(d.portfolio_return * 100)) +
    stat('Annual volatility (σ)',  pct(d.portfolio_volatility * 100));

  document.querySelector('#sharpe-mdd').innerHTML =
    stat('Sharpe ratio', num(d.sharpe, 4)) +
    stat('Maximum drawdown', `<strong style="color:#ff9f9f">${pct(d.max_drawdown * 100)}</strong>`);

  const conf = document.querySelector('#confidence').value;
  document.querySelector('#hist-risk').innerHTML =
    stat(`Hist. VaR rate (${conf}%)`,  red(pct(d.hist_var_rate))) +
    stat(`Hist. VaR (${conf}%)`,        red(money(d.hist_var))) +
    stat(`Hist. CVaR rate (${conf}%)`,  red(pct(d.hist_cvar_rate))) +
    stat(`Hist. CVaR (${conf}%)`,       red(money(d.hist_cvar)));

  document.querySelector('#param-risk').innerHTML =
    stat(`Param. VaR rate (${conf}%)`,  red(pct(d.param_var_rate))) +
    stat(`Param. VaR (${conf}%)`,       red(money(d.param_var))) +
    stat(`Param. CVaR rate (${conf}%)`, red(pct(d.param_cvar_rate))) +
    stat(`Param. CVaR (${conf}%)`,      red(money(d.param_cvar)));

  document.querySelector('#results').hidden = false;
}
