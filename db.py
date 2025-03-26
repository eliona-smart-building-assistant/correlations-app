
from psycopg2 import OperationalError, connect

import logging
import os

logger = logging.getLogger(__name__)
DATABASE_URL = os.getenv("CONNECTION_STRING")



def create_schema_and_table():
    try:
        connection = connect(DATABASE_URL)
        cursor = connection.cursor()
        create_schema_query = "CREATE SCHEMA IF NOT EXISTS correlations;"
        cursor.execute(create_schema_query)
        create_table_query = """
        CREATE TABLE IF NOT EXISTS correlations.requests (
            id SERIAL PRIMARY KEY,  
            assets JSONB NOT NULL,
            lags JSONB,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            to_email VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        cursor.execute(create_table_query)
        connection.commit()
        cursor.close()
        connection.close()

    except OperationalError as e:
        logger.info(f"Connection failed: {e}")
        if connection:
            connection.close()
