from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Optional
from enum import Enum
from datetime import datetime

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
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class CorrelateChildrenRequest(BaseModel):
    asset_id: int
    lag: Optional[Dict[LagUnit, int]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class InDepthCorrelationRequest(BaseModel):
    assets: List[AssetAttribute]
    lags: Optional[List[Dict[LagUnit, int]]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class CorrelationResult(BaseModel):
    attribute_pair: List[str]
    lag_correlations: Dict[LagUnit, float]
    best_correlation: float
    best_lag: LagUnit


@app.post("/correlate")
def correlate_assets(request: CorrelationRequest):
    end_time = request.end_time or datetime.now()
    # Placeholder for correlation logic
    return {
        "assets": request.assets,
        "lags": request.lags,
        "start_time": request.start_time,
        "end_time": end_time,
        "correlation": "To be implemented",
    }


@app.post("/correlate-children")
def correlate_asset_children(request: CorrelateChildrenRequest):
    end_time = request.end_time or datetime.now()
    # Placeholder for correlation logic for asset's children
    return {
        "asset_id": request.asset_id,
        "lag": request.lag,
        "start_time": request.start_time,
        "end_time": end_time,
        "correlation": "To be implemented",
    }


@app.post("/in-depth-correlation")
def in_depth_correlation(request: InDepthCorrelationRequest):
    end_time = request.end_time or datetime.now()
    # Placeholder for in-depth correlation logic
    return {
        "assets": request.assets,
        "lags": request.lags,
        "start_time": request.start_time,
        "end_time": end_time,
        "in_depth_correlation": "To be implemented",
    }
