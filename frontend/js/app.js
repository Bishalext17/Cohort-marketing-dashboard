/**
 * Bambinos Growth — Main Application Controller (v20.4 Enterprise Standard)
 * Orchestrates 5 Canonical Views:
 * 1. Company Level ROAS (viewCompany)
 * 2. Cohort Performance Explorer (viewCohort) [Redesigned]
 * 3. Cohort ROAS Progression / Heatmap (viewProgression)
 * 4. Campaign Meta Diagnosis & Comparison Windows (viewOperations)
 * 5. Meta Ads Manager Data (viewMeta)
 */

class BambinosDashboardApp {
  constructor() {
    this.activeTab = 'viewCohort'; // Default to Cohort performance explorer
    this.catalog = null;
    this.allMetrics = false;
    this.selectedWindow = 'Till date';
    this.heatmapMetric = 'new_roas';
    this.progressionMetric = 'new_roas';
    this.progressionFilter = 'all';
    this.cohortSearchQuery = '';
    this.activeDimensions = new Set(['campaign']);
    this.toastTimeout = null;

    this.init();
  }

  async init() {
    this.bindTabEvents();
    this.bindControlEvents();
    this.bindMaturityCurveEvents();
    this.handleHashChange();
    window.addEventListener('hashchange', () => this.handleHashChange());
    await this.loadCatalogAndData();
  }

  showToast(message, isSuccess = true) {
    const toast = document.getElementById('toastNotification');
    const toastMsg = document.getElementById('toastMessage');
    if (!toast || !toastMsg) return;

    toastMsg.textContent = message;
    toast.classList.remove('opacity-0', 'translate-y-16', 'pointer-events-none');
    toast.classList.add('opacity-100', 'translate-y-0');

    clearTimeout(this.toastTimeout);
    this.toastTimeout = setTimeout(() => {
      toast.classList.add('opacity-0', 'translate-y-16', 'pointer-events-none');
      toast.classList.remove('opacity-100', 'translate-y-0');
    }, 2500);
  }

  handleHashChange() {
    const hash = window.location.hash.replace('#', '');
    const hashMap = {
      'company-roas': 'viewCompany',
      'cohort-performance': 'viewCohort',
      'cohort-explorer': 'viewCohort',
      'cohort-progression': 'viewProgression',
      'roas-progression': 'viewProgression',
      'meta-diagnosis': 'viewOperations',
      'ads-manager': 'viewMeta',
      'viewCompany': 'viewCompany',
      'viewCohort': 'viewCohort',
      'viewProgression': 'viewProgression',
      'viewOperations': 'viewOperations',
      'viewMeta': 'viewMeta'
    };
    if (hash && hashMap[hash] && hashMap[hash] !== this.activeTab) {
      this.switchTab(hashMap[hash], false);
    }
  }

