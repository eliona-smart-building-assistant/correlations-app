import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import base64
import io


def create_best_correlation_heatmap(correlations_dict, output_file="/tmp/heatmap.png"):
    """
    Creates a heatmap from the 'best_correlation' values in correlations_dict.
    Saves the resulting figure to 'output_file' instead of showing it.

    The input 'correlations_dict' is expected to look like:
        {
            "colA and colB": {
                "best_correlation": 0.83,
                "best_lag": 2,
                "lag_unit": "days",
                "lag_details": [...]
            },
            "colA and colC": {...},
            ...
        }

    Only the best_correlation field is used for coloring the heatmap
    (pairs with None or NaN are left blank).
    """
    # 1) Gather all columns (col1, col2) by splitting each key on " and "
    all_cols = set()
    data_for_matrix = []
    for pair_key, result in correlations_dict.items():
        if " and " not in pair_key:
            continue
        col1, col2 = pair_key.split(" and ")
        all_cols.add(col1)
        all_cols.add(col2)

        best_corr = result["best_correlation"]
        best_lag = result["best_lag"]
        best_lag_unit = result["lag_unit"]
        data_for_matrix.append((col1, col2, best_corr, best_lag, best_lag_unit))

    # Convert the set of columns to a sorted list (for consistent ordering)
    all_cols = sorted(all_cols)

    # 2) Initialize an NxN DataFrame for numeric correlation
    df_matrix = pd.DataFrame(np.nan, index=all_cols, columns=all_cols)

    # 3) Fill in the best correlations
    for col1, col2, best_corr, best_lag, best_lag_unit in data_for_matrix:
        if best_corr is not None and not np.isnan(best_corr):
            df_matrix.loc[col1, col2] = best_corr
            df_matrix.loc[col2, col1] = best_corr

    # (Optional) Set diagonal to 1.0 correlation
    for col in all_cols:
        df_matrix.loc[col, col] = 1.0

    # 4) Plot the heatmap (no plt.show())
    plt.figure(figsize=(10, 8))
    sns.heatmap(
        df_matrix,
        annot=False,  # Disable text annotations
        cmap="coolwarm",
        square=True,
        center=0.0,
        vmin=-1,
        vmax=1,
    )
    plt.title("Best Correlation Heatmap")
    plt.tight_layout()

    # Save the figure to disk
    plt.savefig(output_file)
    plt.close()  # Close the figure to free resources


def in_depth_plot_scatter(df_info_list, output_file="/tmp/in_depth_scatter.png"):
    """
    Accepts a list of TWO DataFrameInfo objects (each with one column),
    merges them, computes correlation, and returns:
      - correlation value
      - base64-encoded PNG scatter plot of one column on the x-axis, the other on the y-axis

    The resulting plot is saved to 'output_file' and also encoded in Base64 so you can return it in JSON.
    """
    if len(df_info_list) != 2:
        raise ValueError("Exactly two DataFrameInfo objects are required.")

    df_info1, df_info2 = df_info_list
    df1 = df_info1.dataframe
    df2 = df_info2.dataframe

    col1 = df1.columns[0]
    col2 = df2.columns[0]

    # Merge/align on timestamps by an inner join
    df_merged = df1.join(df2, how="inner").dropna()
    if df_merged.shape[0] < 2:
        raise ValueError("Not enough overlapping data points to compute correlation.")

    # Compute correlation
    correlation_value = df_merged.corr().iloc[0, 1]
    correlation_value_rounded = round(correlation_value, 4)

    # Create a scatter plot: x = col1, y = col2
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(df_merged[col1], df_merged[col2], c="blue", alpha=0.6, edgecolor="k")
    ax.set_xlabel(col1)
    ax.set_ylabel(col2)
    ax.set_title(f"Scatter: {col1} vs. {col2} (Corr={correlation_value_rounded})")

    # Optional: Plot a best-fit line (linear regression) for visual emphasis
    # We use np.polyfit to get slope, intercept
    x_vals = df_merged[col1].values
    y_vals = df_merged[col2].values

    # np.polyfit can fail if all x values are the same (vertical line), so handle exceptions
    try:
        slope, intercept = np.polyfit(x_vals, y_vals, 1)
        best_fit_line = slope * x_vals + intercept
        ax.plot(x_vals, best_fit_line, color="red", linewidth=2, label="Best Fit")
        ax.legend()
    except np.linalg.LinAlgError:
        # Could happen if there's no variation in x_vals
        pass

    plt.tight_layout()

    # Save the figure to disk
    plt.savefig(output_file)

    # Also return a base64-encoded version if desired:
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)  # Free resources

    return {
        "correlation": correlation_value_rounded,
        "plot_base64_png": img_base64,
        "columns": [col1, col2],
    }


