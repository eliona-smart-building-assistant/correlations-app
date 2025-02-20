from pydantic import BaseModel
from typing import List, Dict, Optional
from enum import Enum
from datetime import datetime


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
    diff: Optional[bool] = False


class CorrelationRequest(BaseModel):
    assets: List[AssetAttribute]
    lags: Optional[List[Dict[LagUnit, int]]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    to_email: Optional[str] = None


class CorrelateChildrenRequest(BaseModel):
    asset_id: int
    diff: Optional[bool] = False
    lags: Optional[List[Dict[LagUnit, int]]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    to_email: Optional[str] = None


class CorrelationResult(BaseModel):
    attribute_pair: List[str]
    lag_correlations: Dict[LagUnit, float]
    best_correlation: float
    best_lag: LagUnit
