from fastapi import FastAPI, HTTPException

from datetime import datetime
import pytz
import yaml
from api.models import CorrelationRequest, CorrelateChildrenRequest, AssetAttribute
from api.correlation import get_data, compute_correlation
from api.plot_correlation import (
    create_best_correlation_heatmap,
    in_depth_plot_scatter,
    plot_lag_correlations,
)
from get_trend_data import get_all_asset_children


# Create the FastAPI app instance
app = FastAPI(
    title="Correlation App API",
    description="API to manage and query correlations between assets.",
    version="1.0.0",
    openapi_url="/v1/version/openapi.json",
    openapi_version="3.1.0",
)

# Load custom OpenAPI schema
with open("openapi.yaml", "r") as f:
    openapi_yaml = yaml.safe_load(f)


def custom_openapi():
    app.openapi_schema = openapi_yaml
    return app.openapi_schema


app.openapi = custom_openapi


# Define endpoints
@app.post("/v1/correlate")
def correlate_assets(request: CorrelationRequest):
    end_time = request.end_time or datetime.now()
    dataframes = get_data(request)
    correlations = compute_correlation(dataframes, request)
    create_best_correlation_heatmap(correlations)
    return {
        "assets": request.assets,
        "lags": request.lags,
        "start_time": request.start_time,
        "end_time": end_time,
        "correlation": correlations,
    }


@app.post("/v1/correlate-children")
def correlate_asset_children(request: CorrelateChildrenRequest):
    end_time = request.end_time or datetime.now()
    child_asset_ids = get_all_asset_children(request.asset_id)
    print(f"Found {len(child_asset_ids)} children for asset {request.asset_id}")
    correlation_request = CorrelationRequest(
        assets=child_asset_ids,
        lags=request.lags,
        start_time=request.start_time,
        end_time=request.end_time,
    )

    correlations = correlate_assets(correlation_request)

    return {
        "assets": child_asset_ids,
        "lags": request.lags,
        "start_time": request.start_time,
        "end_time": end_time,
        "correlation": correlations,
    }


@app.post("/v1/in-depth-correlation")
def in_depth_correlation(request: CorrelationRequest):
    """
    1) Fetch data for exactly two assets/attributes.
    2) Compute correlation (including lags).
    3) Plot the lag correlation lines.
    4) Create and return a scatter plot in Base64 form.
    """
    if len(request.assets) != 2:
        raise HTTPException(status_code=400, detail="Exactly two assets are required.")

    # 1) Fetch data
    df_infos = get_data(request)
    if len(df_infos) != 2:
        raise HTTPException(
            status_code=400,
            detail="Could not retrieve data for both assets/attributes. Check logs.",
        )

    correlations = compute_correlation(df_infos, request)

    lag_plots = plot_lag_correlations(correlations, output_dir="/tmp/lag_plots")

    try:
        scatter_result = in_depth_plot_scatter(
            df_infos, output_file="/tmp/in_depth_scatter.png"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    end_time = request.end_time or datetime.now(pytz.timezone("Europe/Berlin"))

    return {
        "assets": request.assets,
        "lags": request.lags,
        "start_time": request.start_time,
        "end_time": end_time,
        "correlation": correlations,
        "scatter_plot": scatter_result["plot_base64_png"],
        "columns": scatter_result["columns"],
        "lag_plots": lag_plots,
    }
