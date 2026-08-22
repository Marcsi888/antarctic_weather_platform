import logging
import sys

_LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"


def configure_logging(level: str) -> None:
    """Configure the root logger once, at application startup.

    Every other module should call `logging.getLogger(__name__)` and log
    through that, rather than configuring handlers of its own.
    """
    root = logging.getLogger()
    root.setLevel(level)

    # Clear any handlers from a previous call before adding a new one, so
    # calling this function more than once (as pytest does across test
    # modules that each spin up a FastAPI app) doesn't duplicate every
    # log line once per call.
    root.handlers.clear()

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT))
    root.addHandler(handler)

    # By default httpx logs every outgoing request at INFO level, including
    # the full URL. Our own AEMET client will log request lifecycle events
    # deliberately (see app/integrations/aemet), so httpx's automatic
    # logging would just duplicate that. Raising it to WARNING keeps
    # httpx's logs limited to things actually worth seeing, like retries
    # or connection errors.
    logging.getLogger("httpx").setLevel(logging.WARNING)
