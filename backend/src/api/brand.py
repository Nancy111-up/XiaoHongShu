import json

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.brand.repository import SQLBrandRepository
from src.brand.schemas import BrandProfileInput
from src.brand.service import BrandService
from src.db.models import BrandProfile


def build_router(sessions: async_sessionmaker[AsyncSession]) -> APIRouter:
    router = APIRouter(tags=["brand"])

    @router.get("/brand-profile")
    async def get_brand_profile() -> object:
        async with sessions() as session:
            profile = await session.scalar(
                select(BrandProfile).order_by(BrandProfile.version.desc()).limit(1)
            )
        if profile is None:
            return {"status": "not_configured"}
        return {"version": profile.version, "profile": json.loads(profile.profile_json)}

    @router.put("/brand-profile")
    async def update_brand_profile(payload: BrandProfileInput) -> object:
        saved = await BrandService(SQLBrandRepository(sessions)).update(payload)
        return saved.model_dump(by_alias=True)

    return router
