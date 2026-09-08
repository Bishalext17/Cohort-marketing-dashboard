/**
 * Main Application Controller for Cohort Marketing Performance Dashboard
 */

class CohortApp {
  constructor() {
    this.metadata = null;
    this.state = {
      cohort_period: "Till date",
      date_from: "2026-07-01",
      date_to: "2026-07-31",
      channels: [],
      platforms: [],
      countries: [],
      courses: [],
      campaign_names: [],
      campaign_ids: [],
      adset_names: [],
      adset_ids: [],
      ad_names: [],
      ad_ids: [],
      slicers: ["date"]
    };
    
    this.init();
  }

  async init() {
    await this.fetchMetadata();
    this.setupNavigation();
    this.renderControls();
    await this.refreshDashboard();
    this.checkHealth();
  }

  async checkHealth() {
    try {
      const res = await fetch("/health");
      const data = await res.json();
      const badge = document.getElementById("dbStatusBadge");
      if (badge) {
        if (data.database_connected) {
          badge.className = "badge live";
          badge.innerHTML = `<span class="badge-dot"></span> MariaDB Live`;
        } else {
          badge.className = "badge mock";
          badge.innerHTML = `<span class="badge-dot"></span> Analytical Engine Active`;
        }
      }
    } catch (e) {
      console.warn("Health check error:", e);
    }
  }

  async fetchMetadata() {
    try {
      const res = await fetch("/api/v1/metadata");
      this.metadata = await res.json();
      
      // Initialize filters as fully selected by default
      this.state.channels = [...this.metadata.channels];
      this.state.platforms = [...this.metadata.platforms];
      this.state.countries = [...this.metadata.countries];
      this.state.courses = [...this.metadata.courses];
      
      const lastUpd = document.getElementById("lastUpd");
      if (lastUpd && this.metadata.meta) {
        lastUpd.innerText = this.metadata.meta.lastUpdated.replace("T", " ");
      }
    } catch (e) {
      console.error("Error fetching metadata:", e);
    }
  }

  setupNavigation() {
    document.querySelectorAll(".nav-tab").forEach(tab => {
      tab.addEventListener("click", () => {
        document.querySelectorAll(".nav-tab").forEach(t => t.classList.remove("active"));
        tab.classList.add("active");
        
        const targetView = tab.dataset.view;
        document.querySelectorAll(".view-section").forEach(sec => {
          sec.style.display = (sec.id === targetView) ? "block" : "none";
        });

        if (targetView === "viewFollowups") {
          window.followUpManager.loadContacts("all");
        } else if (targetView === "viewDiagnostics") {
          this.loadDeviceDiagnostics();
        }
      });
    });
  }

