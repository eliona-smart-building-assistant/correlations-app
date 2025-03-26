import os
import uvicorn
from register_app import Initialize
from db import create_schema_and_table
import logging
logger = logging.getLogger(__name__)


def start_api():
    port = int(os.getenv("API_SERVER_PORT", 3000))
    uvicorn.run("api.openapi:app", host="0.0.0.0", port=port)
    
create_schema_and_table()
logger.info("Database schema and table created")
Initialize()
logger.info("App initialized")
logger.info("Starting API server")
start_api()
