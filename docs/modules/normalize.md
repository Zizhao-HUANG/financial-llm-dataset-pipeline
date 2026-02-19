# Module: `normalize.py`

The `normalize.py` module is responsible for the first stage of data transformation in the pipeline. Its purpose is to take the raw data fetched by the `transport` layer and convert it into a clean, standardized "silver" format.

## Class: `Normalizer`

This class handles the cleaning and structuring of raw data.

### `__init__(self, configs, silver_dir)`

-   **Purpose**: Initializes the normalizer.
-   **Inputs**:
    -   `configs`: The global configuration dictionary, used to access the `interfaces` configuration.
    -   `silver_dir`: The path to the output directory for silver data (e.g., `data_silver/`).

### `process(self, fetched_results: List[Dict[str, Any]]) -> Dict[str, str]`

-   **Inputs**:
    -   `fetched_results`: The list of dictionaries returned by the transport layer. Each dictionary contains the `task` info and a `raw_file_path` pointing to the downloaded data.
-   **Logic**:
    1.  **Group by Interface**: It first groups the incoming raw dataframes by their `interface_id`. This is necessary because multiple tasks (e.g., fetching data for multiple stocks from the same interface) will need to be consolidated.
    2.  **Normalize Columns**: For each dataframe, it applies the `columns_map` from the `config/interfaces.yaml` file. This renames the source-specific column names to the pipeline's internal standard names (e.g., renames `日期` to `date`).
    3.  **Standardize Dates**: It looks for a `date` column and creates a new, standardized `effective_date` column in `YYYY-MM-DD` format. This ensures that all date columns across all datasets are consistent.
    4.  **Add Ticker**: If the task was for a specific ticker but the raw data does not contain a ticker column, it adds the ticker information from the task manifest.
    5.  **Consolidate and Save**: After processing all dataframes for a given interface, it concatenates them into a single, large dataframe. This consolidated dataframe is then saved as a single Parquet file (`data.parquet`) inside a dedicated directory for that interface (e.g., `data_silver/interface=stock_zh_a_hist/`).
-   **Output**: A dictionary that maps each `interface_id` to the file path of its corresponding silver Parquet file. This dictionary is then passed to the `Assembler` in the next stage of the pipeline.
