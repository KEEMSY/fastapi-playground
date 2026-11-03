from fastapi import APIRouter
from src.common.constants import APIVersion

def create_versioned_router(
    prefix: str,
    version: APIVersion = APIVersion.V1,
    **kwargs
) -> APIRouter:
    return APIRouter(
        prefix=f"/api/{version}/{prefix}",
        **kwargs
    ) 