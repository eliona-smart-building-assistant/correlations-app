import pandas as pd
import numpy as np
from datetime import timedelta
import eliona.api_client2
from eliona.api_client2.rest import ApiException
from eliona.api_client2.api.data_api import DataApi
import os
import logging
import pytz
from datetime import datetime

# Initialize the logger
logger = logging.getLogger(__name__)
# Set up configuration for the Eliona API
configuration = eliona.api_client2.Configuration(host=os.getenv("API_ENDPOINT"))
configuration.api_key["ApiKeyAuth"] = os.getenv("API_TOKEN")

# Create an instance of the API client
api_client = eliona.api_client2.ApiClient(configuration)
data_api = DataApi(api_client)


def get_trend_data(asset_id, start_date, end_date):
    asset_id = int(asset_id)
    from_date = start_date.isoformat()
    to_date = end_date.isoformat()
    try:
        logger.info(f"Fetching data for asset {asset_id} from {from_date} to {to_date}")
        result = data_api.get_data_trends(
            from_date=from_date,
            to_date=to_date,
            asset_id=asset_id,
            data_subtype="input",
        )
        logger.info(f"Received {len(result)} data points")
        return result
    except ApiException as e:
        logger.info(f"Exception when calling DataApi->get_data_trends: {e}")
        return None


def fetch_data_in_chunks(asset_id, start_date, end_date):
    all_data = []
    current_start = start_date
    while current_start < end_date:
        current_end = min(current_start + timedelta(days=5), end_date)
        data_chunk = get_trend_data(asset_id, current_start, current_end)
        if data_chunk:
            all_data.extend(data_chunk)
        current_start = current_end + timedelta(seconds=1)
    return all_data


def convert_to_pandas(data):
    # Dictionary to hold the rows, using the timestamp as the key
    formatted_data = {}

    for entry in data:
        # Extract timestamp and data
        timestamp = entry.timestamp
        data_dict = entry.data

        # If this timestamp already exists, update the existing row
        if timestamp in formatted_data:
            formatted_data[timestamp].update(data_dict)
        else:
            # Create a new row for this timestamp
            formatted_data[timestamp] = data_dict

    # Convert the dictionary to a pandas DataFrame
    df = pd.DataFrame.from_dict(formatted_data, orient="index")

    # Set the index (timestamp) as a proper datetime index
    df.index = pd.to_datetime(df.index, utc=True)

    # Convert the index to the desired timezone (e.g., Europe/Berlin)
    df.index = df.index.tz_convert("Europe/Berlin")

    # **Optional: Sort the DataFrame by index (timestamp)**
    df.sort_index(inplace=True)

    # Reset index to have 'timestamp' as a column
    df.reset_index(inplace=True)
    df.rename(columns={"index": "timestamp"}, inplace=True)

    return df


def fetch_pandas_data(
    asset_id,
    start_date,
    end_date,
):
    # Fetch all data without filtering by attributes
    print(f"Fetching data for asset {asset_id} from {start_date} to {end_date}")
    data = fetch_data_in_chunks(asset_id, start_date, end_date)

    # Convert data to pandas DataFrame
    df = convert_to_pandas(data)

    return df
