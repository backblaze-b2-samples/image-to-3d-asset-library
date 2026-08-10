import logging

# Sync `def` handlers on purpose (see runtime/files.py): the B2 calls are
# blocking boto3, so Starlette runs these in its threadpool and one slow bucket
# listing can't stall the event loop.
from fastapi import APIRouter, HTTPException

from app.service.assets import (
    AssetInputError,
    AssetNotFoundError,
    AssetStateError,
    asset_stats,
    create_asset,
    delete_asset,
    get_asset,
    list_assets,
    list_engines,
    regenerate_asset,
    update_asset,
)
from app.types import (
    Asset,
    AssetCreateRequest,
    AssetStats,
    AssetUpdateRequest,
    EngineInfo,
    RegenerateRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# SECURITY: like the file routes, these are intentionally UNAUTHENTICATED and
# bucket-wide (single-tenant demo stance — see docs/SECURITY.md). A multi-tenant
# clone must add auth AND scope the library prefix per user.


@router.post("/assets", response_model=Asset, status_code=201)
def create_asset_endpoint(req: AssetCreateRequest):
    try:
        return create_asset(req)
    except AssetInputError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None


@router.get("/assets", response_model=list[Asset])
def list_assets_endpoint():
    return list_assets()


@router.get("/assets/stats", response_model=AssetStats)
def asset_stats_endpoint():
    return asset_stats()


@router.get("/assets/engines", response_model=list[EngineInfo])
def list_engines_endpoint():
    return list_engines()


@router.get("/assets/{asset_id}", response_model=Asset)
def get_asset_endpoint(asset_id: str):
    try:
        return get_asset(asset_id)
    except AssetNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None


@router.patch("/assets/{asset_id}", response_model=Asset)
def update_asset_endpoint(asset_id: str, req: AssetUpdateRequest):
    try:
        return update_asset(asset_id, req)
    except AssetNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None


@router.delete("/assets/{asset_id}")
def delete_asset_endpoint(asset_id: str):
    try:
        deleted = delete_asset(asset_id)
    except AssetNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    logger.info("Asset deleted: id=%s objects=%d", asset_id, deleted)
    return {"deleted": True, "id": asset_id, "objects_removed": deleted}


@router.post("/assets/{asset_id}/regenerate", response_model=Asset)
def regenerate_asset_endpoint(asset_id: str, req: RegenerateRequest):
    try:
        return regenerate_asset(asset_id, req)
    except AssetNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    except AssetStateError as e:
        raise HTTPException(status_code=409, detail=e.detail) from None
    except AssetInputError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
