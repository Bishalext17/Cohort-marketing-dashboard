import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def create_rollout_pdf(output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=32,
        bottomMargin=32
    )

    styles = getSampleStyleSheet()

    # Premium Color Palette
    c_primary = colors.HexColor("#0F172A")    # Deep Slate
    c_brand = colors.HexColor("#0284C7")      # Vibrant Sky Blue
    c_brand_dark = colors.HexColor("#0369A1") # Dark Petrol
    c_teal = colors.HexColor("#0D9488")       # Teal Accent
    c_gray_dark = colors.HexColor("#334155")  # Ink Gray
    c_gray_light = colors.HexColor("#F8FAFC") # Paper background
    c_border = colors.HexColor("#CBD5E1")     # Line color
    c_green = colors.HexColor("#16A34A")      # Green Success
    c_card_bg = colors.HexColor("#F1F5F9")    # Card Background

    # Typography Styles
    style_title = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=c_primary,
        spaceAfter=2
    )
    style_subtitle = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=13,
        textColor=c_brand_dark,
        spaceAfter=8
    )
    style_h1 = ParagraphStyle(
        'Header1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11.5,
        leading=15,
        textColor=c_primary,
        spaceBefore=8,
        spaceAfter=4
    )
    style_h2 = ParagraphStyle(
        'Header2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=13,
        textColor=c_brand_dark,
        spaceBefore=6,
        spaceAfter=2
    )
    style_body = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=c_gray_dark,
        spaceAfter=4
    )
    style_bullet = ParagraphStyle(
        'Bullet',
        parent=style_body,
        leftIndent=10,
        firstLineIndent=-6,
        spaceAfter=2
    )
    style_callout = ParagraphStyle(
        'Callout',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#1E293B")
    )
    style_tbl_hdr = ParagraphStyle(
        'TableHdr',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white
    )
    style_tbl_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=9.5,
        textColor=c_primary
    )
    style_tbl_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=style_tbl_cell,
        fontName='Helvetica-Bold'
    )

    story = []

    # ═════════════════════════════════════════════════════════════════════════
    # PAGE 1: ROLLOUT ROADMAP & PHASES 1-3
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("Bambinos Marketing & Cohort Intelligence Platform", style_title))
    story.append(Paragraph("PRODUCTION ROLLOUT & EXECUTION PLAN: DIRECT META MARKETING INGESTION", style_subtitle))
    story.append(HRFlowable(width="100%", thickness=1.5, color=c_brand, spaceAfter=6, spaceBefore=0))

    meta_data = [
        [
            Paragraph("<b>Target Standard:</b> v14 Production Live Standard", style_body),
            Paragraph("<b>Scheduled Run:</b> Daily 08:00 AM IST (02:30 UTC)", style_body),
        ],
        [
            Paragraph("<b>Database Protection:</b> 500-Row Chunks + 50ms Throttle", style_body),
            Paragraph("<b>Deployment Target:</b> GCP Cloud Run Jobs / GitHub Actions", style_body)
        ]
    ]
    t_meta = Table(meta_data, colWidths=[270, 270])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), c_gray_light),
        ('BOX', (0,0), (-1,-1), 0.5, c_border),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 6))

    story.append(Paragraph("1. Executive Rollout Overview", style_h1))
    story.append(Paragraph(
        "This execution plan details the 5-phase rollout strategy to operationalize the Direct Meta Marketing Graph API "
        "pipeline into Bambinos' live database infrastructure. It enforces zero database CPU spikes, complete data privacy, "
        "zero-discrepancy financial reconciliation, and automated sub-50ms dashboard query serving.",
        style_body
    ))
    story.append(Spacer(1, 4))

    story.append(Paragraph("2. Detailed 5-Phase Execution Sequence", style_h1))

    # Phase 1
    story.append(Paragraph("Phase 1: Environment & Staging Schema Provisioning", style_h2))
    story.append(Paragraph("• <b>Step 1.1 (Staging DDL Execution):</b> Execute <code>queries/01_production/00_create_staging_tables.sql</code> to create <code>raw_meta_ads_delivery</code> (clustered primary key) and <code>data_pipeline_runs</code>.", style_bullet))
    story.append(Paragraph("• <b>Step 1.2 (Credential Configuration):</b> Add <code>META_ACCESS_TOKEN</code> (System User Token with <code>ads_read</code>) and <code>META_AD_ACCOUNT_IDS</code> to <code>backend/.env</code> and Secret Manager.", style_bullet))

    # Phase 2
    story.append(Spacer(1, 3))
    story.append(Paragraph("Phase 2: Live Ingestion & Historical Backfill", style_h2))
    story.append(Paragraph("• <b>Step 2.1 (Dry-Run Verification):</b> Run <code>python backend/scripts/ingest_meta_direct.py --days 7 --dry-run</code> to test API connectivity and action unnesting without DB writes.", style_bullet))
    story.append(Paragraph("• <b>Step 2.2 (30-Day Initial Backfill):</b> Execute live extraction: <code>python backend/scripts/ingest_meta_direct.py --days 30</code> with 500-row batching and 50ms micro-throttles.", style_bullet))
    story.append(Paragraph("• <b>Step 2.3 (Staging Validation):</b> Verify row counts in <code>raw_meta_ads_delivery</code> and confirm <code>SUCCESS</code> status in <code>data_pipeline_runs</code>.", style_bullet))

    # Phase 3
    story.append(Spacer(1, 3))
    story.append(Paragraph("Phase 3: Materialized Cache Synchronization & Benchmarking", style_h2))
    story.append(Paragraph("• <b>Step 3.1 (Stored Procedure Compilation):</b> Ensure procedures from <code>28_nightly_cache.sql</code> (<code>sp_refresh_cohort_cache_nightly</code>) are compiled on MariaDB.", style_bullet))
    story.append(Paragraph("• <b>Step 3.2 (Rolling Cache Sync):</b> Run <code>python backend/scripts/sync_cohort_cache.py --mode incremental</code> across the active 35-day maturation window to populate <code>cohort_detail_cache</code>.", style_bullet))
    story.append(Paragraph("• <b>Step 3.3 (Latency Benchmarking):</b> Verify FastAPI endpoint response times drop from >15s to <50ms.", style_bullet))

    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    # PAGE 2: PHASES 4-5, CPU SAFEGUARDS & SIGN-OFF
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("Phase 4: Quality Assurance & Reconciliation Gate", style_h2))
    story.append(Paragraph("• <b>Step 4.1 (Zero-Discrepancy Audit):</b> Run <code>python backend/scripts/verify_reconciliation.py</code> to confirm: (1) <code>SUM(spend)</code> in staging matches <code>SUM(spend)</code> in cohort cache exactly, and (2) Unmapped campaign spend is <2%.", style_bullet))
    story.append(Paragraph("• <b>Step 4.2 (RAM Cache Invalidation):</b> Flush backend memory caches via <code>cache_manager.clear()</code> to propagate fresh figures immediately to all cards.", style_bullet))

    # Phase 5
    story.append(Spacer(1, 3))
    story.append(Paragraph("Phase 5: Automated Cloud Orchestration & Monitoring", style_h2))
    story.append(Paragraph("• <b>Option A (GitHub Actions):</b> Push repository with <code>.github/workflows/daily-marketing-sync.yml</code> scheduled for daily <b>08:00 AM IST (02:30 UTC)</b> with manual on-demand trigger support.", style_bullet))
    story.append(Paragraph("• <b>Option B (GCP Cloud Run Job):</b> Execute <code>bash deploy_marketing_job.sh</code> to create <code>marketing-daily-sync</code> Cloud Run Job in <code>asia-south1</code> matching <code>bambinos-core</code> conventions.", style_bullet))

    story.append(Spacer(1, 6))

    # ── CPU & PERFORMANCE SAFEGUARDS TABLE ──
    story.append(Paragraph("3. Database Health & Zero-CPU-Spike Safeguards", style_h1))

    safe_rows = [
        [Paragraph("Safeguard Mechanism", style_tbl_hdr), Paragraph("Engineering Implementation", style_tbl_hdr), Paragraph("Production Impact", style_tbl_hdr)],
        [
            Paragraph("<b>Batch Size Cap</b>", style_tbl_cell_bold),
            Paragraph("500 rows per transaction chunk", style_tbl_cell),
            Paragraph("Prevents InnoDB buffer pool exhaustion and row-lock escalation.", style_tbl_cell)
        ],
        [
            Paragraph("<b>Inter-Batch Throttling</b>", style_tbl_cell_bold),
            Paragraph("50ms micro-sleep (<code>time.sleep(0.05)</code>)", style_tbl_cell),
            Paragraph("Yields CPU and lock resources to concurrent web queries and CRM users.", style_tbl_cell)
        ],
        [
            Paragraph("<b>In-Memory Offloading</b>", style_tbl_cell_bold),
            Paragraph("Actions unnested in Python RAM", style_tbl_cell),
            Paragraph("Zero JSON parsing or regex evaluation on the database CPU.", style_tbl_cell)
        ],
        [
            Paragraph("<b>Idempotent Upsert</b>", style_tbl_cell_bold),
            Paragraph("<code>ON DUPLICATE KEY UPDATE</code>", style_tbl_cell),
            Paragraph("Re-running backfills updates existing rows with zero duplicate spend.", style_tbl_cell)
        ],
        [
            Paragraph("<b>Sliding Window Sync</b>", style_tbl_cell_bold),
            Paragraph("Rolling 35 days (incremental mode)", style_tbl_cell),
            Paragraph("Refreshes only active maturing cohorts rather than scanning years of history.", style_tbl_cell)
        ]
    ]
    t_safe = Table(safe_rows, colWidths=[120, 160, 260])
    t_safe.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_brand_dark),
        ('BOX', (0,0), (-1,-1), 0.5, c_border),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_gray_light])
    ]))
    story.append(t_safe)

    story.append(Spacer(1, 6))

    # ── VERIFICATION COMMANDS TABLE ──
    story.append(Paragraph("4. Quick-Reference Operational Commands", style_h1))

    cmd_rows = [
        [Paragraph("Operational Action", style_tbl_hdr), Paragraph("Terminal Command", style_tbl_hdr)],
        [
            Paragraph("<b>Run Full Test Suite</b>", style_tbl_cell_bold),
            Paragraph("<code>python -m unittest discover -s backend/tests -p \"test_*.py\"</code>", style_tbl_cell)
        ],
        [
            Paragraph("<b>Test Dry-Run Master Pipeline</b>", style_tbl_cell_bold),
            Paragraph("<code>python backend/scripts/run_daily_pipeline.py --days 3 --dry-run</code>", style_tbl_cell)
        ],
        [
            Paragraph("<b>Execute Live 30-Day Backfill</b>", style_tbl_cell_bold),
            Paragraph("<code>python backend/scripts/run_daily_pipeline.py --days 30</code>", style_tbl_cell)
        ],
        [
            Paragraph("<b>Deploy Cloud Run Job</b>", style_tbl_cell_bold),
            Paragraph("<code>bash deploy_marketing_job.sh</code>", style_tbl_cell)
        ]
    ]
    t_cmd = Table(cmd_rows, colWidths=[160, 380])
    t_cmd.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('BOX', (0,0), (-1,-1), 0.5, c_border),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_gray_light])
    ]))
    story.append(t_cmd)

    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.75, color=c_border, spaceAfter=6, spaceBefore=4))

    # ── SIGN-OFF & CONCLUSION ──
    sign_text = (
        "<b>Rollout Approval:</b> This execution plan provides an end-to-end, zero-risk pathway to live production. "
        "All code, DDL, procedures, unit tests, and schedulers are verified and ready for execution upon credential input."
    )
    story.append(Paragraph(sign_text, style_callout))

    doc.build(story)
    print(f"Successfully generated Rollout Plan PDF at: {output_path}")

if __name__ == "__main__":
    out = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "docs",
        "Bambinos_Production_Rollout_Plan.pdf"
    )
    create_rollout_pdf(out)
