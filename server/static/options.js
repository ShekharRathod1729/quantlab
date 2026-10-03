/* ============================================================
   QUANTLAB — OPTIONS PAGE CONTROLLER
   ============================================================ */

let comparisonChart, strikeChart, timeChart, rateChart, volChart, terminalChart;
loadStocks().then(() => initStockSearch('#stock-search'));

// Datalist value is "AAPL – Apple Inc. (S&P 500)"; strip everything after " – ".
const ticker = () => document.querySelector('#stock-search').value.split(' – ')[0].trim();
const formValues = () => ({
  ticker: ticker(),
  strike: document.querySelector('#strike').value,
  horizon: document.querySelector('#horizon').value,
  optionType: document.querySelector('#option-type').value,
  numSim: document.querySelector('#num-sim').value,
});

/* ---------- helpers for secondary calls ---------- */

function sensitivityPayload() {
  return {
    ticker: ticker(),
    strike: document.querySelector('#strike').value,
    horizon: document.querySelector('#horizon').value,
    optionType: document.querySelector('#option-type').value,
  };
}

function terminalPayload() {
  return {
    ticker: ticker(),
    horizon: document.querySelector('#horizon').value,
    numSim: document.querySelector('#terminal-sim').value,
  };
}

/** Fire sensitivity + terminal requests (both are independent of main pricing). */
function fetchExtras() {
  const sensP = post('/api/options/bsm/sensitivity', sensitivityPayload())
    .then(renderSensitivity)
    .catch(() => {});          // don't let secondary failure block main result
  const termP = post('/api/options/bsm/terminal', terminalPayload())
    .then(renderTerminal)
    .catch(() => {});
  return Promise.all([sensP, termP]);
}

/* ===================== MAIN FORM HANDLERS ===================== */

document.querySelector('#option-form').addEventListener('submit', async event => {
  event.preventDefault(); const button = event.submitter; button.disabled = true;
  message('Calculating BSM and Monte Carlo prices…', 'pending');
  try {
    const [data] = await Promise.all([post('/api/options/mcs', formValues()), fetchExtras()]);
    display(data); message('Pricing complete.');
  }
  catch (error) { message(error.message, 'error'); } finally { button.disabled = false; }
});

document.querySelector('#bsm').addEventListener('click', async event => {
  event.currentTarget.disabled = true; message('Calculating the Black–Scholes–Merton price…', 'pending');
  try {
    const [data] = await Promise.all([post('/api/options/bsm', formValues()), fetchExtras()]);
    displayBsm(data); message('BSM pricing complete.');
  }
  catch (error) { message(error.message, 'error'); } finally { event.currentTarget.disabled = false; }
});

document.querySelector('#compare').addEventListener('click', async event => {
  event.currentTarget.disabled = true; message('Building the convergence plot; this runs the full simulation range…', 'pending');
  try {
    const [data] = await Promise.all([post('/api/options/comparison', formValues()), fetchExtras()]);
    comparison(data); message('Convergence plot complete.');
  }
  catch (error) { message(error.message, 'error'); } finally { event.currentTarget.disabled = false; }
});

/* ===================== EXISTING DISPLAY FUNCTIONS ===================== */

function display(data) {
  const money = v => `$${v.toFixed(4)}`;
  document.querySelector('#prices').innerHTML =
    stat('Black–Scholes–Merton', money(data.bsm.price)) +
    stat(`Monte Carlo · ${data.simulations.toLocaleString()}`, money(data.monteCarlo)) +
    stat('Difference', money(data.monteCarlo - data.bsm.price));
  document.querySelector('#greek-values').innerHTML =
    ['delta','gamma','theta','vega','rho'].map(k => stat(k[0].toUpperCase()+k.slice(1), data.bsm[k].toFixed(6))).join('');
  document.querySelector('#results').hidden = false;
}

function displayBsm(data) {
  const money = v => `$${v.toFixed(4)}`;
  document.querySelector('#prices').innerHTML = stat('Black–Scholes–Merton', money(data.result.price));
  document.querySelector('#greek-values').innerHTML =
    ['delta','gamma','theta','vega','rho'].map(k => stat(k[0].toUpperCase()+k.slice(1), data.result[k].toFixed(6))).join('');
  document.querySelector('#results').hidden = false;
}

