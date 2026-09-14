import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def create_executive_pdf(output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom Palette
    c_primary = colors.HexColor("#0F172A")    # Deep Slate
    c_brand = colors.HexColor("#0284C7")      # Vibrant Petrol Blue
    c_brand_dark = colors.HexColor("#0369A1") # Dark Petrol
    c_teal = colors.HexColor("#0D9488")       # Teal
    c_gray_dark = colors.HexColor("#334155")  # Ink2
    c_gray_light = colors.HexColor("#F8FAFC") # Paper background
    c_border = colors.HexColor("#E2E8F0")     # Line color
    c_warn = colors.HexColor("#DC2626")       # Red Alert
    c_green = colors.HexColor("#16A34A")      # Green Success

    # Custom Typography Styles
    style_title = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=c_primary,
        spaceAfter=4
    )
    style_subtitle = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=c_brand_dark,
        spaceAfter=12
    )
    style_h1 = ParagraphStyle(
        'Header1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=c_primary,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )
    style_h2 = ParagraphStyle(
        'Header2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=c_brand_dark,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )
    style_body = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12.5,
        textColor=c_gray_dark,
        spaceAfter=5
    )
    style_bullet = ParagraphStyle(
        'BulletText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=c_gray_dark,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=3
    )
    style_callout = ParagraphStyle(
        'CalloutText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=c_primary
    )
    style_table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10.5,
        textColor=c_gray_dark
    )
    style_table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10.5,
        textColor=c_primary
    )

    story = []

    # ==================== HEADER ====================
    story.append(Paragraph("BAMBINOS GROWTH MARKETING INTELLIGENCE", style_subtitle))
    story.append(Paragraph("Executive Platform Architecture, Ingestion Governance & Security Protocol", style_title))
    story.append(Paragraph("<b>Confidential Briefing for Senior Leadership</b> · Target Version: v14 Production Standard · IST Timezone", style_body))
    story.append(HRFlowable(width="100%", thickness=1.5, color=c_brand, spaceBefore=4, spaceAfter=10))

    # ==================== 1. EXECUTIVE SUMMARY ====================
    story.append(Paragraph("1. Executive Summary & Core Purpose", style_h1))
    story.append(Paragraph(
        "The <b>Bambinos Marketing Intelligence Suite</b> is a unified, dual-truth analytics platform engineered to provide 100% visibility into acquisition unit economics, lead maturation cohorts, financial ROAS, and campaign diagnostics. It eliminates conversion ambiguity by bridging two separate sources of truth:",
        style_body
    ))
    story.append(Paragraph("• <b>Meta Ads Platform Delivery (via Windsor.ai)</b>: Ingests granular advertising data (Spend, Impressions, Link Clicks, CPM, CPC, Landing Page Views, and Meta conversion actions) broken down by Campaign, Ad Set, Ad, Placement, and Device OS.", style_bullet))
    story.append(Paragraph("• <b>Internal Business Outcomes (via Metabase / Database)</b>: Tracks verified CRM records (Unique Contact Submissions, Demos Booked, Demos Attended, Paying Enrolments, and Governed New-Business Revenue).", style_bullet))
    story.append(Spacer(1, 6))

    # ==================== 2. THE 5 CANONICAL VIEWS ====================
    story.append(Paragraph("2. The 5 Canonical Intelligence Modules", style_h1))
    
    modules_data = [
        [Paragraph("Module", style_table_cell_bold), Paragraph("Executive Scope", style_table_cell_bold), Paragraph("Key Metrics & Decision Value", style_table_cell_bold)],
        [
            Paragraph("<b>1. Company Level ROAS</b>", style_table_cell),
            Paragraph("Calendar-date financial reconciliation by invoice/payment date.", style_table_cell),
            Paragraph("Marketing Spend, New Revenue, Renewal Revenue, Company ROAS, Cost per Demo Booked, Revenue per Demo Booked.", style_table_cell)
        ],
        [
            Paragraph("<b>2. Cohort Performance Explorer</b>", style_table_cell),
            Paragraph("Permanent lead-capture cohort tracking across D0–D30 maturity windows.", style_table_cell),
            Paragraph("Fixed D0 acquisition investment vs moving mature conversions, attendance %, ARPU, and multi-dimensional slicing.", style_table_cell)
        ],
        [
            Paragraph("<b>3. Cohort ROAS Progression</b>", style_table_cell),
            Paragraph("Maturation Heatmap Matrix visualizing lead capture date vs outcome window.", style_table_cell),
            Paragraph("Dynamic HSL color grading for ROAS, Lead Conversion %, and Demos Attended across D0 through Till Date.", style_table_cell)
        ],
        [
            Paragraph("<b>4. Campaign Meta Diagnosis</b>", style_table_cell),
            Paragraph("Comparative diagnostic engine (Performance Window vs Comparison Window).", style_table_cell),
            Paragraph("6-stage funnel volume audit + 5-driver multiplicative cost pressure decomposition (CPM, CTR, Landing %, Lead %, Booking %).", style_table_cell)
        ],
        [
            Paragraph("<b>5. Meta Ads Manager Data</b>", style_table_cell),
            Paragraph("Ad delivery facts and creative/device distribution directly from Meta.", style_table_cell),
            Paragraph("Impression Device OS (iOS vs Android vs Desktop), placement efficiency, and independent booking event selection.", style_table_cell)
        ]
    ]
    t_modules = Table(modules_data, colWidths=[1.4*inch, 2.3*inch, 3.3*inch])
    t_modules.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_gray_light),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_modules)
    story.append(Spacer(1, 8))

    # ==================== 3. WINDSOR.AI INGESTION & COST OPTIMIZATION ====================
    story.append(Paragraph("3. Third-Party Ingestion Governance & API Cost Control Plan", style_h1))
    story.append(Paragraph(
        "To guarantee <b>zero runaway API costs and minimal token/credit consumption</b>, Windsor.ai integration operates under strict architectural constraints:",
        style_body
    ))

    cost_guardrails = [
        [Paragraph("Cost / Token Guardrail", style_table_cell_bold), Paragraph("Implementation Mechanism", style_table_cell_bold), Paragraph("Financial & Operational Benefit", style_table_cell_bold)],
        [
            Paragraph("<b>1. Zero On-Demand User API Calls</b>", style_table_cell),
            Paragraph("The dashboard frontend & API endpoints read 100% from precomputed local cache (JSON/Redis).", style_table_cell),
            Paragraph("Users switching tabs, filters, or date ranges generate <b>0 external API calls and 0 token cost</b>.", style_table_cell)
        ],
        [
            Paragraph("<b>2. Single Daily Batch Ingestion</b>", style_table_cell),
            Paragraph("Scheduled once per 24 hours at 08:00 IST (02:30 UTC) covering the previous completed day.", style_table_cell),
            Paragraph("Eliminates continuous polling, erratic scrapers, and background quota drain.", style_table_cell)
        ],
        [
            Paragraph("<b>3. Incremental Delta Sync (Active Window)</b>", style_table_cell),
            Paragraph("Historical months (>30 days) are frozen as immutable ledgers; only the moving 30-day window is queried.", style_table_cell),
            Paragraph("Reduces payload transfer volume by <b>over 85%</b> and avoids repetitive re-fetching of historical facts.", style_table_cell)
        ],
        [
            Paragraph("<b>4. Consolidated Field Selection</b>", style_table_cell),
            Paragraph("All necessary metrics, conversion actions, placements, and devices are pulled in a single batch query.", style_table_cell),
            Paragraph("Prevents redundant multi-query breakdowns for the same date/account grain.", style_table_cell)
        ],
        [
            Paragraph("<b>5. Hard Circuit Breakers & Quota Caps</b>", style_table_cell),
            Paragraph("Maximum 3 retries with exponential backoff; hard cap of max 5 API requests per day.", style_table_cell),
            Paragraph("Prevents runaway infinite retry loops during network or third-party outages.", style_table_cell)
        ]
    ]
    t_cost = Table(cost_guardrails, colWidths=[1.8*inch, 2.5*inch, 2.7*inch])
    t_cost.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_gray_light),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_cost)
    story.append(Spacer(1, 8))

    # ==================== 4. DATA SECURITY & ANTI-BREACH PROTOCOLS ====================
    story.append(Paragraph("4. Data Security, Privacy & Anti-Breach Safeguards", style_h1))
    story.append(Paragraph(
        "Protecting company proprietary data, customer privacy, and preventing unauthorized third-party access or data leakage is paramount. The system enforces the following <b>zero-trust security policies</b>:",
        style_body
    ))

    story.append(Paragraph("• <b>Zero External Data Exposure (Air-Gapped Ingestion)</b>: Third-party connectors (Windsor.ai, Meta API) are strictly <i>read-only</i> and <i>one-way</i>. No internal customer records, payment logs, or database credentials are ever sent to Windsor or any external third party.", style_bullet))
    story.append(Paragraph("• <b>PII Protection & Hash Masking</b>: Raw lead phone numbers and parent contact information are restricted to authorized admissions staff under role-based access control (RBAC). In analytical and reporting aggregates, identifiers are masked or one-way tokenized.", style_bullet))
    story.append(Paragraph("• <b>Server-Side Secret Isolation</b>: All API tokens (<code>WINDSOR_API_KEY</code>, <code>METABASE_API_KEY</code>, DB passwords) reside exclusively in encrypted server environment variables. They are never transmitted to the browser client or exposed in JavaScript.", style_bullet))
    story.append(Paragraph("• <b>Masked Error Logging & Sanitization</b>: The ingestion and analytical engine deliberately filters out raw HTTP request bodies, headers, and API responses from logs to prevent accidental credential leakage during service exceptions.", style_bullet))
    story.append(Paragraph("• <b>Staging Snapshot Integrity & Gating</b>: Daily data is ingested into an isolated staging sandbox first. It requires an automated checksum receipt (<code>success.json</code>) verifying row integrity, positive spend, and non-empty conversion columns before promotion to production.", style_bullet))
    story.append(Spacer(1, 8))

    # ==================== 5. STRICT METRIC & GOVERNANCE CONTRACT ====================
    story.append(Paragraph("5. Strict Calculation Contracts & Campaign Governance", style_h1))
    story.append(Paragraph(
        "<b>The Cardinal Law: 'Never Average Ratios'</b>. All unit ratios (ROAS, Cost/Demo, Attendance %, Lead Conversion %) divide filtered aggregated sums after all slicers are applied:",
        style_body
    ))
    story.append(Paragraph("• <b>Cost per Demo Booked</b> = $\\sum \\text{Spend} / \\sum \\text{Demos Booked}$ (Sum-first, zero bookings displays an em dash).", style_bullet))
    story.append(Paragraph("• <b>Revenue per Demo Booked</b> = $\\sum \\text{New Revenue} / \\sum \\text{Demos Booked}$ (Governed <code>new_revenue</code>).", style_bullet))
    story.append(Paragraph("• <b>Anti-Double-Counting for Meta Events</b>: <code>CompleteRegistration</code> and <code>StartTrial</code> are independent booking signals and are never summed together.", style_bullet))
    story.append(Paragraph("• <b>Campaign Governance (<code>campaign-tags.csv</code>)</b>: Standardized registry matching names/aliases to canonical Display Name, Course, Market, and Channel. Unmatched campaigns strictly become <code>Unmapped</code>.", style_bullet))
    story.append(Spacer(1, 8))

    # ==================== 6. IMPLEMENTATION ROADMAP & STATUS ====================
    story.append(Paragraph("6. Current Progress & Project Status", style_h1))
    
    status_data = [
        [Paragraph("Phase", style_table_cell_bold), Paragraph("Deliverable & Scope", style_table_cell_bold), Paragraph("Status", style_table_cell_bold)],
        [
            Paragraph("<b>Phase 1</b>", style_table_cell),
            Paragraph("Metric Contracts, Booking Economics & Gating Engine", style_table_cell),
            Paragraph("<font color='#16A34A'><b>✓ COMPLETED</b></font>", style_table_cell)
        ],
        [
            Paragraph("<b>Phase 2</b>", style_table_cell),
            Paragraph("FastAPI Modular Backend (/revenue, /analytics, /operations, /catalog)", style_table_cell),
            Paragraph("<font color='#16A34A'><b>✓ COMPLETED</b></font>", style_table_cell)
        ],
        [
            Paragraph("<b>Phase 3</b>", style_table_cell),
            Paragraph("Frontend UI with 5 Canonical Tabs, Heatmap Matrix & Driver Charts", style_table_cell),
            Paragraph("<font color='#16A34A'><b>✓ COMPLETED</b></font>", style_table_cell)
        ],
        [
            Paragraph("<b>Phase 4</b>", style_table_cell),
            Paragraph("Automated Windsor Ingestion, Token Control & Daily 08:00 IST Workflow", style_table_cell),
            Paragraph("<font color='#0284C7'><b>▶ IN EXECUTION</b></font>", style_table_cell)
        ],
        [
            Paragraph("<b>Phase 5</b>", style_table_cell),
            Paragraph("Reconciliation & Full Production Deployment", style_table_cell),
            Paragraph("Pending Phase 4", style_table_cell)
        ]
    ]
    t_status = Table(status_data, colWidths=[1.2*inch, 4.3*inch, 1.5*inch])
    t_status.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_gray_light),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_status)
    story.append(Spacer(1, 14))

    # ==================== SIGN-OFF / FOOTER ====================
    story.append(HRFlowable(width="100%", thickness=1, color=c_border, spaceBefore=4, spaceAfter=8))
    story.append(Paragraph("<b>Report Prepared For:</b> Bambinos Senior Leadership & Growth Executive Team<br/><b>Security Classification:</b> Highly Confidential · Internal Use Only · Validated against v14 Source Commit", style_subtitle))

    doc.build(story)
    print(f"Executive PDF generated successfully at: {output_path}")

if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs")
    os.makedirs(out_dir, exist_ok=True)
    target_file = os.path.join(out_dir, "Bambinos_Marketing_Intelligence_Executive_Report.pdf")
    create_executive_pdf(target_file)
