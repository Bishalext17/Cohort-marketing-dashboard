-- =============================================================================
-- 01 · PRODUCTION COMPOSITE INDEXES & ATTRIBUTION SCHEMA
-- =============================================================================
-- Purpose:
-- 1. Accelerates cohort pipeline queries by eliminating full-table scans.
-- 2. Bridges deterministic lead-to-booking joins via leads_contact_utm_id.
-- 3. Enables direct invoice UTM attribution to resolve untagged revenue records.
-- =============================================================================

-- ── 1. INVOICE SCHEMA ATTRIBUTION UPGRADE ────────────────────────────────────
-- Add leads_contact_utm_id to invoices if not already present
SET @col_exists = 0;
SELECT COUNT(*) INTO @col_exists
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'invoices'
  AND column_name = 'leads_contact_utm_id';

SET @sql = IF(@col_exists = 0,
    'ALTER TABLE invoices ADD COLUMN leads_contact_utm_id BIGINT NULL AFTER parent_id;',
    'SELECT "Column leads_contact_utm_id already exists in invoices" AS status;'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


-- ── 2. BOOKING & CONVERSION INDEXES ──────────────────────────────────────────
-- Index on classschedulebookings for deterministic lead join
SET @idx_exists = 0;
SELECT COUNT(*) INTO @idx_exists FROM information_schema.statistics
WHERE table_schema = DATABASE() AND table_name = 'classschedulebookings' AND index_name = 'idx_lcui';
SET @sql = IF(@idx_exists = 0,
    'ALTER TABLE classschedulebookings ADD INDEX idx_lcui (leads_contact_utm_id);',
    'SELECT "Index idx_lcui exists on classschedulebookings" AS status;'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Composite index on classschedulebookings for fallback parent lookup and date filter
SET @idx_exists = 0;
SELECT COUNT(*) INTO @idx_exists FROM information_schema.statistics
WHERE table_schema = DATABASE() AND table_name = 'classschedulebookings' AND index_name = 'idx_parent_created';
SET @sql = IF(@idx_exists = 0,
    'ALTER TABLE classschedulebookings ADD INDEX idx_parent_created (parent_id, created_at);',
    'SELECT "Index idx_parent_created exists" AS status;'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Composite index for demo status and soft delete filtering
SET @idx_exists = 0;
SELECT COUNT(*) INTO @idx_exists FROM information_schema.statistics
WHERE table_schema = DATABASE() AND table_name = 'classschedulebookings' AND index_name = 'idx_demo_created';
SET @sql = IF(@idx_exists = 0,
    'ALTER TABLE classschedulebookings ADD INDEX idx_demo_created (demo_class, deleted_at, created_at);',
    'SELECT "Index idx_demo_created exists" AS status;'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;


-- ── 3. PARENT & INVOICE INDEXES ──────────────────────────────────────────────
-- Fast phone lookup on parents table
SET @idx_exists = 0;
SELECT COUNT(*) INTO @idx_exists FROM information_schema.statistics
WHERE table_schema = DATABASE() AND table_name = 'parents' AND index_name = 'idx_parent_mobile';
SET @sql = IF(@idx_exists = 0,
    'ALTER TABLE parents ADD INDEX idx_parent_mobile (mobile_number, deleted_at);',
    'SELECT "Index idx_parent_mobile exists" AS status;'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Composite index on invoices for customer conversion lookups
SET @idx_exists = 0;
SELECT COUNT(*) INTO @idx_exists FROM information_schema.statistics
WHERE table_schema = DATABASE() AND table_name = 'invoices' AND index_name = 'idx_inv_parent_type_created';
SET @sql = IF(@idx_exists = 0,
    'ALTER TABLE invoices ADD INDEX idx_inv_parent_type_created (parent_id, invoice_type, created_at);',
    'SELECT "Index idx_inv_parent_type_created exists" AS status;'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Index on invoices for direct UTM key lookup
SET @idx_exists = 0;
SELECT COUNT(*) INTO @idx_exists FROM information_schema.statistics
WHERE table_schema = DATABASE() AND table_name = 'invoices' AND index_name = 'idx_inv_lcui';
SET @sql = IF(@idx_exists = 0,
    'ALTER TABLE invoices ADD INDEX idx_inv_lcui (leads_contact_utm_id);',
    'SELECT "Index idx_inv_lcui exists" AS status;'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;


-- ── 4. EVENT LOGS & AD DELIVERY INDEXES ───────────────────────────────────────
-- Event log indexing for fast capture date querying
SET @idx_exists = 0;
SELECT COUNT(*) INTO @idx_exists FROM information_schema.statistics
WHERE table_schema = DATABASE() AND table_name = 'leads_contact_event_logs' AND index_name = 'idx_evt_created';
SET @sql = IF(@idx_exists = 0,
    'ALTER TABLE leads_contact_event_logs ADD INDEX idx_evt_created (event_type, deleted_at, created_at);',
    'SELECT "Index idx_evt_created exists" AS status;'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @idx_exists = 0;
SELECT COUNT(*) INTO @idx_exists FROM information_schema.statistics
WHERE table_schema = DATABASE() AND table_name = 'leads_contact_event_logs' AND index_name = 'idx_evt_phone';
SET @sql = IF(@idx_exists = 0,
    'ALTER TABLE leads_contact_event_logs ADD INDEX idx_evt_phone (phone);',
    'SELECT "Index idx_evt_phone exists" AS status;'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Class date range index on classschedules
SET @idx_exists = 0;
SELECT COUNT(*) INTO @idx_exists FROM information_schema.statistics
WHERE table_schema = DATABASE() AND table_name = 'classschedules' AND index_name = 'idx_class_date';
SET @sql = IF(@idx_exists = 0,
    'ALTER TABLE classschedules ADD INDEX idx_class_date (class_date, deleted_at);',
    'SELECT "Index idx_class_date exists" AS status;'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
