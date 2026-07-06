"""
Bharat Tech Atlas — Data Loading Layer
Loads transformed records into SQLite with R-Tree spatial indexing.
Handles upserts, batch inserts, and index maintenance.
"""
import sqlite3
import json
import logging
from typing import List, Optional

from .transform import TransformedRecord

logger = logging.getLogger(__name__)


class ETLLoader:
    """
    Load transformed records into the spatial database.
    Supports batch inserts, upserts (update existing), and R-Tree maintenance.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def load_all(self, records: List[TransformedRecord], batch_size: int = 100) -> dict:
        """
        Load all transformed records into the database.
        Returns stats: inserted, updated, skipped, errors.
        """
        stats = {"inserted": 0, "updated": 0, "skipped": 0, "errors": 0}
        conn = self._get_conn()

        try:
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                batch_stats = self._load_batch(conn, batch)
                for key in stats:
                    stats[key] += batch_stats[key]

                if (i + batch_size) % 500 == 0:
                    logger.info(f"Loaded {i + batch_size}/{len(records)} records...")

            conn.commit()
            logger.info(f"Loading complete: {stats}")
        except Exception as e:
            conn.rollback()
            logger.error(f"Loading failed: {e}")
            raise
        finally:
            conn.close()

        return stats

    def _load_batch(self, conn: sqlite3.Connection, batch: List[TransformedRecord]) -> dict:
        """Load a batch of records with upsert logic."""
        stats = {"inserted": 0, "updated": 0, "skipped": 0, "errors": 0}

        for record in batch:
            try:
                existing = conn.execute(
                    "SELECT id FROM entities WHERE slug = ?", (record.slug,)
                ).fetchone()

                if existing:
                    self._update_record(conn, existing["id"], record)
                    stats["updated"] += 1
                else:
                    entity_id = self._insert_record(conn, record)
                    self._insert_rtree(conn, entity_id, record)
                    stats["inserted"] += 1

            except Exception as e:
                logger.error(f"Failed to load {record.name}: {e}")
                stats["errors"] += 1

        return stats

    def _insert_record(self, conn: sqlite3.Connection, record: TransformedRecord) -> int:
        """Insert a new entity record and return its ID."""
        cursor = conn.execute("""
            INSERT INTO entities (
                name, slug, entity_type, sectors, dpiit_category,
                business_model, stage, dpiit_recognized, nsa_winner,
                is_women_led, is_rural_impact, is_campus_startup,
                unicorn_status, funding_inr, funding_stage, valuation_usd,
                description, website, linkedin_url, investors,
                address, city, district, state, pin_code,
                latitude, longitude, founded_year, employee_count,
                data_sources, is_active
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1
            )
        """, (
            record.name, record.slug, record.entity_type,
            json.dumps(record.sectors), record.dpiit_category,
            record.business_model, record.stage,
            int(record.dpiit_recognized), int(record.nsa_winner),
            int(record.is_women_led), int(record.is_rural_impact),
            int(record.is_campus_startup), record.unicorn_status,
            record.funding_inr, record.funding_stage, record.valuation_usd,
            record.description, record.website, record.linkedin_url,
            json.dumps(record.investors), record.address,
            record.city, record.district, record.state, record.pin_code,
            record.latitude, record.longitude,
            record.founded_year, record.employee_count,
            json.dumps(record.data_sources),
        ))
        return cursor.lastrowid

    def _update_record(self, conn: sqlite3.Connection, entity_id: int,
                       record: TransformedRecord):
        """Update an existing entity with new data (merge strategy)."""
        conn.execute("""
            UPDATE entities SET
                funding_inr = MAX(funding_inr, ?),
                employee_count = COALESCE(?, employee_count),
                description = COALESCE(?, description),
                website = COALESCE(?, website),
                linkedin_url = COALESCE(?, linkedin_url),
                valuation_usd = COALESCE(?, valuation_usd),
                updated_at = datetime('now')
            WHERE id = ?
        """, (
            record.funding_inr, record.employee_count,
            record.description, record.website,
            record.linkedin_url, record.valuation_usd,
            entity_id,
        ))

        # Update R-Tree if coordinates changed
        self._update_rtree(conn, entity_id, record)

    def _insert_rtree(self, conn: sqlite3.Connection, entity_id: int,
                      record: TransformedRecord):
        """Insert spatial index entry for the entity."""
        conn.execute("""
            INSERT OR REPLACE INTO entities_rtree (id, min_lng, max_lng, min_lat, max_lat)
            VALUES (?, ?, ?, ?, ?)
        """, (
            entity_id,
            record.longitude, record.longitude,
            record.latitude, record.latitude,
        ))

    def _update_rtree(self, conn: sqlite3.Connection, entity_id: int,
                      record: TransformedRecord):
        """Update spatial index for an existing entity."""
        conn.execute("""
            UPDATE entities_rtree SET
                min_lng = ?, max_lng = ?, min_lat = ?, max_lat = ?
            WHERE id = ?
        """, (
            record.longitude, record.longitude,
            record.latitude, record.latitude,
            entity_id,
        ))

    def rebuild_rtree(self):
        """Rebuild R-Tree index from scratch (maintenance operation)."""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM entities_rtree")
            conn.execute("""
                INSERT INTO entities_rtree (id, min_lng, max_lng, min_lat, max_lat)
                SELECT id, longitude, longitude, latitude, latitude
                FROM entities WHERE is_active = 1
            """)
            conn.commit()
            logger.info("R-Tree index rebuilt successfully")
        finally:
            conn.close()

    def get_stats(self) -> dict:
        """Get current database statistics."""
        conn = self._get_conn()
        try:
            total = conn.execute("SELECT COUNT(*) FROM entities WHERE is_active=1").fetchone()[0]
            by_type = dict(conn.execute(
                "SELECT entity_type, COUNT(*) FROM entities WHERE is_active=1 GROUP BY entity_type"
            ).fetchall())
            by_source = conn.execute(
                "SELECT data_sources, COUNT(*) FROM entities WHERE is_active=1 GROUP BY data_sources"
            ).fetchall()
            return {
                "total_entities": total,
                "by_type": by_type,
                "by_source": [dict(r) for r in by_source],
            }
        finally:
            conn.close()

    def deactivate_stale(self, days: int = 90):
        """Mark entities not updated in N days as inactive."""
        conn = self._get_conn()
        try:
            result = conn.execute("""
                UPDATE entities SET is_active = 0
                WHERE updated_at < datetime('now', ? || ' days')
                AND is_active = 1
            """, (f"-{days}",))
            conn.commit()
            logger.info(f"Deactivated {result.rowcount} stale entities (>{days} days)")
        finally:
            conn.close()
