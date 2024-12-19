import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import pytz
from datetime import datetime
from get_trend_data import fetch_pandas_data


def compute_cross_correlation(df, lags, frequency_label):
    """
    Compute cross-correlation for a given DataFrame and lags.
    """
    best_correlation_results = []
    for col1 in numerical_columns:
        for col2 in numerical_columns:
            max_corr = 0
            best_lag = 0
            for lag in lags:
                shifted_series = df[col2].shift(lag)
                correlation = df[col1].corr(shifted_series)
                if abs(correlation) > abs(max_corr):
                    max_corr = correlation
                    best_lag = lag
            best_correlation_results.append(
                {
                    "Attribute 1": col1,
                    "Attribute 2": col2,
                    "Best Lag": best_lag,
                    "Max Correlation": max_corr,
                    "Frequency": frequency_label,
                }
            )
    return pd.DataFrame(best_correlation_results)


def plot_heatmap(results_df, frequency_label):
    """
    Plot heatmap for the results DataFrame.
    """
    heatmap_corr = pd.DataFrame(
        index=numerical_columns, columns=numerical_columns, dtype=float
    )
    heatmap_lag = pd.DataFrame(
        index=numerical_columns, columns=numerical_columns, dtype=int
    )

    # Fill heatmap data
    for _, row in results_df.iterrows():
        attr1 = row["Attribute 1"]
        attr2 = row["Attribute 2"]
        heatmap_corr.loc[attr1, attr2] = row["Max Correlation"]
        heatmap_corr.loc[attr2, attr1] = row["Max Correlation"]  # Symmetric matrix
        heatmap_lag.loc[attr1, attr2] = row["Best Lag"]
        heatmap_lag.loc[attr2, attr1] = row["Best Lag"]  # Symmetric matrix

    # Fill NaN values with 0 for correlations and lags
    heatmap_corr = heatmap_corr.fillna(0)
    heatmap_lag = heatmap_lag.fillna(0)

    # Create annotation matrix with both correlation and lag
    annotations = heatmap_corr.copy()
    for i in annotations.index:
        for j in annotations.columns:
            corr_value = heatmap_corr.loc[i, j]
            lag_value = heatmap_lag.loc[i, j]
            annotations.loc[i, j] = f"{corr_value:.2f}\nLag: {int(lag_value)}"

    # Plot heatmap
    plt.figure(figsize=(12, 8))
    sns.heatmap(
        heatmap_corr,
        annot=annotations,
        fmt="",
        cmap="coolwarm",
        cbar=True,
        linewidths=0.5,
        vmin=-1,  # Minimum value for color scale
        vmax=1,  # Maximum value for color scale
    )
    plt.title(f"Cross-Correlation Heatmap ({frequency_label})")
    plt.show()


# Fetch data
tz = pytz.timezone("Europe/Berlin")
start_date_str = "2024-1-1"
start_date = tz.localize(datetime.strptime(start_date_str, "%Y-%m-%d"))
end_date_str = "2025-1-1"
end_date = tz.localize(datetime.strptime(end_date_str, "%Y-%m-%d"))
df = fetch_pandas_data(1603, start_date, end_date)

# Print initial data
print("Initial Data:")
print(df.head())

# Combine rows with the same minute by grouping by rounded timestamps
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["minute"] = df["timestamp"].dt.floor("T")  # Round to the nearest minute
df = df.groupby("minute").mean()  # Average the values for each minute
df = df.reset_index().rename(columns={"minute": "timestamp"})

# Forward-fill missing values
df = df.fillna(method="ffill")

# Print cleaned data
print("Cleaned Data:")
print(df.head())

# Select numerical attributes
numerical_columns = df.select_dtypes(include=[np.number]).columns

# Define time scales for analysis
time_scales = [
    {"label": "Minutes", "groupby": "T", "lags": range(-60, 61)},
    {"label": "Hours", "groupby": "H", "lags": range(-24, 25)},
    {"label": "Days", "groupby": "D", "lags": range(-30, 31)},
    {"label": "Months", "groupby": "M", "lags": range(-12, 13)},
]

# Analyze for each time scale
for scale in time_scales:
    print(f"Analyzing for {scale['label']} scale...")
    df_grouped = df.copy()

    # Sicherstellen, dass keine doppelten Spaltennamen entstehen
    df_grouped = df_grouped.loc[
        :, ~df_grouped.columns.duplicated()
    ]  # Entfernt doppelte Spalten

    # Timestamp auf die entsprechende Zeitskala abrunden
    df_grouped["time_unit"] = pd.to_datetime(df_grouped["timestamp"]).dt.floor(
        scale["groupby"]
    )

    # Gruppieren nach der Zeitskala und Mittelwerte berechnen
    df_grouped = df_grouped.groupby("time_unit").mean().reset_index()

    # Fehlende Werte vorwärts füllen
    df_grouped = df_grouped.ffill()

    # Cross-Correlation berechnen
    results = compute_cross_correlation(df_grouped, scale["lags"], scale["label"])
    print(f"Results for {scale['label']} scale:")
    print(results)

    # Heatmap plotten
    plot_heatmap(results, scale["label"])
