"""
EnterpriseIQ ML — Shared Logging Setup
Configures structlog for all ML services with Cloud Logging compatibility.
"""

from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(service_name: str, level: str = "INFO") -> None:
    """Call once at startup in each service's main.py."""

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_logger_name,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            # Cloud Logging expects JSON on stdout
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
    )

    # Tag every log with the service name
    structlog.contextvars.bind_contextvars(service=service_name)
