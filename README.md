# Correlation App

The Correlation App computes correlations between asset attributes with customizable lag intervals and generates detailed reports, including visualizations.

---

## Features

- **Lag-Based Correlation Analysis**: Analyze correlations for specified time lags.
- **Report Generation**: Create detailed reports available as both HTML and PDF, featuring heatmaps, scatter plots, and lag plots.
- **Email Integration**: Send reports directly to specified recipients.
- **Customizable Time Range**: Define start and end times for correlation analysis.



## Configuration

### Environment Variables

| Variable             | Description                                                        | Example                                 |
|----------------------|--------------------------------------------------------------------|-----------------------------------------|
| `CONNECTION_STRING`  | Configures the Eliona database connection.                         | `postgres://user:pass@host:port/dbname` |
| `API_ENDPOINT`       | API endpoint for accessing Eliona services.                        | `http://api-v2:3000/v2`                 |
| `API_TOKEN`          | Authentication token for accessing Eliona services.                | `your_api_token`                        |
| `API_SERVER_PORT`    | (Optional) Port for running the API server. Default: `3000`.       | `3000`                                  |
| `SMTP_SERVER`        | SMTP server address.                                               | `smtp.example.com`                      |
| `SMTP_PORT`          | SMTP server port.                                                  | `587`                                   |
| `SMTP_USER`          | SMTP username.                                                     | `user@example.com`                      |
| `SMTP_PASSWORD`      | SMTP password.                                                     | `password`                              |

---

## API Endpoints

### **1. POST /v1/correlate**

**Description**: Compute correlations between multiple specified asset attributes.

- If only the asset ID is provided (without attribute names), the app correlates all attributes of that asset with each other.

**Request Body**:
```json
{
    "assets": ,
    "lags": ,
    "start_time":,
    "end_time": ,
    "to_email": ,
}
```

**Response**:
- **200 OK**: Returns details including:
  - Input assets and lags.
  - Date range for analysis.
  - Correlation results with `best_correlation`, `best_lag`, and `lag_details`.
  - An HTML report (`report_html`) with heatmap visualizations and correlation values.
  - If `to_email` is provided, the report is emailed to the recipient.
- **400 Bad Request**: Invalid input parameters.

---

### **2. POST /v1/correlate-children**

**Description**: Correlate all attributes of an asset's children and their descendants.

**Request Body**: Similar to `/v1/correlate`, but requires `asset_id` instead of a list of assets.

**Response**: Same as `/v1/correlate`, including an HTML report (`report_html`) with heatmaps and correlation details.

---

### **3. POST /v1/in-depth-correlation**

**Description**: Perform detailed correlation analysis for exactly two attributes.

**Response**:
- Input assets and lags.
- Date range for analysis.
- Correlation details including:
  - Best correlation value.
  - Lag offset and unit.
  - Lag-specific correlations.
- An HTML report (`report_html`) with scatter plots and lag-specific visualizations.

---



## Request Parameters

The following parameters can be included in the request body for correlation analysis:

- **assets**: A list of asset-attribute pairs for analysis. If only `asset_id` is provided, the app analyzes all attributes of the specified asset. If diff is true it will transform the data to be  the difference between consecutive and corelating that instead of just taking the normal data.
- **lags**: Optional time lag intervals to include in the correlation analysis (e.g., `{"hours": 10}`).
- **start_time**, **end_time**: The date range for the analysis.
- **to_email**: (Optional) An email address to which the generated report will be sent as a PDF.

### Example Request
```json
{
    "assets": [
        {"asset_id": 123, "attribute_name": "temperature", "diff": true},
        {"asset_id": 456, "attribute_name": "humidity", "diff": false}
    ],
    "lags": [
        {"minutes": 15},
        {"hours": 2},
        {"days": 1}
    ],
    "start_time": "2025-01-01T00:00:00",
    "end_time": "2025-01-03T23:59:59",
    "to_email": "example@domain.com"
}
```

---

## Correlation Results

The response includes the results of the correlation analysis, including:

- **assets**: The list of assets and attributes analyzed.
- **lags**: The time lag intervals used for the analysis.
- **start_time**, **end_time**: The date range covered in the analysis.
- **correlation**: Detailed correlation results, including:
  - **best_correlation**: The highest correlation value found.
  - **best_lag**: The time offset (lag) corresponding to the best correlation.
  - **lag_unit**: The unit of the lag (e.g., minutes, hours).
  - **lag_details**: A breakdown of correlation values for each tested lag.
- **report_html**: An HTML report with visualizations and analysis details, provided as a string.

### Example Response
```json
{
    "assets": [
        {"asset_id": 123, "attribute_name": "temperature", "diff": true},
        {"asset_id": 456, "attribute_name": "humidity"}
    ],
    "lags": [
        {"minutes": 15},
        {"hours": 2},
        {"days": 1}
    ],
    "start_time": "2025-01-01T00:00:00",
    "end_time": "2025-01-03T23:59:59",
    "correlation": {
        "temperature and humidity": {
            "best_correlation": 0.85,
            "best_lag": 2,
            "lag_unit": "hours",
            "lag_details": [
                {"lag_step": -2, "lag_unit": "hours", "correlation": 0.75},
                {"lag_step": 0, "lag_unit": "hours", "correlation": 0.85},
                {"lag_step": 2, "lag_unit": "hours", "correlation": 0.80}
            ]
        }
    },
    "report_html": "<!DOCTYPE html><html><head>...</head><body>...</body></html>"
}
```

The response structure allows users to review the results programmatically or visually through the provided `report_html`.

---

## Report Generation

Reports include the following visualizations:

### HTML Report
Generated for the `/v1/correlate` and `/v1/correlate-children` endpoints:
- **Heatmaps**: Highlight the best correlations between attributes.
- **Correlation Numbers**: Detailed statistics for each correlation.

Generated for the `/v1/in-depth-correlation` endpoint:
- **Scatter Plot**: Illustrates attribute relationships.
- **Lag Plots**: Show correlation trends over time offsets.








