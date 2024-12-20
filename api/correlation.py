import numpy as np
import pandas as pd
from datetime import datetime
from get_trend_data import fetch_pandas_data
from api.models import CorrelationRequest, CorrelationResult, LagUnit
import pytz
from typing import Optional
from pydantic import BaseModel, ConfigDict


class DataFrameInfo(BaseModel):
    dataframe: pd.DataFrame
    frequency: Optional[str]
    data_size: int
    start_date: Optional[pd.Timestamp]
    end_date: Optional[pd.Timestamp]

    model_config = ConfigDict(arbitrary_types_allowed=True)


def get_data(request: CorrelationRequest):
    data_frames = []
    timezone = pytz.timezone("Europe/Berlin")  # Desired timezone

    # Convert start_time and end_time to the desired timezone
    start_time = request.start_time.astimezone(timezone) if request.start_time else None
    end_time = (
        request.end_time.astimezone(timezone)
        if request.end_time
        else datetime.now(timezone)
    )

    for asset in request.assets:
        df = fetch_pandas_data(asset.asset_id, start_time, end_time)

        # Convert the timestamp to the desired timezone (e.g., Europe/Berlin)
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert(
            "Europe/Berlin"
        )

        if asset.attribute_name:
            if asset.attribute_name in df.columns:
                df = df[["timestamp", asset.attribute_name]]
                df.set_index("timestamp", inplace=True)
                df.columns = [f"{asset.asset_id}_{asset.attribute_name}"]
                df.dropna(inplace=True)  # Remove NaN values
                data_frames.append(df)
            else:
                print(
                    f"Attribute '{asset.attribute_name}' not found in asset {asset.asset_id}. Skipping this attribute."
                )
                continue
        else:
            for column in df.columns:
                if column != "timestamp":
                    temp_df = df[["timestamp", column]].copy()
                    temp_df.set_index("timestamp", inplace=True)
                    temp_df.columns = [f"{asset.asset_id}_{column}"]
                    temp_df.dropna(inplace=True)  # Remove NaN values
                    data_frames.append(temp_df)

    data_frame_infos = []

    for df in data_frames:
        frequency = pd.infer_freq(df.index)
        if frequency is None:
            diffs = df.index.to_series().diff().dropna()
            most_common_diff = diffs.mode()[0]
            frequency = pd.tseries.frequencies.to_offset(most_common_diff).freqstr

        # Resample the data frame on its most common frequency with forward fill
        df_resampled = df.resample(frequency).ffill().dropna()

        # Create DataFrameInfo instance
        df_info = DataFrameInfo(
            dataframe=df_resampled,
            frequency=frequency,
            data_size=len(df_resampled),
            start_date=df_resampled.index.min(),
            end_date=df_resampled.index.max(),
        )
        print("dataframe head", df_info.dataframe.head())
        print("frequency", df_info.frequency)
        print("data_size", df_info.data_size)
        print("start_date", df_info.start_date)
        print("end_date", df_info.end_date)
        data_frame_infos.append(df_info)

    return data_frame_infos
