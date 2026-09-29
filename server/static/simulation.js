let terminalChart, pathsChart;
loadStocks();
const pathsInput = document.querySelector('#path-count');
pathsInput.addEventListener('input', () => document.querySelector('#path-count-output').value = pathsInput.value);
document.querySelector('#simulation-form').addEventListener('submit', async event => {
  event.preventDefault(); message('Running simulations…', 'pending');
  const button = event.submitter; button.disabled = true;
  try {
    const data = await post('/api/simulations', {ticker:document.querySelector('#stock-search').value, horizon:document.querySelector('#horizon').value, numSim:document.querySelector('#num-sim').value, pathCount:pathsInput.value});
    render(data); document.querySelector('#results').hidden = false; message('Simulation complete.');
  } catch (error) { message(error.message, 'error'); } finally { button.disabled = false; }
});
function render(data) {
  const money = value => `$${value.toFixed(2)}`;
  document.querySelector('#stats').innerHTML = stat('Mean terminal price',money(data.summary.mean))+stat('Median',money(data.summary.median))+stat('5th percentile',money(data.summary.p05))+stat('95th percentile',money(data.summary.p95));
  const labels = data.histogram.edges.slice(0,-1).map((edge,index) => `${edge.toFixed(2)}–${data.histogram.edges[index+1].toFixed(2)}`);
  terminalChart?.destroy(); terminalChart = new Chart(document.querySelector('#terminal-chart'), {type:'bar',data:{labels,datasets:[{label:'Terminal prices',data:data.histogram.frequencies,backgroundColor:'#56d4bb'}]},options:{plugins:{legend:{display:false}},scales:{x:{ticks:{maxTicksLimit:8}},y:{title:{display:true,text:'Simulations'}}}}});
  pathsChart?.destroy(); const colors=['#56d4bb','#75a7ff','#fdba74','#f0abfc','#a3e635','#fca5a5'];
  pathsChart = new Chart(document.querySelector('#paths-chart'), {type:'line',data:{labels:data.paths.dates,datasets:data.paths.values[0].map((_,i)=>({label:`Path ${i+1}`,data:data.paths.values.map(row=>row[i]),borderColor:colors[i%colors.length],borderWidth:1,pointRadius:0}))},options:{plugins:{legend:{display:false}},scales:{x:{ticks:{maxTicksLimit:6}},y:{title:{display:true,text:'Price'}}}}});
}
