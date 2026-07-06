"""
Bharat Tech Atlas — ETL Pipeline Orchestrator
Coordinates Extract → Transform → Load with scheduling, logging, and error recovery.
"""
import asyncio
import logging
import time
from typing import Dict, Optional
from datetime import datetime

from .extract import ETLExtractor, RawStartupRecord
from .transform import ETLTransformer, Geocoder
from .load import ETLLoader

logger = logging.getLogger(__name__)


class ETLPipeline:
    """
    Full ETL pipeline orchestrator.

    Usage:
        config = {
            "db_path": "./data/bharattechatlas.db",
            "dpiit_api_key": "...",
            "tracxn_token": "...",
            "crunchbase_key": "...",
            "geocoder_api_key": "...",  # Optional: for Nominatim/Google
        }
        pipeline = ETLPipeline(config)
        result = await pipeline.run()
    """

    def __init__(self, config: Dict):
        self.config = config
        self.extractor = ETLExtractor(config)
        self.transformer = ETLTransformer(
            geocoder=Geocoder(api_key=config.get("geocoder_api_key"))
        )
        self.loader = ETLLoader(db_path=config.get("db_path", "./data/bharattechatlas.db"))
        self._run_history = []

    async def run(self, sources: Optional[list] = None) -> Dict:
        """
        Execute the full ETL pipeline.

        Args:
            sources: Optional list of sources to extract from.
                     Default: all sources ['dpiit', 'tracxn', 'crunchbase']

        Returns:
            Pipeline run report with stats and timing.
        """
        run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        report = {
            "run_id": run_id,
            "started_at": datetime.utcnow().isoformat(),
            "status": "running",
            "extract": {},
            "transform": {},
            "load": {},
            "errors": [],
        }

        logger.info(f"═══ ETL Pipeline Run {run_id} ═══")

        try:
            # ─── EXTRACT ─────────────────────────────────────────────────
            t0 = time.time()
            logger.info("Phase 1/3: EXTRACT — Fetching from data sources...")

            raw_records = await self.extractor.extract_all()

            report["extract"] = {
                "records": len(raw_records),
                "duration_sec": round(time.time() - t0, 2),
                "sources": self._count_by_source(raw_records),
            }
            logger.info(f"  ✓ Extracted {len(raw_records)} records in {report['extract']['duration_sec']}s")

            # ─── TRANSFORM ───────────────────────────────────────────────
            t1 = time.time()
            logger.info("Phase 2/3: TRANSFORM — Cleaning, normalizing, geocoding...")

            transformed_records = self.transformer.transform_all(raw_records)

            report["transform"] = {
                "input_records": len(raw_records),
                "output_records": len(transformed_records),
                "deduplication_rate": round(
                    1 - len(transformed_records) / max(len(raw_records), 1), 3
                ),
                "duration_sec": round(time.time() - t1, 2),
            }
            logger.info(f"  ✓ Transformed {len(transformed_records)} records in {report['transform']['duration_sec']}s")

            # ─── LOAD ────────────────────────────────────────────────────
            t2 = time.time()
            logger.info("Phase 3/3: LOAD — Writing to spatial database...")

            load_stats = self.loader.load_all(transformed_records)

            report["load"] = {
                **load_stats,
                "duration_sec": round(time.time() - t2, 2),
            }
            logger.info(f"  ✓ Loaded: {load_stats} in {report['load']['duration_sec']}s")

            # ─── FINALIZE ────────────────────────────────────────────────
            report["status"] = "success"
            report["completed_at"] = datetime.utcnow().isoformat()
            report["total_duration_sec"] = round(time.time() - t0, 2)

        except Exception as e:
            report["status"] = "failed"
            report["errors"].append(str(e))
            logger.error(f"Pipeline failed: {e}")

        self._run_history.append(report)
        logger.info(f"═══ ETL Pipeline {report['status'].upper()} ({report.get('total_duration_sec', 0)}s) ═══")
        return report

    async def run_incremental(self, since_hours: int = 24) -> Dict:
        """
        Run incremental ETL — only fetch records updated in the last N hours.
        More efficient for scheduled runs (e.g., daily cron).
        """
        logger.info(f"Running incremental ETL (last {since_hours}h)...")
        # In production, pass date filters to extractors
        return await self.run()

    def _count_by_source(self, records: list) -> Dict[str, int]:
        """Count records by source."""
        counts = {}
        for r in records:
            if hasattr(r, 'source'):
                counts[r.source] = counts.get(r.source, 0) + 1
        return counts

    def get_run_history(self) -> list:
        """Get history of pipeline runs."""
        return self._run_history

    def get_db_stats(self) -> Dict:
        """Get current database statistics."""
        return self.loader.get_stats()


class ETLScheduler:
    """
    Schedule ETL pipeline runs using cron-like patterns.
    Supports: full daily runs, incremental hourly updates.

    In production, use with:
    - APScheduler for in-process scheduling
    - Celery + Redis for distributed task queues
    - GitHub Actions / cron for external scheduling
    """

    def __init__(self, pipeline: ETLPipeline):
        self.pipeline = pipeline
        self._running = False

    async def start(self, full_interval_hours: int = 24,
                    incremental_interval_hours: int = 6):
        """
        Start the scheduler loop.
        - Full ETL every `full_interval_hours`
        - Incremental every `incremental_interval_hours`
        """
        self._running = True
        last_full_run = 0

        while self._running:
            now = time.time()
            hours_since_full = (now - last_full_run) / 3600

            if hours_since_full >= full_interval_hours:
                logger.info("Scheduler: Running FULL ETL pipeline")
                await self.pipeline.run()
                last_full_run = now
            else:
                logger.info("Scheduler: Running INCREMENTAL ETL")
                await self.pipeline.run_incremental(
                    since_hours=incremental_interval_hours
                )

            # Sleep until next run
            await asyncio.sleep(incremental_interval_hours * 3600)

    def stop(self):
        """Stop the scheduler."""
        self._running = False
        logger.info("ETL Scheduler stopped")
