import logging

from api import router
from core import lifespan
from fastapi import FastAPI


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Creative Classification API", lifespan=lifespan)

logger.info("Подключение роутеров...")

app.include_router(router)

logger.info("Роутеры подключены. Список маршрутов:")
for route in app.routes:
    if hasattr(route, "path"):
        method = getattr(route, "methods", "UNKNOWN")
        logger.info(f"  {method} {route.path} → {route.name}")
