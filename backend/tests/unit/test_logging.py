import logging

from app.core.logging import configure_logging


def test_configure_logging_sets_root_level() -> None:
    configure_logging("WARNING")

    assert logging.getLogger().level == logging.WARNING


def test_configure_logging_is_idempotent() -> None:
    configure_logging("INFO")
    configure_logging("INFO")

    assert len(logging.getLogger().handlers) == 1


def test_configure_logging_quiets_httpx() -> None:
    configure_logging("INFO")

    assert logging.getLogger("httpx").level == logging.WARNING
