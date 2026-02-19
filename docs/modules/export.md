# Module: `export.py`

The `export.py` module is the final stage of data processing before the audit. Its purpose is to take the structured, tabular data from the `gold` layer and convert it into formats suitable for training Large Language Models (LLMs) and for human review.

## Class: `Exporter`

This class handles the logic for merging the final feature and label tables and exporting them into various formats.

### `__init__(self, configs, gold_dir, exports_dir)`

-   **Purpose**: Initializes the exporter.
-   **Inputs**:
    -   `configs`: The global configuration dictionary.
    -   `gold_dir`: The path to the gold data directory, to load the features and labels.
    -   `exports_dir`: The root path for all exported files (e.g., `exports/`).

### `export_all(self, filename_suffix: str = "smoke")`

-   **Inputs**:
    -   `filename_suffix`: A string to append to the output filenames (e.g., "smoke" or "full_run").
-   **Logic**:
    1.  **Load and Merge**: It first calls the private method `_load_and_merge_gold_data()` to load `features_gold.parquet` and `labels_gold.parquet` and merge them into a single DataFrame on `(ticker, date)`.
    2.  **Iterate and Format**: It then iterates through every row of this merged DataFrame and generates three distinct representations of the data.
-   **Output**: This method does not return a value, but it writes three files to the `exports/` directory.

---

## Export Formats

For each row in the gold dataset, the following three files are appended to.

### 1. Human-Readable Preview (`exports/txt/`)

-   **Filename**: `finset_[suffix]_preview.txt`
-   **Purpose**: Provides a simple, human-readable text format for easy inspection and debugging.
-   **Format**: Each record is a block of text containing the ticker, date, a list of features, and the target label, separated by `---`.

### 2. Continued Pre-Training (CPT) Format (`exports/cpt/`)

-   **Filename**: `finset_cpt_[suffix].jsonl`
-   **Purpose**: This format is designed for the continued pre-training of an LLM. The goal is to teach the model the "language" of financial data.
-   **Format**: A JSON Lines (`.jsonl`) file, where each line is a JSON object with a single key, `"text"`. The value is a string that concatenates all the feature and label information into a single block of text.

### 3. Supervised Fine-Tuning (SFT) Format (`exports/sft/`)

-   **Filename**: `finset_sft_[suffix].jsonl`
-   **Purpose**: This format is designed for instruction fine-tuning an LLM. The goal is to teach the model to perform a specific task, in this case, predicting future returns.
-   **Format**: A JSON Lines (`.jsonl`) file following the "Alpaca-style" format. Each line is a JSON object with three keys:
    -   `"Instruction"`: A fixed instruction telling the model what to do (e.g., "predict the future return...").
    -   `"Input"`: The context, which includes the ticker, date, and the block of feature data.
    -   `"Output"`: The expected answer, which is the target return value.
