-- =============================================================================
-- 00 · STAGING & AUDIT TABLES DDL (Optimized for Zero CPU & Minimal Lock Load)
-- =============================================================================
-- Optimization Design:
-- 1. Compact data types (VARCHAR(64), INT UNSIGNED, DECIMAL(12,4)) to keep index trees in RAM.
-- 2. Clustered Primary Key for O(1) point-lookup upserts (INSERT ... ON DUPLICATE KEY UPDATE).
-- 3. Separate staging from analytical cache to prevent locking production tables.
-- =============================================================================

-- ── 1. RAW META ADS DELIVERY STAGING TABLE ───────────────────────────────────
CREATE TABLE IF NOT EXISTS raw_meta_ads_delivery (
    date                DATE          NOT NULL,
    account_id          VARCHAR(64)   NOT NULL,
    campaign_id         VARCHAR(64)   NOT NULL,
    campaign_name       VARCHAR(255)  NOT NULL,
    adset_id            VARCHAR(64)   NOT NULL,
    adset_name          VARCHAR(255)  NOT NULL,
    ad_id               VARCHAR(64)   NOT NULL,
    ad_name             VARCHAR(500)  NOT NULL,
    impression_device   VARCHAR(40)   NOT NULL DEFAULT 'all',  -- 'iphone', 'android_smartphone', 'desktop'
    publisher_platform  VARCHAR(40)   NOT NULL DEFAULT 'all',  -- 'facebook', 'instagram'
    
    -- Volume & Delivery Metrics (Fixed at D0)
    spend               DECIMAL(12,4) NOT NULL DEFAULT 0.0000,
    impressions         INT UNSIGNED  NOT NULL DEFAULT 0,
    clicks              INT UNSIGNED  NOT NULL DEFAULT 0,
    link_clicks         INT UNSIGNED  NOT NULL DEFAULT 0,
    landing_page_views  INT UNSIGNED  NOT NULL DEFAULT 0,
    
    -- Pixel & CAPI Conversion Events
    complete_registration INT UNSIGNED NOT NULL DEFAULT 0,
    start_trial           INT UNSIGNED NOT NULL DEFAULT 0,
    purchases             INT UNSIGNED NOT NULL DEFAULT 0,
    
    created_at          TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Clustered Compound Primary Key for fast O(1) Upsert
    PRIMARY KEY (date, account_id, ad_id, impression_device, publisher_platform),
    INDEX idx_date_camp (date, campaign_name),
    INDEX idx_ad (ad_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC;


-- ── 2. DATA PIPELINE EXECUTION AUDIT TABLE ──────────────────────────────────
CREATE TABLE IF NOT EXISTS data_pipeline_runs (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    job_name        VARCHAR(100)  NOT NULL,
    status          ENUM('RUNNING', 'SUCCESS', 'FAILED') NOT NULL,
    date_from       DATE          NOT NULL,
    date_to         DATE          NOT NULL,
    rows_processed  INT UNSIGNED  DEFAULT 0,
    duration_sec    DECIMAL(8,2)  DEFAULT 0.00,
    error_message   TEXT          NULL,
    created_at      TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_job_date (job_name, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
