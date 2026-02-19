# Module: `label.py`

The `label.py` module is responsible for creating the target variables (or "labels") that a machine learning model will be trained to predict. After the `Assembler` has created the gold feature table, the `Labeler` uses this table to generate corresponding labels.

## Class: `Labeler`

This class encapsulates all the logic for label generation.

### `__init__(self, configs, gold_dir, silver_dir)`

-   **Purpose**: Initializes the labeler.
-   **Inputs**:
    -   `configs`: The global configuration dictionary.
    -   `gold_dir`: The path to the gold data directory, used for saving the output labels.
    -   `silver_dir`: The path to the silver data directory, needed to access historical price and calendar data.

### `process(self, gold_features_path: str) -> str`

-   **Inputs**:
    -   `gold_features_path`: The file path to the `features_gold.parquet` table created by the `Assembler`.
-   **Logic**:
    1.  **Load Data**: It loads the gold feature table, the silver historical price data (`stock_zh_a_hist`), and the silver trading calendar data.
    2.  **Iterate and Calculate**: It iterates through every row (`ticker`, `date`) of the gold features table.
    3.  **Calculate Future Returns**: For each row, it calculates the forward-looking returns for several time horizons (specifically 1, 5, and 20 trading days).
        - To do this, it finds the current date in the trading calendar and looks `h` days into the future to get the future date.
        - It then looks up the price for the `(ticker, future_date)` pair.
        - The return is calculated in **basis points (bps)**, where 100 bps = 1%.
    4.  **Clip Outliers**: To prevent extreme values from dominating model training, the calculated returns are clipped to a range of +/- 2000 bps (i.e., +/- 20%).
    5.  **Handle Missing Labels**: If a future price is not available (e.g., for dates near the end of the dataset), the return cannot be calculated. In this case, the return is set to `NaN`, and a corresponding `label_na_{h}d` flag is set to `1`. This flag is crucial for filtering out unusable samples during model training.
-   **Output**: The file path to the final labels table, which is saved to `data_gold/labels/labels_gold.parquet`. This table contains the `ticker`, `date`, and the calculated future return columns (e.g., `r_1d`, `r_5d`, etc.).
