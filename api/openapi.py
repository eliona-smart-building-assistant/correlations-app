from fastapi import FastAPI
from datetime import datetime
from api.models import (
    CorrelationRequest,
    CorrelateChildrenRequest,
)
from api.correlation import get_data

app = FastAPI()


@app.post("/correlate")
def correlate_assets(request: CorrelationRequest):
    end_time = request.end_time or datetime.now()
    get_data(request)
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
    return {
        "asset_id": request.asset_id,
        "lag": request.lag,
        "start_time": request.start_time,
        "end_time": end_time,
        "correlation": "To be implemented",
    }


@app.post("/in-depth-correlation")
def in_depth_correlation(request: CorrelationRequest):
    end_time = request.end_time or datetime.now()
    return {
        "assets": request.assets,
        "lags": request.lags,
        "start_time": request.start_time,
        "end_time": end_time,
        "in_depth_correlation": "To be implemented",
    }
