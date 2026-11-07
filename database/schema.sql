-- ========================================================
-- Placement Intelligence Hub — D1 / SQLite Universal Schema
-- ========================================================

-- 1. Sources Registry
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'company_portal',
    base_url TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    check_interval_minutes INTEGER NOT NULL DEFAULT 15,
    last_checked_at TEXT,
    last_status TEXT NOT NULL DEFAULT 'pending',
    error_message TEXT,
    health_score REAL NOT NULL DEFAULT 1.0,
    total_discovered INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 2. Canonical Opportunities Table
CREATE TABLE IF NOT EXISTS opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL,
    external_id TEXT,
    company TEXT NOT NULL,
    title TEXT NOT NULL,
    normalized_title TEXT NOT NULL,
    role_category TEXT NOT NULL DEFAULT 'full_time',
    locations TEXT NOT NULL DEFAULT '[]',         -- JSON array
    eligible_batches TEXT NOT NULL DEFAULT '[]',  -- JSON array
    eligible_degrees TEXT NOT NULL DEFAULT '[]',  -- JSON array
    eligible_branches TEXT NOT NULL DEFAULT '[]', -- JSON array
    ctc_min REAL,
    ctc_max REAL,
    ctc_currency TEXT NOT NULL DEFAULT 'INR',
    ctc_text TEXT,
    apply_url TEXT NOT NULL,
    canonical_url_hash TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    raw_description TEXT,
    summary TEXT,
    requirements TEXT NOT NULL DEFAULT '[]',      -- JSON array
    deadline TEXT,
    status TEXT NOT NULL DEFAULT 'pending_approval',
    confidence_score REAL NOT NULL DEFAULT 1.0,
    verification_status TEXT NOT NULL DEFAULT 'verified_official',
    verification_evidence TEXT NOT NULL DEFAULT '{}', -- JSON object
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_opp_url_hash ON opportunities(canonical_url_hash);
CREATE INDEX IF NOT EXISTS idx_opp_company ON opportunities(company);
CREATE INDEX IF NOT EXISTS idx_opp_status ON opportunities(status);
CREATE INDEX IF NOT EXISTS idx_opp_category ON opportunities(role_category);

-- 3. Opportunity Versions (Tracks Reopening & Updates)
CREATE TABLE IF NOT EXISTS opportunity_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_id INTEGER NOT NULL REFERENCES opportunities(id) ON DELETE CASCADE,
    version_num INTEGER NOT NULL DEFAULT 1,
    snapshot_data TEXT NOT NULL, -- JSON
    change_summary TEXT,
    recorded_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 4. Approval Queue
CREATE TABLE IF NOT EXISTS approval_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_id INTEGER NOT NULL REFERENCES opportunities(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending',
    reviewed_by TEXT,
    feedback TEXT,
    decided_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_approval_opp_id ON approval_queue(opportunity_id);

-- 5. Multi-Platform Publications
CREATE TABLE IF NOT EXISTS publications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_id INTEGER NOT NULL REFERENCES opportunities(id) ON DELETE CASCADE,
    platform TEXT NOT NULL, -- telegram_channel, telegram_topic, whatsapp_clipboard
    destination_id TEXT,
    message_id TEXT,
    status TEXT NOT NULL DEFAULT 'sent',
    formatted_content TEXT NOT NULL,
    error_message TEXT,
    published_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 6. Audit Logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id INTEGER,
    actor TEXT NOT NULL DEFAULT 'system',
    details TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

