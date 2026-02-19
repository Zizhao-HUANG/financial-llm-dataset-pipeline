# Architecture and Design Principles

The Financial Dataset Construction Pipeline is built upon a set of core design principles that ensure modularity, scalability, and reliability. This document outlines the key architectural concepts.

## 1. Modular and Single-Responsibility Design

The pipeline's logic is cleanly separated into distinct Python modules, each with a single, well-defined responsibility. All core logic is located in the `src/` directory.

This design has several advantages:
- **Clarity**: It is easy to understand the purpose of each part of the pipeline.
- **Maintainability**: Changes to one module are less likely to have unintended side effects on other parts of the system.
- **Extensibility**: New functionality can be added by creating new modules or extending existing ones without altering the core orchestration logic.

The main entry points (`run_smoke_test.py` for offline tests, `run_pipeline.py` for online execution) are kept lean. They are primarily responsible for initializing and running the `Orchestrator` class from `src/orchestrator.py`, which encapsulates the core pipeline sequence.

## 2. Configuration over Code

The pipeline is designed to be highly configurable. Instead of hardcoding parameters like data sources, schemas, or API details into the source code, these are defined in human-readable YAML files located in the `config/` directory.

This principle means that many changes—such as adding a new data column, changing a rate limit, or registering a new data interface—can be accomplished by simply editing a configuration file, without modifying the Python code.

## 3. Offline-First Development

The entire pipeline is built and tested using an "offline-first" approach. This is centered around the `ReplayTransport` module, which simulates data fetching by reading from a pre-saved local dataset located in `data_raw/bootstrap/`.

The benefits of this approach are significant:
- **Decoupling**: The data transformation and feature engineering logic (`normalize`, `assemble`, `label`, etc.) is developed and tested independently of the live data fetching process. This separates the complex logic of data manipulation from the complexities of network requests, proxies, and rate limits.
- **Reproducibility**: The offline "smoke test" (`run_bootstrap.sh`) provides a deterministic way to verify that the entire pipeline is working as expected.
- **Speed**: Running the pipeline on a small, local dataset is much faster than fetching data from live endpoints, leading to a more efficient development cycle.

## 4. Immutable Data Layers: Raw, Silver, and Gold

The pipeline processes data through a standard multi-stage architecture, often referred to as a "bronze, silver, gold" or, in this project, a "raw, silver, gold" model. Each layer represents a progressively higher level of data quality and structure. The data layers are immutable, meaning that data in a lower layer is never modified by a higher one; instead, each stage reads from the previous layer and writes to the next.

### Raw Data (`data_raw/`)
- **Purpose**: This layer contains the raw, unprocessed data exactly as it was received from the source.
- **Format**: The format can vary (e.g., CSV, JSON) depending on the source.
- **State**: Data is transient and may not be cleaned, validated, or standardized. The `data_raw/bootstrap/` subdirectory contains the static data used by `ReplayTransport`.

### Silver Data (`data_silver/`)
- **Purpose**: This is the intermediate layer where the data is cleaned, standardized, and conformed.
- **Tasks Performed**:
    - Column names are standardized (e.g., all date columns are renamed to a consistent name).
    - Data types are corrected.
    - Data from multiple fetches of the same interface is consolidated into a single table per interface.
- **Format**: Data is stored in an efficient format like Apache Parquet, organized by `interface_id`.

### Gold Data (`data_gold/`)
- **Purpose**: This is the final, model-ready layer. The data here is fully processed, feature-engineered, and ready for consumption by downstream systems like machine learning models.
- **Structure**:
    - **`features/`**: Contains the main feature table (`features_gold.parquet`), where all the different silver datasets have been joined together in a point-in-time correct manner to prevent lookahead bias.
    - **`labels/`**: Contains the target variables (`labels_gold.parquet`) generated for the feature set, such as future returns.
