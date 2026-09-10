/**
 * Interactive Visualization & Charting Engine
 * Pure SVG & CSS-rendered responsive charts for:
 * 1. Step-by-Step Acquisition & Conversion Funnel
 * 2. Cumulative Cohort Progression Curves (D0 -> D30)
 * 3. iOS vs Android Device Funnel Audit
 */

class CohortChartRenderer {
  renderFunnel(containerId, data) {
    const el = document.getElementById(containerId);
    if (!el) return;

    const stages = [
      { name: "Impressions", val: data.impressions, color: "#64748B" },
      { name: "Clicks", val: data.clicks, color: "#0284C7" },
      { name: "Contacts Registered", val: data.contacts_registered, color: "#0D9488" },
      { name: "Demos Booked", val: data.demos_booked, color: "#6366F1" },
      { name: "Demos Attended", val: data.demos_attended, color: "#D97706" },
      { name: "Paying Conversions", val: data.conversions, color: "#10B981" }
    ];

    const maxVal = Math.max(...stages.map(s => s.val), 1);

    let html = `<div style="display:flex;flex-direction:column;gap:12px;padding:8px 0;">`;
    stages.forEach((st, idx) => {
      const pctOfMax = Math.max((st.val / maxVal * 100), 2.5);
      const prevVal = idx > 0 ? stages[idx - 1].val : null;
      const stepConv = prevVal && prevVal > 0 ? ((st.val / prevVal) * 100).toFixed(1) + "% step conv" : "100% baseline";
      const leadConv = stages[2].val > 0 && idx >= 2 ? ` · ${((st.val / stages[2].val) * 100).toFixed(1)}% of leads` : "";

      html += `
        <div>
          <div style="display:flex;justify-content:space-between;align-items:baseline;font-size:12px;margin-bottom:5px;">
            <span style="font-weight:600;color:var(--ink);">${st.name}</span>
            <span style="font-family:var(--mono);font-weight:700;color:var(--ink);">
              ${st.val.toLocaleString()} 
              <span style="font-size:11px;color:var(--ink3);font-weight:500;">(${stepConv}${leadConv})</span>
            </span>
          </div>
          <div style="height:20px;background:var(--line2);border-radius:4px;overflow:hidden;border:1px solid var(--line);position:relative;">
            <div style="height:100%;width:${pctOfMax}%;background:${st.color};border-radius:3px;transition:width 0.4s cubic-bezier(0.4, 0, 0.2, 1);"></div>
          </div>
        </div>
      `;
    });
    html += `</div>`;
    el.innerHTML = html;
  }

  renderProgressionCurve(containerId, daysData) {
    const el = document.getElementById(containerId);
    if (!el || !daysData || daysData.length === 0) return;

    // Build SVG Line Chart
    const w = 680;
    const h = 260;
    const pad = { top: 20, right: 30, bottom: 40, left: 55 };
    const chartW = w - pad.left - pad.right;
    const chartH = h - pad.top - pad.bottom;

    const maxLeads = Math.max(...daysData.map(d => d.leads_captured), 1);
    const maxConv = Math.max(...daysData.map(d => d.conversions_count), 1);

    const xStep = chartW / Math.max(daysData.length - 1, 1);

    const leadsPoints = daysData.map((d, i) => `${pad.left + i * xStep},${pad.top + chartH - (d.leads_captured / maxLeads * chartH)}`).join(" ");
    const convPoints = daysData.map((d, i) => `${pad.left + i * xStep},${pad.top + chartH - (d.conversions_count / maxConv * (chartH * 0.85))}`).join(" ");

    let svg = `
      <svg viewBox="0 0 ${w} ${h}" style="width:100%;height:auto;overflow:visible;font-family:var(--mono);font-size:10px;">
        <!-- Grid lines -->
        <line x1="${pad.left}" y1="${pad.top}" x2="${w - pad.right}" y2="${pad.top}" stroke="#E2E8F0" stroke-dasharray="3,3" />
        <line x1="${pad.left}" y1="${pad.top + chartH/2}" x2="${w - pad.right}" y2="${pad.top + chartH/2}" stroke="#E2E8F0" stroke-dasharray="3,3" />
        <line x1="${pad.left}" y1="${pad.top + chartH}" x2="${w - pad.right}" y2="${pad.top + chartH}" stroke="#CBD5E1" stroke-width="1.5" />
        
        <!-- Y-Axis Labels -->
        <text x="${pad.left - 8}" y="${pad.top + 4}" text-anchor="end" fill="#64748B">${maxLeads}</text>
        <text x="${pad.left - 8}" y="${pad.top + chartH/2 + 4}" text-anchor="end" fill="#64748B">${Math.round(maxLeads/2)}</text>
        <text x="${pad.left - 8}" y="${pad.top + chartH + 4}" text-anchor="end" fill="#64748B">0</text>

        <!-- X-Axis Labels -->
        <text x="${pad.left}" y="${h - 10}" fill="#64748B">Day 1</text>
        <text x="${pad.left + chartW/2}" y="${h - 10}" text-anchor="middle" fill="#64748B">Day 15</text>
        <text x="${w - pad.right}" y="${h - 10}" text-anchor="end" fill="#64748B">Day 31</text>

        <!-- Leads Path -->
        <polyline fill="none" stroke="#0284C7" stroke-width="2.5" points="${leadsPoints}" />
        
        <!-- Conversions Path -->
        <polyline fill="none" stroke="#10B981" stroke-width="2.5" stroke-dasharray="4,2" points="${convPoints}" />

        <!-- Data points -->
        ${daysData.map((d, i) => `
          <circle cx="${pad.left + i * xStep}" cy="${pad.top + chartH - (d.leads_captured / maxLeads * chartH)}" r="${d.is_mature ? 3 : 2}" fill="${d.is_mature ? '#0284C7' : '#EA580C'}" />
        `).join("")}
      </svg>
      <div style="display:flex;gap:18px;justify-content:center;font-size:12px;margin-top:8px;">
        <span style="display:flex;align-items:center;gap:6px;"><i style="width:12px;height:3px;background:#0284C7;display:inline-block;"></i> Leads Captured</span>
        <span style="display:flex;align-items:center;gap:6px;"><i style="width:12px;height:3px;background:#10B981;border-bottom:1px dashed #10B981;display:inline-block;"></i> Realized Conversions</span>
      </div>
    `;

    el.innerHTML = svg;
  }

