import asyncio
import os
from pathlib import Path
from typing import List, Dict
from app.config import Settings
from app.utils import get_logger

logger = get_logger(__name__)

class LogSentinel:
    """Proactive log monitor for KYNIKOS with Auto-Healing contracts"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.contract = settings.contract_settings
        self.watch_list: Dict[str, int] = {} # Path: last_position
        self.is_running = False
        self._alert_tasks: List[asyncio.Task] = []
        
        # Default logs to watch
        self.add_watch("logs/kynikos.log")

    def add_watch(self, file_path: str):
        """Add a log file to the monitor list"""
        path = Path(file_path).resolve()
        if path.exists():
            # Start from the end of the file
            self.watch_list[str(path)] = path.stat().st_size
            logger.info(f"🐕 Centinela vigilando: {file_path}")
        else:
            # If it doesn't exist, create it or wait for it
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
            self.watch_list[str(path)] = 0
            logger.info(f"🐕 Centinela esperando archivo: {file_path}")

    async def run(self):
        """Main loop for log monitoring"""
        self.is_running = True

        # Import here to avoid circular imports
        from app.cloud.telegram_bot import send_alert
        from app.cloud.whatsapp_bridge import send_whatsapp_alert
        
        # Use settings from ContractSettings
        interval = self.contract.log_check_interval
        logger.info(f"🐕 Centinela iniciado (Check interval: {interval}s)")

        while self.is_running:
            if not self.contract.sentinel_enabled:
                await asyncio.sleep(interval)
                continue

            for path_str, last_pos in list(self.watch_list.items()):
                try:
                    path = Path(path_str)
                    if not path.exists():
                        continue
                        
                    current_size = path.stat().st_size
                    
                    if current_size < last_pos:
                        # File was truncated/rotated
                        self.watch_list[path_str] = 0
                        continue
                        
                    if current_size > last_pos:
                        # New data!
                        with open(path, "r", encoding="utf-8", errors="ignore") as f:
                            f.seek(last_pos)
                            new_lines = f.readlines()
                            
                        self.watch_list[path_str] = current_size
                        
                        # Analyze lines
                        for line in new_lines:
                            if any(trigger in line.upper() for trigger in ["ERROR", "CRITICAL", "EXCEPTION", "FAILED"]):
                                # Send alert to all configured channels if enabled
                                if self.contract.alert_on_failure:
                                    message = f"Fallo detectado en {path.name}:\n`{line.strip()[:200]}`"
                                    # Non-blocking alerts — tasks are tracked for clean shutdown
                                    t1 = asyncio.create_task(send_alert(message, self.settings))
                                    t2 = asyncio.create_task(send_whatsapp_alert(message, self.settings))
                                    self._alert_tasks.extend([t1, t2])
                                
                                # Auto-healing logic could go here
                                if self.contract.auto_healing_enabled:
                                    # Placeholder for auto-healing logic
                                    pass
                except Exception as e:
                    # Don't use logger.error here as it might trigger a loop if watching kynikos.log
                    print(f"Centinela Error: {e}")
                    
            await asyncio.sleep(interval)

    def stop(self):
        self.is_running = False
        for task in self._alert_tasks:
            if not task.done():
                task.cancel()
        self._alert_tasks.clear()
