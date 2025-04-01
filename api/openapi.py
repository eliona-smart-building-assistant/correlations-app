from fastapi import FastAPI, HTTPException, Depends

from datetime import datetime
import yaml
from api.models import CorrelationRequest, AssetAttribute,CorrelationCreateRequest
from api.correlation import get_data, compute_correlation

from api.get_trend_data import get_all_asset_children
import os
from sqlalchemy import (
    MetaData,
    Table,
    create_engine,
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session
from create_asset import create_asset_to_save_reports

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
    
def process_correlation(correlation_request_obj, db: Session):
    # If there's exactly one asset and no attribute defined, process children
    if len(correlation_request_obj.assets) == 1 and not correlation_request_obj.assets[0].attribute_name:
        child_asset_ids = get_all_asset_children(correlation_request_obj.assets[0].asset_id)
        print(f"Found {len(child_asset_ids)} children for asset {correlation_request_obj.assets[0].asset_id}")
        assets = [
            AssetAttribute(
                asset_id=child_id.asset_id,
                diff=correlation_request_obj.assets[0].diff     # use attribute access!
            )
            for child_id in child_asset_ids
        ]
        # Update assets attribute of the model (if needed, convert each to dict)
        correlation_request_obj.assets = [asset.model_dump() for asset in assets]
        return process_correlation(correlation_request_obj, db)
    else:
        dataframes = get_data(correlation_request_obj)
        correlations = compute_correlation(dataframes, correlation_request_obj)
        return correlations

def custom_openapi():
    app.openapi_schema = openapi_yaml
    return app.openapi_schema


app.openapi = custom_openapi
@app.post("/v1/create-correlation")
def create_correlation(request: CorrelationCreateRequest, db: Session = Depends(get_db)):
    """
    Save a correlation request to the database.
    """
    try:
        assets = [asset.model_dump() for asset in request.assets] if request.assets else []
        insert_stmt = (
            CorrelationRequestTable.insert()
            .values(
                name=request.name,
                assets=assets,
                lags=request.lags,
                start_time=request.start_time,
                end_time=request.end_time,
                to_email=request.to_email,
            )
            .returning(CorrelationRequestTable.c.id)
        )
        result = db.execute(insert_stmt)
        new_id = result.fetchone()[0]
        db.commit()
        
        create_asset_to_save_reports(
            project_id=request.project_id, correlation_id=new_id
        )
        return {"message": "Correlation request saved successfully.", "id": new_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save correlation request: {str(e)}")
    
@app.get("/v1/get-all-correlations")
def get_all_correlations(db: Session = Depends(get_db)):
    """
    Retrieve all correlation requests from the database.
    """
    try:
        # Query the database for all correlation requests
        query = db.execute(CorrelationRequestTable.select())
        results = query.fetchall()

        # Convert the results to a list of dictionaries
        correlations = [
            {
                "id": result.id,
                "name": result.name,
                "assets": result.assets,
                "lags": result.lags,
                "start_time": result.start_time,
                "end_time": result.end_time,
                "to_email": result.to_email,
                "created_at": result.created_at,
            }
            for result in results
        ]
        return correlations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve correlations: {str(e)}")
    
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
        
        # Convert assets to JSON if provided, else use empty list
        assets = [asset.model_dump() for asset in request.assets] if request.assets else []
        
        # Update the correlation request
        db.execute(
            CorrelationRequestTable.update()
            .where(CorrelationRequestTable.c.id == correlation_id)
            .values(
                name=request.name,
                assets=assets,
                lags=request.lags,
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
            "name" : result.name,
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
    # Retrieve the correlation request from the database
    query = db.execute(
        CorrelationRequestTable.select().where(CorrelationRequestTable.c.id == correlation_id)
    )
    result = query.fetchone()
    if not result:
        raise HTTPException(status_code=404, detail="Correlation request not found.")
    correlation_request_dict = {
        "name": result.name,
        "assets": result.assets,
        "lags": result.lags,
        "start_time": result.start_time,
        "end_time": result.end_time,
        "to_email": result.to_email,
    }
    correlation_request_obj = CorrelationRequest.model_validate(correlation_request_dict)
    correlations = process_correlation(correlation_request_obj, db)
    end_time = correlation_request_obj.end_time or datetime.now()
    return {
        "name": correlation_request_obj.name,
        "assets": correlation_request_obj.assets,
        "lags": correlation_request_obj.lags,
        "start_time": correlation_request_obj.start_time,
        "end_time": end_time,
        "correlation": correlations,
    }
    
@app.delete("/v1/delete-correlation/{correlation_id}")
def delete_correlation(correlation_id: int, db: Session = Depends(get_db)):
    """
    Delete a correlation request from the database by its ID.
    """
    try:
        # Check if the correlation request exists
        query = db.execute(
            CorrelationRequestTable.select().where(CorrelationRequestTable.c.id == correlation_id)
        )
        result = query.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Correlation request not found.")

        # Delete the correlation request
        db.execute(
            CorrelationRequestTable.delete().where(CorrelationRequestTable.c.id == correlation_id)
        )
        db.commit()
        return {"message": "Correlation request deleted successfully."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete correlation request: {str(e)}")
  