function comparison(data) {
  document.querySelector('#comparison-card').hidden = false;
  comparisonChart?.destroy();
  comparisonChart = new Chart(document.querySelector('#comparison-chart'), {
    type: 'line',
    data: {
      labels: data.simulations.map(x => x.toLocaleString()),
      datasets: [
        { label: 'Monte Carlo', data: data.prices, borderColor: '#56d4bb', tension: .2 },
        { label: 'BSM benchmark', data: data.simulations.map(() => data.bsm.price), borderColor: '#75a7ff', borderDash: [7,5], pointRadius: 0 },
      ],
    },
    options: { scales: { x: { title: { display: true, text: 'Number of simulations' } }, y: { title: { display: true, text: 'Option price (USD)' } } } },
  });
}

/* ===================== SENSITIVITY CHARTS ===================== */

function makeSensChart(canvasId, existingChart, labels, values, xLabel) {
  existingChart?.destroy();
  return new Chart(document.querySelector(`#${canvasId}`), {
    type: 'line',
    data: {
      labels: labels.map(v => v.toFixed(4)),
      datasets: [{
        label: 'Option price',
        data: values,
        borderColor: '#41c9a0',
        backgroundColor: 'rgba(65,201,160,.08)',
        fill: true,
        tension: .25,
        pointRadius: 0,
        borderWidth: 2,
      }],
    },
    options: {
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: items => `${xLabel}: ${items[0].label}`,
            label: item => `Price: $${item.raw.toFixed(4)}`,
          },
        },
      },
      scales: {
        x: { title: { display: true, text: xLabel }, ticks: { maxTicksLimit: 8 } },
        y: { title: { display: true, text: 'Option price (USD)' } },
      },
    },
  });
}

function renderSensitivity(data) {
  strikeChart = makeSensChart('chart-vs-strike', strikeChart, data.vsStrike.strikes, data.vsStrike.opt_vals, 'Strike price (USD)');
  timeChart   = makeSensChart('chart-vs-time',   timeChart,   data.vsTime.time,       data.vsTime.opt_vals,   'Time to maturity (years)');
  rateChart   = makeSensChart('chart-vs-rate',   rateChart,   data.vsRate.rate,       data.vsRate.opt_vals,   'Risk-free rate');
  volChart    = makeSensChart('chart-vs-vol',    volChart,    data.vsVol.sigma_vals,  data.vsVol.opt_vals,    'Volatility (σ)');
  document.querySelector('#sensitivity-section').hidden = false;
}

/* ===================== TERMINAL HISTOGRAM ===================== */

function renderTerminal(data) {
  const money = v => `$${v.toFixed(2)}`;

  // Summary stats
  document.querySelector('#terminal-stats').innerHTML =
    stat('Mean', money(data.summary.mean)) +
    stat('Median', money(data.summary.median)) +
    stat('5th percentile', money(data.summary.p05)) +
    stat('95th percentile', money(data.summary.p95)) +
    stat('Simulations', data.simulations.toLocaleString());

  // Histogram
  const labels = data.histogram.edges.slice(0, -1).map((edge, i) =>
    `${edge.toFixed(2)} – ${data.histogram.edges[i + 1].toFixed(2)}`
  );

  terminalChart?.destroy();
  terminalChart = new Chart(document.querySelector('#terminal-hist'), {
    type: 'bar',
    data: {
      labels,
      datasets: [{ label: 'Price range', data: data.histogram.frequencies, backgroundColor: '#6b9fff', borderRadius: 0, borderSkipped: false }],
    },
    options: {
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: items => `$${items[0].label}`,
            label: item => `${item.raw.toLocaleString()} simulations`,
          },
        },
      },
      scales: {
        x: { ticks: { display: false }, grid: { display: false } },
        y: { title: { display: true, text: 'Simulations' } },
      },
    },
  });

  document.querySelector('#terminal-section').hidden = false;
}
