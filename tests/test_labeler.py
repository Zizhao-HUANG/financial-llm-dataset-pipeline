import pandas as pd
import numpy as np
import os
import pytest

# Since the 'tests' directory is at the same level as 'src', pytest will
# automatically handle the import path for 'src' when run from the root.
from src.label import Labeler

@pytest.fixture
def setup_labeler_test_data(tmp_path):
    """
    Sets up a temporary directory with dummy silver and gold data
    for testing the Labeler module.
    """
    # Define directory paths using pytest's tmp_path fixture
    gold_dir = tmp_path / "gold"
    silver_dir = tmp_path / "silver"
    os.makedirs(gold_dir / "labels", exist_ok=True)
    os.makedirs(silver_dir / "interface=stock_zh_a_hist", exist_ok=True)
    os.makedirs(silver_dir / "interface=tool_trade_date_hist_sina", exist_ok=True)

    # --- Create Mock Data ---

    # 1. Gold features table (the input for the labeler)
    df_gold_features = pd.DataFrame({
        'ticker': ['TICKER_A', 'TICKER_A'],
        'date': ['2024-01-02', '2024-01-03'], # Two days to test
        'adj_close_hfq': [100.0, 102.0]
    })
    gold_features_path = gold_dir / "features_gold.parquet"
    df_gold_features.to_parquet(gold_features_path)

    # 2. Full price history (for lookups)
    df_prices = pd.DataFrame({
        'ticker': ['TICKER_A', 'TICKER_A', 'TICKER_A'],
        'date': ['2024-01-02', '2024-01-03', '2024-01-04'],
        'adj_close_hfq': [100.0, 102.0, 99.96] # Day 3 has a negative return
    })
    price_path = silver_dir / "interface=stock_zh_a_hist" / "data.parquet"
    df_prices.to_parquet(price_path)

    # 3. Trading calendar
    df_calendar = pd.DataFrame({
        'trade_date': ['2024-01-02', '2024-01-03', '2024-01-04']
    })
    calendar_path = silver_dir / "interface=tool_trade_date_hist_sina" / "data.parquet"
    df_calendar.to_parquet(calendar_path)

    # Return all necessary paths and objects for the test
    return {
        "gold_features_path": gold_features_path,
        "gold_dir": gold_dir,
        "silver_dir": silver_dir
    }

def test_labeler_calculates_returns_correctly(setup_labeler_test_data):
    """
    Tests that the Labeler correctly calculates a simple 1-day future return.
    """
    # Arrange: Get the data paths from the fixture
    test_data = setup_labeler_test_data

    # Act: Instantiate and run the Labeler
    labeler = Labeler(configs={}, gold_dir=test_data["gold_dir"], silver_dir=test_data["silver_dir"])
    labels_path = labeler.process(test_data["gold_features_path"])

    # Assert: Check the output
    df_result = pd.read_parquet(labels_path)

    # --- Check results for the first date: 2024-01-02 ---
    row1 = df_result[df_result['date'] == '2024-01-02'].iloc[0]
    # Expected return: (102.0 / 100.0 - 1) * 10000 = 200.0 bps
    expected_r_1d_row1 = 200.0
    assert row1['label_na_1d'] == 0
    assert np.isclose(row1['r_1d'], expected_r_1d_row1)

    # --- Check results for the second date: 2024-01-03 ---
    row2 = df_result[df_result['date'] == '2024-01-03'].iloc[0]
    # Expected return: (99.96 / 102.0 - 1) * 10000 = -200.0 bps
    expected_r_1d_row2 = -200.0
    assert row2['label_na_1d'] == 0
    assert np.isclose(row2['r_1d'], expected_r_1d_row2)

    # --- Check that horizons with no data are handled correctly ---
    # For 2024-01-03, the 5-day and 20-day returns should be NA
    assert row2['label_na_5d'] == 1
    assert pd.isna(row2['r_5d'])
    assert row2['label_na_20d'] == 1
    assert pd.isna(row2['r_20d'])
