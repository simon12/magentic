import logging
import os
from functools import lru_cache

try:
    import logfire_api
except ImportError:  # pragma: no cover
    logfire_api = None  # type: ignore[assignment]

try:
    import sentry_sdk
except ImportError:  # pragma: no cover
    sentry_sdk = None  # type: ignore[assignment]

logger = logging.getLogger("magentic")
# Set default log level to WARNING so INFO logs must be explicitly enabled
if logger.level == logging.NOTSET:
    logger.setLevel(logging.WARNING)

# Initialize Logfire if available
logfire = None
if logfire_api is not None:
    logfire = logfire_api.Logfire(otel_scope="magentic")  # TODO: Pass version here too


@lru_cache(maxsize=1)
def initialize_sentry() -> None:
    """Initialize Sentry SDK if SENTRY_DSN is set."""
    if sentry_sdk is None:
        logger.debug("sentry-sdk not installed. Sentry integration disabled.")
        return

    sentry_dsn = os.getenv("SENTRY_DSN")
    if not sentry_dsn:
        logger.debug("SENTRY_DSN not set. Sentry integration disabled.")
        return

    # Initialize Sentry with appropriate configuration
    sentry_sdk.init(
        dsn=sentry_dsn,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
        enable_tracing=True,
        # Don't send performance traces for now, focus on errors
        traces_sampler=None,
    )
    logger.debug("Sentry initialized successfully")


def capture_exception_for_sentry(error: BaseException, **context: str) -> None:
    """Capture an exception in Sentry with additional context if available."""
    if sentry_sdk is None:
        return

    # Lazy initialize Sentry on first error
    initialize_sentry()

    # Add context to the scope before capturing
    if context:
        with sentry_sdk.push_scope() as scope:
            for key, value in context.items():
                scope.set_context("magentic", {key: value})
            sentry_sdk.capture_exception(error)
    else:
        sentry_sdk.capture_exception(error)