  renderDeviceComparison(containerId, deviceData) {
    const el = document.getElementById(containerId);
    if (!el || !deviceData || !deviceData.devices) return;

    const ios = deviceData.devices.find(d => d.os === "iOS") || deviceData.devices[0];
    const android = deviceData.devices.find(d => d.os === "Android") || deviceData.devices[1];

    let html = `
      <div style="font-size:13px;line-height:1.6;margin-bottom:18px;color:#1E293B;background:var(--card);border:1px solid var(--line);padding:14px 16px;border-radius:var(--radius-md);box-shadow:var(--shadow-sm);">
        <b style="color:var(--petrol-dark);">Diagnostic Audit Finding:</b> ${deviceData.summary_insight}
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
        <div style="background:#F0FDF4;border:1px solid #BBF7D0;border-radius:var(--radius-md);padding:16px;box-shadow:var(--shadow-sm);">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
            <span style="font-weight:700;font-size:15px;color:#166534;">🍎 Apple iOS Funnel</span>
            <span style="font-family:var(--mono);font-size:11px;background:#DCFCE7;color:#166534;padding:3px 8px;border-radius:12px;font-weight:700;">${ios.leads_share_pct}% of total leads</span>
          </div>
          <div style="font-size:12.5px;display:flex;flex-direction:column;gap:8px;">
            <div style="display:flex;justify-content:space-between;"><span>Registered Leads:</span> <b>${ios.leads.toLocaleString()}</b></div>
            <div style="display:flex;justify-content:space-between;"><span>Demo Booking Rate:</span> <b>${ios.booked_pct}%</b></div>
            <div style="display:flex;justify-content:space-between;"><span>Demo Attendance Rate:</span> <b style="color:#0D9488;">${ios.attended_pct}%</b></div>
            <div style="display:flex;justify-content:space-between;border-top:1px dashed #BBF7D0;padding-top:6px;">
              <span>Lead Conversion Rate:</span> 
              <b style="color:#16A34A;font-size:14px;">${ios.conversion_pct}% (${ios.conversion_ratio_vs_android}× Android)</b>
            </div>
            <div style="display:flex;justify-content:space-between;"><span>Total Realized Revenue:</span> <b>₹${ios.revenue.toLocaleString()}</b></div>
            <div style="display:flex;justify-content:space-between;"><span>ARPU (Paying Parent):</span> <b>₹${ios.arpu.toLocaleString()}</b></div>
          </div>
        </div>

        <div style="background:#FFFBEB;border:1px solid #FDE68A;border-radius:var(--radius-md);padding:16px;box-shadow:var(--shadow-sm);">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
            <span style="font-weight:700;font-size:15px;color:#92400E;">🤖 Google Android Funnel</span>
            <span style="font-family:var(--mono);font-size:11px;background:#FEF3C7;color:#92400E;padding:3px 8px;border-radius:12px;font-weight:700;">${android.leads_share_pct}% of total leads</span>
          </div>
          <div style="font-size:12.5px;display:flex;flex-direction:column;gap:8px;">
            <div style="display:flex;justify-content:space-between;"><span>Registered Leads:</span> <b>${android.leads.toLocaleString()}</b></div>
            <div style="display:flex;justify-content:space-between;"><span>Demo Booking Rate:</span> <b>${android.booked_pct}% (Parity)</b></div>
            <div style="display:flex;justify-content:space-between;"><span>Demo Attendance Rate:</span> <b style="color:#EA580C;">${android.attended_pct}% (Primary Friction Point)</b></div>
            <div style="display:flex;justify-content:space-between;border-top:1px dashed #FDE68A;padding-top:6px;">
              <span>Lead Conversion Rate:</span> 
              <b style="color:#92400E;font-size:14px;">${android.conversion_pct}%</b>
            </div>
            <div style="display:flex;justify-content:space-between;"><span>Total Realized Revenue:</span> <b>₹${android.revenue.toLocaleString()}</b></div>
            <div style="display:flex;justify-content:space-between;"><span>ARPU (Paying Parent):</span> <b>₹${android.arpu.toLocaleString()}</b></div>
          </div>
        </div>
      </div>
    `;
    el.innerHTML = html;
  }
}

window.chartRenderer = new CohortChartRenderer();
