/**
 * Interactive Follow-up Contact Hub
 * Enables instant searching, filtering, one-click phone copy, and CSV export
 */

class FollowUpManager {
  constructor() {
    this.currentCategory = "all";
    this.contactsData = [];
    this.searchQuery = "";
  }

  async loadContacts(category = "all") {
    this.currentCategory = category;
    const container = document.getElementById("followupTableBody");
    const countEl = document.getElementById("followupCount");
    const revEl = document.getElementById("followupTotalRev");

    if (container) {
      container.innerHTML = `<tr><td colspan="9" style="text-align:center;padding:24px;color:#64748B;">Loading contact list...</td></tr>`;
    }

    try {
      const res = await fetch(`/api/v1/followups?category=${category}`);
      const data = await res.json();
      this.contactsData = data.contacts || [];
      
      if (countEl) countEl.innerText = `${data.count} contacts`;
      if (revEl) revEl.innerText = `₹${data.total_potential_or_actual_revenue.toLocaleString()}`;
      
      this.renderTable();
    } catch (e) {
      console.error("Error loading followups:", e);
      if (container) {
        container.innerHTML = `<tr><td colspan="9" style="text-align:center;color:#C2410C;padding:20px;">Failed to load contacts.</td></tr>`;
      }
    }
  }

  setSearchQuery(q) {
    this.searchQuery = (q || "").toLowerCase().trim();
    this.renderTable();
  }

  renderTable() {
    const container = document.getElementById("followupTableBody");
    if (!container) return;

    const filtered = this.contactsData.filter(c => {
      if (!this.searchQuery) return true;
      return (
        c.lead_id.toLowerCase().includes(this.searchQuery) ||
        c.phone.includes(this.searchQuery) ||
        c.parent_name.toLowerCase().includes(this.searchQuery) ||
        c.course.toLowerCase().includes(this.searchQuery) ||
        c.campaign_name.toLowerCase().includes(this.searchQuery)
      );
    });

    if (filtered.length === 0) {
      container.innerHTML = `<tr><td colspan="9" style="text-align:center;padding:30px;color:#64748B;">No contacts match your filter.</td></tr>`;
      return;
    }

    let html = "";
    filtered.forEach(c => {
      const badgeColor = c.converted ? "#DCFCE7;color:#166534" : (c.attended ? "#FEF3C7;color:#92400E" : "#F1F5F9;color:#475569");
      const priorityBadge = c.followup_priority === "High" ? "background:#FEE2E2;color:#991B1B" : "background:#F1F5F9;color:#475569";

      html += `
        <tr>
          <td style="font-family:var(--mono);font-weight:600;">${c.lead_id}</td>
          <td><b>${c.parent_name}</b></td>
          <td>
            <span style="font-family:var(--mono);">${c.phone}</span>
            <button class="copy-btn" onclick="followUpManager.copyPhone('${c.phone}')" title="Copy Phone">Copy</button>
          </td>
          <td style="font-family:var(--mono);">${c.lead_date}</td>
          <td>${c.course}</td>
          <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;" title="${c.campaign_name}">${c.campaign_name}</td>
          <td><span style="padding:2px 6px;border-radius:3px;font-size:11px;background:${badgeColor}">${c.status}</span></td>
          <td style="font-family:var(--mono);text-align:right;">₹${c.amount.toLocaleString()}</td>
          <td><span style="padding:2px 6px;border-radius:3px;font-size:10px;font-weight:700;${priorityBadge}">${c.followup_priority}</span></td>
        </tr>
      `;
    });
    container.innerHTML = html;
  }

  copyPhone(phone) {
    navigator.clipboard.writeText(phone).then(() => {
      alert(`Copied phone number: ${phone}`);
    });
  }

  exportCSV() {
    window.location.href = `/api/v1/followups/export-csv?category=${this.currentCategory}`;
  }
}

window.followUpManager = new FollowUpManager();