  renderControls() {
    if (!this.metadata) return;

    // 1. Cohort Segments
    const segContainer = document.getElementById("segCohort");
    if (segContainer) {
      segContainer.innerHTML = this.metadata.cohort_options.map(opt => `
        <button class="${opt === this.state.cohort_period ? 'sel' : ''}" data-val="${opt}">
          ${opt}
        </button>
      `).join("");

      segContainer.querySelectorAll("button").forEach(btn => {
        btn.addEventListener("click", (e) => {
          segContainer.querySelectorAll("button").forEach(b => b.classList.remove("sel"));
          btn.classList.add("sel");
          this.state.cohort_period = btn.dataset.val;
          this.refreshDashboard();
        });
      });
    }

    // 2. Multi-select Dropdowns
    this.createDropdown("ddChannel", "Channel", this.metadata.channels, "channels");
    this.createDropdown("ddPlatform", "Platform", this.metadata.platforms, "platforms");
    this.createDropdown("ddCountry", "Country", this.metadata.countries, "countries");
    this.createDropdown("ddCourse", "Course", this.metadata.courses, "courses");

    // Ad hierarchy dropdowns
    const campNames = [...new Set(this.metadata.campaigns.map(c => c.name))];
    const campIds = this.metadata.campaigns.map(c => c.id);
    const adsetNames = [...new Set(this.metadata.adsets.map(a => a.name))];
    const adsetIds = this.metadata.adsets.map(a => a.id);
    const adNames = [...new Set(this.metadata.ads.map(a => a.name))];
    const adIds = this.metadata.ads.map(a => a.id);

    this.createDropdown("ddCampName", "Campaign Name", campNames, "campaign_names");
    this.createDropdown("ddCampId", "Campaign ID", campIds, "campaign_ids");
    this.createDropdown("ddAdsetName", "Adset Name", adsetNames, "adset_names");
    this.createDropdown("ddAdsetId", "Adset ID", adsetIds, "adset_ids");
    this.createDropdown("ddAdName", "Ad Name", adNames, "ad_names");
    this.createDropdown("ddAdId", "Ad ID", adIds, "ad_ids");

    // 3. Slicers
    const slicerContainer = document.getElementById("slicers");
    if (slicerContainer) {
      slicerContainer.innerHTML = this.metadata.slicer_options.map(s => `
        <button class="chip ${this.state.slicers.includes(s.key) ? 'on' : ''}" data-slicer="${s.key}">
          ${s.label}
        </button>
      `).join("");

      slicerContainer.querySelectorAll("button").forEach(btn => {
        btn.addEventListener("click", () => {
          const key = btn.dataset.slicer;
          if (this.state.slicers.includes(key)) {
            this.state.slicers = this.state.slicers.filter(k => k !== key);
            btn.classList.remove("on");
          } else {
            this.state.slicers.push(key);
            btn.classList.add("on");
          }
          this.refreshMasterTable();
        });
      });
    }

    // Reset All Filters
    const resetBtn = document.getElementById("resetAll");
    if (resetBtn) {
      resetBtn.addEventListener("click", () => {
        this.state.channels = [...this.metadata.channels];
        this.state.platforms = [...this.metadata.platforms];
        this.state.countries = [...this.metadata.countries];
        this.state.courses = [...this.metadata.courses];
        this.state.campaign_names = [];
        this.state.campaign_ids = [];
        this.state.adset_names = [];
        this.state.adset_ids = [];
        this.state.ad_names = [];
        this.state.ad_ids = [];
        this.renderControls();
        this.refreshDashboard();
      });
    }

    // CSV Download
    const dlCsvBtn = document.getElementById("dlCsv");
    if (dlCsvBtn) {
      dlCsvBtn.addEventListener("click", () => this.downloadTableCSV());
    }
  }

