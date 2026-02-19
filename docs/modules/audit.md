# Module: `audit.py`

The `audit.py` module is the final, critical step in the data pipeline. Its purpose is to perform a series of automated checks on the final, merged gold dataset to ensure data quality and generate statistical reports. A thorough audit is essential for trusting the data that will be used for model training.

## Class: `Auditor`

This class contains all the methods for running the various audit checks.

### `__init__(self, configs, gold_dir, exports_dir)`

-   **Purpose**: Initializes the auditor.
-   **Inputs**:
    -   `configs`: The global configuration dictionary.
    -   `gold_dir`: The path to the gold data directory, to load the data for auditing.
    -   `exports_dir`: The root path for saving the output statistics files (e.g., `exports/stats/`).

### `run_all_audits(self, filename_suffix: str = "smoke")`

-   **Inputs**:
    -   `filename_suffix`: A string to append to the output filenames (e.g., "smoke").
-   **Logic**:
    1.  **Load Data**: It first loads and merges the gold features and labels into a single DataFrame.
    2.  **Run Audits**: It then executes a series of audit functions on this DataFrame.
-   **Output**: This method does not return a value, but it saves two CSV report files to the `exports/stats/` directory.

---

## Audit Checks and Reports

### 1. Lookahead Audit

-   **Purpose**: This is one of the most critical checks in a financial data pipeline. It ensures that no data from the future has accidentally leaked into the features for a given day.
-   **Logic**: It finds any column in the dataset that contains the name `effective_date`. It then checks if any value in these columns is later than the main `date` of the row. If it finds any such case, it logs a critical error.
-   **Importance**: A violation here would invalidate the entire dataset for backtesting, as it would mean the model is being trained on information that would not have been available at that point in time.

### 2. Coverage and Missing Value Report

-   **Purpose**: To understand the completeness of the final dataset.
-   **Logic**: It calculates the total count and percentage of missing (`NaN`) values for every single column in the DataFrame.

### 3. Descriptive Statistics

-   **Purpose**: To get a high-level statistical summary of the dataset.
-   **Logic**: For all numeric columns, it calculates standard descriptive statistics (mean, standard deviation, min, max, quartiles, etc.).

### 4. NA Label Report

-   **Purpose**: To specifically quantify how many of the generated labels are unusable.
-   **Logic**: It counts the total number of missing labels for each prediction horizon by summing up the `label_na_{h}d` columns.

### 5. Output Reports

The results of the audits are saved in two CSV files:

-   **`stats_summary_[suffix].csv`**: A comprehensive report that combines the descriptive statistics and the missing value counts for every column.
-   **`stats_label_na_[suffix].csv`**: A smaller report that shows only the missing label counts for each horizon.
