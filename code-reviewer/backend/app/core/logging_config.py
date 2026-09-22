"""
core/logging_config.py
=======================
Sets up consistent, structured console logging for the whole application.

Real production services never rely on `print()` — logging lets you control
verbosity per environment (verbose in development, quieter in production)
and is what your hosting platform (Docker, Kubernetes, systemd) will
actually capture and forward to log-aggregation tools.
"""

import logging
import sys


def configure_logging(environment: str) -> None:
    """
    Configure the root logger.

    Args:
        environment: "development" -> DEBUG-level, human-friendly format.
                     "production"  -> INFO-level, slightly more compact.
    """
    level = logging.DEBUG if environment == "development" else logging.INFO

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers = [handler]

    # Quiet down noisy third-party loggers so they don't drown out our own.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
