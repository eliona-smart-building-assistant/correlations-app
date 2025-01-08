import numpy as np
import pandas as pd
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
import pytz

from api.get_trend_data import fetch_pandas_data
from api.models import CorrelationRequest, LagUnit


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
        if len(df.index) > 3:
            frequency = pd.infer_freq(df.index)
        else:
            frequency = None
        if frequency is None:
            diffs = df.index.to_series().diff().dropna()
            if not diffs.empty:
                most_common_diff = diffs.mode()[0]
                frequency = pd.tseries.frequencies.to_offset(most_common_diff).freqstr
            else:
                frequency = None

        # Create DataFrameInfo instance
        df_info = DataFrameInfo(
            dataframe=df,
            frequency=frequency,
            data_size=len(df),
            start_date=df.index.min() if not df.empty else None,
            end_date=df.index.max() if not df.empty else None,
        )
        data_frame_infos.append(df_info)

    return data_frame_infos


def compute_correlation(data_frame_infos, request: CorrelationRequest):
    """
    Goes through all pairs of DataFrameInfo objects. If request.lags is provided,
    it will sweep from -lag_value to +lag_value for each {lag_unit: lag_value} in the list,
    matching the higher-frequency DataFrame to the nearest timestamps in the lower-frequency DataFrame
    within a tolerance of the higher frequency.

    We only store lag_details if the correlation is a valid (non-null) value.
    Additionally, correlation values are rounded to 4 decimal places.
    """
    correlation_details = {}

    def make_offset(lag_unit: LagUnit, step: int):
        """Build a pd.DateOffset for a given unit (hours, months, etc.) and a signed step."""
        if lag_unit == LagUnit.seconds:
            return pd.DateOffset(seconds=step)
        elif lag_unit == LagUnit.minutes:
            return pd.DateOffset(minutes=step)
        elif lag_unit == LagUnit.hours:
            return pd.DateOffset(hours=step)
        elif lag_unit == LagUnit.days:
            return pd.DateOffset(days=step)
        elif lag_unit == LagUnit.months:
            return pd.DateOffset(months=step)
        elif lag_unit == LagUnit.years:
            return pd.DateOffset(years=step)
        else:
            return pd.DateOffset(0)

    def frequency_to_timedelta(freq: Optional[str]) -> Optional[pd.Timedelta]:
        """
        Converts a pandas frequency string (e.g., 'S', 'T', 'H', 'D') to a pd.Timedelta.
        Returns None if frequency is None or not in the map.
        """
        if freq is None:
            return None
        freq_map = {
            "S": pd.Timedelta(seconds=1),
            "T": pd.Timedelta(minutes=1),
            "min": pd.Timedelta(minutes=1),
            "H": pd.Timedelta(hours=1),
            "D": pd.Timedelta(days=1),
        }
        # If freq is e.g. '15T' => 15 minutes, try parsing
        if freq.endswith("T"):  # e.g. '15T'
            try:
                mins = int(freq.replace("T", ""))
                return pd.Timedelta(minutes=mins)
            except ValueError:
                pass
        return freq_map.get(freq, None)

    for i, df_info1 in enumerate(data_frame_infos):
        for j, df_info2 in enumerate(data_frame_infos):
            col1 = df_info1.dataframe.columns[0]
            col2 = df_info2.dataframe.columns[0]

            # Determine which DF is "higher frequency" (smaller time delta)
            freq1 = frequency_to_timedelta(df_info1.frequency)
            freq2 = frequency_to_timedelta(df_info2.frequency)

            if freq1 is not None and freq2 is not None:
                if freq1 < freq2:
                    left_df = df_info1.dataframe
                    right_df = df_info2.dataframe
                    tolerance = freq1
                else:
                    left_df = df_info2.dataframe
                    right_df = df_info1.dataframe
                    tolerance = freq2
            else:
                # Fallback if we can't parse frequencies
                left_df = df_info1.dataframe
                right_df = df_info2.dataframe
                tolerance = None

            # If no lags, do a single "merge_asof" nearest match
            if not request.lags:
                merged = merge_with_nearest(left_df, right_df, tolerance=tolerance)
                if merged.shape[0] > 1:
                    # Round the correlation
                    best_correlation = round(merged.corr().iloc[0, 1], 4)
                else:
                    best_correlation = np.nan

                best_lag = 0
                best_lag_unit = None
                lag_details = []

            else:
                best_correlation = None
                best_lag = 0
                best_lag_unit = None
                lag_details = []

                for lag_dict in request.lags:
                    # Example lag_dict might be {"hours": 10} or {"days": 3}
                    for lag_unit, lag_value in lag_dict.items():
                        # We'll sweep from -lag_value to +lag_value
                        for step in range(-lag_value, lag_value + 1):
                            # Shift the 'right_df'
                            right_shifted = right_df.copy()
                            offset = make_offset(lag_unit, step)
                            right_shifted.index = right_shifted.index + offset

                            merged = merge_with_nearest(
                                left_df, right_shifted, tolerance=tolerance
                            )
                            if merged.shape[0] < 2:
                                current_corr = np.nan
                            else:
                                current_corr = merged.corr().iloc[0, 1]

                            # Only store details if correlation is not null
                            if pd.notna(current_corr):
                                corr_rounded = round(current_corr, 4)  # <-- round here
                                lag_details.append(
                                    {
                                        "lag_unit": lag_unit,
                                        "lag_step": step,
                                        "correlation": float(corr_rounded),
                                    }
                                )

                                # Update best correlation if needed (compare absolute values)
                                if (best_correlation is None) or (
                                    abs(corr_rounded) > abs(best_correlation)
                                ):
                                    best_correlation = corr_rounded
                                    best_lag = step
                                    best_lag_unit = lag_unit

            correlation_details[(col1, col2)] = {
                "best_correlation": (
                    float(best_correlation) if best_correlation is not None else None
                ),
                "best_lag": best_lag,
                "best_lag_unit": best_lag_unit,
                "lag_details": lag_details,
            }

    correlations = convert_correlations_to_dict(correlation_details)
    print("correlations", correlations)
    return correlations


def merge_with_nearest(
    df_left: pd.DataFrame,
    df_right: pd.DataFrame,
    tolerance: Optional[pd.Timedelta] = None,
) -> pd.DataFrame:
    """
    Merge df_left and df_right by nearest timestamps using merge_asof with optional tolerance.
    The 'left' DataFrame is assumed to be the higher frequency (or you can flip if needed).
    """
    df_left_reset = df_left.reset_index().rename(columns={"index": "timestamp"})
    df_right_reset = df_right.reset_index().rename(columns={"index": "timestamp"})
    df_left_reset = df_left_reset.sort_values("timestamp")
    df_right_reset = df_right_reset.sort_values("timestamp")

    merged = pd.merge_asof(
        left=df_left_reset,
        right=df_right_reset,
        on="timestamp",
        direction="nearest",
        tolerance=tolerance,
    )
    # Drop rows where we have no match (NaN from the right columns)
    merged.dropna(inplace=True)
    merged.set_index("timestamp", inplace=True)
    return merged


def convert_correlations_to_dict(correlations):
    """
    Converts the internal correlation_details dictionary into a user-friendly dictionary.
    """
    result = {}
    for (col1, col2), info in correlations.items():
        result[f"{col1} and {col2}"] = {
            "best_correlation": info["best_correlation"],
            "best_lag": info["best_lag"],
            "lag_unit": info["best_lag_unit"],
            "lag_details": info["lag_details"],
        }
    return result
