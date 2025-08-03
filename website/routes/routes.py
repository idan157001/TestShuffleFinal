# routes/routes.py

from fastapi import APIRouter
from website.routes.main import router as main_router
from .auth import router as auth_router

router = APIRouter()


# Include auth routes with /auth prefix
router.include_router(auth_router, prefix="/auth", tags=["auth"])

# Include main routes (home, dashboard, etc.) without prefix
router.include_router(main_router)
