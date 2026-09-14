/**
 * Bambinos Growth — Interactive Visualization & Charting Engine
 * Supports Chart.js and SVG rendering for:
 * 1. Company Level Financial ROAS (Composed Bar & Line)
 * 2. Campaign Meta Diagnosis Driver Pressure Bars
 * 3. Operations Daily Performance Trend Curves
 * 4. Meta Spend Trends & Top Campaign Rankings
 */

class CohortChartRenderer {
  constructor() {
    this.chartInstances = {};
  }

  destroyChart(id) {
    if (this.chartInstances[id]) {
      try {
        this.chartInstances[id].destroy();
      } catch (e) {
        console.warn('Error destroying chart instance:', e);
      }
      delete this.chartInstances[id];
    }
  }

  // ==================== TAB 1: COMPANY FINANCIAL CHART ====================
  renderCompanyFinancialChart(canvasId, rows, isDaily = true) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || typeof Chart === 'undefined') return;

    this.destroyChart(canvasId);
    const ctx = canvas.getContext('2d');

    const labels = rows.map(r => isDaily ? (r.date ? r.date.slice(5) : '—') : 'Selected Period');
    const revenues = rows.map(r => r.revenue || r.new_revenue || 0);
    const spends = rows.map(r => r.spend || 0);
    const roasValues = rows.map(r => r.roas != null ? Number(r.roas.toFixed(2)) : null);

    this.chartInstances[canvasId] = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          {
            type: 'line',
            label: 'ROAS (×)',
            data: roasValues,
            borderColor: '#0284c7',
            backgroundColor: '#0284c7',
            borderWidth: 2.5,
            pointRadius: rows.length < 20 ? 4 : 2,
            pointHoverRadius: 6,
            pointBackgroundColor: '#ffffff',
            pointBorderColor: '#0284c7',
            pointBorderWidth: 2,
            fill: false,
            yAxisID: 'yRoas',
            order: 1
          },
          {
            type: 'bar',
            label: 'New Revenue (₹)',
            data: revenues,
            backgroundColor: 'rgba(37, 99, 235, 0.85)',
            hoverBackgroundColor: '#2563eb',
            borderRadius: 4,
            yAxisID: 'yMoney',
            order: 2
          },
          {
            type: 'bar',
            label: 'Meta Spend (₹)',
            data: spends,
            backgroundColor: 'rgba(148, 163, 184, 0.85)',
            hoverBackgroundColor: '#94a3b8',
            borderRadius: 4,
            yAxisID: 'yMoney',
            order: 3
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 400 },
        interaction: {
          mode: 'index',
          intersect: false
        },
        plugins: {
          legend: {
            position: 'top',
            labels: { font: { family: 'Inter', size: 12 }, boxWidth: 12, usePointStyle: true }
          },
          tooltip: {
            padding: 10,
            cornerRadius: 8,
            callbacks: {
              label: function(context) {
                const label = context.dataset.label || '';
                const val = context.raw;
                if (label.includes('ROAS')) return `${label}: ${val != null ? val.toFixed(2) + '×' : '—'}`;
                return `${label}: ₹${Math.round(val).toLocaleString('en-IN')}`;
              }
            }
          }
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { font: { family: 'JetBrains Mono', size: 10 }, color: '#64748b' }
          },
          yMoney: {
            type: 'linear',
            position: 'left',
            grid: { color: '#f1f5f9' },
            ticks: {
              font: { family: 'JetBrains Mono', size: 10 },
              color: '#64748b',
              callback: v => v >= 100000 ? '₹' + (v / 100000).toFixed(1) + 'L' : v >= 1000 ? '₹' + (v / 1000).toFixed(0) + 'k' : '₹' + v
            }
          },
          yRoas: {
            type: 'linear',
            position: 'right',
            grid: { display: false },
            ticks: {
              font: { family: 'JetBrains Mono', size: 10 },
              color: '#0284c7',
              callback: v => v.toFixed(1) + '×'
            }
          }
        }
      }
    });
  }

  // ==================== TAB 4: DRIVER PRESSURE CHART ====================
  renderDriverPressureChart(canvasId, drivers) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || typeof Chart === 'undefined') return;

    this.destroyChart(canvasId);
    const ctx = canvas.getContext('2d');

    const labels = drivers.map(d => d.label);
    const pressures = drivers.map(d => d.multiplier != null ? Number(((d.multiplier - 1) * 100).toFixed(1)) : 0);
    const colors = pressures.map(p => p > 0 ? 'rgba(239, 68, 68, 0.85)' : 'rgba(16, 185, 129, 0.85)');

    this.chartInstances[canvasId] = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Cost Impact %',
          data: pressures,
          backgroundColor: colors,
          borderRadius: 4
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 400 },
        plugins: {
          legend: { display: false },
          tooltip: {
            padding: 8,
            cornerRadius: 6,
            callbacks: {
              label: ctx => `${ctx.raw > 0 ? '+' : ''}${ctx.raw}% booking cost pressure`
            }
          }
        },
        scales: {
          x: {
            grid: { color: '#f1f5f9' },
            ticks: {
              font: { family: 'JetBrains Mono', size: 10 },
              callback: v => (v > 0 ? '+' : '') + v + '%'
            }
          },
          y: {
            grid: { display: false },
            ticks: { font: { family: 'Inter', size: 11, weight: '500' }, color: '#334155' }
          }
        }
      }
    });
  }

  // ==================== TAB 4: OPERATIONS TREND LINE CHART ====================
  renderOpsTrendChart(canvasId, series, metricKey, metricLabel) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || typeof Chart === 'undefined') return;

    this.destroyChart(canvasId);
    const ctx = canvas.getContext('2d');

    const labels = series.map(s => s.date ? s.date.slice(5) : '');
    const data = series.map(s => s[metricKey] != null ? s[metricKey] : null);

    this.chartInstances[canvasId] = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: metricLabel,
          data: data,
          borderColor: '#0284c7',
          backgroundColor: 'rgba(2, 132, 199, 0.1)',
          borderWidth: 2.5,
          fill: true,
          tension: 0.25,
          pointRadius: 4,
          pointHoverRadius: 6,
          pointBackgroundColor: '#ffffff',
          pointBorderColor: '#0284c7',
          pointBorderWidth: 2
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 400 },
        plugins: {
          legend: { display: false },
          tooltip: {
            padding: 8,
            cornerRadius: 6,
            callbacks: {
              label: ctx => {
                const v = ctx.raw;
                if (v == null) return '—';
                if (['cpm', 'cpc', 'cpdb', 'costPerResult'].includes(metricKey)) return `₹${Math.round(v).toLocaleString('en-IN')}`;
                if (['ctr', 'landing', 'resultsRate'].includes(metricKey)) return `${(v * 100).toFixed(2)}%`;
                return v;
              }
            }
          }
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { font: { family: 'JetBrains Mono', size: 10 }, color: '#64748b' }
          },
          y: {
            grid: { color: '#f1f5f9' },
            ticks: {
              font: { family: 'JetBrains Mono', size: 10 },
              color: '#64748b',
              callback: v => ['cpm', 'cpc', 'cpdb'].includes(metricKey) ? `₹${Math.round(v)}` : ['ctr', 'landing', 'resultsRate'].includes(metricKey) ? `${(v * 100).toFixed(1)}%` : v
            }
          }
        }
      }
    });
  }

  // ==================== TAB 5: META SPEND TREND AREA CHART ====================
  renderMetaSpendTrendChart(canvasId, series) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || typeof Chart === 'undefined') return;

    this.destroyChart(canvasId);
    const ctx = canvas.getContext('2d');

    const labels = series.map(s => s.date ? s.date.slice(5) : '');
    const spends = series.map(s => s.spend || 0);

    this.chartInstances[canvasId] = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: 'Daily Ad Spend',
          data: spends,
          borderColor: '#0284c7',
          backgroundColor: 'rgba(2, 132, 199, 0.12)',
          borderWidth: 2,
          fill: true,
          tension: 0.2,
          pointRadius: 4,
          pointHoverRadius: 6,
          pointBackgroundColor: '#ffffff',
          pointBorderColor: '#0284c7',
          pointBorderWidth: 2
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 400 },
        plugins: {
          legend: { display: false },
          tooltip: {
            padding: 8,
            cornerRadius: 6,
            callbacks: {
              label: ctx => `Spend: ₹${Math.round(ctx.raw).toLocaleString('en-IN')}`
            }
          }
        },
        scales: {
          x: { grid: { display: false }, ticks: { font: { family: 'JetBrains Mono', size: 10 }, color: '#64748b' } },
          y: {
            grid: { color: '#f1f5f9' },
            ticks: {
              font: { family: 'JetBrains Mono', size: 10 },
              color: '#64748b',
              callback: v => v >= 100000 ? `₹${(v/100000).toFixed(1)}L` : v >= 1000 ? `₹${(v/1000).toFixed(0)}k` : `₹${v}`
            }
          }
        }
      }
    });
  }

  // ==================== TAB 5: TOP CAMPAIGNS BY SPEND ====================
  renderMetaTopCampaignsChart(canvasId, campaigns) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || typeof Chart === 'undefined') return;

    this.destroyChart(canvasId);
    const ctx = canvas.getContext('2d');

    const top = campaigns.slice(0, 6);
    const labels = top.map(c => (c.campaign || 'Campaign').length > 25 ? (c.campaign || '').slice(0, 25) + '…' : c.campaign);
    const spends = top.map(c => c.spend || 0);

    this.chartInstances[canvasId] = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Spend',
          data: spends,
          backgroundColor: '#0d9488',
          hoverBackgroundColor: '#0f766e',
          borderRadius: 4
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 400 },
        plugins: {
          legend: { display: false },
          tooltip: {
            padding: 8,
            cornerRadius: 6,
            callbacks: {
              label: ctx => `Spend: ₹${Math.round(ctx.raw).toLocaleString('en-IN')}`
            }
          }
        },
        scales: {
          x: {
            grid: { color: '#f1f5f9' },
            ticks: {
              font: { family: 'JetBrains Mono', size: 10 },
              color: '#64748b',
              callback: v => v >= 100000 ? `₹${(v/100000).toFixed(1)}L` : v >= 1000 ? `₹${(v/1000).toFixed(0)}k` : `₹${v}`
            }
          },
          y: {
            grid: { display: false },
            ticks: { font: { family: 'Inter', size: 11 }, color: '#334155' }
          }
        }
      }
    });
  }
}

window.cohortChartRenderer = new CohortChartRenderer();
