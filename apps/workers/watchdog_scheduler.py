import asyncio
import logging
from datetime import datetime
from packages.core.config import settings
from apps.workers.ingestion_worker import IngestionWorker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("WatchdogScheduler")

class WatchdogScheduler:
    """
    Continuous background loop that monitors Ethara, Amazon, and ATS boards.
    """
    _running = False

    @classmethod
    async def start(cls):
        cls._running = True
        logger.info("📡 Placement Watchdog Scheduler started.")

        # Run initial acquisition pass on startup
        try:
            logger.info("Executing initial source acquisition pass...")
            res = await IngestionWorker.run_acquisition_cycle()
            logger.info(f"Initial acquisition complete: {res['new_opportunities_created']} new, {res['duplicates_skipped']} duplicates skipped.")
        except Exception as e:
            logger.error(f"Error during initial acquisition: {e}")

        # Continuous loop
        while cls._running:
            try:
                # Interval sleep (default 15 minutes or test interval)
                interval = min(settings.ETHARA_CHECK_INTERVAL_MINUTES, 15) * 60
                await asyncio.sleep(interval)
                logger.info("⏰ Triggering scheduled watchdog scan cycle...")
                res = await IngestionWorker.run_acquisition_cycle()
                logger.info(f"Scan complete: {res['new_opportunities_created']} new jobs found.")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Watchdog scheduler error: {e}")
                await asyncio.sleep(60)

    @classmethod
    def stop(cls):
        cls._running = False
        logger.info("🛑 Watchdog Scheduler stopped.")

if __name__ == "__main__":
    asyncio.run(WatchdogScheduler.start())