  createDropdown(containerId, label, options, stateKey) {
    const el = document.getElementById(containerId);
    if (!el) return;

    let selected = this.state[stateKey] || [];
    let isAll = selected.length === options.length || selected.length === 0;
    let labelVal = isAll ? "All" : `${selected.length} selected`;

    el.className = "dd";
    el.innerHTML = `
      <button class="dd-btn ${selected.length === 0 && !isAll ? 'none' : (isAll ? '' : 'part')}" type="button">
        <span class="k">${label}</span>
        <span class="v">${labelVal}</span>
        <span class="caret">▼</span>
      </button>
      <div class="dd-pop">
        <div class="dd-tools">
          <button class="mini sel-all" type="button">Select all</button>
          <button class="mini clear-all" type="button">Clear</button>
        </div>
        <div class="dd-list">
          ${options.map(opt => `
            <label class="opt">
              <input type="checkbox" value="${opt}" ${isAll || selected.includes(opt) ? 'checked' : ''}>
              <span>${opt}</span>
            </label>
          `).join("")}
        </div>
      </div>
    `;

    const btn = el.querySelector(".dd-btn");
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      document.querySelectorAll(".dd").forEach(d => { if (d !== el) d.classList.remove("open"); });
      el.classList.toggle("open");
    });

    el.querySelector(".sel-all").addEventListener("click", () => {
      this.state[stateKey] = [...options];
      this.createDropdown(containerId, label, options, stateKey);
      this.refreshDashboard();
    });

    el.querySelector(".clear-all").addEventListener("click", () => {
      this.state[stateKey] = ["__EMPTY__"]; // Represents explicitly empty filter
      this.createDropdown(containerId, label, options, stateKey);
      this.refreshDashboard();
    });

    el.querySelectorAll(".dd-list input").forEach(inp => {
      inp.addEventListener("change", () => {
        const checked = Array.from(el.querySelectorAll(".dd-list input:checked")).map(i => i.value);
        this.state[stateKey] = checked;
        this.createDropdown(containerId, label, options, stateKey);
        this.refreshDashboard();
      });
    });
  }

  async refreshDashboard() {
    await Promise.all([
      this.refreshMaturity(),
      this.refreshKPIs(),
      this.refreshMasterTable()
    ]);
  }

  async refreshMaturity() {
    try {
      const res = await fetch("/api/v1/cohorts/maturity", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(this.state)
      });
      const data = await res.json();
      
      const stripEl = document.getElementById("strip");
      const noteEl = document.getElementById("matNote");
      const matHead = document.getElementById("matHead");

      if (matHead) matHead.innerText = `· ${data.counted_dates} counted, ${data.dropped_dates} dropped`;
      if (noteEl) {
        noteEl.className = `note ${data.dropped_dates === 0 ? 'clear' : ''}`;
        noteEl.innerHTML = `<b>Maturity Status:</b> ${data.note}`;
      }

      if (stripEl && data.days) {
        stripEl.innerHTML = data.days.map(d => `
          <div class="cell ${d.status === 'counted' ? 'inc' : 'exc'}" title="${d.date}: ${d.leads_captured} leads (${d.status})"></div>
        `).join("");
      }
    } catch (e) {
      console.error("Error refreshing maturity:", e);
    }
  }

  async refreshKPIs() {
    try {
      const res = await fetch("/api/v1/kpis", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(this.state)
      });
      const data = await res.json();
      
      const kpiContainer = document.getElementById("kpis");
      if (!kpiContainer) return;

      const tiles = [
        data.spend, data.leads, data.cpl, data.demos_attended,
        data.attendance_pct, data.conversions, data.conversion_pct,
        data.revenue, data.arpu, data.roas
      ];

      kpiContainer.innerHTML = tiles.map(t => `
        <div class="kpi">
          <div class="k">${t.label}</div>
          <div class="v">${t.value}</div>
          <div class="d">${t.description}</div>
        </div>
      `).join("");

      // Render chart funnel in overview
      if (window.chartRenderer) {
        window.chartRenderer.renderFunnel("overviewFunnelChart", {
          impressions: data.impressions.numeric_value,
          clicks: data.clicks.numeric_value,
          contacts_registered: data.leads.numeric_value,
          demos_booked: Math.round(data.leads.numeric_value * 0.6),
          demos_attended: data.demos_attended.numeric_value,
          conversions: data.conversions.numeric_value
        });
      }
    } catch (e) {
      console.error("Error refreshing KPIs:", e);
    }
  }

  async refreshMasterTable() {
    try {
      const res = await fetch("/api/v1/cohorts/master", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(this.state)
      });
      const data = await res.json();
      
      const tbl = document.getElementById("tbl");
      const rowCountEl = document.getElementById("rowCount");
      const blankEl = document.getElementById("blank");

      if (!tbl) return;
      if (rowCountEl) rowCountEl.innerText = `${data.row_count} rows`;

      if (data.row_count === 0) {
        tbl.style.display = "none";
        if (blankEl) {
          blankEl.style.display = "block";
          blankEl.innerText = "No data found matching the selected filter criteria.";
        }
        return;
      }

      tbl.style.display = "table";
      if (blankEl) blankEl.style.display = "none";

      // 1. Table Header
      const thead = tbl.querySelector("thead");
      thead.innerHTML = `
        <tr>
          ${data.headers.map((h, i) => `
            <th class="${i === 0 ? 'stick dim' : (h.key.includes('name') || h.key.includes('course') || h.key.includes('country') ? 'dim' : '')}">
              ${h.label}
            </th>
          `).join("")}
        </tr>
      `;

      // 2. Table Body
      const tbody = tbl.querySelector("tbody");
      tbody.innerHTML = data.rows.map(r => {
        let dimHtml = "";
        data.headers.forEach((h, i) => {
          if (r.dimensions && r.dimensions[h.key] !== undefined) {
            dimHtml += `<td class="${i === 0 ? 'stick dim' : 'dim'}">${r.dimensions[h.key]}</td>`;
          }
        });

        return `
          <tr>
            ${dimHtml}
            <td class="num">₹${r.spend.toLocaleString()}</td>
            <td class="num">${r.impressions.toLocaleString()}</td>
            <td class="num">${r.clicks.toLocaleString()}</td>
            <td class="num"><b>${r.contacts_registered.toLocaleString()}</b></td>
            <td class="num">₹${r.cpl.toFixed(2)}</td>
            <td class="num">${r.demos_booked.toLocaleString()}</td>
            <td class="num">${r.demos_attended.toLocaleString()}</td>
            <td class="num" style="background:${r.attendance_pct > 30 ? 'var(--teal-soft)' : ''}"><b>${r.attendance_pct.toFixed(1)}%</b></td>
            <td class="num">${r.conversions.toLocaleString()}</td>
            <td class="num" style="background:${r.conversion_pct > 3 ? 'var(--teal-soft)' : ''}"><b>${r.conversion_pct.toFixed(2)}%</b></td>
            <td class="num" style="color:var(--petrol);font-weight:700;">₹${r.new_revenue.toLocaleString()}</td>
            <td class="num">₹${r.arpu.toLocaleString()}</td>
            <td class="num" style="font-weight:700;">${r.roas.toFixed(2)}x</td>
          </tr>
        `;
      }).join("");

      // 3. Table Footer (Totals row)
      const tfoot = tbl.querySelector("tfoot");
      const tot = data.totals;
      let footDimCols = "";
      data.headers.forEach((h, i) => {
        if (h.key in (tot.dimensions || {}) || i < (this.state.slicers.length || 1)) {
          footDimCols += `<td class="${i === 0 ? 'stick dim' : 'dim'}">${i === 0 ? 'TOTAL' : ''}</td>`;
        }
      });

      tfoot.innerHTML = `
        <tr>
          ${footDimCols}
          <td class="num">₹${tot.spend.toLocaleString()}</td>
          <td class="num">${tot.impressions.toLocaleString()}</td>
          <td class="num">${tot.clicks.toLocaleString()}</td>
          <td class="num">${tot.contacts_registered.toLocaleString()}</td>
          <td class="num">₹${tot.cpl.toFixed(2)}</td>
          <td class="num">${tot.demos_booked.toLocaleString()}</td>
          <td class="num">${tot.demos_attended.toLocaleString()}</td>
          <td class="num">${tot.attendance_pct.toFixed(1)}%</td>
          <td class="num">${tot.conversions.toLocaleString()}</td>
          <td class="num">${tot.conversion_pct.toFixed(2)}%</td>
          <td class="num">₹${tot.new_revenue.toLocaleString()}</td>
          <td class="num">₹${tot.arpu.toLocaleString()}</td>
          <td class="num">${tot.roas.toFixed(2)}x</td>
        </tr>
      `;

      this.currentTableData = data;
    } catch (e) {
      console.error("Error refreshing master table:", e);
    }
  }

  async loadDeviceDiagnostics() {
    try {
      const res = await fetch("/api/v1/devices/comparison");
      const data = await res.json();
      if (window.chartRenderer) {
        window.chartRenderer.renderDeviceComparison("deviceComparisonContainer", data);
      }
    } catch (e) {
      console.error("Error loading device diagnostics:", e);
    }
  }

  downloadTableCSV() {
    if (!this.currentTableData || !this.currentTableData.rows) return;
    
    let csv = "";
    const headers = this.currentTableData.headers.map(h => `"${h.label}"`).join(",");
    csv += headers + "\n";

    this.currentTableData.rows.forEach(r => {
      let rowVals = [];
      this.currentTableData.headers.forEach(h => {
        if (r.dimensions && r.dimensions[h.key] !== undefined) {
          rowVals.push(`"${r.dimensions[h.key]}"`);
        } else if (r[h.key] !== undefined) {
          rowVals.push(r[h.key]);
        }
      });
      csv += rowVals.join(",") + "\n";
    });

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `cohort_master_${this.state.cohort_period}.csv`);
    link.click();
  }
}

// Global click listener to close popups
document.addEventListener("click", () => {
  document.querySelectorAll(".dd").forEach(d => d.classList.remove("open"));
});

window.addEventListener("DOMContentLoaded", () => {
  window.cohortApp = new CohortApp();
});
