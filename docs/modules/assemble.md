# Module: `assemble.py`

The `assemble.py` module is the heart of the feature engineering process. Its role is to take all the clean, standardized "silver" datasets and combine them into a single, wide "gold" feature table. The most critical function of this module is to perform this assembly in a **point-in-time correct** manner to prevent lookahead bias.

## Class: `Assembler`

This class contains the logic for constructing the final feature set.

### `__init__(self, ...)`

-   **Purpose**: Initializes the assembler.
-   **Inputs**: It takes paths to the `silver`, `gold`, `inputs`, and `raw_data` directories, as well as the global `configs` dictionary.

### `process(self, silver_data_paths, start_date, end_date) -> str`

-   **Inputs**:
    -   `silver_data_paths`: The dictionary from the `Normalizer` that maps interface IDs to their silver data file paths.
    -   `start_date`, `end_date`: The date range for the feature set.
-   **Logic**:
    1.  **Create Base Grid**: The process begins by calling `_get_base_grid()`. This private method creates a master DataFrame containing every combination of `ticker` (from `inputs/CSI300.csv`) and `date` (from the trading calendar) for the specified period. This ensures the final dataset is a dense, rectangular grid.
    2.  **Iterate and Join**: The method then iterates through each silver dataset. For each one, it performs a join against the main gold DataFrame.
    3.  **Select Join Strategy**: This is the most important step. The assembler chooses a join strategy based on the `freq` (frequency) of the data, as defined in `config/interfaces.yaml`:
        -   **For daily data (`freq: 'D'`)**: It uses a standard `pandas.merge` (a left join). This is appropriate for data that has a new value every day.
        -   **For low-frequency data (e.g., quarterly reports, `freq: 'Q'`)**: It uses `pandas.merge_asof`. This "as-of" join is crucial for preventing lookahead bias. It merges the data by finding the most recent value for a given ticker *on or before* the date in the gold table. This correctly simulates having access only to past information.
    4.  **Rename Columns**: To avoid name collisions and maintain data lineage, columns from the silver tables are renamed to include the interface ID as a suffix (e.g., `feat_some_metric_interface_id`).
-   **Output**: The file path to the final gold features table, which is saved to `data_gold/features/features_gold.parquet`. This path is then passed to the `Labeler` module.

### Preventing Lookahead Bias

The use of `pd.merge_asof` is the key mechanism that makes this pipeline suitable for financial modeling. Without it, if you were to do a simple merge on a quarterly feature, the value from the end of the quarter (e.g., March 31st) would only be joined on that specific date. The as-of join correctly forward-fills that value from March 31st until the next value becomes available (e.g., June 30th), which is the correct representation of information availability in the real world.
