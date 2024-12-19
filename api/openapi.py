from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Optional
from enum import Enum

app = FastAPI()


class LagUnit(str, Enum):
    seconds = "seconds"
    minutes = "minutes"
    hours = "hours"
    days = "days"
    months = "months"
    years = "years"


class AssetAttribute(BaseModel):
    asset_id: int
    attribute_name: Optional[str] = None


class CorrelationRequest(BaseModel):
    assets: List[AssetAttribute]
    lags: Optional[List[Dict[LagUnit, int]]] = None


class CorrelateChildrenRequest(BaseModel):
    asset_id: int
    lag: Optional[Dict[LagUnit, int]] = None


class InDepthCorrelationRequest(BaseModel):
    assets: List[AssetAttribute]
    lags: Optional[List[Dict[LagUnit, int]]] = None


@app.post("/correlate")
def correlate_assets(request: CorrelationRequest):
    # Placeholder for correlation logic
    return {
        "assets": request.assets,
        "lags": request.lags,
        "correlation": "To be implemented",
    }


@app.post("/correlate-children")
def correlate_asset_children(request: CorrelateChildrenRequest):
    # Placeholder for correlation logic for asset's children
    return {
        "asset_id": request.asset_id,
        "lag": request.lag,
        "correlation": "To be implemented",
    }


@app.post("/in-depth-correlation")
def in_depth_correlation(request: InDepthCorrelationRequest):
    # Placeholder for in-depth correlation logic
    return {
        "assets": request.assets,
        "lags": request.lags,
        "in_depth_correlation": "To be implemented",
    }
