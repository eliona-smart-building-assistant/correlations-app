from fastapi import FastAPI, HTTPException
from datetime import datetime
from api.models import (
    CorrelationRequest,
    CorrelateChildrenRequest,
)
from api.correlation import get_data, compute_correlation
from api.plot_correlation import (
    create_best_correlation_heatmap,
    in_depth_plot_scatter,
    plot_lag_correlations,
)
import pytz

app = FastAPI()


@app.post("/correlate")
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

    # 2) Compute correlation (including any lags) for these two DataFrameInfo
    correlations = compute_correlation(df_infos, request)
    # 'correlations' is a dict that includes "lag_details" for the single pair, e.g.:
    #  {
    #    "867_energy_costs and 867_Wirkleistung": {
    #      "best_correlation": 0.16,
    #      "best_lag": 3,
    #      "best_lag_unit": "hours",
    #      "lag_details": [
    #        {"lag_unit": "hours", "lag_step": -10, "correlation": 0.05}, ...
    #      ]
    #    }
    #  }

    # 3) Plot the lag correlation lines for that single pair
    #    This will create line plots in "lag_plots/" (by default) for each lag unit
    plot_lag_correlations(correlations, output_dir="lag_plots")

    # 4) Also create a scatter plot of the raw data to see direct x-y relationship
    #    (We re-use 'df_infos' -> 2 DataFrameInfo objects)
    try:
        scatter_result = in_depth_plot_scatter(
            df_infos, output_file="in_depth_scatter.png"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    end_time = request.end_time or datetime.now(pytz.timezone("Europe/Berlin"))

    return {
        "assets": request.assets,
        "start_time": request.start_time,
        "end_time": end_time,
        "best_correlation": scatter_result["correlation"],  # correlation from scatter
        "plot_base64_png": scatter_result["plot_base64_png"],  # scatter in Base64
        "lag_correlation_plots": "Saved in lag_plots/ directory",
        "detailed_correlations": correlations,  # full correlation details with lags
    }
