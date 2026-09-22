import logging
import os

from app.config import get_settings

_configured_levels: set[str] = set()


def get_logger(name: str) -> logging.Logger:
    settings = get_settings()

    logger = logging.getLogger(name)

    # Configure the root app logger once; child loggers just propagate.
    if name != "app" and not name.startswith("app."):
        return logger

    if name in _configured_levels:
        return logger

    numeric_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(numeric_level)
    logger.propagate = False

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File logging is opt-in so writable ./logs is never a production
    # dependency (many container platforms ship a read-only filesystem).
    if settings.LOG_FILE:
        log_dir = os.path.dirname(settings.LOG_FILE)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(filename=settings.LOG_FILE, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    _configured_levels.add(name)
    return logger
