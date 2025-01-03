from fastapi import FastAPI, HTTPException

from datetime import datetime
import pytz
import yaml
from api.models import CorrelationRequest, CorrelateChildrenRequest
from api.correlation import get_data, compute_correlation
from api.plot_correlation import (
    create_best_correlation_heatmap,
    in_depth_plot_scatter,
    plot_lag_correlations,
)
from api.get_trend_data import get_all_asset_children
from api.pdf_template import create_pdf
from fastapi.responses import FileResponse
from api.sendEmail import send_evaluation_report_as_mail

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

    include_heatmap: bool = True
    include_scatter: bool = False
    include_lag_plots: bool = False
    include_details: bool = True

    pdf_file_path = "/tmp/correlation_report.pdf"
    create_pdf(
        request.start_time,
        request.end_time,
        pdf_file_path,
        correlations,
        include_heatmap,
        include_scatter,
        include_lag_plots,
        include_details,
    )
    html_file_path = "/tmp/report.html"
    with open(html_file_path, "r", encoding="utf-8") as html_file:
        html_content = html_file.read()
    if request.to_email:
        send_evaluation_report_as_mail(pdf_file_path, request.to_email)
    return {
        "assets": request.assets,
        "lags": request.lags,
        "start_time": request.start_time,
        "end_time": end_time,
        "correlation": correlations,
        "report_html": html_content,
    }


@app.post("/v1/correlate-children")
def correlate_asset_children(request: CorrelateChildrenRequest):
    child_asset_ids = get_all_asset_children(request.asset_id)
    print(f"Found {len(child_asset_ids)} children for asset {request.asset_id}")
    correlation_request = CorrelationRequest(
        assets=child_asset_ids,
        lags=request.lags,
        start_time=request.start_time,
        end_time=request.end_time,
        to_email=request.to_email,
    )

    response = correlate_assets(correlation_request)
    correlations = response["correlation"]
    html_content = response["report_html"]

    return {
        "assets": child_asset_ids,
        "lags": request.lags,
        "start_time": request.start_time,
        "end_time": request.end_time,
        "correlation": correlations,
        "report_html": html_content,
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

    lag_plot_filenames = plot_lag_correlations(
        correlations, output_dir="/tmp/lag_plots"
    )

    try:
        scatter_result = in_depth_plot_scatter(
            df_infos, output_file="/tmp/in_depth_scatter.png"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    include_heatmap: bool = False
    include_scatter: bool = True
    include_lag_plots: bool = True
    include_details: bool = True

    pdf_file_path = "/tmp/correlation_report.pdf"
    create_pdf(
        request.start_time,
        request.end_time,
        pdf_file_path,
        correlations,
        include_heatmap,
        include_scatter,
        include_lag_plots,
        include_details,
        lag_plot_filenames,
    )
    html_file_path = "/tmp/report.html"
    with open(html_file_path, "r", encoding="utf-8") as html_file:
        html_content = html_file.read()

    if request.to_email:
        send_evaluation_report_as_mail(pdf_file_path, request.to_email)
    return {
        "assets": request.assets,
        "lags": request.lags,
        "start_time": request.start_time,
        "end_time": request.end_time,
        "correlation": correlations,
        "scatter_result_columns": scatter_result["columns"],
        "report_html": html_content,
    }


@app.post("/v1/generate-report")
def generate_report(request: CorrelationRequest):
    """
    Generate a PDF report for the correlation analysis.
    """
    include_heatmap: bool = False
    include_scatter: bool = True
    include_lag_plots: bool = True
    include_details: bool = True
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

    lag_plot_filenames = plot_lag_correlations(
        correlations, output_dir="/tmp/lag_plots"
    )

    try:
        scatter_result = in_depth_plot_scatter(
            df_infos, output_file="/tmp/in_depth_scatter.png"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    end_time = request.end_time or datetime.now(pytz.timezone("Europe/Berlin"))

    pdf_file_path = "/tmp/correlation_report.pdf"
    create_pdf(
        request.start_time,
        request.end_time,
        pdf_file_path,
        correlations,
        include_heatmap,
        include_scatter,
        include_lag_plots,
        include_details,
        lag_plot_filenames,
    )
    if request.to_email:
        send_evaluation_report_as_mail(pdf_file_path, request.to_email)
    return FileResponse(
        pdf_file_path, media_type="application/pdf", filename="correlation_report.pdf"
    )
