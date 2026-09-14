import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def create_phase4_pdf(output_path: str):
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
    c_brand = colors.HexColor("#0284C7")      # Vibrant Sky/Petrol Blue
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
    # PAGE 1: OBJECTIVES, ARCHITECTURE & INGESTION CORE
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("Bambinos Marketing & Cohort Intelligence Platform", style_title))
    story.append(Paragraph("PHASE 4 DETAILED IMPLEMENTATION PLAN: DATA GOVERNANCE, INGESTION & PIPELINES", style_subtitle))
    story.append(HRFlowable(width="100%", thickness=1.5, color=c_brand, spaceAfter=6, spaceBefore=0))

    meta_data = [
        [
            Paragraph("<b>Target Standard:</b> v14 Dual-Source Truth Engine", style_body),
            Paragraph("<b>Target Cadence:</b> Daily 08:00 AM IST (02:30 UTC)", style_body),
        ],
        [
            Paragraph("<b>Data Sources:</b> Windsor.ai (Meta Ads) & MariaDB CRM", style_body),
            Paragraph("<b>Orchestration:</b> GCP Cloud Run Jobs + GitHub Actions", style_body)
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

    story.append(Paragraph("1. Executive Overview & Core Objectives", style_h1))
    story.append(Paragraph(
        "Phase 4 establishes an automated, fault-tolerant data pipeline connecting external Meta Ads delivery facts "
        "(via Windsor.ai) with internal CRM bookings, attendance, and invoiced revenue facts in MariaDB. "
        "The primary objectives are: (1) eliminate manual report consolidation, (2) guarantee sub-50ms dashboard query "
        "latency via pre-aggregated materialized cache tables (<code>cohort_detail_cache</code>), and (3) enforce "
        "zero-discrepancy checksum reconciliation between ad spend and financial truth.",
        style_body
    ))
    story.append(Spacer(1, 4))

    story.append(Paragraph("2. Pipeline End-to-End Architecture", style_h1))

    arch_rows = [
        [Paragraph("Pipeline Stage", style_tbl_hdr), Paragraph("Component / Module", style_tbl_hdr), Paragraph("Function & Safeguards", style_tbl_hdr), Paragraph("Latency", style_tbl_hdr)],
        [
            Paragraph("<b>1. Ingestion</b>", style_tbl_cell_bold),
            Paragraph("<code>ingest_windsor.py</code>", style_tbl_cell),
            Paragraph("Pulls ad delivery (Spend, Imps, Clicks, LPVs, OS, Placement) from Windsor.ai. Enforces token budgets, 3x backoff, and upserts to <code>raw_meta_ads_delivery</code>.", style_tbl_cell),
            Paragraph("~45 sec", style_tbl_cell)
        ],
        [
            Paragraph("<b>2. Normalization</b>", style_tbl_cell_bold),
            Paragraph("<code>campaign_tagger.py</code>", style_tbl_cell),
            Paragraph("Maps raw campaign strings to canonical Market, Course, and Channel via <code>campaign-tags.csv</code>. Strict exact-matching; unmapped fallback.", style_tbl_cell),
            Paragraph("< 2 sec", style_tbl_cell)
        ],
        [
            Paragraph("<b>3. Materialization</b>", style_tbl_cell_bold),
            Paragraph("<code>sync_cohort_cache.py</code>", style_tbl_cell),
            Paragraph("Executes <code>28_nightly_cache.sql</code>. Refreshes rolling 35-day cohort window across D0-D30 + Till Date into <code>cohort_detail_cache</code>.", style_tbl_cell),
            Paragraph("~60 sec", style_tbl_cell)
        ],
        [
            Paragraph("<b>4. Reconciliation</b>", style_tbl_cell_bold),
            Paragraph("<code>verify_reconciliation.py</code>", style_tbl_cell),
            Paragraph("Validates control totals: Spend, Invoiced Revenue, and Lead Counts. Compares raw tables vs cache. Triggers alerts on >0.01% anomaly.", style_tbl_cell),
            Paragraph("< 5 sec", style_tbl_cell)
        ],
        [
            Paragraph("<b>5. Invalidation</b>", style_tbl_cell_bold),
            Paragraph("<code>cache_manager.clear()</code>", style_tbl_cell),
            Paragraph("Purges backend RAM/file cache, pushes execution telemetry to <code>audit_logger</code>, and exposes fresh state to REST endpoints.", style_tbl_cell),
            Paragraph("< 1 sec", style_tbl_cell)
        ]
    ]
    t_arch = Table(arch_rows, colWidths=[65, 110, 305, 60])
    t_arch.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('BOX', (0,0), (-1,-1), 0.5, c_border),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_gray_light])
    ]))
    story.append(t_arch)
    story.append(Spacer(1, 6))

    story.append(Paragraph("3. Deep-Dive: Ingestion & Normalization Mechanics", style_h1))
    story.append(Paragraph("Component 1: Windsor.ai Meta Ads Daily Ingestion Engine (<code>ingest_windsor.py</code>)", style_h2))
    story.append(Paragraph("• <b>API Endpoint:</b> <code>https://connectors.windsor.ai/meta</code> with dynamic date-window chunking to prevent API gateway timeouts.", style_bullet))
    story.append(Paragraph("• <b>Extracted Grain:</b> <code>date, account_id, campaign_id, campaign_name, adset_id, ad_id, ad_name, impression_device, publisher_platform</code>.", style_bullet))
    story.append(Paragraph("• <b>Metrics Captured:</b> Spend (Day 0 fixed), Impressions, Link Clicks, Landing Page Views (LPV), and Meta Conversion Actions.", style_bullet))
    story.append(Paragraph("• <b>Resilience & Cost Controls:</b> Exponential backoff with jitter (3 retries on 429/500), token usage caps, and idempotent <code>ON DUPLICATE KEY UPDATE</code> upserts.", style_bullet))
    story.append(Paragraph("• <b>Staging Table DDL (<code>00_create_staging_tables.sql</code>):</b> High-performance compound primary key on <code>(date, account_id, ad_id, impression_device, publisher_platform)</code>.", style_bullet))

    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    # PAGE 2: MATERIALIZATION, VERIFICATION & ROADMAP
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("4. Materialization, Quality Control & Automation", style_h1))

    # Component 2
    story.append(Paragraph("Component 2: MariaDB Materialized Cache Synchronization (<code>sync_cohort_cache.py</code>)", style_h2))
    story.append(Paragraph("• <b>Stored Procedure Execution:</b> Calls <code>sp_refresh_cohort_cache_nightly()</code> compiled from <code>28_nightly_cache.sql</code>.", style_bullet))
    story.append(Paragraph("• <b>Rolling 35-Day Window:</b> Recalculates cohorts within the active maturation window so that conversion and attendance events accumulating over D1-D30 are captured accurately.", style_bullet))
    story.append(Paragraph("• <b>Historical Rebuild Mode:</b> Supports full multi-year rebuild via <code>--mode full</code> with chunked transactions.", style_bullet))

    # Component 3
    story.append(Spacer(1, 4))
    story.append(Paragraph("Component 3: Checksum & Data Integrity Verification Suite (<code>verify_reconciliation.py</code>)", style_h2))
    story.append(Paragraph("• <b>Spend Reconciliation:</b> Verifies that <code>SUM(spend)</code> in <code>raw_meta_ads_delivery</code> matches <code>SUM(spend)</code> in <code>cohort_detail_cache</code> exactly.", style_bullet))
    story.append(Paragraph("• <b>Revenue Reconciliation:</b> Cross-checks invoiced <code>new_revenue</code> in internal billing against cohort total new revenue.", style_bullet))
    story.append(Paragraph("• <b>Lead & Booking Integrity:</b> Ensures contact counts and demo counts match internal MariaDB truth.", style_bullet))
    story.append(Paragraph("• <b>Governance Alert:</b> Flags any unmapped campaigns exceeding a 2% spend threshold for immediate tagging.", style_bullet))

    # Component 4
    story.append(Spacer(1, 4))
    story.append(Paragraph("Component 4: Scheduled Orchestration & Automation", style_h2))
    story.append(Paragraph("• <b>Master Runner:</b> <code>backend/scripts/run_daily_pipeline.py</code> chains Ingestion → Cache Sync → Verification → Cache Flush.", style_bullet))
    story.append(Paragraph("• <b>GCP Cloud Run Job:</b> <code>deploy_marketing_job.sh</code> creates <code>marketing-daily-sync</code> Cloud Run Job in <code>asia-south1</code> matching <code>bambinos-core</code> conventions.", style_bullet))
    story.append(Paragraph("• <b>Cloud Scheduler / GitHub Actions:</b> Scheduled to fire at <b>08:00 AM IST (02:30 UTC)</b> daily with manual on-demand trigger support.", style_bullet))

    story.append(Spacer(1, 6))

    # ── STEP-BY-STEP IMPLEMENTATION TIMELINE ──
    story.append(Paragraph("5. Step-by-Step Implementation & Delivery Roadmap", style_h1))

    roadmap_data = [
        [Paragraph("Step", style_tbl_hdr), Paragraph("Task Description", style_tbl_hdr), Paragraph("Deliverables", style_tbl_hdr), Paragraph("Validation Method", style_tbl_hdr)],
        [
            Paragraph("<b>4.1</b>", style_tbl_cell_bold),
            Paragraph("Windsor.ai Ingestion Engine", style_tbl_cell),
            Paragraph("<code>ingest_windsor.py</code><br/><code>00_create_staging_tables.sql</code>", style_tbl_cell),
            Paragraph("Mocked unit tests + dry-run API pull verifying schema mapping & deduplication.", style_tbl_cell)
        ],
        [
            Paragraph("<b>4.2</b>", style_tbl_cell_bold),
            Paragraph("Cohort Cache Sync Engine", style_tbl_cell),
            Paragraph("<code>sync_cohort_cache.py</code><br/>Stored procedure runner", style_tbl_cell),
            Paragraph("Verify table population and query speed improvement (<50ms).", style_tbl_cell)
        ],
        [
            Paragraph("<b>4.3</b>", style_tbl_cell_bold),
            Paragraph("Checksum & Quality Gate", style_tbl_cell),
            Paragraph("<code>verify_reconciliation.py</code><br/>Control total checkers", style_tbl_cell),
            Paragraph("Automated reconciliation unit tests with artificial discrepancy checks.", style_tbl_cell)
        ],
        [
            Paragraph("<b>4.4</b>", style_tbl_cell_bold),
            Paragraph("Master Runner & Schedulers", style_tbl_cell),
            Paragraph("<code>run_daily_pipeline.py</code><br/><code>daily-marketing-sync.yml</code><br/><code>deploy_marketing_job.sh</code>", style_tbl_cell),
            Paragraph("End-to-end execution test in CLI and simulated GitHub Actions run.", style_tbl_cell)
        ]
    ]
    t_road = Table(roadmap_data, colWidths=[35, 125, 170, 210])
    t_road.setStyle(TableStyle([
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
    story.append(t_road)

    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.75, color=c_border, spaceAfter=6, spaceBefore=4))
    
    # ── SIGN-OFF & NOTES ──
    sign_text = (
        "<b>Architectural Sign-off:</b> This plan strictly adheres to the Bambinos v14 analytical contract: "
        "Spend is fixed at D0, Leads belong permanently to their capture cohort, and Ratios are never averaged. "
        "Upon approval, implementation proceeds systematically through Steps 4.1 to 4.4."
    )
    story.append(Paragraph(sign_text, style_callout))

    doc.build(story)
    print(f"Successfully generated Phase 4 Implementation Plan PDF at: {output_path}")

if __name__ == "__main__":
    out = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "docs",
        "Bambinos_Phase4_Implementation_Plan.pdf"
    )
    create_phase4_pdf(out)
