import logging

from api import router
from core import lifespan
from fastapi import FastAPI


class StatusFilter(logging.Filter):
    def filter(self, record):
        if hasattr(record, 'args') and record.args and len(record.args) >= 5:  # noqa: PLR2004
            method = record.args[1]
            path = record.args[2]
            status_code = record.args[4]
            if method == "GET" and path.startswith("/status/") and status_code == 200:  # noqa: PLR2004
                return False
        return True

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

uvicorn_access_logger = logging.getLogger("uvicorn.access")
if uvicorn_access_logger:
    uvicorn_access_logger.addFilter(StatusFilter())
    logger.info("StatusFilter applied to uvicorn.access logger.")

app = FastAPI(title="Creative Classification API", lifespan=lifespan)

logger.info("Подключение роутеров...")

app.include_router(router)

logger.info("Роутеры подключены. Список маршрутов:")
for route in app.routes:
    if hasattr(route, "path"):
        method = getattr(route, "methods", "UNKNOWN")
        logger.info(f"  {method} {route.path} → {route.name}")
