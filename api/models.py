from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Optional
from enum import Enum
from datetime import datetime
import pandas as pd


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
    lags: Optional[List[Dict[LagUnit, int]]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class CorrelationResult(BaseModel):
    attribute_pair: List[str]
    lag_correlations: Dict[LagUnit, float]
    best_correlation: float
    best_lag: LagUnit
