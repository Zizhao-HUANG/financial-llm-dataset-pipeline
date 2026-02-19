# Extending the Pipeline: Adding a New Data Source

This guide provides a step-by-step tutorial for adding a new data source (an "interface") to the pipeline. The modular design of the pipeline makes this process straightforward.

The core of the process involves two main stages:
1.  **Configuration**: Defining the new data source in the configuration files.
2.  **Offline Testing**: Providing sample data and ensuring the existing pipeline modules can handle it correctly.

---

## Step 1: Register the New Interface

The first step is to tell the pipeline about your new data source. All data interfaces are registered in `config/interfaces.yaml`.

Open this file and add a new entry to the `interfaces` list. Here is an example template:

```yaml
- id: my_new_interface_id # A unique ID for your new source
  source_domain: some_website.com
  freq: D # The data's frequency (D, Q, A, static, event)
  scope: market_wide_single_day # The scope for the manifest generator
  columns_map:
    SourceColumnName1: target_column_name1
    SourceColumnName2: target_column_name2
  bootstrap_source: my_new_data.csv
  params: [date] # List of params for the akshare function in online mode
```

-   **`id`**: This is the most important field. It must be unique.
-   **`freq`**: This is critical. Set it correctly to ensure the `Assembler` uses the correct join strategy. Use `D` for daily data and `Q` or `A` for less frequent data that requires an as-of join.
-   **`columns_map`**: This tells the `Normalizer` how to rename the columns from your source data to the pipeline's internal standard.
-   **`bootstrap_source`**: This is the name of the local data file you will use for offline testing.

For more details on these fields, see the [Configuration Documentation](./configuration.md).

---

## Step 2: Provide Bootstrap Data for Offline Testing

The pipeline is designed to be "offline-first". This means you must provide a sample of your new data so that the entire pipeline can be tested without making live network calls.

1.  **Obtain Sample Data**: Get a small, representative sample of your data. For example, run your `akshare` function once and save the result.
2.  **Save the File**: Save this sample data as a `.csv` file in the `data_raw/bootstrap/` directory. The filename must match the `bootstrap_source` you defined in `interfaces.yaml`.

For example, if you set `bootstrap_source: my_new_data.csv`, you should have a file at `data_raw/bootstrap/my_new_data.csv`.

---

## Step 3: Update the Manifest (If Necessary)

For most common data types (e.g., daily data, quarterly reports), the `ManifestGenerator` should be able to create tasks for your new interface automatically during a `--full-run` based on its `scope` and `freq`.

You would only need to modify `src/manifest.py` if your new interface requires a completely novel way of generating tasks that doesn't fit the existing patterns (e.g., it needs to iterate based on a new dimension). This is an advanced use case.

---

## Step 4: Run the Smoke Test

Once you have configured the interface and provided the bootstrap data, you can run the standard offline smoke test to see if the pipeline can process it.

```bash
bash run_bootstrap.sh
```

**Pay close attention to the logs.** The pipeline should:
1.  **Manifest**: Create a task for your new interface (if you added it to the smoke test logic, otherwise this will be skipped).
2.  **Transport**: Read your `my_new_data.csv` file.
3.  **Normalize**: Rename the columns and save the data to `data_silver/interface=my_new_interface_id/data.parquet`.
4.  **Assemble**: Join your new data into the `features_gold.parquet` table.

If the run completes successfully, you have added your new data source!

---

## Step 5: Add Online Capabilities (Optional)

To make your new interface work in `online` mode, you need to do two more things:

1.  **Map the `akshare` function**: In `src/transport.py`, find the `ak_func_map` dictionary inside the `HttpTransport` class and add a new entry that maps your `interface_id` to the actual `akshare` function.
    ```python
    self.ak_func_map = {
        # ... existing entries
        "my_new_interface_id": self.ak.the_actual_akshare_function,
    }
    ```
2.  **Verify Parameters**: Ensure the `params` list you defined in `interfaces.yaml` matches the parameters expected by the `akshare` function.

After these changes, you can test your new interface with a small online run:
```bash
python3 run_pipeline.py
```
(The default online run is a small test. You may need to modify the `create_online_test_manifest` method in `src/manifest.py` to temporarily include your new interface for this test).
