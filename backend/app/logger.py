"""Logging configuration using structlog with colored output for development."""

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor


def add_app_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add application context to log entries."""
    event_dict["app"] = "memoro"
    return event_dict


def setup_logging(log_level: str = "INFO", environment: str = "development") -> None:
    """
    Configure structlog with appropriate processors for the environment.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        environment: Environment name (development, production)
    """
    # Convert string log level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Common processors for all environments
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        add_app_context,
        structlog.processors.StackInfoRenderer(),
    ]

    if environment == "development":
        # Development: colored console output with key-value pairs
        processors: list[Processor] = shared_processors + [
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.rich_traceback,
            )
        ]
    else:
        # Production: JSON output for log aggregation
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=numeric_level,
    )

    # Set log level for uvicorn loggers
    logging.getLogger("uvicorn").setLevel(numeric_level)
    logging.getLogger("uvicorn.access").setLevel(numeric_level)
    logging.getLogger("uvicorn.error").setLevel(numeric_level)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)
