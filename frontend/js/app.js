/**
 * Main Application Controller for Cohort Marketing Performance Dashboard
 * Handles Master Cohort Table, Slicers, Filtering, Sorting, Pagination & SQL Query Studio
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

    this.tableState = {
      sortKey: null,
      sortAsc: false,
      searchFilter: "",
      page: 1,
      pageSize: 25
    };

    this.currentTableData = null;

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
      this.isDatabaseLive = !!data.database_connected;
      const badge = document.getElementById("dbStatusBadge");
      if (badge) {
        if (this.isDatabaseLive) {
          badge.className = "badge live";
          badge.innerHTML = `<span class="badge-dot"></span> MariaDB Live`;
        } else {
          badge.className = "badge mock";
          badge.innerHTML = `<span class="badge-dot"></span> Analytical Engine (DB Disconnected)`;
        }
      }
    } catch (e) {
      console.warn("Health check error:", e);
    }
  }

  updateTimestamp(customTime = null) {
    const lastUpd = document.getElementById("lastUpd");
    if (!lastUpd) return;
    if (customTime) {
      lastUpd.innerText = customTime.replace("T", " ");
      return;
    }
    const d = new Date();
    const pad = (n) => String(n).padStart(2, '0');
    const ts = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
    lastUpd.innerText = ts;
  }

  async fetchMetadata() {
    try {
      const res = await (window.authFetch || fetch)("/api/v1/metadata");
      this.metadata = await res.json();
      
      this.state.channels = [...this.metadata.channels];
      this.state.platforms = [...this.metadata.platforms];
      this.state.countries = [...this.metadata.countries];
      this.state.courses = [...this.metadata.courses];
      
      if (this.metadata && this.metadata.meta && this.metadata.meta.lastUpdated) {
        this.updateTimestamp(this.metadata.meta.lastUpdated);
      } else {
        this.updateTimestamp();
      }
    } catch (e) {
      console.error("Error fetching metadata:", e);
      this.updateTimestamp();
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
        } else if (targetView === "viewFunnels") {
          this.refreshKPIs();
          this.refreshMaturity();
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
        btn.addEventListener("click", () => {
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
          this.refreshDashboard();
        });
      });
    }

    // Date inputs
    const dateFromInp = document.getElementById("inputDateFrom");
    const dateToInp = document.getElementById("inputDateTo");
    if (dateFromInp) {
      dateFromInp.value = this.state.date_from;
      dateFromInp.addEventListener("change", (e) => {
        this.state.date_from = e.target.value;
        if (dateToInp && this.state.date_from > this.state.date_to) {
          this.state.date_to = this.state.date_from;
          dateToInp.value = this.state.date_to;
        }
        this.refreshDashboard();
      });
    }
    if (dateToInp) {
      dateToInp.value = this.state.date_to;
      dateToInp.addEventListener("change", (e) => {
        this.state.date_to = e.target.value;
        if (dateFromInp && this.state.date_to < this.state.date_from) {
          this.state.date_from = this.state.date_to;
          dateFromInp.value = this.state.date_from;
        }
        this.refreshDashboard();
      });
    }

    // Table Search
    const tblSearchInp = document.getElementById("tableSearchInput");
    if (tblSearchInp) {
      tblSearchInp.addEventListener("input", (e) => {
        this.tableState.searchFilter = e.target.value.toLowerCase().trim();
        this.tableState.page = 1;
        this.renderTableContent();
      });
    }

    // Force Refresh Live DB
    const refreshBtn = document.getElementById("refreshDataBtn");
    if (refreshBtn) {
      refreshBtn.addEventListener("click", async () => {
        const icon = document.getElementById("refreshIcon");
        if (icon) {
          icon.style.transition = "transform 0.8s ease";
          icon.style.transform = "rotate(360deg)";
        }
        refreshBtn.disabled = true;
        refreshBtn.style.opacity = "0.6";
        this.state.force_refresh = true;
        
        await this.fetchMetadata();
        await this.checkHealth();
        await this.refreshDashboard();
        
        this.state.force_refresh = false;
        refreshBtn.disabled = false;
        refreshBtn.style.opacity = "1";
        if (icon) {
          setTimeout(() => { icon.style.transform = "none"; }, 800);
        }
      });
    }

    // Reset All Filters
    const resetBtn = document.getElementById("resetAll");
    if (resetBtn) {
      resetBtn.addEventListener("click", () => {
        this.state.date_from = "2026-07-01";
        this.state.date_to = "2026-07-31";
        if (dateFromInp) dateFromInp.value = this.state.date_from;
        if (dateToInp) dateToInp.value = this.state.date_to;
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
      this.state[stateKey] = ["__EMPTY__"];
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
    this.updateTimestamp();
    this.showLoadingSkeletons();
    await Promise.all([
      this.refreshMaturity(),
      this.refreshMasterTable().then(() => this.refreshKPIs())
    ]);
  }

  showLoadingSkeletons() {
    const kpiContainer = document.getElementById("kpis");
    if (kpiContainer) {
      const labels = [
        "Spend", "Contacts Registered", "Cost Per Lead (CPL)", "Demos Attended",
        "Attendance Rate", "Conversions", "Conversion Rate", "New Revenue",
        "ARPU (Paying)", "New Rev ROAS"
      ];
      kpiContainer.innerHTML = labels.map(l => `
        <div class="kpi skeleton">
          <div class="k">${l}</div>
          <div class="v">···</div>
          <div class="d">Querying MariaDB database...</div>
        </div>
      `).join("");
    }

    const tbody = document.querySelector("#tbl tbody");
    if (tbody) {
      tbody.innerHTML = `
        <tr>
          <td colspan="15">
            <div class="tbl-spinner">
              <div class="spinner-icon"></div>
              <span>Executing master cohort query against live database...</span>
            </div>
          </td>
        </tr>
      `;
    }
  }

  getEffectivePayload() {
    const payload = { ...this.state };
    
    // Check dropdowns: if "All" are selected (length matches metadata options or empty), set to [] so backend doesn't filter out unlisted countries/channels
    const checkAll = (key, metaKey) => {
      const opts = this.metadata ? this.metadata[metaKey] : [];
      const sel = payload[key] || [];
      if (!opts || sel.length === 0 || (Array.isArray(opts) && sel.length >= opts.length)) {
        payload[key] = [];
      }
    };
    
    checkAll("channels", "channels");
    checkAll("platforms", "platforms");
    checkAll("countries", "countries");
    checkAll("courses", "courses");
    
    return payload;
  }

  async refreshMaturity() {
    try {
      const res = await (window.authFetch || fetch)("/api/v1/cohorts/maturity", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(this.getEffectivePayload())
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
          <div class="cell ${d.status === 'counted' ? 'inc' : 'exc'}" title="${d.date}: ${d.status}"></div>
        `).join("");

        const stripAxisEl = document.getElementById("stripAxis");
        if (stripAxisEl && data.days.length > 0) {
          const first = data.days[0].date;
          const midIdx = Math.floor(data.days.length / 2);
          const mid = data.days[midIdx].date;
          const last = data.days[data.days.length - 1].date;
          stripAxisEl.innerHTML = `
            <span>Day 1 (${first.slice(5)})</span>
            <span>Day ${midIdx + 1} (${mid.slice(5)})</span>
            <span>Day ${data.days.length} (${last.slice(5)})</span>
          `;
        }

        // Render progression curve chart
        if (window.chartRenderer) {
          window.chartRenderer.renderProgressionCurve("cohortProgressionChart", data.days);
        }
      }
    } catch (e) {
      console.error("Error refreshing maturity:", e);
    }
  }

  async refreshKPIs() {
    try {
      const res = await (window.authFetch || fetch)("/api/v1/kpis", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(this.getEffectivePayload())
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

      // Render funnel chart
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
    const t0 = performance.now();
    try {
      const res = await (window.authFetch || fetch)("/api/v1/cohorts/master", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(this.getEffectivePayload())
      });
      const t1 = performance.now();
      const durationMs = Math.round(t1 - t0);

      this.currentTableData = await res.json();
      this.tableState.page = 1;
      this.renderTableContent();

      const cacheBadge = document.getElementById("cacheBadge");
      if (cacheBadge) {
        if (!this.isDatabaseLive) {
          cacheBadge.style.background = "rgba(245,158,11,0.15)";
          cacheBadge.style.color = "var(--warn)";
          cacheBadge.innerText = `🟡 Analytical Simulator (${durationMs}ms)`;
        } else if (durationMs < 50 && !this.state.force_refresh) {
          cacheBadge.style.background = "rgba(99,102,241,0.12)";
          cacheBadge.style.color = "var(--brand)";
          cacheBadge.innerText = `⚡ Cached (${durationMs}ms)`;
        } else {
          cacheBadge.style.background = "rgba(16,185,129,0.12)";
          cacheBadge.style.color = "var(--teal)";
          cacheBadge.innerText = `🟢 Live MariaDB (${durationMs}ms)`;
        }
      }
    } catch (e) {
      console.error("Error refreshing master table:", e);
    }
  }

  renderTableContent() {
    const data = this.currentTableData;
    if (!data) return;

    const tbl = document.getElementById("tbl");
    const rowCountEl = document.getElementById("rowCount");
    const blankEl = document.getElementById("blank");

    if (!tbl) return;

    // Filter rows by table search
    let filteredRows = (data.rows || []).filter(r => {
      if (!this.tableState.searchFilter) return true;
      const dimStr = Object.values(r.dimensions || {}).join(" ").toLowerCase();
      return dimStr.includes(this.tableState.searchFilter);
    });

    // Sort rows if sortKey is set
    if (this.tableState.sortKey) {
      const key = this.tableState.sortKey;
      const asc = this.tableState.sortAsc;
      filteredRows.sort((a, b) => {
        let valA = a.dimensions && a.dimensions[key] !== undefined ? a.dimensions[key] : a[key];
        let valB = b.dimensions && b.dimensions[key] !== undefined ? b.dimensions[key] : b[key];
        if (typeof valA === "number" && typeof valB === "number") {
          return asc ? valA - valB : valB - valA;
        }
        return asc ? String(valA).localeCompare(String(valB)) : String(valB).localeCompare(String(valA));
      });
    }

    if (rowCountEl) rowCountEl.innerText = `${filteredRows.length} rows`;

    if (filteredRows.length === 0) {
      tbl.style.display = "none";
      if (blankEl) {
        blankEl.style.display = "block";
        blankEl.innerHTML = `
          <div style="padding:20px;text-align:center;">
            <div style="font-size:24px;margin-bottom:8px;">🔍</div>
            <div style="font-weight:600;color:var(--ink);margin-bottom:4px;">No records found for ${this.state.date_from} → ${this.state.date_to}</div>
            <div style="font-size:12px;color:var(--ink3);margin-bottom:14px;">Try expanding your date range or adjusting the active filters.</div>
          </div>
        `;
      }
      this.renderPagination(0);
      return;
    }

    tbl.style.display = "table";
    if (blankEl) blankEl.style.display = "none";

    // Paginate
    const startIdx = (this.tableState.page - 1) * this.tableState.pageSize;
    const pagedRows = filteredRows.slice(startIdx, startIdx + this.tableState.pageSize);

    // 1. Table Header
    const thead = tbl.querySelector("thead");
    thead.innerHTML = `
      <tr>
        ${data.headers.map((h, i) => {
          const isSorted = this.tableState.sortKey === h.key;
          const sortIcon = isSorted ? (this.tableState.sortAsc ? "▲" : "▼") : "";
          const isStick = i === 0;
          return `
            <th class="${isStick ? 'stick dim' : 'dim'} ${isSorted ? 'sorted' : ''}" onclick="cohortApp.handleTableSort('${h.key}')">
              ${h.label} <span class="sort-icon">${sortIcon}</span>
            </th>
          `;
        }).join("")}
      </tr>
    `;

    // 2. Table Body
    const tbody = tbl.querySelector("tbody");
    tbody.innerHTML = pagedRows.map(r => {
      let rowCells = "";
      data.headers.forEach((h, i) => {
        const isDim = ["date", "campaign", "adset", "ad", "channel", "platform", "country", "course"].includes(h.key);
        if (isDim) {
          const val = (r.dimensions && (r.dimensions[h.key] || r.dimensions[h.key + "_name"])) || "-";
          if (["campaign", "adset", "ad"].includes(h.key) && val && val !== "All" && val !== "NA" && val !== "Not Available" && val !== "-") {
            const extraId = (h.key === "campaign" && r.dimensions && r.dimensions.campaign_id) ? ` <span style="font-size:10px;color:var(--ink4);font-family:var(--mono);">(${r.dimensions.campaign_id})</span>` : "";
            rowCells += `<td class="${i === 0 ? 'stick dim' : 'dim'}"><button class="tbl-link-btn" onclick="cohortApp.filterByDimension('${h.key}', '${encodeURIComponent(val)}')" title="Click to filter by ${val}">${val}</button>${extraId}</td>`;
          } else {
            rowCells += `<td class="${i === 0 ? 'stick dim' : 'dim'}">${val}</td>`;
          }
        } else {
          // Metric Column
          if (h.key === "spend") {
            rowCells += `<td class="num">₹${(r.spend || 0).toLocaleString()}</td>`;
          } else if (h.key === "impressions") {
            rowCells += `<td class="num">${(r.impressions || 0).toLocaleString()}</td>`;
          } else if (h.key === "clicks") {
            rowCells += `<td class="num">${(r.clicks || 0).toLocaleString()}</td>`;
          } else if (h.key === "contacts_registered") {
            rowCells += `<td class="num"><b>${(r.contacts_registered || 0).toLocaleString()}</b></td>`;
          } else if (h.key === "cpl") {
            rowCells += `<td class="num">₹${(r.cpl || 0).toFixed(2)}</td>`;
          } else if (h.key === "demos_booked") {
            rowCells += `<td class="num">${(r.demos_booked || 0).toLocaleString()}</td>`;
          } else if (h.key === "demos_attended") {
            rowCells += `<td class="num">${(r.demos_attended || 0).toLocaleString()}</td>`;
          } else if (h.key === "attendance_pct") {
            rowCells += `<td class="num" style="background:${r.attendance_pct > 30 ? 'var(--teal-soft)' : ''}"><b>${(r.attendance_pct || 0).toFixed(1)}%</b></td>`;
          } else if (h.key === "conversions") {
            rowCells += `<td class="num">${(r.conversions || 0).toLocaleString()}</td>`;
          } else if (h.key === "conversion_pct") {
            rowCells += `<td class="num" style="background:${r.conversion_pct > 3 ? 'var(--teal-soft)' : ''}"><b>${(r.conversion_pct || 0).toFixed(2)}%</b></td>`;
          } else if (h.key === "new_revenue") {
            rowCells += `<td class="num" style="color:var(--petrol);font-weight:700;">₹${(r.new_revenue || 0).toLocaleString()}</td>`;
          } else if (h.key === "arpu") {
            rowCells += `<td class="num">₹${(r.arpu || 0).toLocaleString()}</td>`;
          } else if (h.key === "roas") {
            rowCells += `<td class="num" style="font-weight:700;">${(r.roas || 0).toFixed(2)}x</td>`;
          } else {
            rowCells += `<td class="num">${r[h.key] !== undefined ? r[h.key] : '-'}</td>`;
          }
        }
      });

      return `<tr>${rowCells}</tr>`;
    }).join("");

    // 3. Table Footer (Totals row)
    const tfoot = tbl.querySelector("tfoot");
    const tot = data.totals || {};
    let footCells = "";
    let isFirstDim = true;

    data.headers.forEach((h, i) => {
      const isDim = ["date", "campaign", "adset", "ad", "channel", "platform", "country", "course"].includes(h.key);
      if (isDim) {
        footCells += `<td class="${i === 0 ? 'stick dim' : 'dim'}">${isFirstDim ? 'TOTAL' : ''}</td>`;
        isFirstDim = false;
      } else {
        if (h.key === "spend") {
          footCells += `<td class="num">₹${(tot.spend || 0).toLocaleString()}</td>`;
        } else if (h.key === "impressions") {
          footCells += `<td class="num">${(tot.impressions || 0).toLocaleString()}</td>`;
        } else if (h.key === "clicks") {
          footCells += `<td class="num">${(tot.clicks || 0).toLocaleString()}</td>`;
        } else if (h.key === "contacts_registered") {
          footCells += `<td class="num">${(tot.contacts_registered || 0).toLocaleString()}</td>`;
        } else if (h.key === "cpl") {
          footCells += `<td class="num">₹${(tot.cpl || 0).toFixed(2)}</td>`;
        } else if (h.key === "demos_booked") {
          footCells += `<td class="num">${(tot.demos_booked || 0).toLocaleString()}</td>`;
        } else if (h.key === "demos_attended") {
          footCells += `<td class="num">${(tot.demos_attended || 0).toLocaleString()}</td>`;
        } else if (h.key === "attendance_pct") {
          footCells += `<td class="num">${(tot.attendance_pct || 0).toFixed(1)}%</td>`;
        } else if (h.key === "conversions") {
          footCells += `<td class="num">${(tot.conversions || 0).toLocaleString()}</td>`;
        } else if (h.key === "conversion_pct") {
          footCells += `<td class="num">${(tot.conversion_pct || 0).toFixed(2)}%</td>`;
        } else if (h.key === "new_revenue") {
          footCells += `<td class="num">₹${(tot.new_revenue || 0).toLocaleString()}</td>`;
        } else if (h.key === "arpu") {
          footCells += `<td class="num">₹${(tot.arpu || 0).toLocaleString()}</td>`;
        } else if (h.key === "roas") {
          footCells += `<td class="num">${(tot.roas || 0).toFixed(2)}x</td>`;
        } else {
          footCells += `<td class="num">-</td>`;
        }
      }
    });

    tfoot.innerHTML = `<tr>${footCells}</tr>`;

    this.renderPagination(filteredRows.length);
  }

  handleTableSort(key) {
    if (this.tableState.sortKey === key) {
      this.tableState.sortAsc = !this.tableState.sortAsc;
    } else {
      this.tableState.sortKey = key;
      this.tableState.sortAsc = false;
    }
    this.renderTableContent();
  }

  renderPagination(totalRows) {
    const pagEl = document.getElementById("tablePagination");
    if (!pagEl) return;

    const totalPages = Math.ceil(totalRows / this.tableState.pageSize) || 1;
    pagEl.innerHTML = `
      <span>Showing <b>${Math.min((this.tableState.page - 1) * this.tableState.pageSize + 1, totalRows)}</b> - <b>${Math.min(this.tableState.page * this.tableState.pageSize, totalRows)}</b> of <b>${totalRows}</b></span>
      <div style="display:flex;gap:6px;align-items:center;">
        <button class="mini" ${this.tableState.page <= 1 ? 'disabled' : ''} onclick="cohortApp.setPage(${this.tableState.page - 1})">Prev</button>
        <span>Page ${this.tableState.page} / ${totalPages}</span>
        <button class="mini" ${this.tableState.page >= totalPages ? 'disabled' : ''} onclick="cohortApp.setPage(${this.tableState.page + 1})">Next</button>
      </div>
    `;
  }

  setPage(p) {
    this.tableState.page = p;
    this.renderTableContent();
  }

  async loadDeviceDiagnostics() {
    try {
      const res = await (window.authFetch || fetch)("/api/v1/devices/comparison");
      const data = await res.json();
      if (window.chartRenderer) {
        window.chartRenderer.renderDeviceComparison("deviceComparisonContainer", data);
      }
    } catch (e) {
      console.error("Error loading device diagnostics:", e);
    }
  }

  resetToJulyRange() {
    this.state.date_from = "2026-07-01";
    this.state.date_to = "2026-07-31";
    const dateFromInp = document.getElementById("inputDateFrom");
    const dateToInp = document.getElementById("inputDateTo");
    if (dateFromInp) dateFromInp.value = this.state.date_from;
    if (dateToInp) dateToInp.value = this.state.date_to;
    this.refreshDashboard();
  }

  filterByDimension(dimKey, encodedVal) {
    const val = decodeURIComponent(encodedVal);
    const keyMap = {
      campaign: "campaign_names",
      adset: "adset_names",
      ad: "ad_names"
    };
    const stateKey = keyMap[dimKey];
    if (!stateKey) return;

    if (this.state[stateKey] && this.state[stateKey].includes(val)) {
      this.state[stateKey] = [];
    } else {
      this.state[stateKey] = [val];
    }
    this.refreshDashboard();
  }

  filterByCampaign(encodedCampName) {
    this.filterByDimension("campaign", encodedCampName);
  }

  filterByAdset(encodedAdsetName) {
    this.filterByDimension("adset", encodedAdsetName);
  }

  filterByAd(encodedAdName) {
    this.filterByDimension("ad", encodedAdName);
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

// Global click listener to close dropdown popups
document.addEventListener("click", () => {
  document.querySelectorAll(".dd").forEach(d => d.classList.remove("open"));
});

// App lifecycle & Authentication bindings
window.addEventListener("DOMContentLoaded", async () => {
  // Setup login form submission
  const loginForm = document.getElementById("loginForm");
  if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const u = document.getElementById("loginUsername").value.trim();
      const p = document.getElementById("loginPassword").value;
      if (u && p) {
        await Auth.login(u, p);
      }
    });
  }

  // Setup password show/hide toggle
  const btnTogglePw = document.getElementById("btnTogglePassword");
  if (btnTogglePw) {
    btnTogglePw.addEventListener("click", () => {
      const pwInput = document.getElementById("loginPassword");
      if (pwInput) {
        const isPw = pwInput.type === "password";
        pwInput.type = isPw ? "text" : "password";
        btnTogglePw.innerHTML = isPw
          ? `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>`
          : `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>`;
      }
    });
  }

  // Setup logout button
  const btnLogout = document.getElementById("btnLogout");
  if (btnLogout) {
    btnLogout.addEventListener("click", async () => {
      if (confirm("Are you sure you want to sign out of the Marketing Suite?")) {
        await Auth.logout();
      }
    });
  }

  // Verify session and load app
  const isAuth = await Auth.verifyToken();
  if (isAuth) {
    window.cohortApp = new CohortApp();
  }
});

