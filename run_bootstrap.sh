#!/bin/bash
# This script serves as the main entry point to run the entire offline bootstrap process.
# It ensures dependencies are installed and then executes the main Python orchestrator.

# Exit immediately if a command exits with a non-zero status.
set -e

echo "--- Setting up environment and installing dependencies ---"
# Install necessary Python packages.
# pandas: for data manipulation.
# pyarrow: for reading/writing Parquet files.
# pyyaml: for loading the configuration files.
# akshare: for fetching live financial data.
# pydantic: for robust configuration and data model validation.
pip install pandas pyarrow pyyaml akshare pydantic --quiet

echo
echo "--- Starting the offline smoke test script ---"
# Execute the main smoke test script.
python3 run_smoke_test.py

echo
echo "--- Bootstrap runner finished successfully ---"
