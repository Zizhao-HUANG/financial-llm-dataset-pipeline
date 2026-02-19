# Financial LLM Dataset Pipeline

A modular, configuration-driven pipeline for collecting, processing, and exporting Chinese A-share financial data into LLM-ready training formats.

## Overview

This project implements a production-grade data engineering workflow that transforms raw financial market data (sourced via [AKShare](https://github.com/akfamily/akshare)) into structured datasets suitable for Large Language Model training. The pipeline follows a standard **raw → silver → gold** medallion architecture with built-in auditing and quality checks at each stage.

### Key Features

- **Medallion Architecture** — Three-stage data processing (`data_raw/` → `data_silver/` → `data_gold/`) ensuring traceability and data quality
- **Multiple Export Formats** — Generates datasets in CPT (continued pre-training), SFT (instruction fine-tuning), and TXT (human-readable preview) formats
- **Configuration-Driven** — All data sources, feature schemas, rate limits, and processing parameters are defined in YAML files
- **Offline-First Design** — Core logic is developed and validated using a local bootstrap dataset before connecting to live data sources, ensuring reproducibility
- **Built-in Auditing** — Automated checks for data quality issues such as lookahead bias, missing values, and statistical anomalies
- **Robust Online Transport** — HTTP transport layer with proxy rotation, rate limiting, checkpointing, and resumable downloads

## Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Transport   │───▶│  Normalize   │───▶│  Assemble    │───▶│   Label     │
│  (fetch)     │    │  (clean)     │    │  (features)  │    │  (targets)  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                                                │
                                                                ▼
                                                         ┌─────────────┐
                                              ┌─────────▶│   Export     │
                                              │          │  (CPT/SFT)  │
                                              │          └─────────────┘
                                              │                │
                                              │                ▼
                                              │          ┌─────────────┐
                                              └─────────▶│   Audit     │
                                                         │  (quality)  │
                                                         └─────────────┘
```

The `Orchestrator` coordinates all pipeline stages. Each module is a standalone, single-responsibility component:

| Module | Responsibility |
|--------|---------------|
| `transport.py` | Data fetching — `ReplayTransport` for offline, `HttpTransport` for online (with proxy/rate-limit) |
| `normalize.py` | Standardize raw data into a consistent schema |
| `assemble.py` | Join normalized tables into a unified feature matrix |
| `label.py` | Compute forward-looking labels (e.g., next-day returns) |
| `export.py` | Convert gold data into LLM training formats |
| `audit.py` | Data quality validation and statistical profiling |
| `manifest.py` | Task list generation and checkpoint management |

## Directory Structure

```
├── config/             # YAML configuration files
│   ├── interfaces.yaml     # Data source definitions and API schemas
│   ├── features_schema.yaml  # Feature engineering specifications
│   ├── rate_limits.yaml    # Rate limiting rules per data source
│   └── split.yaml          # Train/validation/test split definitions
├── data_raw/           # Raw data from sources (bronze layer)
├── data_silver/        # Cleaned, standardized data (silver layer)
├── data_gold/          # Feature matrices and labels (gold layer)
├── exports/            # Final LLM-ready datasets and statistics
├── manifests/          # Task lists and processing checkpoints
├── src/                # Pipeline source code
│   ├── orchestrator.py     # Central pipeline coordinator
│   ├── transport.py        # Data fetching (replay + HTTP)
│   ├── normalize.py        # Data cleaning and standardization
│   ├── assemble.py         # Feature matrix construction
│   ├── label.py            # Target label computation
│   ├── export.py           # Dataset export (CPT / SFT / TXT)
│   └── audit.py            # Quality checks and profiling
├── tests/              # Test suite
├── run_pipeline.py     # Entry point for online data collection
└── run_smoke_test.py   # Entry point for offline validation
```

## Quick Start

### Offline Smoke Test

Validate the entire pipeline using pre-saved local data:

```bash
bash run_bootstrap.sh
```

This runs the complete `raw → silver → gold → export → audit` workflow without network access.

### Online Data Collection

```bash
# Set proxy credentials (for data source access)
export BRD_USERNAME_BASE="your-proxy-username"
export BRD_PASSWORD="your-proxy-password"

# Run online pipeline
python run_pipeline.py --mode online
```

## Export Formats

| Format | Use Case | Description |
|--------|----------|-------------|
| **CPT** (JSONL) | Continued pre-training | Raw financial text for domain adaptation |
| **SFT** (JSONL) | Instruction fine-tuning | Alpaca-style instruction/input/output triples |
| **TXT** | Inspection | Human-readable preview for quick validation |

## License

This project is for educational and research purposes.
