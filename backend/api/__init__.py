from fastapi import APIRouter

from .groups import router as groups_router
from .upload import router as upload_router
from .creatives import router as creatives_router
from .status import router as status_router
from .analytics import router as analytics_router

router = APIRouter()

router.include_router(groups_router)
router.include_router(upload_router)
router.include_router(creatives_router)
router.include_router(status_router)
router.include_router(analytics_router)
