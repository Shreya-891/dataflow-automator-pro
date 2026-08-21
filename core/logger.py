"""
DataFlow Automator Pro - Structured Logging System
Supports colored console output, rotating log files, and an in-memory queue for real-time UI log streaming.
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from collections import deque
import threading

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
DEFAULT_LOG_FILE = os.path.join(LOG_DIR, "automation.log")

# In-memory log buffer for real-time UI consumption (max 200 entries)
_LOG_BUFFER = deque(maxlen=200)
_BUFFER_LOCK = threading.Lock()


class UILogHandler(logging.Handler):
    """Custom logging handler to keep in-memory logs for Web UI monitoring."""
    def emit(self, record):
        try:
            log_entry = {
                "timestamp": datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S"),
                "level": record.levelname,
                "module": record.name,
                "message": record.getMessage()
            }
            with _BUFFER_LOCK:
                _LOG_BUFFER.append(log_entry)
        except Exception:
            self.handleError(record)


def get_ui_logs(limit: int = 50):
    """Retrieve the most recent log entries from the in-memory buffer."""
    with _BUFFER_LOCK:
        logs = list(_LOG_BUFFER)
    return logs[-limit:]


def clear_ui_logs():
    """Clear in-memory logs."""
    with _BUFFER_LOCK:
        _LOG_BUFFER.clear()


class ColoredFormatter(logging.Formatter):
    """ANSI colored console formatter for terminal logs."""
    COLORS = {
        logging.DEBUG: "\033[36m",    # Cyan
        logging.INFO: "\033[32m",     # Green
        logging.WARNING: "\033[33m",  # Yellow
        logging.ERROR: "\033[31m",    # Red
        logging.CRITICAL: "\033[35m"  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelno, self.RESET)
        record.levelname_color = f"{color}{record.levelname:<8}{self.RESET}"
        formatter = logging.Formatter(
            f"%(asctime)s | %(levelname_color)s | [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        return formatter.format(record)


def setup_logger(name: str = "DataFlowAutomator", log_file: str = DEFAULT_LOG_FILE, level: int = logging.INFO) -> logging.Logger:
    """
    Configures and returns a logger instance with console, file, and in-memory UI handlers.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        # 1. Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(ColoredFormatter())
        logger.addHandler(console_handler)

        # 2. Rotating File Handler (max 5MB per file, up to 5 backups)
        file_handler = RotatingFileHandler(
            log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # 3. UI In-Memory Handler
        ui_handler = UILogHandler()
        ui_handler.setLevel(level)
        logger.addHandler(ui_handler)

    return logger

# Global default logger
logger = setup_logger()
