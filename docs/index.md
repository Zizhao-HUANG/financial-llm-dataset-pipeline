# Welcome to the Financial Dataset Construction Pipeline Documentation

This documentation provides a comprehensive guide to the Financial Dataset Construction Pipeline. The project is designed to be a robust, modular, and scalable system for collecting, processing, and preparing financial data for use in training Large Language Models (LLMs).

## Project Overview

The core purpose of this pipeline is to transform raw financial data from various sources into a clean, structured, and model-ready format. It follows best practices in data engineering, including a multi-stage `raw -> silver -> gold` architecture, configuration-driven design, and an "offline-first" development approach to ensure reliability and reproducibility.

This documentation will guide you through the project's architecture, execution, configuration, and core components.

## Table of Contents

### 1. Core Concepts
*   [**Architecture and Design** (`architecture.md`)](): Understand the foundational principles of the pipeline, including the data flow, modularity, and offline-first approach.
*   [**Pipeline Execution** (`execution.md`)](): Learn how to run the pipeline, from the entry-point script to the different operational modes.
*   [**Directory Structure** (`execution.md#directory-structure`)](): A detailed breakdown of the project's folder structure.

### 2. Pipeline Details
*   [**Configuration** (`configuration.md`)](): A guide to the YAML configuration files that drive the pipeline's behavior.
*   [**Data Model** (`data_model.md`)](): A description of the data schemas at each stage (`silver`, `gold`) and the final exported formats.
*   [**Extending the Pipeline** (`extending.md`)](): A step-by-step tutorial on how to add a new data source.

### 3. Core Modules (`src/`)
This section details the purpose and logic of each Python module in the `src/` directory.

*   [**`utils.py`** (`modules/utils.md`)](): Core helper functions.
*   [**`manifest.py`** (`modules/manifest.md`)](): Task generation and management.
*   [**`transport.py`** (`modules/transport.md`)](): Data fetching (offline and online).
*   [**`normalize.py`** (`modules/normalize.md`)](): Raw-to-Silver data standardization.
*   [**`assemble.py`** (`modules/assemble.md`)](): Silver-to-Gold feature assembly.
*   [**`label.py`** (`modules/label.md`)](): Target label generation.
*   [**`export.py`** (`modules/export.md`)](): Final data export to model-ready formats.
*   [**`audit.py`** (`modules/audit.md`)](): Data quality and statistical auditing.
