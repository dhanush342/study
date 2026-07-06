"""
Bharat Tech Atlas — Database layer using SQLite with R-Tree spatial indexing.
v3.2: Added connection pooling, schema_version table for migrations, and
      proper cleanup on shutdown.
"""
import sqlite3
import os
import math
import threading

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "bharattechatlas.db")
SCHEMA_VERSION = 2  # Bump when schema changes

# ─── Connection pool ──────────────────────────────────────────────────────────
_pool_lock = threading.Lock()
_pool = {}


def _create_connection():
    """Create a new SQLite connection with optimized PRAGMAs."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA cache_size=-8000")
    conn.execute("PRAGMA mmap_size=67108864")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def get_db():
    """Get a connection from the pool (one per thread). Reopens if closed."""
    tid = threading.current_thread().ident
    with _pool_lock:
        conn = _pool.get(tid)
        # Check if connection is closed by trying a harmless operation
        is_closed = False
        if conn is None:
            is_closed = True
        else:
            try:
                conn.total_changes
            except sqlite3.ProgrammingError:
                is_closed = True
        if is_closed:
            _pool[tid] = _create_connection()
        return _pool[tid]


def close_all_connections():
    """Close all pooled connections. Call on shutdown."""
    with _pool_lock:
        for tid, conn in list(_pool.items()):
            try:
                conn.close()
            except Exception:
                pass
            _pool[tid] = None
        _pool.clear()


def init_db():
    """Initialize database schema with migration tracking."""
    conn = _create_connection()

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            entity_type TEXT NOT NULL CHECK (entity_type IN (
                'startup', 'sme', 'college_ecell', 'incubator',
                'accelerator', 'coworking', 'investor'
            )),
            sectors TEXT NOT NULL DEFAULT '[]',
            dpiit_category TEXT,
            business_model TEXT CHECK (business_model IN (
                'lifestyle', 'scalable', 'social', 'large_company', NULL
            )),
            stage TEXT CHECK (stage IN (
                'ideation', 'validation', 'early_traction',
                'scaling', 'mature', NULL
            )),
            dpiit_recognized INTEGER DEFAULT 0,
            nsa_winner INTEGER DEFAULT 0,
            nsa_category TEXT,
            is_women_led INTEGER DEFAULT 0,
            is_rural_impact INTEGER DEFAULT 0,
            is_campus_startup INTEGER DEFAULT 0,
            unicorn_status TEXT CHECK (unicorn_status IN (
                'unicorn', 'soonicorn', NULL
            )),
            funding_inr REAL DEFAULT 0,
            funding_stage TEXT,
            last_funding_date TEXT,
            funding_rounds TEXT DEFAULT '[]',
            valuation_usd REAL,
            description TEXT,
            website TEXT,
            logo_url TEXT,
            linkedin_url TEXT,
            instagram_url TEXT,
            facebook_url TEXT,
            twitter_url TEXT,
            linkedin_team_size INTEGER,
            linkedin_industry TEXT,
            linkedin_specialties TEXT,
            investors TEXT DEFAULT '[]',
            ynos_profile_url TEXT,
            address TEXT,
            city TEXT NOT NULL,
            district TEXT,
            state TEXT NOT NULL,
            pin_code TEXT,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            founded_year INTEGER,
            employee_count INTEGER,
            college_name TEXT,
            data_sources TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            is_active INTEGER DEFAULT 1
        );

        CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type) WHERE is_active = 1;
        CREATE INDEX IF NOT EXISTS idx_entities_city ON entities(city);
        CREATE INDEX IF NOT EXISTS idx_entities_state ON entities(state);
        CREATE INDEX IF NOT EXISTS idx_entities_slug ON entities(slug);
        CREATE INDEX IF NOT EXISTS idx_entities_founded ON entities(founded_year);
        CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name COLLATE NOCASE);
        CREATE INDEX IF NOT EXISTS idx_entities_dpiit_cat ON entities(dpiit_category);
        CREATE INDEX IF NOT EXISTS idx_entities_biz_model ON entities(business_model);
        CREATE INDEX IF NOT EXISTS idx_entities_unicorn ON entities(unicorn_status);
        CREATE INDEX IF NOT EXISTS idx_entities_funding ON entities(funding_inr DESC) WHERE is_active = 1;
        CREATE INDEX IF NOT EXISTS idx_entities_type_state ON entities(entity_type, state) WHERE is_active = 1;
        CREATE INDEX IF NOT EXISTS idx_entities_type_funding ON entities(entity_type, funding_inr DESC) WHERE is_active = 1;
        CREATE INDEX IF NOT EXISTS idx_entities_active_type ON entities(is_active, entity_type);
        CREATE INDEX IF NOT EXISTS idx_entities_active_latlon ON entities(is_active, latitude, longitude);
    """)

    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS entities_rtree
        USING rtree(id, min_lng, max_lng, min_lat, max_lat)
    """)

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sectors (
            slug TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            parent_slug TEXT,
            icon TEXT,
            color TEXT,
            category TEXT DEFAULT 'top_sector',
            FOREIGN KEY (parent_slug) REFERENCES sectors(slug)
        );

        INSERT OR IGNORE INTO sectors (slug, label, icon, color, category) VALUES
            ('fintech', 'FinTech', '💳', '#3B82F6', 'top_sector'),
            ('saas_ai', 'SaaS / AI', '☁️', '#6366F1', 'top_sector'),
            ('ecommerce', 'E-Commerce', '🛒', '#F59E0B', 'top_sector'),
            ('healthcare', 'Healthcare', '🏥', '#10B981', 'top_sector'),
            ('manufacturing', 'Manufacturing', '🏭', '#78716C', 'top_sector'),
            ('edtech', 'EdTech', '📚', '#8B5CF6', 'dpiit_category'),
            ('agritech', 'AgriTech', '🌾', '#84CC16', 'dpiit_category'),
            ('cleantech', 'CleanTech', '🌿', '#22C55E', 'dpiit_category'),
            ('deeptech', 'DeepTech', '🔬', '#EC4899', 'dpiit_category'),
            ('logistics', 'Logistics', '🚛', '#F97316', 'dpiit_category'),
            ('gaming', 'Gaming', '🎮', '#EF4444', 'dpiit_category'),
            ('ai_ml', 'AI / ML', '🤖', '#7C3AED', 'dpiit_category'),
            ('cybersecurity', 'Cybersecurity', '🔒', '#0EA5E9', 'dpiit_category'),
            ('foodtech', 'FoodTech', '🍔', '#D97706', 'dpiit_category'),
            ('proptech', 'PropTech', '🏠', '#14B8A6', 'dpiit_category'),
            ('legaltech', 'LegalTech', '⚖️', '#64748B', 'dpiit_category'),
            ('mediatech', 'MediaTech', '📺', '#E11D48', 'dpiit_category'),
            ('mobility', 'Mobility', '🚗', '#0891B2', 'dpiit_category'),
            ('social_impact', 'Social Impact', '🌍', '#059669', 'dpiit_category'),
            ('biotech', 'BioTech', '🧬', '#A855F7', 'dpiit_category'),
            ('spacetech', 'SpaceTech', '🚀', '#1D4ED8', 'dpiit_category'),
            ('d2c', 'D2C / E-Commerce', '🛍️', '#F59E0B', 'dpiit_category'),
            ('saas', 'SaaS', '💻', '#6366F1', 'dpiit_category'),
            ('healthtech', 'HealthTech', '💊', '#10B981', 'dpiit_category'),
            ('iot', 'IoT', '📡', '#0D9488', 'dpiit_category'),
            ('drone_tech', 'Drone Tech', '🛸', '#4F46E5', 'dpiit_category'),
            ('ev', 'EV / E-Mobility', '🔋', '#16A34A', 'dpiit_category'),
            ('insurtech', 'InsurTech', '🛡️', '#2563EB', 'dpiit_category'),
            ('wealthtech', 'WealthTech', '📈', '#7C3AED', 'dpiit_category');
    """)

    # ─── Schema versioning / migrations ───────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("INSERT OR IGNORE INTO schema_version (version) VALUES (0)")
    conn.commit()

    # Run migrations
    current = conn.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1").fetchone()[0]
    if current < 1:
        conn.execute("UPDATE schema_version SET version = 1 WHERE version = 0")
        conn.commit()
    if current < 2:
        try:
            conn.execute("ALTER TABLE entities ADD COLUMN github_stars INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        conn.execute("UPDATE schema_version SET version = 2 WHERE version = 1")
        conn.commit()

    conn.close()


def is_seeded() -> bool:
    """Check if database already has seed data."""
    try:
        conn = get_db()
        count = conn.execute("SELECT COUNT(*) FROM entities WHERE is_active = 1").fetchone()[0]
        return count > 100
    except Exception:
        return False


def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.asin(math.sqrt(a))
    return R * c
