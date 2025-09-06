// charts.js — mobile-first, desktop-safe, HTMX-friendly

let CHART_payment = null;
let CHART_rentbuy = null;      // up to resale
let CHART_rentbuyFull = null;  // full loan duration
let CHART_cumint = null;

// ----- Utils -----
function usd(v) {
  try { return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(v); }
  catch { return '$' + (Math.round(v*100)/100).toLocaleString(); }
}
function destroyIfExists(chart) { if (chart) chart.destroy(); }
function isMobile() { return window.matchMedia('(max-width: 639px)').matches; }
const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

// Cap pixel ratio on mobile so canvases don’t get too heavy
const DPR_CAP = isMobile() ? 2 : 3;
if (window.devicePixelRatio && window.devicePixelRatio > DPR_CAP) {
  Object.defineProperty(window, 'devicePixelRatio', {
    get: () => DPR_CAP
  });
}

// Shared chart options tuned for responsiveness
function baseOptions(yLabelText) {
  return {
    responsive: true,
    maintainAspectRatio: false,      // crucial with .chart-box height wrappers
    resizeDelay: 100,
    interaction: { mode: 'index', intersect: false },
    animation: reduceMotion ? false : { duration: 250 },
    layout: { padding: 0 },
    plugins: {
      legend: {
        position: 'bottom',
        labels: { usePointStyle: true, boxWidth: 12 }
      },
      tooltip: {
        callbacks: { label: (ctx) => {
          const v = ctx.parsed.y ?? ctx.parsed; // line vs doughnut
          return `${ctx.dataset?.label || ctx.label}: ${usd(v)}`;
        }}
      }
    },
    scales: yLabelText ? {
      x: { title: { display: true, text: 'Month' } },
      y: {
        title: { display: true, text: yLabelText },
        ticks: { callback: (v) => usd(v) }
      }
    } : undefined
  };
}

// Line style tweaks (smaller points on mobile)
function lineDataset(extra = {}) {
  return {
    borderWidth: 2,
    pointRadius: isMobile() ? 0 : 2,
    pointHitRadius: 10,
    tension: 0.25,
    fill: false,
    ...extra
  };
}

// ----- Individual charts -----
function initPaymentChart(ctx, data) {
  destroyIfExists(CHART_payment);
  const labels = ['Principal & Interest', 'Taxes', 'Insurance', 'HOA', 'Maintenance'];
  const values = [data.pi, data.taxes, data.ins, data.hoa, data.maint];

  if (data.pmi && data.pmi > 0) {
    labels.push('PMI');
    values.push(data.pmi);
  }

  CHART_payment = new Chart(ctx, {
    type: 'doughnut',
    data: { labels, datasets: [{ data: values }] },
    options: {
      ...baseOptions(),
      plugins: {
        ...baseOptions().plugins,
        tooltip: { callbacks: { label: (ctx) => `${ctx.label}: ${usd(ctx.parsed)}` } }
      },
      cutout: '60%' // balanced center space on mobile
    }
  });
}

function initRentBuyChart(ctx, data) {
  destroyIfExists(CHART_rentbuy);
  const len = Math.max(data.rent.length, data.buy.length);
  const labels = Array.from({ length: len }, (_, i) => i + 1);

  CHART_rentbuy = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        { label: 'Rent (cumulative)', data: data.rent, ...lineDataset() },
        { label: 'Buy (cumulative)',  data: data.buy,  ...lineDataset() }
      ]
    },
    options: baseOptions('Cumulative Cost ($)')
  });
}

function initRentBuyFullChart(ctx, data) {
  destroyIfExists(CHART_rentbuyFull);
  const len = Math.max(data.rent.length, data.buy.length);
  const labels = Array.from({ length: len }, (_, i) => i + 1);

  CHART_rentbuyFull = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        { label: 'Rent (cumulative) — Full', data: data.rent, ...lineDataset() },
        { label: 'Buy  (cumulative) — Full', data: data.buy,  ...lineDataset() }
      ]
    },
    options: baseOptions('Cumulative Cost ($)')
  });
}

function initCumInterestChart(ctx, data) {
  destroyIfExists(CHART_cumint);
  const labels = Array.from({ length: data.months }, (_, i) => i + 1);

  CHART_cumint = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        { label: 'Cumulative Interest', data: data.data, ...lineDataset() }
      ]
    },
    options: baseOptions('Amount ($)')
  });
}

// ----- Public API used by HTMX swap -----
function initCharts(payload) {
  // The canvases live inside .chart-box wrappers; maintainAspectRatio=false lets them fill that height
  const c1     = document.getElementById('chartPayment');
  const c2full = document.getElementById('chartRentBuyFull');
  const c2     = document.getElementById('chartRentBuy');
  const c3     = document.getElementById('chartCumInterest');

  if (c1)    initPaymentChart(c1.getContext('2d'), payload.payment);
  if (c2full && payload.rentbuyFull) initRentBuyFullChart(c2full.getContext('2d'), payload.rentbuyFull);
  if (c2)    initRentBuyChart(c2.getContext('2d'), payload.rentbuy);
  if (c3)    initCumInterestChart(c3.getContext('2d'), payload.cuminterest);

  // Nudge all charts after layout settles (tabs, font loading, etc.)
  queueMicrotask(() => {
    if (window.Chart && Chart.instances) {
      Object.values(Chart.instances).forEach((inst) => inst.resize());
    }
  });
}

// Expose for inline script
window.initCharts = window.initCharts || initCharts;

// Re-resize on orientation change / viewport resize
window.addEventListener('resize', () => {
  if (window.Chart && Chart.instances) {
    Object.values(Chart.instances).forEach((inst) => inst.resize());
  }
});
