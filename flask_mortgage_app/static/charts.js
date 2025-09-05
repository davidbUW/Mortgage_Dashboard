// charts.js
let CHART_payment = null;
let CHART_rentbuy = null;      // up to resale
let CHART_rentbuyFull = null;  // full loan duration
let CHART_cumint = null;

function usd(v) {
  try { return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(v); }
  catch { return '$' + (Math.round(v*100)/100).toLocaleString(); }
}
function destroyIfExists(chart) { if (chart) chart.destroy(); }

function initPaymentChart(ctx, data) {
  destroyIfExists(CHART_payment);
  const labels = ['Principal & Interest', 'Taxes', 'Insurance', 'HOA', 'Maintenance'];
  const values = [data.pi, data.taxes, data.ins, data.hoa, data.maint];

  // Add PMI as a sixth slice if > 0
  if (data.pmi && data.pmi > 0) {
    labels.push('PMI');
    values.push(data.pmi);
  }

  CHART_payment = new Chart(ctx, {
    type: 'doughnut',
    data: { labels, datasets: [{ data: values }] },
    options: {
      plugins: {
        tooltip: { callbacks: { label: (ctx) => `${ctx.label}: ${usd(ctx.parsed)}` } },
        legend: { position: 'bottom' }
      }
    }
  });
}


function initRentBuyChart(ctx, data) {
  destroyIfExists(CHART_rentbuy);
  const labels = Array.from({length: Math.max(data.rent.length, data.buy.length)}, (_, i) => i+1);
  CHART_rentbuy = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        { label: 'Rent (cumulative)', data: data.rent, borderWidth: 2, fill: false },
        { label: 'Buy (cumulative)', data: data.buy, borderWidth: 2, fill: false }
      ]
    },
    options: {
      interaction: { mode: 'index', intersect: false },
      plugins: {
        tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}: ${usd(ctx.parsed.y)}` } },
        legend: { position: 'bottom' }
      },
      scales: {
        x: { title: { display: true, text: 'Month' } },
        y: { title: { display: true, text: 'Cumulative Cost ($)' },
             ticks: { callback: (v) => usd(v) } }
      }
    }
  });
}

function initRentBuyFullChart(ctx, data) {
  destroyIfExists(CHART_rentbuyFull);
  const labels = Array.from({length: Math.max(data.rent.length, data.buy.length)}, (_, i) => i+1);
  CHART_rentbuyFull = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        { label: 'Rent (cumulative) — Full', data: data.rent, borderWidth: 2, fill: false },
        { label: 'Buy (cumulative) — Full', data: data.buy, borderWidth: 2, fill: false }
      ]
    },
    options: {
      interaction: { mode: 'index', intersect: false },
      plugins: {
        tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}: ${usd(ctx.parsed.y)}` } },
        legend: { position: 'bottom' }
      },
      scales: {
        x: { title: { display: true, text: 'Month' } },
        y: { title: { display: true, text: 'Cumulative Cost ($)' },
             ticks: { callback: (v) => usd(v) } }
      }
    }
  });
}

function initCumInterestChart(ctx, data) {
  destroyIfExists(CHART_cumint);
  const labels = Array.from({length: data.months}, (_, i) => i+1);
  CHART_cumint = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        { label: 'Cumulative Interest', data: data.data, borderWidth: 2, fill: false }
      ]
    },
    options: {
      plugins: {
        tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}: ${usd(ctx.parsed.y)}` } },
        legend: { position: 'bottom' }
      },
      scales: {
        x: { title: { display: true, text: 'Month' } },
        y: { title: { display: true, text: 'Amount ($)' },
             ticks: { callback: (v) => usd(v) } }
      }
    }
  });
}

function initCharts(payload) {
  const c1 = document.getElementById('chartPayment');
  const c2full = document.getElementById('chartRentBuyFull');
  const c2 = document.getElementById('chartRentBuy');
  const c3 = document.getElementById('chartCumInterest');

  if (c1) initPaymentChart(c1.getContext('2d'), payload.payment);
  if (c2full && payload.rentbuyFull) initRentBuyFullChart(c2full.getContext('2d'), payload.rentbuyFull);
  if (c2) initRentBuyChart(c2.getContext('2d'), payload.rentbuy);
  if (c3) initCumInterestChart(c3.getContext('2d'), payload.cuminterest);
}


// Expose for inline script
window.initCharts = window.initCharts || initCharts;
