# Agent Instructions and Developer Notes

This document provides technical notes and guidance for an AI agent working on this repository.

## 1. Core Design Principles

Your primary goal is to maintain and extend this data pipeline while adhering to its core design principles:

- **Modularity and Single Responsibility**: All core logic is encapsulated in single-purpose Python classes within the `src/` directory. When adding new functionality, create or extend these modules rather than adding complex logic to the `bootstrap_runner.py` orchestrator.
- **Configuration over Code**: The pipeline is driven by YAML files in the `config/` directory. To change parameters, data sources, or schemas, modify these files first. Avoid hardcoding values in the Python source code.
- **Offline-First Development**: The `ReplayTransport` allows the entire data processing logic to be developed and tested offline. Before implementing any live data fetching, ensure the corresponding data transformation logic works perfectly in offline mode.
- **Immutable Data Layers**: The `raw -> silver -> gold` data flow is designed to be immutable. Data in a lower layer should never be modified by a higher layer. Each step reads from the previous layer and writes to the next, ensuring traceability and reproducibility.

## 2. Key Files and Entry Points

- **`src/orchestrator.py`**: This file contains the `Orchestrator` class, which is the heart of the pipeline. It encapsulates the entire workflow logic.
- **`run_smoke_test.py`**: This is the dedicated entry point for running the full, end-to-end OFFLINE smoke test. It simply calls the `Orchestrator` in `replay` mode.
- **`run_pipeline.py`**: This is the dedicated entry point for ONLINE data collection. It calls the `Orchestrator` in `online` mode and handles production-related arguments.
- **`run_bootstrap.sh`**: This is a convenience script that installs dependencies and runs the smoke test (`run_smoke_test.py`).
- **`config/interfaces.yaml`**: This is a critical configuration file. It defines the data sources (`akshare` interfaces) and their properties.

## 3. How to Extend the Pipeline

### Adding a New Data Interface (e.g., a new `akshare` endpoint)

1.  **Register the Interface**: Add a new entry to `config/interfaces.yaml`. Define its `id`, `source_domain`, `scope`, and `columns_map`.
2.  **Create Bootstrap Data**: For offline testing, you would first need to fetch a sample of this data and place it in `data_raw/bootstrap/`.
3.  **Update Manifest**: Modify `src/manifest.py` to generate tasks for this new interface.
4.  **Update Normalizer**: If the new data requires special cleaning, update the `process` method in `src/normalize.py` to handle the new `interface_id`.
5.  **Update Assembler**: Modify `src/assemble.py` to correctly join or incorporate the new data into the gold feature table.

## 4. Online Mode Functionality

The pipeline is fully functional in both offline (`replay`) and online modes. The `HttpTransport` class in `src/transport.py` handles live data fetching with a robust set of features.

### Key Features of `HttpTransport`:
1.  **Proxy Integration**: Reads Bright Data credentials from environment variables (`BRD_USERNAME_BASE`, `BRD_PASSWORD`) and automatically rotates proxy sessions for each request to prevent IP bans.
2.  **Resumable Downloads (Checkpointing)**: The transport layer tracks successfully downloaded tasks in `manifests/checkpoints.parquet`. If a run is interrupted, it will automatically resume from where it left off, skipping already completed tasks.
3.  **Domain-Specific Rate Limiting**: A thread-safe token bucket system enforces the rate limits defined in `config/rate_limits.yaml` on a per-domain basis, ensuring compliance with source-specific rules even under concurrent fetching.
4.  **Robust Retries**: Failed requests are automatically retried with exponential backoff. The error handling is designed to distinguish between network-level failures and other issues.

### How to Run:
- **Offline Mode (Default):**
  ```bash
  bash run_bootstrap.sh
  ```
- **Online Mode:**
  1.  Set your proxy credentials:
      ```bash
      export BRD_USERNAME_BASE="your_brightdata_username_base"
      export BRD_PASSWORD="your_brightdata_password"
      ```
  2.  Run the script with the `--mode=online` flag:
      ```bash
      python3 bootstrap_runner.py --mode=online
      ```
