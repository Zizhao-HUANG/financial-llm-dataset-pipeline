# Module: `manifest.py`

The `manifest.py` module is responsible for generating the "plan of attack" for a pipeline run. The `ManifestGenerator` class creates a task list, known as a manifest, which is a pandas DataFrame detailing every atomic data fetching operation that needs to be performed.

## Class: `ManifestGenerator`

This is the sole class in the module. It is initialized with the loaded configurations and paths to the manifest and raw data directories.

### `__init__(self, configs, manifest_dir, raw_data_dir)`

-   **Purpose**: Initializes the generator.
-   **Inputs**:
    -   `configs`: The global configuration dictionary.
    -   `manifest_dir`: The directory to save manifest files (e.g., `manifests/`).
    -   `raw_data_dir`: The path to the raw data directory, used to get smoke test info.

### Key Methods

#### `create_smoke_test_manifest(self) -> pd.DataFrame`

-   **Purpose**: Generates the manifest for the standard offline smoke test (`replay` mode).
-   **Logic**:
    1.  It gets the specific tickers and dates for the smoke test from `utils.get_smoke_test_info()`.
    2.  It creates tasks for the historical price data (`stock_zh_a_hist`) for each of these tickers.
    3.  It creates a single task for the market trading calendar (`tool_trade_date_hist_sina`).
    4.  Crucially, for each task, it populates a `replay_path` column, which points to the exact location of the local bootstrap data file in `data_raw/bootstrap/`.
-   **Output**: A pandas DataFrame containing the list of tasks. This DataFrame is also saved as `manifests/tasks_replay.parquet`.

#### `create_online_test_manifest(self) -> pd.DataFrame`

-   **Purpose**: Generates a minimal manifest for a quick online test. This is useful for verifying that the `HttpTransport` and proxy configuration are working without launching a full-scale run.
-   **Logic**:
    1.  It creates a single, hardcoded task for a specific interface (`stock_gpzy_pledge_ratio_em`) on a recent date.
    2.  This task does **not** have a `replay_path`. Instead, it has a `params` dictionary that will be passed to the live `akshare` function.
-   **Output**: A single-row DataFrame saved as `manifests/tasks_online_test.parquet`.

#### `create_full_manifest(self, start_date, end_date) -> pd.DataFrame`

-   **Purpose**: Generates a comprehensive manifest for a large-scale data collection run in `online` mode.
-   **Logic**:
    1.  It reads the list of all stocks to process (from `inputs/CSI300.csv`) and the trading calendar.
    2.  It iterates through every data interface defined in `config/interfaces.yaml`.
    3.  Based on the `scope` and `freq` (frequency) defined for each interface, it generates tasks for the appropriate dates and stocks within the given `start_date` and `end_date`. It correctly handles daily, quarterly, annual, and per-stock data generation logic.
-   **Output**: A potentially very large DataFrame containing all tasks for the full run, saved as `manifests/tasks_full_run.parquet`.
