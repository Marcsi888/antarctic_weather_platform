import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    AemetAuthenticationError,
    AemetError,
    ApplicationError,
    PersistenceError,
    ValidationError,
)

logger = logging.getLogger(__name__)

# Ordered from most to least specific: AemetAuthenticationError is an
# AemetError subclass, so it must be checked before the general AemetError
# case or it would never be reached.
_STATUS_BY_EXCEPTION: list[tuple[type[ApplicationError], int]] = [
    (ValidationError, 400),
    (AemetAuthenticationError, 500),
    (AemetError, 502),
    (PersistenceError, 500),
]


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApplicationError)
    async def handle_application_error(request: Request, exc: ApplicationError) -> JSONResponse:
        status_code = 500
        for exception_type, mapped_status in _STATUS_BY_EXCEPTION:
            if isinstance(exc, exception_type):
                status_code = mapped_status
                break

        if status_code >= 500:
            # 5xx messages may name internal details (a table, a config
            # variable, an upstream URL) that shouldn't reach the caller;
            # the real detail goes to the server log only.
            logger.exception("Unhandled application error", exc_info=exc)
            detail = "An internal error occurred."
        else:
            logger.info("Request rejected: %s", exc)
            detail = str(exc)

        return JSONResponse(status_code=status_code, content={"detail": detail})
