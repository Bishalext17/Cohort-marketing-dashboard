/**
 * Actionable CRM Follow-up Lead Manager
 * Provides search, priority filtering, inline status update, counselor notes, and CSV streaming
 */

class FollowUpManager {
  constructor() {
    this.currentCategory = "all";
    this.contactsData = [];
    this.searchQuery = "";
    this.activeNoteLeadId = null;
  }

  async loadContacts(category = "all") {
    this.currentCategory = category;
    
    // Update chip styling
    document.querySelectorAll(".followup-chip").forEach(btn => {
      btn.classList.toggle("on", btn.dataset.cat === category);
    });

    const container = document.getElementById("followupTableBody");
    const countEl = document.getElementById("followupCount");
    const revEl = document.getElementById("followupTotalRev");

    if (container) {
      container.innerHTML = `<tr><td colspan="10" style="text-align:center;padding:30px;color:var(--ink3);">Loading contact pipeline...</td></tr>`;
    }

    try {
      const res = await (window.authFetch || fetch)(`/api/v1/followups?category=${category}`);
      const data = await res.json();
      this.contactsData = data.contacts || [];
      
      if (countEl) countEl.innerText = `${data.count} actionable leads`;
      if (revEl) revEl.innerText = `₹${data.total_potential_or_actual_revenue.toLocaleString()}`;
      
      this.renderTable();
    } catch (e) {
      console.error("Error loading followups:", e);
      if (container) {
        container.innerHTML = `<tr><td colspan="10" style="text-align:center;color:var(--warn);padding:24px;">Failed to load contacts.</td></tr>`;
      }
    }
  }

  setSearchQuery(q) {
    this.searchQuery = (q || "").toLowerCase().trim();
    this.renderTable();
  }

  async updateLead(leadId, patchData) {
    try {
      const res = await (window.authFetch || fetch)(`/api/v1/followups/${leadId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patchData)
      });

      if (res.ok) {
        const updated = await res.json();
        const idx = this.contactsData.findIndex(c => c.lead_id === leadId);
        if (idx >= 0) {
          this.contactsData[idx] = updated;
        }
        this.renderTable();
      }
    } catch (e) {
      console.error(`Error updating lead ${leadId}:`, e);
    }
  }

  openNotesModal(leadId) {
    this.activeNoteLeadId = leadId;
    const contact = this.contactsData.find(c => c.lead_id === leadId);
    if (!contact) return;

    const modal = document.getElementById("notesModal");
    const leadNameEl = document.getElementById("notesModalLeadName");
    const textarea = document.getElementById("notesModalTextarea");

    if (leadNameEl) leadNameEl.innerText = `${contact.parent_name} (${contact.lead_id}) · ${contact.course}`;
    if (textarea) textarea.value = contact.notes || "";
    if (modal) modal.style.display = "flex";
  }

  closeNotesModal() {
    const modal = document.getElementById("notesModal");
    if (modal) modal.style.display = "none";
    this.activeNoteLeadId = null;
  }

  saveActiveNote() {
    if (!this.activeNoteLeadId) return;
    const textarea = document.getElementById("notesModalTextarea");
    const noteVal = textarea ? textarea.value.trim() : "";
    this.updateLead(this.activeNoteLeadId, { notes: noteVal });
    this.closeNotesModal();
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
        c.campaign_name.toLowerCase().includes(this.searchQuery) ||
        (c.notes && c.notes.toLowerCase().includes(this.searchQuery))
      );
    });

    if (filtered.length === 0) {
      container.innerHTML = `<tr><td colspan="10" style="text-align:center;padding:36px;color:var(--ink3);">No contacts match your filter criteria.</td></tr>`;
      return;
    }

    let html = "";
    filtered.forEach(c => {
      const priorityBadge = c.followup_priority === "High" ? "background:#FEE2E2;color:#991B1B" : (c.followup_priority === "Medium" ? "background:#FEF3C7;color:#92400E" : "background:#F1F5F9;color:#475569");
      const hasNote = Boolean(c.notes && c.notes.trim());

      html += `
        <tr>
          <td style="font-family:var(--mono);font-weight:600;">${c.lead_id}</td>
          <td><b>${c.parent_name}</b></td>
          <td>
            <span style="font-family:var(--mono);">${c.phone}</span>
            <button class="copy-btn" onclick="followUpManager.copyPhone('${c.phone}')" title="Copy Phone">Copy</button>
          </td>
          <td style="font-family:var(--mono);font-size:11.5px;">${c.lead_date}</td>
          <td><span style="font-weight:600;color:var(--petrol);">${c.course}</span></td>
          <td style="max-width:180px;overflow:hidden;text-overflow:ellipsis;" title="${c.campaign_name}">${c.campaign_name}</td>
          <td>
            <select class="status-select" onchange="followUpManager.updateLead('${c.lead_id}', { status: this.value })">
              <option value="Registered" ${c.status === 'Registered' ? 'selected' : ''}>Registered</option>
              <option value="Booked (Not Attended)" ${c.status === 'Booked (Not Attended)' ? 'selected' : ''}>Booked (Not Attended)</option>
              <option value="Attended (Unpaid)" ${c.status === 'Attended (Unpaid)' ? 'selected' : ''}>Attended (Unpaid)</option>
              <option value="Converted" ${c.status === 'Converted' ? 'selected' : ''}>Converted</option>
              <option value="Follow-up Call Scheduled" ${c.status === 'Follow-up Call Scheduled' ? 'selected' : ''}>Follow-up Call</option>
              <option value="Dropped / Not Interested" ${c.status === 'Dropped / Not Interested' ? 'selected' : ''}>Dropped</option>
            </select>
          </td>
          <td style="font-family:var(--mono);text-align:right;font-weight:700;">₹${c.amount.toLocaleString()}</td>
          <td><span style="padding:3px 8px;border-radius:12px;font-size:10px;font-weight:700;font-family:var(--mono);${priorityBadge}">${c.followup_priority}</span></td>
          <td style="text-align:center;">
            <button class="mini" onclick="followUpManager.openNotesModal('${c.lead_id}')" style="${hasNote ? 'border-color:var(--petrol);color:var(--petrol);font-weight:700;' : ''}">
              ${hasNote ? '📝 View Notes' : '+ Note'}
            </button>
          </td>
        </tr>
      `;
    });
    container.innerHTML = html;
  }

  copyPhone(phone) {
    navigator.clipboard.writeText(phone).then(() => {
      alert(`Copied phone number to clipboard: ${phone}`);
    });
  }

  exportCSV() {
    window.location.href = `/api/v1/followups/export-csv?category=${this.currentCategory}`;
  }
}

window.followUpManager = new FollowUpManager();
