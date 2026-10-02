let terminalChart, pathsChart;
let catalog = [];

// Load catalog and wire smart search (dropdown only appears when typing)
loadStocks().then(stocks => { catalog = stocks; });
initStockSearch('#stock-search');

const pathsInput = document.querySelector('#path-count');
pathsInput.addEventListener('input', () => document.querySelector('#path-count-output').value = pathsInput.value);

document.querySelector('#simulation-form').addEventListener('submit', async event => {
  event.preventDefault();
  message('Running simulations…', 'pending');
  const button = event.submitter; button.disabled = true;
  try {
    const rawValue = document.querySelector('#stock-search').value;
    const ticker = rawValue.split(' – ')[0].trim().toUpperCase();
    const data = await post('/api/simulations', {
      ticker,
      horizon: document.querySelector('#horizon').value,
      numSim:  document.querySelector('#num-sim').value,
      pathCount: pathsInput.value,
    });
    render(data);
    document.querySelector('#results').hidden = false;
    message('Simulation complete.');
  } catch (error) {
    message(error.message, 'error');
  } finally {
    button.disabled = false;
  }
});

function render(data) {
  const money = v => `$${v.toFixed(2)}`;
  const horizonLabel = { '1w':'1 week','1m':'1 month','3m':'3 months','6m':'6 months','1y':'1 year' };

  // --- Company header ---
  const stock = catalog.find(s => s.symbol === data.ticker);
  const name  = stock ? stock.name : data.ticker;
  renderLogo(data.ticker, '#stock-logo');
  document.querySelector('#result-title').textContent = name;
  document.querySelector('#result-subtitle').textContent =
    `${data.ticker} · ${horizonLabel[data.horizon] || data.horizon} · ${data.simulations.toLocaleString()} simulations`;

  // --- Summary stat cards (mean & median only) ---
  document.querySelector('#stats').innerHTML =
    stat('Mean terminal price', money(data.summary.mean)) +
    stat('Median terminal price', money(data.summary.median));

  // --- Interpretive percentile messages ---
  document.querySelector('#interpretations').innerHTML = `
    <div class="stat" style="border-top:2px solid var(--accent)">
      <span>5th percentile</span>
      <strong style="font-size:.95rem;margin-top:5px;color:var(--accent)">${money(data.summary.p05)}</strong>
      <p style="color:var(--text-dim);font-size:.8rem;margin:.5rem 0 0;max-width:none">
        ${data.ticker} went below <strong style="color:var(--text);font-family:var(--mono)">${money(data.summary.p05)}</strong>
        in less than 5% of simulations.
      </p>
    </div>
    <div class="stat" style="border-top:2px solid var(--text-dim)">
      <span>95th percentile</span>
      <strong style="font-size:.95rem;margin-top:5px;color:var(--text)">${money(data.summary.p95)}</strong>
      <p style="color:var(--text-dim);font-size:.8rem;margin:.5rem 0 0;max-width:none">
        ${data.ticker} exceeded <strong style="color:var(--text);font-family:var(--mono)">${money(data.summary.p95)}</strong>
        in less than 5% of simulations.
      </p>
    </div>`;

  // --- Terminal-price histogram ---
  // Labels are the price ranges (shown in tooltips on hover); hidden on the x-axis.
  const labels = data.histogram.edges.slice(0, -1).map((edge, i) =>
    `${edge.toFixed(2)} – ${data.histogram.edges[i + 1].toFixed(2)}`
  );
  terminalChart?.destroy();
  terminalChart = new Chart(document.querySelector('#terminal-chart'), {
    type: 'bar',
    data: {
      labels,
      datasets: [{ label: 'Price range', data: data.histogram.frequencies, backgroundColor: '#41c9a0', borderRadius: 0, borderSkipped: false }],
    },
    options: {
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: items => `$${items[0].label}`,
            label:  item  => `${item.raw.toLocaleString()} simulations`,
          },
        },
      },
      scales: {
        x: { ticks: { display: false }, grid: { display: false } },   // ← hide x-axis labels
        y: { title: { display: true, text: 'Simulations' } },
      },
    },
  });

  // --- Simulated paths chart ---
  // Format ISO dates as "1 Oct", "15 Nov", etc.
  const dateLabels = data.paths.dates.map(d => {
    const dt = new Date(d);
    return dt.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
  });
  const colors = ['#41c9a0','#6b9fff','#f0a855','#c77dff','#7ae582','#e05c5c','#4dd9e8','#a8b2c0'];
  pathsChart?.destroy();
  pathsChart = new Chart(document.querySelector('#paths-chart'), {
    type: 'line',
    data: {
      labels: dateLabels,
      datasets: data.paths.values[0].map((_, i) => ({
        label: `Path ${i + 1}`,
        data:  data.paths.values.map(row => row[i]),
        borderColor: colors[i % colors.length],
        borderWidth: 1,
        pointRadius: 0,
      })),
    },
    options: {
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { maxTicksLimit: 8 } },
        y: { title: { display: true, text: `${data.ticker} price (USD)` } },
      },
    },
  });
}