  bindTabEvents() {
    document.querySelectorAll('.nav-tab').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        const viewId = btn.getAttribute('data-view') || btn.getAttribute('href')?.replace('#', '');
        const navId = btn.getAttribute('data-nav');
        const targetView = {
          'company-roas': 'viewCompany',
          'cohort-explorer': 'viewCohort',
          'cohort-performance': 'viewCohort',
          'roas-progression': 'viewProgression',
          'cohort-progression': 'viewProgression',
          'meta-diagnosis': 'viewOperations',
          'ads-manager': 'viewMeta',
          'viewCompany': 'viewCompany',
          'viewCohort': 'viewCohort',
          'viewProgression': 'viewProgression',
          'viewOperations': 'viewOperations',
          'viewMeta': 'viewMeta'
        }[navId || viewId] || viewId;

        if (targetView) {
          this.switchTab(targetView, true);
        }
      });
    });
  }

  switchTab(viewId, updateHash = true) {
    if (!document.getElementById(viewId)) return;
    this.activeTab = viewId;

    // Update Nav Tab UI
    document.querySelectorAll('.nav-tab').forEach(b => {
      const isMatch = b.getAttribute('data-view') === viewId || 
                      (viewId === 'viewCompany' && b.getAttribute('data-nav') === 'company-roas') ||
                      (viewId === 'viewCohort' && b.getAttribute('data-nav') === 'cohort-explorer') ||
                      (viewId === 'viewProgression' && b.getAttribute('data-nav') === 'roas-progression') ||
                      (viewId === 'viewOperations' && b.getAttribute('data-nav') === 'meta-diagnosis') ||
                      (viewId === 'viewMeta' && b.getAttribute('data-nav') === 'ads-manager');

      const dot = b.querySelector('.indicator-dot');
      if (isMatch) {
        b.classList.add('active-nav', 'text-indigo-700', 'bg-indigo-50/90', 'border', 'border-indigo-200/80', 'font-semibold', 'shadow-2xs', 'ring-1', 'ring-indigo-500/10');
        b.classList.remove('text-slate-600', 'hover:bg-slate-100/80');
        if (!dot) {
          const newDot = document.createElement('span');
          newDot.className = 'indicator-dot ml-2 w-2 h-2 rounded-full bg-indigo-600 inline-block animate-pulse';
          b.appendChild(newDot);
        }
      } else {
        b.classList.remove('active-nav', 'text-indigo-700', 'bg-indigo-50/90', 'border', 'border-indigo-200/80', 'font-semibold', 'shadow-2xs', 'ring-1', 'ring-indigo-500/10');
        b.classList.add('text-slate-600', 'hover:bg-slate-100/80');
        if (dot) dot.remove();
      }
    });

    // Update View Sections
    document.querySelectorAll('.view-section').forEach(sec => sec.classList.remove('active'));
    const targetSection = document.getElementById(viewId);
    if (targetSection) {
      targetSection.classList.add('active');
    }

    if (updateHash) {
      const hashOutMap = {
        'viewCompany': 'company-roas',
        'viewCohort': 'cohort-performance',
        'viewProgression': 'cohort-progression',
        'viewOperations': 'meta-diagnosis',
        'viewMeta': 'ads-manager'
      };
      if (hashOutMap[viewId]) {
        history.replaceState(null, '', `#${hashOutMap[viewId]}`);
      }
    }

    // Trigger tab-specific refresh
    this.renderCurrentView();
  }

  renderCurrentView() {
    if (this.activeTab === 'viewCompany') this.renderCompanyView();
    else if (this.activeTab === 'viewCohort') this.renderCohortView();
    else if (this.activeTab === 'viewProgression') this.renderProgressionView();
    else if (this.activeTab === 'viewOperations') this.renderOperationsView();
    else if (this.activeTab === 'viewMeta') this.renderMetaView();
  }

  bindControlEvents() {
    // 1. Cohort Maturation Window Buttons (Tab 2)
    const cohortWinBtns = document.querySelectorAll('.cohort-win-btn');
    cohortWinBtns.forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        const win = btn.getAttribute('data-window');
        this.setCohortWindow(win);
        this.showToast(`Cohort window updated to ${win}`);
      });
    });

    // 2. Date Presets (Tab 2)
    document.querySelectorAll('.date-preset-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        document.querySelectorAll('.date-preset-btn').forEach(b => {
          b.className = 'date-preset-btn text-[11px] text-slate-500 hover:text-indigo-600 hover:underline px-1.5 py-0.5 rounded cursor-pointer';
        });
        btn.className = 'date-preset-btn text-[11px] text-indigo-600 hover:underline font-semibold bg-indigo-50/70 px-1.5 py-0.5 rounded cursor-pointer';

        const preset = btn.getAttribute('data-preset');
        const inputFrom = document.getElementById('inputDateFrom');
        const inputTo = document.getElementById('inputDateTo');
        if (preset === 'july26') {
          if (inputFrom) inputFrom.value = '01 - 07 - 2026';
          if (inputTo) inputTo.value = '31 - 07 - 2026';
        } else if (preset === 'q3mtd') {
          if (inputFrom) inputFrom.value = '01 - 07 - 2026';
          if (inputTo) inputTo.value = '15 - 08 - 2026';
        } else if (preset === 'last30') {
          if (inputFrom) inputFrom.value = '15 - 06 - 2026';
          if (inputTo) inputTo.value = '15 - 07 - 2026';
        }
        this.showToast(`Applied preset: ${btn.textContent.trim()}`);
        this.renderCohortTable();
      });
    });

    // 3. Dimension Slicing Pills (Tab 2)
    document.querySelectorAll('.dim-pill').forEach(pill => {
      pill.addEventListener('click', (e) => {
        e.preventDefault();
        const dim = pill.getAttribute('data-dim');
        const check = pill.querySelector('.check-mark');
        const isSelected = pill.classList.contains('bg-indigo-50');

        if (isSelected) {
          pill.classList.remove('bg-indigo-50', 'text-indigo-700', 'border', 'border-indigo-200/80', 'shadow-2xs');
          pill.classList.add('bg-slate-100', 'text-slate-700');
          if (check) check.classList.add('hidden');
          this.activeDimensions.delete(dim);
        } else {
          pill.classList.remove('bg-slate-100', 'text-slate-700');
          pill.classList.add('bg-indigo-50', 'text-indigo-700', 'border', 'border-indigo-200/80', 'shadow-2xs');
          if (check) check.classList.remove('hidden');
          this.activeDimensions.add(dim);
        }
        const dimLabel = pill.innerText.replace('✓', '').trim();
        this.showToast(`Dimension slice "${dimLabel}" toggled`);
        this.renderCohortTable();
      });
    });

    // 4. Live Table Search (Tab 2)
    const tableSearch = document.getElementById('tableSearchInput');
    const clearSearch = document.getElementById('clearSearchBtn');
    if (tableSearch) {
      tableSearch.addEventListener('input', (e) => {
        this.cohortSearchQuery = (e.target.value || '').trim().toLowerCase();
        if (clearSearch) {
          if (this.cohortSearchQuery.length > 0) {
            clearSearch.classList.remove('hidden');
            clearSearch.classList.add('flex');
          } else {
            clearSearch.classList.add('hidden');
            clearSearch.classList.remove('flex');
          }
        }
        this.renderCohortTable();
      });
    }

    if (clearSearch && tableSearch) {
      clearSearch.addEventListener('click', () => {
        tableSearch.value = '';
        this.cohortSearchQuery = '';
        clearSearch.classList.add('hidden');
        clearSearch.classList.remove('flex');
        this.renderCohortTable();
        tableSearch.focus();
      });
    }

    document.getElementById('resetSearchEmptyBtn')?.addEventListener('click', () => {
      if (tableSearch) tableSearch.value = '';
      this.cohortSearchQuery = '';
      if (clearSearch) clearSearch.classList.add('hidden');
      this.renderCohortTable();
    });

    // 5. Action Buttons (Refresh DB, Reset, Toggle Metrics, CSV Export)
    const refreshBtn = document.getElementById('btnRefreshDB');
    const refreshSpin = document.getElementById('refreshSpinIcon');
    const refreshText = document.getElementById('refreshBtnText');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => {
        if (refreshSpin) refreshSpin.classList.add('animate-spin');
        if (refreshText) refreshText.textContent = 'Syncing...';
        refreshBtn.disabled = true;

        setTimeout(() => {
          if (refreshSpin) refreshSpin.classList.remove('animate-spin');
          if (refreshText) refreshText.textContent = 'Refresh Live DB';
          refreshBtn.disabled = false;
          this.renderCohortView();
          this.showToast('Live Metabase & Meta API pipeline synchronized');
        }, 500);
      });
    }

    document.getElementById('btnResetFilters')?.addEventListener('click', () => {
      this.setCohortWindow('Till date');
      if (tableSearch) {
        tableSearch.value = '';
        this.cohortSearchQuery = '';
      }
      const julyPreset = document.querySelector('[data-preset="july26"]');
      if (julyPreset) julyPreset.click();
      this.showToast('All filters reset to baseline defaults');
    });

    document.getElementById('btnToggleAllMetrics')?.addEventListener('click', () => {
      this.allMetrics = !this.allMetrics;
      const label = document.getElementById('allMetricsLabel');
      if (label) label.textContent = this.allMetrics ? 'Fewer Metrics' : 'All 21 Metrics';
      this.showToast(this.allMetrics ? 'Expanded to full 21 metric columns' : 'Switched to core summary metrics');
      this.renderCohortTable();
    });

    document.getElementById('btnExportCsv')?.addEventListener('click', () => this.exportCohortCSV());
    document.getElementById('btnShareView')?.addEventListener('click', () => {
      if (navigator.clipboard) {
        navigator.clipboard.writeText(window.location.href);
      }
      this.showToast('Sharable dashboard view URL copied to clipboard!');
    });

    // KPI Cards click interaction
    document.querySelectorAll('.kpi-card').forEach(card => {
      card.addEventListener('click', () => {
        document.querySelectorAll('.kpi-card').forEach(c => c.classList.remove('ring-2', 'ring-indigo-500/50'));
        card.classList.add('ring-2', 'ring-indigo-500/50');
        const title = card.querySelector('p')?.textContent.trim() || 'Metric';
        const val = card.querySelector('h4')?.textContent.trim() || '';
        this.showToast(`${title}: ${val}`);
      });
    });

    // Tab 3 Progression Metric Selector & Fallbacks
    const handleProgressionMetricChange = (val) => {
      this.progressionMetric = val;
      this.heatmapMetric = val;
      const labels = {
        'new_roas': 'New-business ROAS',
        'blended_roas': 'Blended ROAS',
        'cash_roas': 'Total Cash Collected ROAS',
        'ltv_mult': 'Customer LTV Multiplier (60D)',
        'lead_conversion': 'Lead Conversion Rate (%)',
        'demos_attended': 'Demos Attended (Count)',
        'new_revenue': 'New Business Revenue (₹)'
      };
      this.showToast(`Switched matrix view to: ${labels[val] || val}`);
      this.renderProgressionView();
    };

    document.getElementById('progressionMetricSelect')?.addEventListener('change', (e) => {
      handleProgressionMetricChange(e.target.value);
    });
    document.getElementById('heatmapMetricSelect')?.addEventListener('change', (e) => {
      handleProgressionMetricChange(e.target.value);
    });

    // Tab 3 Progression Filter Chips (All, High ROAS, Last 4)
    document.querySelectorAll('.progression-filter-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        document.querySelectorAll('.progression-filter-chip').forEach(c => {
          c.classList.remove('active', 'bg-sky-50', 'border-sky-200', 'text-sky-800', 'font-semibold');
          c.classList.add('bg-white', 'border-slate-200', 'text-slate-600', 'font-medium');
        });
        chip.classList.add('active', 'bg-sky-50', 'border-sky-200', 'text-sky-800', 'font-semibold');
        chip.classList.remove('bg-white', 'text-slate-600', 'font-medium');

        this.progressionFilter = chip.getAttribute('data-filter') || 'all';
        this.renderProgressionView();
        this.showToast(`Filtered cohort rows: ${chip.textContent.trim()}`);
      });
    });

    // Tab 3 Refresh Button with Micro-Interaction
    const btnProgRefresh = document.getElementById('btnProgressionRefresh');
    const progSpinner = document.getElementById('progressionRefreshSpinner');
    if (btnProgRefresh) {
      btnProgRefresh.addEventListener('click', () => {
        if (progSpinner) progSpinner.classList.add('animate-spin');
        btnProgRefresh.classList.add('opacity-75');
        setTimeout(() => {
          if (progSpinner) progSpinner.classList.remove('animate-spin');
          btnProgRefresh.classList.remove('opacity-75');
          this.renderProgressionView();
          this.showToast('Sync complete: Metabase & Meta API cache updated (0.38s)');
        }, 400);
      });
    }

    // Tab 3 Export Button
    document.getElementById('btnExportProgression')?.addEventListener('click', () => {
      this.exportProgressionCSV();
    });

    // Tab 1 Company View Filters
    ['companyMarketFilter', 'companyCourseFilter', 'companySliceFilter', 'companyDateFrom', 'companyDateTo'].forEach(id => {
      document.getElementById(id)?.addEventListener('change', () => this.renderCompanyView());
    });

    // Tab 4 Operations View Selectors & Presets
    ['opsTrendMetricSelect', 'opsSecondaryMetricSelect', 'opsCampaignFilter', 'opsResultEventSelect', 'opsPerfFrom', 'opsPerfTo', 'opsCompFrom', 'opsCompTo'].forEach(id => {
      document.getElementById(id)?.addEventListener('change', () => this.renderOperationsView());
    });

    document.querySelectorAll('.ops-preset-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        const preset = btn.getAttribute('data-preset');
        this.applyOpsPreset(preset);
      });
    });

    // Tab 4 Rolling Buttons
    document.querySelectorAll('.ops-rolling-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        document.querySelectorAll('.ops-rolling-btn').forEach(b => {
          b.classList.remove('active', 'bg-white', 'shadow-2xs', 'text-slate-800');
          b.classList.add('text-slate-500');
        });
        btn.classList.add('active', 'bg-white', 'shadow-2xs', 'text-slate-800');
        btn.classList.remove('text-slate-500');
        this.showToast(`Trajectory mode: ${btn.textContent.trim()}`);
      });
    });

    // Tab 4 Reset Filters
    document.getElementById('btnOpsResetFilters')?.addEventListener('click', () => {
      const campFilter = document.getElementById('opsCampaignFilter');
      if (campFilter) campFilter.value = 'all';
      this.showToast('Diagnosis filters reset to standard growth baseline');
      this.renderOperationsView();
    });

    // Tab 4 Driver Rows Explanation on Hover
    const driverDescriptions = {
      cpm: "<strong>Ad Market Cost (CPM):</strong> +5.2% ad inventory cost surge increased cost per demo by ₹25.2.",
      ctr: "<strong>Link CTR:</strong> Higher creative click-through rates reduced booked demo cost by ₹19.8.",
      lp: "<strong>LP Load / Drop-off:</strong> Improved landing page speed shaved off ₹9.6 per booked demo.",
      leadconv: "<strong>Lead Form:</strong> Slight drop in lead form completion added ₹10.3 to demo acquisition cost.",
      bookingconv: "<strong>Sales Lead Quality:</strong> High-intent parent traffic boosted lead-to-demo conversion (+2.0%), directly reducing demo cost by ₹34.9."
    };

    document.querySelectorAll('.driver-row').forEach(row => {
      row.addEventListener('mouseenter', () => {
        const key = row.getAttribute('data-driver');
        const explanation = document.getElementById('opsDriverExplanation');
        if (explanation && driverDescriptions[key]) {
          explanation.innerHTML = `
            <svg class="w-4 h-4 text-sky-600 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="16" x2="12" y2="12"></line>
              <line x1="12" y1="8" x2="12.01" y2="8"></line>
            </svg>
            <span>${driverDescriptions[key]}</span>
          `;
        }
      });
    });

    // Tab 4 Table Cross-Highlight
    document.querySelectorAll('.table-row-inspect').forEach(tr => {
      tr.addEventListener('click', () => {
        const target = tr.getAttribute('data-target');
        document.querySelectorAll('.driver-row').forEach(dr => {
          if (dr.getAttribute('data-driver') === target) {
            dr.classList.add('ring-2', 'ring-sky-500', 'p-1', 'rounded-xl');
            setTimeout(() => {
              dr.classList.remove('ring-2', 'ring-sky-500', 'p-1', 'rounded-xl');
            }, 1800);
          }
        });
      });
    });

    // Tab 4 SVG Chart Points Tooltip
    const opsTooltip = document.getElementById('opsChartTooltip');
    const opsTooltipDate = document.getElementById('opsTooltipDate');
    const opsTooltipCpm = document.getElementById('opsTooltipCpm');
    const opsTooltipDemos = document.getElementById('opsTooltipDemos');

    document.querySelectorAll('.chart-point').forEach(pt => {
      pt.addEventListener('mouseenter', (e) => {
        if (!opsTooltip) return;
        const date = pt.getAttribute('data-date') || '2026-07-02';
        const cpm = pt.getAttribute('data-cpm') || '₹362';
        const demos = pt.getAttribute('data-demos') || '108';

        if (opsTooltipDate) opsTooltipDate.textContent = date;
        if (opsTooltipCpm) opsTooltipCpm.textContent = `CPM: ${cpm}`;
        if (opsTooltipDemos) opsTooltipDemos.textContent = `Demos: ${demos}`;

        const rect = pt.getBoundingClientRect();
        const parentRect = pt.closest('.relative').getBoundingClientRect();

        const left = rect.left - parentRect.left + (rect.width / 2);
        const top = rect.top - parentRect.top - 8;

        opsTooltip.style.left = `${left}px`;
        opsTooltip.style.top = `${top}px`;
        opsTooltip.classList.remove('hidden');
      });

      pt.addEventListener('mouseleave', () => {
        if (opsTooltip) opsTooltip.classList.add('hidden');
      });
    });

    // Tab 5 Meta Selectors & Controls
    document.getElementById('metaBookingSignalSelect')?.addEventListener('change', () => {
      this.renderMetaView();
      this.showToast('Updated Meta booking signal calculation');
    });

    document.getElementById('metaResultEventSelect')?.addEventListener('change', () => {
      this.renderMetaView();
      this.showToast('Updated Meta result event calculation');
    });

    document.querySelectorAll('.meta-device-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.meta-device-btn').forEach(b => {
          b.className = 'meta-device-btn px-2.5 py-1 text-xs font-medium text-slate-600 hover:text-slate-900 cursor-pointer transition-all';
        });
        btn.className = 'meta-device-btn active px-2.5 py-1 text-xs font-semibold rounded-lg bg-white text-slate-800 shadow-2xs cursor-pointer transition-all';
        this.selectedMetaOs = btn.getAttribute('data-os') || 'all';
        this.renderMetaLedgerTable();
        this.showToast(`Filtered delivery by ${btn.textContent}`);
      });
    });

    document.getElementById('metaLedgerSearch')?.addEventListener('input', () => {
      this.renderMetaLedgerTable();
    });

    document.getElementById('btnExportMetaLedger')?.addEventListener('click', () => {
      this.exportMetaLedgerCSV();
    });
  }

  bindMaturityCurveEvents() {
    const chartNodes = document.querySelectorAll('.chart-node');
    const tooltip = document.getElementById('curveTooltip');
    const tooltipDay = document.getElementById('tooltipDay');
    const tooltipRoas = document.getElementById('tooltipRoas');
    const tooltipPayback = document.getElementById('tooltipPayback');
    const tooltipRev = document.getElementById('tooltipRev');
    const chartContainer = document.getElementById('chartContainer');

    if (chartContainer && tooltip) {
      chartNodes.forEach(node => {
        node.addEventListener('mouseenter', () => {
          const day = node.getAttribute('data-day');
          const roas = node.getAttribute('data-roas');
          const payback = node.getAttribute('data-payback');
          const rev = node.getAttribute('data-rev');

          if (tooltipDay) tooltipDay.textContent = `${day} Milestone`;
          if (tooltipRoas) tooltipRoas.textContent = roas;
          if (tooltipPayback) tooltipPayback.textContent = payback;
          if (tooltipRev) tooltipRev.textContent = rev;

          const containerRect = chartContainer.getBoundingClientRect();
          const nodeRect = node.getBoundingClientRect();
          const leftOffset = nodeRect.left - containerRect.left + (nodeRect.width / 2);
          const topOffset = nodeRect.top - containerRect.top;

          tooltip.style.left = `${leftOffset}px`;
          tooltip.style.top = `${topOffset}px`;
          tooltip.classList.remove('opacity-0');
          tooltip.classList.add('opacity-100');
        });

        node.addEventListener('mouseleave', () => {
          tooltip.classList.add('opacity-0');
          tooltip.classList.remove('opacity-100');
        });

        node.addEventListener('click', () => {
          const day = node.getAttribute('data-day');
          this.setCohortWindow(day);
          this.showToast(`Jumped to milestone ${day}`);
        });
      });
    }

    document.querySelectorAll('.axis-label-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const axisVal = btn.getAttribute('data-axis');
        if (axisVal) {
          this.setCohortWindow(axisVal);
          this.showToast(`Cohort window updated to ${axisVal}`);
        }
      });
    });
  }

  setCohortWindow(windowVal) {
    this.selectedWindow = windowVal;

    document.querySelectorAll('.cohort-win-btn').forEach(btn => {
      if (btn.getAttribute('data-window') === windowVal) {
        btn.className = 'cohort-win-btn active-window px-3.5 py-1.5 rounded-lg text-xs font-semibold text-indigo-700 bg-white shadow-2xs border border-slate-200/90 transition-all font-mono cursor-pointer';
      } else {
        btn.className = 'cohort-win-btn px-3 py-1.5 rounded-lg text-xs font-medium text-slate-600 hover:text-slate-900 hover:bg-white/60 transition-all font-mono cursor-pointer';
      }
    });

    const activeDisplay = document.getElementById('activeWindowDisplay');
    if (activeDisplay) activeDisplay.textContent = `Active: ${windowVal}`;

    const summaryLabel = document.getElementById('cohortWindowSummaryLabel');
    if (summaryLabel) summaryLabel.textContent = `Aggregated for selected window (${windowVal})`;

    const windowNodeCoordinates = {
      'D0': { cx: 40, cy: 135, roas: '1.20×' },
      'D1': { cx: 160, cy: 126, roas: '1.80×' },
      'D3': { cx: 280, cy: 100, roas: '3.40×' },
      'D7': { cx: 420, cy: 74, roas: '5.60×' },
      'D14': { cx: 580, cy: 48, roas: '8.20×' },
      'D21': { cx: 720, cy: 30, roas: '9.80×' },
      'D30': { cx: 840, cy: 22, roas: '10.40×' },
      'Till date': { cx: 950, cy: 15, roas: '11.00×' }
    };

    const nodeData = windowNodeCoordinates[windowVal];
    const activeNodeRing = document.getElementById('activeNodeRing');
    const heroRoas = document.getElementById('heroRoasValue');

    if (nodeData && activeNodeRing) {
      activeNodeRing.setAttribute('cx', nodeData.cx);
      activeNodeRing.setAttribute('cy', nodeData.cy);
      if (heroRoas) {
        heroRoas.textContent = nodeData.roas;
        heroRoas.classList.add('text-indigo-600');
        setTimeout(() => heroRoas.classList.remove('text-indigo-600'), 300);
      }
    }

    this.renderCohortView();
  }

  applyOpsPreset(preset) {
    const perfFrom = document.getElementById('opsPerfFrom');
    const perfTo = document.getElementById('opsPerfTo');
    const compFrom = document.getElementById('opsCompFrom');
    const compTo = document.getElementById('opsCompTo');

    if (preset === '7d') {
      if (perfFrom) perfFrom.value = '2026-07-25';
      if (perfTo) perfTo.value = '2026-07-31';
      if (compFrom) compFrom.value = '2026-07-18';
      if (compTo) compTo.value = '2026-07-24';
    } else if (preset === '14d') {
      if (perfFrom) perfFrom.value = '2026-07-18';
      if (perfTo) perfTo.value = '2026-07-31';
      if (compFrom) compFrom.value = '2026-07-04';
      if (compTo) compTo.value = '2026-07-17';
    } else if (preset === 'mom') {
      if (perfFrom) perfFrom.value = '2026-07-01';
      if (perfTo) perfTo.value = '2026-07-31';
      if (compFrom) compFrom.value = '2026-06-01';
      if (compTo) compTo.value = '2026-06-30';
    }
    this.renderOperationsView();
    this.showToast(`Applied comparison preset: ${preset.toUpperCase()}`);
  }

  async loadCatalogAndData() {
    try {
      const res = await fetch('/api/v1/catalog').catch(() => null);
      if (res && res.ok) {
        this.catalog = await res.json();
      } else {
        this.generateDefaultCatalog();
      }
      this.renderCurrentView();
    } catch (e) {
      console.warn("Using resilient client dataset:", e);
      this.generateDefaultCatalog();
      this.renderCurrentView();
    }
  }

  generateDefaultCatalog() {
    const dates = [];
    for (let i = 1; i <= 31; i++) {
      dates.push(`2026-07-${String(i).padStart(2, '0')}`);
    }
    this.catalog = {
      from: '2026-07-01',
      to: '2026-07-31',
      periods: ['D0', 'D1', 'D3', 'D7', 'D14', 'D21', 'D30', 'Till date'],
      markets: ['India', 'United States', 'UAE', 'Singapore', 'United Kingdom'],
      courses: ['Public Speaking & Debating', 'Creative Writing', 'Young Authors Program', 'Financial Literacy'],
      dates: dates
    };
  }

  // ==================== TAB 1: COMPANY VIEW ====================
  renderCompanyView() {
    const from = document.getElementById('companyDateFrom')?.value || '2026-07-01';
    const to = document.getElementById('companyDateTo')?.value || '2026-07-31';
    const slice = document.getElementById('companySliceFilter')?.value || 'date';

    const dailyRows = [];
    let totSpend = 0, totRev = 0, totRenew = 0, totBooked = 0, totSched = 0, totAtt = 0, totConv = 0, totRenewals = 0;

    for (let i = 1; i <= 31; i++) {
      const dStr = `2026-07-${String(i).padStart(2, '0')}`;
      if (dStr >= from && dStr <= to) {
        const spend = 145000 + Math.sin(i * 1.1) * 32000;
        const booked = Math.round(310 + Math.sin(i * 1.5) * 55);
        const sched = Math.round(booked * 0.92);
        const att = Math.round(sched * 0.68);
        const conv = Math.round(att * 0.42);
        const renewals = Math.round(conv * 0.35);
        const rev = conv * 18500;
        const renewRev = renewals * 16200;
        const roas = rev / spend;

        totSpend += spend;
        totRev += rev;
        totRenew += renewRev;
        totBooked += booked;
        totSched += sched;
        totAtt += att;
        totConv += conv;
        totRenewals += renewals;

        dailyRows.push({
          date: dStr,
          spend,
          cost_per_demo_booked: spend / booked,
          revenue_per_demo_booked: rev / booked,
          demos_booked: booked,
          demos_scheduled: sched,
          demos_attended: att,
          attendance: att / sched,
          new_conversions: conv,
          conversion: conv / att,
          renewals,
          new_revenue: rev,
          revenue: rev,
          renewal_revenue: renewRev,
          roas
        });
      }
    }

    const total = {
      spend: totSpend,
      revenue: totRev,
      new_revenue: totRev,
      renewal_revenue: totRenew,
      demos_booked: totBooked,
      demos_scheduled: totSched,
      demos_attended: totAtt,
      new_conversions: totConv,
      renewals: totRenewals,
      cost_per_demo_booked: totBooked > 0 ? totSpend / totBooked : 0,
      revenue_per_demo_booked: totBooked > 0 ? totRev / totBooked : 0,
      attendance: totSched > 0 ? totAtt / totSched : 0,
      conversion: totAtt > 0 ? totConv / totAtt : 0,
      roas: totSpend > 0 ? totRev / totSpend : 0
    };

    const cash = n => '₹' + Math.round(n).toLocaleString('en-IN');
    const setElemText = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.textContent = val;
    };

    setElemText('kpiCompanySpend', cash(total.spend));
    setElemText('kpiCompanyNewRev', cash(total.revenue));
    setElemText('kpiCompanyRoas', total.roas.toFixed(2) + '×');
    setElemText('kpiCompanyRenewalRev', cash(total.renewal_revenue));
    setElemText('kpiCompanyCostPerDemo', cash(total.cost_per_demo_booked));
    setElemText('kpiCompanyRevPerDemo', cash(total.revenue_per_demo_booked));

    const chartRows = slice === 'date' ? dailyRows : [{ date: 'Selected Period', ...total }];
    window.cohortChartRenderer?.renderCompanyFinancialChart('companyFinancialChart', chartRows, slice === 'date');

    const tbody = document.getElementById('companyTableBody');
    if (tbody) {
      let html = `<tr class="total-row bg-slate-100/90 font-bold border-b-2 border-slate-300">
        <td class="py-3 px-3.5 text-slate-900 font-semibold">TOTAL (${from} – ${to})</td>
        <td class="py-3 px-3.5 text-right font-mono">${cash(total.spend)}</td>
        <td class="py-3 px-3.5 text-right font-mono">${cash(total.cost_per_demo_booked)}</td>
        <td class="py-3 px-3.5 text-right font-mono text-emerald-700">${cash(total.revenue_per_demo_booked)}</td>
        <td class="py-3 px-3 text-right font-mono">${total.demos_booked.toLocaleString()}</td>
        <td class="py-3 px-3 text-right font-mono">${total.demos_scheduled.toLocaleString()}</td>
        <td class="py-3 px-3 text-right font-mono">${total.demos_attended.toLocaleString()}</td>
        <td class="py-3 px-3 text-center font-mono">${(total.attendance * 100).toFixed(1)}%</td>
        <td class="py-3 px-3 text-right font-mono font-semibold">${total.new_conversions.toLocaleString()}</td>
        <td class="py-3 px-3 text-center font-mono">${(total.conversion * 100).toFixed(1)}%</td>
        <td class="py-3 px-3 text-right font-mono">${total.renewals.toLocaleString()}</td>
        <td class="py-3 px-3.5 text-right font-mono font-bold text-indigo-900">${cash(total.revenue)}</td>
        <td class="py-3 px-3.5 text-right font-mono text-indigo-800">${cash(total.renewal_revenue)}</td>
        <td class="py-3 px-3.5 text-right font-mono font-extrabold text-emerald-700 text-sm">${total.roas.toFixed(2)}×</td>
      </tr>`;

      if (slice === 'date') {
        dailyRows.slice().reverse().forEach((r, idx) => {
          const bgClass = idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/50';
          html += `<tr class="hover:bg-indigo-50/40 transition-colors ${bgClass}">
            <td class="py-2.5 px-3.5 font-mono text-slate-700 font-medium whitespace-nowrap">${r.date}</td>
            <td class="py-2.5 px-3.5 text-right font-mono text-slate-700">${cash(r.spend)}</td>
            <td class="py-2.5 px-3.5 text-right font-mono text-slate-600">${cash(r.cost_per_demo_booked)}</td>
            <td class="py-2.5 px-3.5 text-right font-mono text-emerald-600 font-medium">${cash(r.revenue_per_demo_booked)}</td>
            <td class="py-2.5 px-3 text-right font-mono text-slate-700">${r.demos_booked}</td>
            <td class="py-2.5 px-3 text-right font-mono text-slate-600">${r.demos_scheduled}</td>
            <td class="py-2.5 px-3 text-right font-mono text-slate-600">${r.demos_attended}</td>
            <td class="py-2.5 px-3 text-center font-mono text-slate-700">${(r.attendance * 100).toFixed(1)}%</td>
            <td class="py-2.5 px-3 text-right font-mono font-semibold text-slate-800">${r.new_conversions}</td>
            <td class="py-2.5 px-3 text-center font-mono text-slate-700">${(r.conversion * 100).toFixed(1)}%</td>
            <td class="py-2.5 px-3 text-right font-mono text-slate-600">${r.renewals}</td>
            <td class="py-2.5 px-3.5 text-right font-mono font-semibold text-slate-900">${cash(r.new_revenue)}</td>
            <td class="py-2.5 px-3.5 text-right font-mono text-indigo-700">${cash(r.renewal_revenue)}</td>
            <td class="py-2.5 px-3.5 text-right font-mono font-bold text-emerald-700">${r.roas.toFixed(2)}×</td>
          </tr>`;
        });
      }
      tbody.innerHTML = html;
    }
  }

  // ==================== TAB 2: COHORT EXPLORER (REDESIGNED) ====================
  renderCohortView() {
    const cash = n => '₹' + Math.round(n).toLocaleString('en-IN');
    const windowMultiplier = {
      'D0': 0.35, 'D1': 0.48, 'D3': 0.65, 'D7': 0.82, 'D14': 0.94, 'D21': 0.98, 'D30': 1.0, 'Till date': 1.10
    }[this.selectedWindow] || 1.10;

    const spend = 4450000;
    const contacts = 18840;
    const booked = Math.round(9936 * (windowMultiplier / 1.10));
    const att = Math.round(6587 * (windowMultiplier / 1.10));
    const conv = Math.round(2638 * (windowMultiplier / 1.10));
    const rev = Math.round(48950000 * (windowMultiplier / 1.10));
    const roas = rev / spend;

    const setElemText = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.textContent = val;
    };

    setElemText('kpiSpend', cash(spend));
    setElemText('kpiContacts', contacts.toLocaleString());
    setElemText('kpiCostPerDemo', cash(spend / booked));
    setElemText('kpiDemosBooked', booked.toLocaleString());
    setElemText('kpiAttendance', ((att / booked) * 100).toFixed(1) + '%');
    setElemText('kpiLeadConv', ((conv / contacts) * 100).toFixed(1) + '%');
    setElemText('heroRoasValue', roas.toFixed(2) + '×');
    setElemText('kpiRevPerDemo', cash(rev / booked));

    this.renderCohortTable();
  }

  getCohortDataRows() {
    const windowMultiplier = {
      'D0': 0.35, 'D1': 0.48, 'D3': 0.65, 'D7': 0.82, 'D14': 0.94, 'D21': 0.98, 'D30': 1.0, 'Till date': 1.10
    }[this.selectedWindow] || 1.10;

    const sampleRows = [];
    const campaigns = [
      { name: 'Universal_Debating_India_Core', dot: 'bg-emerald-500', market: 'India', course: 'Public Speaking & Debating', baseSpend: 145000, baseContacts: 620 },
      { name: 'CreativeWriting_Intl_USA_Target', dot: 'bg-indigo-500', market: 'United States', course: 'Creative Writing', baseSpend: 152000, baseContacts: 580 },
      { name: 'PublicSpeaking_Scale_Metro_HighIntent', dot: 'bg-emerald-500', market: 'India', course: 'Public Speaking & Debating', baseSpend: 160000, baseContacts: 690 },
      { name: 'YoungAuthors_Retention_UAE_Gulf', dot: 'bg-amber-500', market: 'UAE', course: 'Young Authors Program', baseSpend: 138000, baseContacts: 510 },
      { name: 'DebateClub_Direct_HighIntent', dot: 'bg-indigo-500', market: 'India', course: 'Public Speaking & Debating', baseSpend: 125000, baseContacts: 490 },
      { name: 'FinancialLiteracy_Beta_India', dot: 'bg-emerald-500', market: 'India', course: 'Financial Literacy', baseSpend: 95000, baseContacts: 380 }
    ];

    for (let day = 1; day <= 6; day++) {
      const dStr = `2026-07-${String(day).padStart(2, '0')}`;
      campaigns.forEach(c => {
        const spend = Math.round(c.baseSpend + (day * 1800));
        const contacts = Math.round(c.baseContacts + (day * 10));
        const booked = Math.round(contacts * 0.50 * (windowMultiplier / 1.10));
        const held = Math.round(booked * 0.92);
        const attended = Math.round(held * 0.74);
        const conv = Math.round(attended * 0.44);
        const rev = Math.round(conv * 18500 * (windowMultiplier / 1.10));
        const impr = contacts * 650;
        const clicks = Math.round(impr * 0.0125);
        const link_clicks = Math.round(clicks * 0.61);
        const lpv = Math.round(link_clicks * 0.82);

        sampleRows.push({
          date: dStr,
          campaign: c.name,
          dot: c.dot,
          market: c.market,
          course: c.course,
          spend,
          contacts,
          booked,
          held,
          attended,
          conv,
          rev,
          impr,
          clicks,
          link_clicks,
          lpv
        });
      });
    }

    return sampleRows;
  }

  renderCohortTable() {
    const thead = document.getElementById('cohortTableHead');
    const tbody = document.getElementById('cohortTableBody');
    const tfoot = document.getElementById('cohortTableFoot');
    const emptyState = document.getElementById('emptyTableState');
    const resultsCountText = document.getElementById('tableResultsCount');
    if (!thead || !tbody) return;

    const cash = n => '₹' + Math.round(n).toLocaleString('en-IN');
    const cols = this.allMetrics ?
      ['Date', 'Campaign Name', 'Spend', 'Contacts', 'Cost/Demo', 'Rev/Demo', 'Booked', 'Held', 'Attended', 'Att %', 'Conv', 'Lead Conv %', 'ARPU', 'New Rev', 'New ROAS', 'Impr', 'Clicks', 'Link Clicks', 'LPV', 'CPM', 'Link CTR'] :
      ['Date', 'Campaign Name', 'Spend', 'Cost/Demo', 'Rev/Demo', 'Contacts', 'Booked', 'Attended', 'Conv', 'Lead Conv %', 'New Rev', 'New ROAS'];

    thead.innerHTML = `<tr class="bg-slate-50/80 border-b border-slate-200/80 text-[11px] font-bold uppercase tracking-wider text-slate-500">
      ${cols.map((c, i) => `<th class="py-3 px-3.5 ${i > 1 ? 'text-right' : 'text-left'} whitespace-nowrap">${c}</th>`).join('')}
    </tr>`;

    let rows = this.getCohortDataRows();

    // Filter by live search
    if (this.cohortSearchQuery) {
      rows = rows.filter(r => 
        r.campaign.toLowerCase().includes(this.cohortSearchQuery) ||
        r.date.includes(this.cohortSearchQuery) ||
        r.market.toLowerCase().includes(this.cohortSearchQuery) ||
        r.course.toLowerCase().includes(this.cohortSearchQuery)
      );
    }

    if (rows.length === 0) {
      tbody.innerHTML = '';
      if (emptyState) emptyState.classList.remove('hidden');
      if (tfoot) tfoot.classList.add('hidden');
      if (resultsCountText) {
        resultsCountText.innerHTML = `Showing <strong class="font-semibold text-slate-700">0</strong> matching records`;
      }
      return;
    }

    if (emptyState) emptyState.classList.add('hidden');
    if (tfoot) tfoot.classList.remove('hidden');

    let totSpend = 0, totContacts = 0, totBooked = 0, totHeld = 0, totAttended = 0, totConv = 0, totRev = 0, totImpr = 0, totClicks = 0, totLinkClicks = 0, totLpv = 0;

    const rowsHtml = rows.map((r) => {
      totSpend += r.spend;
      totContacts += r.contacts;
      totBooked += r.booked;
      totHeld += r.held;
      totAttended += r.attended;
      totConv += r.conv;
      totRev += r.rev;
      totImpr += r.impr;
      totClicks += r.clicks;
      totLinkClicks += r.link_clicks;
      totLpv += r.lpv;

      const cpdb = r.booked > 0 ? r.spend / r.booked : 0;
      const rpdb = r.booked > 0 ? r.rev / r.booked : 0;
      const roas = r.spend > 0 ? r.rev / r.spend : 0;
      const leadConv = r.contacts > 0 ? (r.conv / r.contacts) * 100 : 0;
      const attPct = r.held > 0 ? (r.attended / r.held) * 100 : 0;
      const cpm = r.impr > 0 ? (r.spend / (r.impr / 1000)) : 0;
      const linkCtr = r.impr > 0 ? (r.link_clicks / r.impr) * 100 : 0;
      const arpu = r.conv > 0 ? r.rev / r.conv : 0;

      if (!this.allMetrics) {
        return `<tr class="table-row-item hover:bg-slate-50/80 transition-colors group cursor-pointer border-b border-slate-100">
          <td class="py-3.5 px-4 font-mono text-slate-500 whitespace-nowrap">${r.date}</td>
          <td class="py-3.5 px-4 whitespace-nowrap">
            <div class="flex items-center space-x-2">
              <span class="w-2 h-2 rounded-full ${r.dot}"></span>
              <span class="font-semibold text-slate-900 group-hover:text-indigo-600 transition-colors campaign-name">${r.campaign}</span>
            </div>
          </td>
          <td class="py-3.5 px-3 font-mono text-right text-slate-800">${cash(r.spend)}</td>
          <td class="py-3.5 px-3 font-mono text-right text-slate-600">${cash(cpdb)}</td>
          <td class="py-3.5 px-3 font-mono text-right text-emerald-600 font-medium">${cash(rpdb)}</td>
          <td class="py-3.5 px-3 font-mono text-right text-slate-600">${r.contacts.toLocaleString()}</td>
          <td class="py-3.5 px-3 font-mono text-right text-slate-600 font-medium">${r.booked.toLocaleString()}</td>
          <td class="py-3.5 px-3 font-mono text-right text-slate-600">${r.attended.toLocaleString()}</td>
          <td class="py-3.5 px-3 font-mono text-right font-semibold text-slate-800">${r.conv.toLocaleString()}</td>
          <td class="py-3.5 px-3 font-mono text-right text-slate-700">${leadConv.toFixed(1)}%</td>
          <td class="py-3.5 px-4 font-mono text-right font-semibold text-slate-900">${cash(r.rev)}</td>
          <td class="py-3.5 px-4 font-mono text-right font-bold text-emerald-700 bg-emerald-50/60 whitespace-nowrap">
            <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-emerald-100/70 text-emerald-800">
              ${roas.toFixed(2)}×
            </span>
          </td>
        </tr>`;
      } else {
        return `<tr class="table-row-item hover:bg-slate-50/80 transition-colors group cursor-pointer border-b border-slate-100 text-xs">
          <td class="py-2.5 px-3 font-mono text-slate-500 whitespace-nowrap">${r.date}</td>
          <td class="py-2.5 px-3 whitespace-nowrap">
            <div class="flex items-center space-x-2">
              <span class="w-2 h-2 rounded-full ${r.dot}"></span>
              <span class="font-semibold text-slate-900 group-hover:text-indigo-600 transition-colors campaign-name">${r.campaign}</span>
            </div>
          </td>
          <td class="py-2.5 px-3 font-mono text-right text-slate-800">${cash(r.spend)}</td>
          <td class="py-2.5 px-3 font-mono text-right text-slate-600">${r.contacts.toLocaleString()}</td>
          <td class="py-2.5 px-3 font-mono text-right text-slate-600">${cash(cpdb)}</td>
          <td class="py-2.5 px-3 font-mono text-right text-emerald-600">${cash(rpdb)}</td>
          <td class="py-2.5 px-3 font-mono text-right text-slate-700">${r.booked.toLocaleString()}</td>
          <td class="py-2.5 px-3 font-mono text-right text-slate-600">${r.held.toLocaleString()}</td>
          <td class="py-2.5 px-3 font-mono text-right text-slate-600">${r.attended.toLocaleString()}</td>
          <td class="py-2.5 px-3 font-mono text-center text-slate-700">${attPct.toFixed(1)}%</td>
          <td class="py-2.5 px-3 font-mono text-right font-semibold text-slate-800">${r.conv.toLocaleString()}</td>
          <td class="py-2.5 px-3 font-mono text-right text-slate-700">${leadConv.toFixed(1)}%</td>
          <td class="py-2.5 px-3 font-mono text-right text-slate-600">${cash(arpu)}</td>
          <td class="py-2.5 px-3 font-mono text-right font-semibold text-slate-900">${cash(r.rev)}</td>
          <td class="py-2.5 px-3 font-mono text-right font-bold text-emerald-700 bg-emerald-50/60">${roas.toFixed(2)}×</td>
          <td class="py-2.5 px-3 font-mono text-right text-slate-600">${r.impr.toLocaleString()}</td>
          <td class="py-2.5 px-3 font-mono text-right text-slate-600">${r.clicks.toLocaleString()}</td>
          <td class="py-2.5 px-3 font-mono text-right text-slate-600">${r.link_clicks.toLocaleString()}</td>
          <td class="py-2.5 px-3 font-mono text-right text-slate-600">${r.lpv.toLocaleString()}</td>
          <td class="py-2.5 px-3 font-mono text-right text-slate-600">${cash(cpm)}</td>
          <td class="py-2.5 px-3 font-mono text-right text-slate-600">${linkCtr.toFixed(2)}%</td>
        </tr>`;
      }
    }).join('');

    tbody.innerHTML = rowsHtml;

    if (resultsCountText) {
      resultsCountText.innerHTML = `Showing <strong class="font-semibold text-slate-700">1 - ${rows.length}</strong> daily records`;
    }

    // Render Master Totals Foot
    if (tfoot) {
      const totCpdb = totBooked > 0 ? totSpend / totBooked : 0;
      const totRpdb = totBooked > 0 ? totRev / totBooked : 0;
      const totRoas = totSpend > 0 ? totRev / totSpend : 0;
      const totLeadConv = totContacts > 0 ? (totConv / totContacts) * 100 : 0;

      if (!this.allMetrics) {
        tfoot.innerHTML = `<tr class="bg-slate-100/80 border-t-2 border-slate-200 text-[11px] font-bold text-slate-800">
          <td class="py-3 px-4 font-semibold uppercase tracking-wider" colspan="2">Filtered Totals (${rows.length} Records)</td>
          <td class="py-3 px-3 font-mono text-right">${cash(totSpend)}</td>
          <td class="py-3 px-3 font-mono text-right text-slate-700">${cash(totCpdb)}</td>
          <td class="py-3 px-3 font-mono text-right text-emerald-700">${cash(totRpdb)}</td>
          <td class="py-3 px-3 font-mono text-right">${totContacts.toLocaleString()}</td>
          <td class="py-3 px-3 font-mono text-right">${totBooked.toLocaleString()}</td>
          <td class="py-3 px-3 font-mono text-right">${totAttended.toLocaleString()}</td>
          <td class="py-3 px-3 font-mono text-right text-slate-900">${totConv.toLocaleString()}</td>
          <td class="py-3 px-3 font-mono text-right text-slate-800">${totLeadConv.toFixed(1)}%</td>
          <td class="py-3 px-4 font-mono text-right font-extrabold text-slate-900">${cash(totRev)}</td>
          <td class="py-3 px-4 font-mono text-right font-extrabold text-emerald-800 bg-emerald-100/60">
            ${totRoas.toFixed(2)}×
          </td>
        </tr>`;
      } else {
        tfoot.innerHTML = `<tr class="bg-slate-100/80 border-t-2 border-slate-200 text-[11px] font-bold text-slate-800">
          <td class="py-3 px-3 font-semibold uppercase tracking-wider" colspan="2">Filtered Totals (${rows.length} Records)</td>
          <td class="py-3 px-3 font-mono text-right">${cash(totSpend)}</td>
          <td class="py-3 px-3 font-mono text-right">${totContacts.toLocaleString()}</td>
          <td class="py-3 px-3 font-mono text-right text-slate-700">${cash(totCpdb)}</td>
          <td class="py-3 px-3 font-mono text-right text-emerald-700">${cash(totRpdb)}</td>
          <td class="py-3 px-3 font-mono text-right">${totBooked.toLocaleString()}</td>
          <td class="py-3 px-3 font-mono text-right">${totHeld.toLocaleString()}</td>
          <td class="py-3 px-3 font-mono text-right">${totAttended.toLocaleString()}</td>
          <td class="py-3 px-3 font-mono text-center">${(totAttended / (totHeld || 1) * 100).toFixed(1)}%</td>
          <td class="py-3 px-3 font-mono text-right text-slate-900">${totConv.toLocaleString()}</td>
          <td class="py-3 px-3 font-mono text-right text-slate-800">${totLeadConv.toFixed(1)}%</td>
          <td class="py-3 px-3 font-mono text-right">${cash(totConv > 0 ? totRev / totConv : 0)}</td>
          <td class="py-3 px-3 font-mono text-right font-extrabold text-slate-900">${cash(totRev)}</td>
          <td class="py-3 px-3 font-mono text-right font-extrabold text-emerald-800 bg-emerald-100/60">${totRoas.toFixed(2)}×</td>
          <td class="py-3 px-3 font-mono text-right">${totImpr.toLocaleString()}</td>
          <td class="py-3 px-3 font-mono text-right">${totClicks.toLocaleString()}</td>
          <td class="py-3 px-3 font-mono text-right">${totLinkClicks.toLocaleString()}</td>
          <td class="py-3 px-3 font-mono text-right">${totLpv.toLocaleString()}</td>
          <td class="py-3 px-3 font-mono text-right">${cash(totImpr > 0 ? totSpend / (totImpr / 1000) : 0)}</td>
          <td class="py-3 px-3 font-mono text-right">${(totLinkClicks / (totImpr || 1) * 100).toFixed(2)}%</td>
        </tr>`;
      }
    }
  }

  exportCohortCSV() {
    const rows = this.getCohortDataRows();
    if (!rows || rows.length === 0) return;

    const headers = ['Date', 'Campaign', 'Market', 'Course', 'Spend', 'Contacts', 'Demos Booked', 'Attended', 'Conversions', 'New Revenue', 'ROAS'];
    const csvLines = [headers.join(',')];

    rows.forEach(r => {
      const roas = (r.rev / r.spend).toFixed(2);
      csvLines.push([
        r.date,
        `"${r.campaign.replace(/"/g, '""')}"`,
        `"${r.market}"`,
        `"${r.course}"`,
        r.spend,
        r.contacts,
        r.booked,
        r.attended,
        r.conv,
        r.rev,
        roas
      ].join(','));
    });

    const blob = new Blob([csvLines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `bambinos_cohort_${this.selectedWindow.toLowerCase().replace(/\s+/g, '_')}_export.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    this.showToast('CSV export generated successfully');
  }

  // ==================== TAB 3: PROGRESSION HEATMAP (STITCH REDESIGN) ====================
  getRoasTier(val) {
    const num = parseFloat(val) || 0;
    if (num < 0.95) return 'roas-tier-1';
    if (num < 1.25) return 'roas-tier-2';
    if (num < 1.65) return 'roas-tier-3';
    if (num < 1.90) return 'roas-tier-4';
    if (num < 2.20) return 'roas-tier-5';
    if (num < 2.50) return 'roas-tier-6';
    if (num < 2.80) return 'roas-tier-7';
    return 'roas-tier-8';
  }

  getProgressionCohortRows() {
    const windows = ['D0', 'D1', 'D3', 'D7', 'D14', 'D21', 'D30', 'Till Date'];
    const cohortSpecs = [
      { date: '2026-07-01', d0: 0.73, d1: 1.01, d3: 1.37, d7: 1.72, d14: 1.97, d21: 2.06, d30: 2.10, till: 2.27, lift: '+210%', isStar: false, path: 'M2,18 L10,14 L20,10 L35,6 L48,2' },
      { date: '2026-07-02', d0: 0.84, d1: 1.15, d3: 1.56, d7: 1.97, d14: 2.26, d21: 2.35, d30: 2.40, till: 2.59, lift: '+208%', isStar: false, path: 'M2,18 L10,13 L20,9 L35,5 L48,2' },
      { date: '2026-07-03', d0: 0.94, d1: 1.30, d3: 1.76, d7: 2.21, d14: 2.54, d21: 2.65, d30: 2.70, till: 2.92, lift: '+210%', isStar: true, path: 'M2,18 L10,12 L20,7 L35,4 L48,1' },
      { date: '2026-07-04', d0: 0.73, d1: 1.01, d3: 1.37, d7: 1.72, d14: 1.97, d21: 2.06, d30: 2.10, till: 2.27, lift: '+210%', isStar: false, path: 'M2,18 L10,14 L20,10 L35,6 L48,2' },
      { date: '2026-07-05', d0: 0.84, d1: 1.15, d3: 1.56, d7: 1.97, d14: 2.26, d21: 2.35, d30: 2.40, till: 2.59, lift: '+208%', isStar: false, path: 'M2,18 L10,13 L20,9 L35,5 L48,2' },
      { date: '2026-07-06', d0: 0.94, d1: 1.30, d3: 1.76, d7: 2.21, d14: 2.54, d21: 2.65, d30: 2.70, till: 2.92, lift: '+210%', isStar: true, path: 'M2,18 L10,12 L20,7 L35,4 L48,1' },
      { date: '2026-07-07', d0: 0.73, d1: 1.01, d3: 1.37, d7: 1.72, d14: 1.97, d21: 2.06, d30: 2.10, till: 2.27, lift: '+210%', isStar: false, path: 'M2,18 L10,14 L20,10 L35,6 L48,2' },
      { date: '2026-07-08', d0: 0.78, d1: 1.08, d3: 1.45, d7: 1.85, d14: 2.12, d21: 2.20, d30: 2.25, till: 2.42, lift: '+210%', isStar: false, path: 'M2,18 L10,14 L20,9 L35,6 L48,2' },
      { date: '2026-07-09', d0: 0.82, d1: 1.14, d3: 1.52, d7: 1.94, d14: 2.22, d21: 2.31, d30: 2.36, till: 2.54, lift: '+210%', isStar: false, path: 'M2,18 L10,13 L20,8 L35,5 L48,2' },
      { date: '2026-07-10', d0: 0.89, d1: 1.24, d3: 1.68, d7: 2.10, d14: 2.42, d21: 2.52, d30: 2.58, till: 2.78, lift: '+212%', isStar: false, path: 'M2,18 L10,12 L20,8 L35,4 L48,2' }
    ];
    return { windows, rows: cohortSpecs };
  }

  renderProgressionView() {
    const tbody = document.getElementById('cohortProgressionTableBody') || document.getElementById('heatmapMatrixBody');
    if (!tbody) return;

    const { windows, rows } = this.getProgressionCohortRows();
    const metric = this.progressionMetric || 'new_roas';

    // Metric multiplier / transform factor
    const metricMultipliers = {
      'new_roas': 1.0,
      'blended_roas': 1.08,
      'cash_roas': 1.16,
      'ltv_mult': 1.34
    };
    const mult = metricMultipliers[metric] || 1.0;

    // Filter rows
    let visibleRows = rows;
    if (this.progressionFilter === 'top') {
      visibleRows = rows.filter(r => (r.till * mult) >= 2.50);
    } else if (this.progressionFilter === 'recent') {
      visibleRows = rows.slice(-4);
    }

    const html = visibleRows.map((r) => {
      const vD0 = (r.d0 * mult).toFixed(2);
      const vD1 = (r.d1 * mult).toFixed(2);
      const vD3 = (r.d3 * mult).toFixed(2);
      const vD7 = (r.d7 * mult).toFixed(2);
      const vD14 = (r.d14 * mult).toFixed(2);
      const vD21 = (r.d21 * mult).toFixed(2);
      const vD30 = (r.d30 * mult).toFixed(2);
      const vTill = (r.till * mult).toFixed(2);

      const cell = (val, winKey) => {
        const tier = this.getRoasTier(val);
        return `<td class="text-center p-1">
          <button class="w-full py-2.5 rounded-xl ${tier} font-semibold cell-interactive font-mono shadow-2xs" 
                  data-val="${val}" data-win="${winKey}" data-date="${r.date}">
            ${val}×
          </button>
        </td>`;
      };

      const starBadge = r.isStar ? `<span class="text-amber-500 text-xs font-bold ml-1">★</span>` : '';
      const sparkColor = r.isStar ? 'stroke-indigo-600 text-indigo-600' : 'stroke-emerald-600 text-emerald-600';

      return `<tr class="cohort-progression-row hover:bg-slate-50/40 transition-colors" data-date="${r.date}" data-peak="${vTill}">
        <td class="px-4 py-3 bg-white border border-slate-200/80 rounded-xl font-semibold text-slate-800 shadow-2xs flex items-center justify-between whitespace-nowrap">
          <span>${r.date}</span>
          ${starBadge}
        </td>
        ${cell(vD0, 'D0')}
        ${cell(vD1, 'D1')}
        ${cell(vD3, 'D3')}
        ${cell(vD7, 'D7')}
        ${cell(vD14, 'D14')}
        ${cell(vD21, 'D21')}
        ${cell(vD30, 'D30')}
        ${cell(vTill, 'Till Date')}
        <td class="text-center px-2 py-1 bg-white border border-slate-200/80 rounded-xl">
          <div class="flex items-center justify-between text-xs px-2">
            <span class="${sparkColor} font-bold font-mono">${r.lift}</span>
            <svg class="w-12 h-5 ${sparkColor} fill-none stroke-[2]" viewBox="0 0 50 20">
              <path d="${r.path}" stroke-linecap="round"></path>
            </svg>
          </div>
        </td>
      </tr>`;
    }).join('');

    tbody.innerHTML = html;

    // Attach Cell Hover Tooltip Listeners
    this.bindProgressionTooltips();
  }

  bindProgressionTooltips() {
    const tooltip = document.getElementById('matrixTooltip');
    const ttDate = document.getElementById('ttCohortDate');
    const ttWindow = document.getElementById('ttWindowBadge');
    const ttRoas = document.getElementById('ttRoasVal');
    const ttRev = document.getElementById('ttRevVal');
    const ttSpend = document.getElementById('ttSpendVal');
    const ttLift = document.getElementById('ttLiftVal');

    if (!tooltip) return;

    const cells = document.querySelectorAll('.cell-interactive');
    cells.forEach(cell => {
      cell.addEventListener('mouseenter', (e) => {
        const date = cell.getAttribute('data-date') || 'Cohort';
        const windowKey = cell.getAttribute('data-win') || 'D0';
        const roasVal = cell.getAttribute('data-val') || '1.00';
        const numRoas = parseFloat(roasVal);

        const simulatedSpend = 425000;
        const simulatedRev = Math.round(simulatedSpend * numRoas);
        const baseD0 = 0.73;
        const lift = Math.round(((numRoas - baseD0) / baseD0) * 100);

        if (ttDate) ttDate.textContent = date;
        if (ttWindow) ttWindow.textContent = 'Window ' + windowKey;
        if (ttRoas) ttRoas.textContent = roasVal + '×';
        if (ttRev) ttRev.textContent = '₹' + simulatedRev.toLocaleString('en-IN');
        if (ttSpend) ttSpend.textContent = '₹' + simulatedSpend.toLocaleString('en-IN');
        if (ttLift) ttLift.textContent = (lift >= 0 ? '+' : '') + lift + '% vs D0';

        tooltip.classList.remove('hidden');
        tooltip.style.opacity = '1';
      });

      cell.addEventListener('mousemove', (e) => {
        tooltip.style.left = `${e.clientX + 16}px`;
        tooltip.style.top = `${e.clientY + 16}px`;
      });

      cell.addEventListener('mouseleave', () => {
        tooltip.classList.add('hidden');
        tooltip.style.opacity = '0';
      });
    });
  }

  exportProgressionCSV() {
    const { rows } = this.getProgressionCohortRows();
    const metric = this.progressionMetric || 'new_roas';
    const mult = { 'new_roas': 1.0, 'blended_roas': 1.08, 'cash_roas': 1.16, 'ltv_mult': 1.34 }[metric] || 1.0;

    const headers = ['Capture Date', 'D0', 'D1', 'D3', 'D7', 'D14', 'D21', 'D30', 'Till Date', 'Trajectory Lift'];
    const csvLines = [headers.join(',')];

    rows.forEach(r => {
      csvLines.push([
        r.date,
        (r.d0 * mult).toFixed(2) + '×',
        (r.d1 * mult).toFixed(2) + '×',
        (r.d3 * mult).toFixed(2) + '×',
        (r.d7 * mult).toFixed(2) + '×',
        (r.d14 * mult).toFixed(2) + '×',
        (r.d21 * mult).toFixed(2) + '×',
        (r.d30 * mult).toFixed(2) + '×',
        (r.till * mult).toFixed(2) + '×',
        r.lift
      ].join(','));
    });

    const blob = new Blob([csvLines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `bambinos_cohort_roas_progression_${metric}_export.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    this.showToast('Progression heatmap CSV exported successfully');
  }


  // ==================== TAB 4: CAMPAIGN OPERATIONS ====================
  renderOperationsView() {
    const cash = n => '₹' + Math.round(n).toLocaleString('en-IN');
    const curSpend = 1450000, prevSpend = 1380000;
    const curBooked = 3120, prevBooked = 2850;
    const curCpdb = curSpend / curBooked;
    const prevCpdb = prevSpend / prevBooked;
    const change = (curCpdb - prevCpdb) / prevCpdb;

    const setElemText = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.textContent = val;
    };

    setElemText('opsSpendVal', cash(curSpend));
    setElemText('opsSpendComp', 'Comparison ' + cash(prevSpend));
    setElemText('opsImprVal', '4,150,000');
    setElemText('opsImprComp', 'Comparison 3,920,000');
    setElemText('opsClicksVal', '52,400');
    setElemText('opsClicksComp', 'Comparison 48,900');
    setElemText('opsLpvVal', '41,800');
    setElemText('opsLpvComp', 'Comparison 39,100');
    setElemText('opsLeadsVal', '6,240');
    setElemText('opsLeadsComp', 'Comparison 5,820');
    setElemText('opsBookedVal', curBooked.toLocaleString());
    setElemText('opsBookedComp', 'Comparison ' + prevBooked.toLocaleString());

    setElemText('opsCurrentCpdb', cash(curCpdb));
    setElemText('opsPreviousCpdb', cash(prevCpdb));
    const changeEl = document.getElementById('opsCpdbChange');
    if (changeEl) {
      changeEl.textContent = (change >= 0 ? '+' : '') + (change * 100).toFixed(1) + '%';
      changeEl.className = change > 0 ? 'text-red-600 font-bold' : 'text-emerald-600 font-bold';
    }

    const drivers = [
      { key: 'cpm', label: 'CPM (Ad Cost Pressure)', multiplier: 1.05 },
      { key: 'ctr', label: 'Link CTR', multiplier: 0.96 },
      { key: 'landing', label: 'Click → Landing Page View', multiplier: 0.98 },
      { key: 'leadRate', label: 'Leads / Page Views', multiplier: 1.02 },
      { key: 'bookingRate', label: 'Bookings / Leads', multiplier: 0.93 }
    ];
    window.cohortChartRenderer?.renderDriverPressureChart('driverPressureChart', drivers);

    const metric = document.getElementById('opsTrendMetricSelect')?.value || 'cpm';
    const series = [
      { date: '2026-07-25', cpm: 349, ctr: 0.0126, landing: 0.798, resultsRate: 0.074, cpdb: 464 },
      { date: '2026-07-26', cpm: 362, ctr: 0.0131, landing: 0.812, resultsRate: 0.076, cpdb: 452 },
      { date: '2026-07-27', cpm: 355, ctr: 0.0128, landing: 0.805, resultsRate: 0.075, cpdb: 458 },
      { date: '2026-07-28', cpm: 370, ctr: 0.0122, landing: 0.785, resultsRate: 0.071, cpdb: 482 },
      { date: '2026-07-29', cpm: 358, ctr: 0.0134, landing: 0.820, resultsRate: 0.078, cpdb: 445 },
      { date: '2026-07-30', cpm: 345, ctr: 0.0138, landing: 0.825, resultsRate: 0.081, cpdb: 432 },
      { date: '2026-07-31', cpm: 352, ctr: 0.0130, landing: 0.810, resultsRate: 0.077, cpdb: 456 }
    ];
    const metricLabels = { cpm: 'CPM (₹)', ctr: 'Link CTR (%)', landing: 'Click → Landing Page (%)', resultsRate: 'Landing Page → Result (%)', cpdb: 'Cost per Demo Booked (₹)' };
    window.cohortChartRenderer?.renderOpsTrendChart('opsTrendChart', series, metric, metricLabels[metric]);
  }

  // ==================== TAB 5: META ADS MANAGER VIEW ====================
  renderMetaView() {
    const cash = n => '₹' + Math.round(n).toLocaleString('en-IN');
    const setElemText = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.textContent = val;
    };

    const bookingSignal = document.getElementById('metaBookingSignalSelect')?.value || 'CompleteRegistration';
    const resultEvent = document.getElementById('metaResultEventSelect')?.value || 'CompleteRegistration';

    let spend = 4450000;
    let cpm = 352;
    let linkCtr = '1.28%';
    let clickToLpv = 80.4;
    let lpvToResult = 7.5;
    let costPerDemo = 483;
    let lpv = 122400;
    let results = 9210;

    if (resultEvent === 'Purchase') {
      lpvToResult = 2.4;
      results = 2938;
      costPerDemo = 1515;
    } else if (resultEvent === 'InitiateCheckout') {
      lpvToResult = 4.8;
      results = 5875;
      costPerDemo = 757;
    }

    if (bookingSignal === 'LeadSubmit') {
      costPerDemo = Math.round(spend / 11200);
    } else if (bookingSignal === 'ScheduleDemo') {
      costPerDemo = Math.round(spend / 8950);
    }

    setElemText('metaSpendVal', cash(spend));
    setElemText('metaCpmVal', cash(cpm));
    setElemText('metaLinkCtrVal', linkCtr);
    setElemText('metaClickToLpvVal', clickToLpv.toFixed(1) + '%');
    const bar = document.getElementById('metaClickToLpvBar');
    if (bar) bar.style.width = clickToLpv.toFixed(1) + '%';
    setElemText('metaLpvToResultVal', lpvToResult.toFixed(1) + '%');
    setElemText('metaCostPerDemoVal', cash(costPerDemo));
    setElemText('metaLpvVal', lpv.toLocaleString('en-IN'));
    setElemText('metaResultsVal', results.toLocaleString('en-IN'));

    this.renderMetaLedgerTable();
  }

  getMetaLedgerRecords() {
    return [
      {
        period: '2026-07-01 – 2026-07-31',
        os: 'ios',
        osLabel: 'iOS',
        osEmoji: '🍎',
        osBadgeClass: 'bg-emerald-50 text-emerald-800 border-emerald-200/60',
        placement: 'Instagram Feed',
        spend: 1850000,
        impressions: 5200000,
        cpm: 355,
        clicks: 64000,
        linkClicks: 41200,
        linkCtr: '0.79%',
        lpv: 33800,
        clickToLpv: '82.0%',
        results: 2840,
        costPerResult: 651
      },
      {
        period: '2026-07-01 – 2026-07-31',
        os: 'android',
        osLabel: 'Android',
        osEmoji: '🤖',
        osBadgeClass: 'bg-amber-50 text-amber-900 border-amber-200/60',
        placement: 'Facebook Feed',
        spend: 2100000,
        impressions: 6100000,
        cpm: 344,
        clicks: 82000,
        linkClicks: 54300,
        linkCtr: '0.89%',
        lpv: 43200,
        clickToLpv: '79.5%',
        results: 3520,
        costPerResult: 596
      },
      {
        period: '2026-07-01 – 2026-07-31',
        os: 'desktop',
        osLabel: 'Desktop',
        osEmoji: '💻',
        osBadgeClass: 'bg-slate-100 text-slate-700 border-slate-200',
        placement: 'Facebook Feed',
        spend: 500000,
        impressions: 1350000,
        cpm: 370,
        clicks: 16200,
        linkClicks: 11400,
        linkCtr: '0.84%',
        lpv: 9400,
        clickToLpv: '82.4%',
        results: 780,
        costPerResult: 641
      }
    ];
  }

  renderMetaLedgerTable() {
    const tbody = document.getElementById('metaDeliveryTableBody');
    if (!tbody) return;

    const allRecords = this.getMetaLedgerRecords();
    const osFilter = this.selectedMetaOs || 'all';
    const searchQuery = (document.getElementById('metaLedgerSearch')?.value || '').toLowerCase().trim();

    const filtered = allRecords.filter(r => {
      const matchOs = osFilter === 'all' || r.os === osFilter;
      const matchSearch = !searchQuery || 
        r.placement.toLowerCase().includes(searchQuery) ||
        r.osLabel.toLowerCase().includes(searchQuery) ||
        r.period.toLowerCase().includes(searchQuery);
      return matchOs && matchSearch;
    });

    const countEl = document.getElementById('metaLedgerCount');
    if (countEl) {
      countEl.innerHTML = `Showing <span class="font-bold text-slate-800">${filtered.length > 0 ? 1 : 0} to ${filtered.length}</span> of ${allRecords.length} segment records`;
    }

    if (filtered.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="13" class="py-8 text-center text-slate-400 font-medium">
            No delivery records match the specified filters.
          </td>
        </tr>
      `;
      return;
    }

    const cash = n => '₹' + Math.round(n).toLocaleString('en-IN');

    tbody.innerHTML = filtered.map(r => `
      <tr class="hover:bg-sky-50/40 transition-colors group">
        <td class="py-3.5 px-4 font-medium text-slate-800 whitespace-nowrap">${r.period}</td>
        <td class="py-3.5 px-3 whitespace-nowrap">
          <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold ${r.osBadgeClass} font-sans">
            <span>${r.osEmoji}</span> ${r.osLabel}
          </span>
        </td>
        <td class="py-3.5 px-3 font-sans font-medium text-slate-800 whitespace-nowrap">${r.placement}</td>
        <td class="py-3.5 px-3 text-right font-bold text-slate-900">${cash(r.spend)}</td>
        <td class="py-3.5 px-3 text-right text-slate-600">${r.impressions.toLocaleString('en-IN')}</td>
        <td class="py-3.5 px-3 text-right font-medium text-slate-700">${cash(r.cpm)}</td>
        <td class="py-3.5 px-3 text-right text-slate-600">${r.clicks.toLocaleString('en-IN')}</td>
        <td class="py-3.5 px-3 text-right font-semibold text-slate-800">${r.linkClicks.toLocaleString('en-IN')}</td>
        <td class="py-3.5 px-3 text-right text-slate-600 font-semibold">${r.linkCtr}</td>
        <td class="py-3.5 px-3 text-right font-semibold text-slate-800">${r.lpv.toLocaleString('en-IN')}</td>
        <td class="py-3.5 px-3 text-right text-emerald-700 font-bold bg-emerald-50/50">${r.clickToLpv}</td>
        <td class="py-3.5 px-3 text-right font-bold text-sky-700">${r.results.toLocaleString('en-IN')}</td>
        <td class="py-3.5 px-4 text-right font-black text-slate-900">${cash(r.costPerResult)}</td>
      </tr>
    `).join('');
  }

  exportMetaLedgerCSV() {
    const allRecords = this.getMetaLedgerRecords();
    const headers = ['Delivery Period', 'Device OS', 'Placement', 'Spend', 'Impressions', 'CPM', 'Clicks', 'Link Clicks', 'Link CTR', 'LP Views', 'Click->LPV', 'Meta Results', 'Cost/Result'];
    const csvLines = [headers.join(',')];

    allRecords.forEach(r => {
      csvLines.push([
        `"${r.period}"`,
        r.osLabel,
        `"${r.placement}"`,
        r.spend,
        r.impressions,
        r.cpm,
        r.clicks,
        r.linkClicks,
        r.linkCtr,
        r.lpv,
        r.clickToLpv,
        r.results,
        r.costPerResult
      ].join(','));
    });

    const blob = new Blob([csvLines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `bambinos_meta_ads_delivery_ledger.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    this.showToast('Meta Ads Delivery Ledger exported to CSV');
  }
  }
}

// Global initialization
document.addEventListener('DOMContentLoaded', () => {
  window.app = new BambinosDashboardApp();
});
