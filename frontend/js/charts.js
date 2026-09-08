/**
 * Charting Engine for Cohort Marketing Performance
 * Provides pure JS/SVG interactive visualization for:
 * 1. Conversion & Attendance Funnels
 * 2. iOS vs Android Diagnostic Breakdown
 * 3. Cohort Retention & Progression Sparklines
 */

class CohortChartRenderer {
  renderFunnel(containerId, data) {
    const el = document.getElementById(containerId);
    if (!el) return;

    const stages = [
      { name: "Impressions", val: data.impressions, color: "#64748B" },
      { name: "Clicks", val: data.clicks, color: "#0284C7" },
      { name: "Contacts Reg.", val: data.contacts_registered, color: "#0D9488" },
      { name: "Demos Booked", val: data.demos_booked, color: "#4F46E5" },
      { name: "Demos Attended", val: data.demos_attended, color: "#D97706" },
      { name: "Conversions", val: data.conversions, color: "#16A34A" }
    ];

    const maxVal = Math.max(...stages.map(s => s.val), 1);

    let html = `<div style="display:flex;flex-direction:column;gap:10px;padding:10px 0;">`;
    stages.forEach((st, idx) => {
      const pctOfMax = Math.max((st.val / maxVal * 100), 2);
      const prevVal = idx > 0 ? stages[idx - 1].val : null;
      const convRate = prevVal ? ((st.val / prevVal) * 100).toFixed(1) + "% step conv" : "100% baseline";

      html += `
        <div>
          <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px;">
            <span style="font-weight:600;color:#1E293B;">${st.name}</span>
            <span style="font-family:var(--mono);font-weight:700;">${st.val.toLocaleString()} <span style="font-size:11px;color:#64748B;font-weight:normal;">(${convRate})</span></span>
          </div>
          <div style="height:18px;background:#F1F5F9;border-radius:4px;overflow:hidden;border:1px solid #E2E8F0;">
            <div style="height:100%;width:${pctOfMax}%;background:${st.color};border-radius:3px;transition:width 0.4s ease;"></div>
          </div>
        </div>
      `;
    });
    html += `</div>`;
    el.innerHTML = html;
  }

  renderDeviceComparison(containerId, deviceData) {
    const el = document.getElementById(containerId);
    if (!el || !deviceData || !deviceData.devices) return;

    const ios = deviceData.devices.find(d => d.os === "iOS") || deviceData.devices[0];
    const android = deviceData.devices.find(d => d.os === "Android") || deviceData.devices[1];

    let html = `
      <div style="font-size:12.5px;line-height:1.5;margin-bottom:14px;color:#334155;background:#F8FAFC;border:1px solid #E2E8F0;padding:10px 12px;border-radius:6px;">
        <b>Audit Finding:</b> ${deviceData.summary_insight}
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">
        <div style="background:#F0FDF4;border:1px solid #BBF7D0;border-radius:6px;padding:12px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <span style="font-weight:700;font-size:14px;color:#166534;">🍎 Apple iOS</span>
            <span style="font-family:var(--mono);font-size:11px;background:#DCFCE7;color:#166534;padding:2px 6px;border-radius:3px;">${ios.leads_share_pct}% of leads</span>
          </div>
          <div style="font-size:12px;display:flex;flex-direction:column;gap:6px;">
            <div>Booking Rate: <b>${ios.booked_pct}%</b></div>
            <div>Attendance Rate: <b style="color:#0D9488;">${ios.attended_pct}%</b></div>
            <div>Conversion Rate: <b style="color:#16A34A;font-size:13px;">${ios.conversion_pct}%</b> (2.6× Android)</div>
            <div>Total Revenue: <b>₹${ios.revenue.toLocaleString()}</b></div>
          </div>
        </div>

        <div style="background:#FFFBEB;border:1px solid #FDE68A;border-radius:6px;padding:12px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <span style="font-weight:700;font-size:14px;color:#92400E;">🤖 Android</span>
            <span style="font-family:var(--mono);font-size:11px;background:#FEF3C7;color:#92400E;padding:2px 6px;border-radius:3px;">${android.leads_share_pct}% of leads</span>
          </div>
          <div style="font-size:12px;display:flex;flex-direction:column;gap:6px;">
            <div>Booking Rate: <b>${android.booked_pct}%</b> (Parity)</div>
            <div>Attendance Rate: <b style="color:#C2410C;">${android.attended_pct}%</b> (Drop-off point)</div>
            <div>Conversion Rate: <b style="color:#92400E;">${android.conversion_pct}%</b></div>
            <div>Total Revenue: <b>₹${android.revenue.toLocaleString()}</b></div>
          </div>
        </div>
      </div>
    `;
    el.innerHTML = html;
  }
}

window.chartRenderer = new CohortChartRenderer();
