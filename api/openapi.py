from fastapi import FastAPI, HTTPException, Depends

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
from api.get_trend_data import get_all_asset_children
from api.pdf_template import create_pdf
from fastapi.responses import FileResponse
from api.sendEmail import send_evaluation_report_as_mail
import os
from sqlalchemy import (
    MetaData,
    Table,
    create_engine,
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session


DATABASE_URL = os.getenv("CONNECTION_STRING")
db_url_sql = DATABASE_URL.replace("postgres", "postgresql")
engine = create_engine(db_url_sql)
metadata = MetaData()
CorrelationRequestTable = Table(
    "requests", metadata, autoload_with=engine, schema="correlations"
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
  
def save_request_to_db(db: Session, request: CorrelationRequest):
    try:
        db.execute(
            CorrelationRequestTable.insert().values(
                assets=[asset.dict() for asset in request.assets],  # Convert assets to JSON
                lags=request.lags,  # Lags as JSON
                start_time=request.start_time,
                end_time=request.end_time,
                to_email=request.to_email,
            )
        )
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
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

@app.post("/v1/create-correlation")
def create_correlation(request: CorrelationRequest, db: Session = Depends(get_db)):
    """
    Save a correlation request to the database.
    """
    try:
        # Insert the request into the database
        db.execute(
            CorrelationRequestTable.insert().values(
                assets=[asset.model_dump() for asset in request.assets],  # Convert assets to JSON
                lags=request.lags,  # Lags as JSON
                start_time=request.start_time,
                end_time=request.end_time,
                to_email=request.to_email,
            )
        )
        db.commit()
        return {"message": "Correlation request saved successfully."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save correlation request: {str(e)}")

@app.put("/v1/update-correlation/{correlation_id}")
def update_correlation(
    correlation_id: int, request: CorrelationRequest, db: Session = Depends(get_db)
):
    """
    Update an existing correlation request in the database by its ID.
    """
    try:
        # Check if the correlation request exists
        query = db.execute(
            CorrelationRequestTable.select().where(CorrelationRequestTable.c.id == correlation_id)
        )
        result = query.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Correlation request not found.")

        # Update the correlation request
        db.execute(
            CorrelationRequestTable.update()
            .where(CorrelationRequestTable.c.id == correlation_id)
            .values(
                assets=[asset.dict() for asset in request.assets],  # Convert assets to JSON
                lags=request.lags,  # Lags as JSON
                start_time=request.start_time,
                end_time=request.end_time,
                to_email=request.to_email,
            )
        )
        db.commit()
        return {"message": "Correlation request updated successfully."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update correlation request: {str(e)}")
    
@app.get("/v1/get-correlation/{correlation_id}")
def get_correlation(correlation_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a correlation request from the database by its ID.
    """
    try:
        # Query the database for the correlation request
        query = db.execute(
            CorrelationRequestTable.select().where(CorrelationRequestTable.c.id == correlation_id)
        )
        result = query.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Correlation request not found.")
        
        # Convert the result to a dictionary
        correlation_request = {
            "id": result.id,
            "assets": result.assets,
            "lags": result.lags,
            "start_time": result.start_time,
            "end_time": result.end_time,
            "to_email": result.to_email,
            "created_at": result.created_at,
        }
        return correlation_request
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve correlation request: {str(e)}")
    
@app.post("/v1/correlate/{correlation_id}")
def correlate_assets(correlation_id: int, db: Session = Depends(get_db)):
    """
    Fetch correlation request by ID and process it.
    """
    # Retrieve the correlation request from the database
    query = db.execute(
        CorrelationRequestTable.select().where(CorrelationRequestTable.c.id == correlation_id)
    )
    result = query.fetchone()
    if not result:
        raise HTTPException(status_code=404, detail="Correlation request not found.")

    # Convert the result to a dictionary
    correlation_request = {
        "assets": result.assets,
        "lags": result.lags,
        "start_time": result.start_time,
        "end_time": result.end_time,
        "to_email": result.to_email,
    }

    # Process the correlation request
    end_time = correlation_request["end_time"] or datetime.now()
    dataframes = get_data(correlation_request)
    correlations = compute_correlation(dataframes, correlation_request)
    create_best_correlation_heatmap(correlations)

    include_heatmap: bool = True
    include_scatter: bool = False
    include_lag_plots: bool = False
    include_details: bool = True

    pdf_file_path = "/tmp/correlation_report.pdf"
    create_pdf(
        correlation_request["start_time"],
        correlation_request["end_time"],
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
    if correlation_request["to_email"]:
        send_evaluation_report_as_mail(pdf_file_path, correlation_request["to_email"])
    return {
        "assets": correlation_request["assets"],
        "lags": correlation_request["lags"],
        "start_time": correlation_request["start_time"],
        "end_time": end_time,
        "correlation": correlations,
        "report_html": html_content,
    }

@app.post("/v1/correlate-children/{correlation_id}")
def correlate_asset_children(correlation_id: int, db: Session = Depends(get_db)):
    """
    Fetch correlation request by ID, retrieve child assets, and process it.
    """
    # Retrieve the correlation request from the database
    query = db.execute(
        CorrelationRequestTable.select().where(CorrelationRequestTable.c.id == correlation_id)
    )
    result = query.fetchone()
    if not result:
        raise HTTPException(status_code=404, detail="Correlation request not found.")

    # Convert the result to a dictionary
    correlation_request = {
        "assets": result.assets,
        "lags": result.lags,
        "start_time": result.start_time,
        "end_time": result.end_time,
        "to_email": result.to_email,
    }

    # Retrieve child assets
    child_asset_ids = get_all_asset_children(correlation_request["assets"][0]["asset_id"])
    print(f"Found {len(child_asset_ids)} children for asset {correlation_request['assets'][0]['asset_id']}")
    assets = [
        AssetAttribute(asset_id=child_id.asset_id, diff=correlation_request["assets"][0].get("diff", False))
        for child_id in child_asset_ids
    ]

    # Update the correlation request with child assets
    correlation_request["assets"] = [asset.dict() for asset in assets]

    # Process the correlation request
    response = correlate_assets(correlation_id, db)
    correlations = response["correlation"]
    html_content = response["report_html"]

    return {
        "assets": child_asset_ids,
        "lags": correlation_request["lags"],
        "start_time": correlation_request["start_time"],
        "end_time": correlation_request["end_time"],
        "correlation": correlations,
        "report_html": html_content,
    }
    
@app.post("/v1/in-depth-correlation/{correlation_id}")
def in_depth_correlation(correlation_id: int, db: Session = Depends(get_db)):
    """
    Fetch correlation request by ID and process it for in-depth correlation.
    """
    # Retrieve the correlation request from the database
    query = db.execute(
        CorrelationRequestTable.select().where(CorrelationRequestTable.c.id == correlation_id)
    )
    result = query.fetchone()
    if not result:
        raise HTTPException(status_code=404, detail="Correlation request not found.")

    # Convert the result to a dictionary
    correlation_request = {
        "assets": result.assets,
        "lags": result.lags,
        "start_time": result.start_time,
        "end_time": result.end_time,
        "to_email": result.to_email,
    }

    if len(correlation_request["assets"]) != 2:
        raise HTTPException(status_code=400, detail="Exactly two assets are required.")

    # Process the correlation request
    df_infos = get_data(correlation_request)
    if len(df_infos) != 2:
        raise HTTPException(
            status_code=400,
            detail="Could not retrieve data for both assets/attributes. Check logs.",
        )

    correlations = compute_correlation(df_infos, correlation_request)

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
        correlation_request["start_time"],
        correlation_request["end_time"],
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

    if correlation_request["to_email"]:
        send_evaluation_report_as_mail(pdf_file_path, correlation_request["to_email"])
    return {
        "assets": correlation_request["assets"],
        "lags": correlation_request["lags"],
        "start_time": correlation_request["start_time"],
        "end_time": correlation_request["end_time"],
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