def plot_lag_correlations(correlations_dict, output_dir="/tmp/lag_plots"):
    """
    For each pair of columns in 'correlations_dict', we look at 'lag_details'
    and group them by lag_unit (e.g., hours, days). Then we make a separate plot
    for each (pair, lag_unit) combination, where:
      - x = lag_step (e.g., -10, -9, ... +10)
      - y = correlation at that lag_step

    We skip pairs like "colA and colB" if we've already handled "colB and colA".
    Also skip self-correlation pairs like "colA and colA".
    """
    import os
    import matplotlib.pyplot as plt
    import io
    import base64

    os.makedirs(output_dir, exist_ok=True)

    seen_pairs = set()  # Track pairs we've already plotted
    plot_images = {}  # Dictionary to store base64-encoded images
    plot_filenames = []  # List to store filenames of generated plots

    for pair_name, info in correlations_dict.items():
        # Split on " and " to get the two column names.
        if " and " not in pair_name:
            continue
        col1, col2 = pair_name.split(" and ")

        # Skip self-correlation
        if col1 == col2:
            continue

        # Enforce a consistent ordering so we only handle each pair once.
        # For instance, always use the lexicographically smaller name first.
        sorted_pair = tuple(sorted([col1, col2]))
        if sorted_pair in seen_pairs:
            # Already handled the reversed version of this pair
            continue
        seen_pairs.add(sorted_pair)

        # Now proceed to create the lag plots for this pair
        lag_details = info.get("lag_details", [])
        lag_data_by_unit = {}

        for entry in lag_details:
            unit = entry["lag_unit"]
            step = entry["lag_step"]
            corr = entry["correlation"]
            if corr is not None:
                lag_data_by_unit.setdefault(unit, []).append((step, corr))

        # Plot one figure per lag_unit
        for unit, values in lag_data_by_unit.items():
            values.sort(key=lambda x: x[0])  # sort by lag_step
            x_vals = [v[0] for v in values]
            y_vals = [v[1] for v in values]

            fig, ax = plt.subplots(figsize=(6, 4))
            ax.plot(x_vals, y_vals, marker="o", linestyle="-")
            ax.set_xlabel(f"Lag (in {unit})")
            ax.set_ylabel("Correlation")
            ax.set_title(f"{col1} and {col2} - Lags in {unit}")

            ax.axhline(0, color="gray", linewidth=1, linestyle="--", alpha=0.7)
            ax.grid(True, which="major", linestyle="--", alpha=0.5)

            # Build a safe filename
            pair_label = f"{col1}_and_{col2}".replace(" ", "_")
            safe_unit = unit.replace("/", "_")  # handle e.g. "months/years"
            filename = f"{pair_label}_{safe_unit}.png"
            filepath = os.path.join(output_dir, filename)

            plt.tight_layout()
            plt.savefig(filepath)
            plot_filenames.append(filename)  # Add filename to the list

            # Save the figure to a buffer and encode it in base64
            buf = io.BytesIO()
            fig.savefig(buf, format="png")
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode("utf-8")
            plt.close(fig)  # Free resources

            # Store the base64 image in the dictionary
            plot_images[f"{pair_label}_{safe_unit}"] = img_base64

    return plot_filenames
