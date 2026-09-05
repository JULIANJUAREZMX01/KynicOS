import asyncio
from pathlib import Path
from typing import List, Dict

from app.config import Settings
from app.utils import get_logger

logger = get_logger(__name__)


class LogSentinel:
    """Proactive log monitor for KynicOS."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.watch_list: Dict[str, int] = {}
        self.is_running = False
        self._alert_tasks: List[asyncio.Task] = []
        self.add_watch("logs/kynikos.log")

    def add_watch(self, file_path: str):
        """Add a log file to the monitor list."""
        path = Path(file_path).resolve()
        if path.exists():
            self.watch_list[str(path)] = path.stat().st_size
            logger.info(f"🐕 Centinela vigilando: {file_path}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
            self.watch_list[str(path)] = 0
            logger.info(f"🐕 Centinela esperando archivo: {file_path}")

    async def run(self):
        """Monitor logs and dispatch configured alerts."""
        self.is_running = True
        from app.cloud.telegram_bot import send_alert
        from app.cloud.whatsapp_bridge import send_whatsapp_alert

        interval = max(1, self.settings.log_check_interval)
        logger.info(f"🐕 Centinela iniciado (Check interval: {interval}s)")

        while self.is_running:
            if not self.settings.sentinel_enabled:
                await asyncio.sleep(interval)
                continue

            for path_str, last_pos in list(self.watch_list.items()):
                try:
                    path = Path(path_str)
                    if not path.exists():
                        continue
                    current_size = path.stat().st_size
                    if current_size < last_pos:
                        self.watch_list[path_str] = 0
                        last_pos = 0
                    if current_size > last_pos:
                        with open(path, "r", encoding="utf-8", errors="ignore") as f:
                            f.seek(last_pos)
                            new_lines = f.readlines()
                        self.watch_list[path_str] = current_size

                        for line in new_lines:
                            if any(trigger in line.upper() for trigger in ("ERROR", "CRITICAL", "EXCEPTION", "FAILED")):
                                if self.settings.alert_on_failure:
                                    message = f"Fallo detectado en {path.name}:\n`{line.strip()[:200]}`"
                                    self._alert_tasks.extend([
                                        asyncio.create_task(send_alert(message, self.settings)),
                                        asyncio.create_task(send_whatsapp_alert(message, self.settings)),
                                    ])
                                if self.settings.auto_healing_enabled:
                                    logger.warning(
                                        "Auto-healing is enabled but no healing strategy is configured; alert only."
                                    )
                except Exception as e:
                    print(f"Centinela Error: {e}")

            self._alert_tasks = [task for task in self._alert_tasks if not task.done()]
            await asyncio.sleep(interval)

    def stop(self):
        """Stop monitoring and cancel pending alert tasks."""
        self.is_running = False
        for task in self._alert_tasks:
            if not task.done():
                task.cancel()
        self._alert_tasks.clear()
