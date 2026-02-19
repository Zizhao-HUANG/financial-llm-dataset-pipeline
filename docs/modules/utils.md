# Module: `utils.py`

The `utils.py` module provides core helper functions that are used throughout the data pipeline, primarily for handling configuration files and retrieving information for the smoke test.

## Functions

### `load_yaml_file(filepath: str) -> Dict[str, Any]`

-   **Purpose**: Loads a single YAML file from the given path and parses it into a Python dictionary.
-   **Parameters**:
    -   `filepath`: The path to the YAML file.
-   **Returns**: A dictionary containing the content of the YAML file.
-   **Error Handling**: Raises a `FileNotFoundError` if the file does not exist or a `yaml.YAMLError` if the file is not valid YAML.

### `load_all_configs(config_dir: str) -> Dict[str, Any]`

-   **Purpose**: Scans a specified directory for all files ending in `.yaml` or `.yml` and loads them into a single dictionary.
-   **Parameters**:
    -   `config_dir`: The path to the directory containing the configuration files (e.g., `config/`).
-   **Returns**: A dictionary where each key is the filename (without the extension) and the value is the dictionary content of the corresponding YAML file. For example, `config/interfaces.yaml` would be loaded into the key `interfaces`.
-   **Usage**: This is the primary function used at the start of the pipeline in the `Orchestrator` to load all configurations at once.

### `get_smoke_test_info(raw_data_dir: str) -> Dict[str, Any]`

-   **Purpose**: Retrieves the specific tickers and dates that are required to run the offline smoke test. This centralizes the smoke test's scope.
-   **Parameters**:
    -   `raw_data_dir`: The path to the raw data directory.
-   **Logic**:
    1.  It hardcodes the tickers used in the smoke test (`600519.SH` and `601318.SH`).
    2.  It reads the smoke test dates from the `data_raw/bootstrap/smoke_dates.txt` file.
    3.  If the file is not found, it falls back to a default set of dates to ensure the test can still run.
-   **Returns**: A dictionary with two keys: `tickers` (a list of stock tickers) and `dates` (a list of date strings).

---

## Class: `TokenBucket`

-   **Purpose**: This is a thread-safe class that implements the token bucket algorithm for rate limiting. It is a crucial component used by `HttpTransport` to enforce domain-specific rate limits across multiple concurrent worker threads.
-   **Key Features**:
    -   **Thread-Safety**: Uses a `threading.Lock` to ensure that token consumption is atomic, which is essential in a multi-threaded environment.
    -   **Capacity and Rate**: It is initialized with a `capacity` (the maximum number of tokens the bucket can hold) and a `rate` (the number of tokens added per second).
-   **Usage**: `HttpTransport` creates a dictionary of `TokenBucket` instances, one for each domain defined in `config/rate_limits.yaml`. Before making a request, a worker thread must call the `consume()` method on the appropriate bucket, which will block until a token is available.
