# Configuration Files

The behavior of the data pipeline is controlled by a set of YAML files located in the `config/` directory. This configuration-driven approach allows for significant flexibility and makes it easy to modify the pipeline's behavior without changing the Python source code.

---

## 1. `interfaces.yaml`

This is the most critical configuration file in the project. It acts as a central registry for every data source (or "interface") that the pipeline can interact with.

### Structure

The file contains a single list named `interfaces`. Each item in the list is an object that defines a specific data source with the following keys:

-   `id` (Required): A unique string identifier for the interface (e.g., `stock_zh_a_hist`). This ID is used throughout the pipeline to refer to this data source.
-   `source_domain`: The domain name of the original data provider (e.g., `sina.com.cn`). Used for logging and potentially for domain-specific rate limiting.
-   `freq`: The frequency of the data. This is a critical field that determines the join strategy in the `Assembler`.
    -   `D`: Daily
    -   `Q`: Quarterly
    -   `A`: Annually
    -   `static`: For data that doesn't change often (like a calendar).
    -   `event`: For event-driven data.
-   `scope`: Defines the scope of the data (e.g., `single_stock_date_range`, `market_wide_single_day`). This is used by the `ManifestGenerator` when creating tasks for a full run.
-   `avail_rule`: A field describing the data availability rule (e.g., `T_day_1500`, `T_plus_1`). This is for informational purposes.
-   `columns_map`: A dictionary that maps the original column names from the source data to the standardized internal names used by the pipeline. This is used by the `Normalizer`.
-   `bootstrap_source`: The filename or pattern for the local data file in `data_raw/bootstrap/` that should be used for this interface in `replay` mode.
-   `params`: A list of parameters that the corresponding `akshare` function expects for this interface when running in `online` mode.

---

## 2. `rate_limits.yaml`

This file configures the behavior of the `HttpTransport` when running in `online` mode. It is essential for fetching data responsibly and avoiding IP blocks.

### Structure

It contains a list of `domains`. Each domain object has the following keys:
-   `domain`: The domain name this rule applies to (e.g., `eastmoney.com`). A `default` domain can be set to provide fallback settings.
-   `concurrency`: The maximum number of concurrent requests to make to this domain.
-   `rate`: The maximum number of requests per second.
-   `retry`: The maximum number of times to retry a failed request.
-   `policy`: The name of the proxy policy to use (for future use).

---

## 3. `features_schema.yaml`

This file documents the intended schema for the final gold feature table. While not actively enforced by the current pipeline, it serves as a blueprint for data validation and feature engineering steps that could be added in the future.

### Structure

-   `defaults`: A section for default settings that apply to all features.
-   `schema`: A list of feature objects, each with:
    -   `name`: The name of the feature column.
    -   `dtype`: The expected data type (e.g., `float64`, `int8`).
    -   `missing_strategy`: The strategy for handling missing values (e.g., `keep_nan`, `fill_zero`).
    -   `winsorize`: An optional transformation to clip extreme outliers by specifying lower and upper quantiles.

---

## 4. `split.yaml`

This file defines the date ranges for splitting the final dataset into training, validation, and test sets. This is not used by the data generation pipeline itself but is crucial for ensuring that downstream machine learning experiments are consistent and reproducible.

### Structure

-   `split_boundaries`: An object containing start and end dates for `train`, `validation`, and `test` sets.
