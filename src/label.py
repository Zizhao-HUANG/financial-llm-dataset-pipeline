import pandas as pd
import os
import numpy as np
from typing import Dict, Any, List
import logging

# Set up a logger for this module
logger = logging.getLogger(__name__)

class Labeler:
    """
    Generates target labels (e.g., future returns) for the dataset.
    """

    def __init__(self, configs: Dict[str, Any], gold_dir: str, silver_dir: str):
        self.configs = configs
        self.gold_dir = gold_dir
        self.silver_dir = silver_dir
        os.makedirs(os.path.join(self.gold_dir, 'labels'), exist_ok=True)

    def _load_required_data(self, gold_features_path: str) -> tuple:
        """Helper to load all data needed for label generation."""
        logger.info("  - Loading data required for label generation...")
        df_gold = pd.read_parquet(gold_features_path)

        price_path = os.path.join(self.silver_dir, 'interface=stock_zh_a_hist', 'data.parquet')
        df_prices = pd.read_parquet(price_path)
        if 'effective_date' in df_prices.columns:
            df_prices.rename(columns={'effective_date': 'date'}, inplace=True)

        calendar_path = os.path.join(self.silver_dir, 'interface=tool_trade_date_hist_sina', 'data.parquet')
        df_calendar = pd.read_parquet(calendar_path)
        if 'effective_date' in df_calendar.columns:
            df_calendar.rename(columns={'effective_date': 'date'}, inplace=True)
        elif 'trade_date' in df_calendar.columns:
            df_calendar.rename(columns={'trade_date': 'date'}, inplace=True)

        logger.info(f"    - Loaded {len(df_gold)} gold feature rows, {len(df_prices)} price rows, {len(df_calendar)} calendar days.")
        return df_gold, df_prices, df_calendar

    def process(self, gold_features_path: str) -> str:
        """
        Generates labels for the data in the gold features table.
        """
        logger.info("Generating labels for the gold feature set...")
        df_gold, df_prices, df_calendar = self._load_required_data(gold_features_path)

        price_lookup = df_prices.set_index(['ticker', 'date'])['adj_close_hfq'].to_dict()
        trade_dates = sorted(df_calendar['date'].unique())
        date_to_index = {date: i for i, date in enumerate(trade_dates)}

        horizons = [1, 5, 20]
        results = []

        df_gold['date_str'] = pd.to_datetime(df_gold['date']).dt.strftime('%Y-%m-%d')

        # Dynamically find the adjusted close column from the gold feature table
        adj_close_col = next((c for c in df_gold.columns if 'adj_close_hfq' in c), None)
        if not adj_close_col:
            raise ValueError("Could not find a column containing 'adj_close_hfq' in the gold features table.")
        logger.info(f"Using column '{adj_close_col}' for label calculation.")

        for _, row in df_gold.iterrows():
            ticker, current_date, p_t = row['ticker'], row['date_str'], row[adj_close_col]
            labels = {'ticker': ticker, 'date': row['date']}
            current_date_idx = date_to_index.get(current_date)

            if current_date_idx is None or pd.isna(p_t):
                if current_date_idx is None:
                    logger.warning(f"Date {current_date} not found in trading calendar. Skipping labels.")
                for h in horizons:
                    labels[f'r_{h}d'], labels[f'label_na_{h}d'] = np.nan, 1
                results.append(labels)
                continue

            for h in horizons:
                future_date_idx = current_date_idx + h
                p_t_h = np.nan
                if future_date_idx < len(trade_dates):
                    future_date = trade_dates[future_date_idx]
                    p_t_h = price_lookup.get((ticker, future_date), np.nan)

                if pd.isna(p_t_h) or p_t == 0:
                    ret_bps, label_na = np.nan, 1
                else:
                    ret_bps = 10000 * (p_t_h / p_t - 1)
                    ret_bps = np.clip(ret_bps, -2000, 2000)
                    label_na = 0

                labels[f'r_{h}d'], labels[f'label_na_{h}d'] = ret_bps, label_na

            results.append(labels)

        df_labels = pd.DataFrame(results)

        output_path = os.path.join(self.gold_dir, 'labels', 'labels_gold.parquet')
        df_labels.to_parquet(output_path, index=False)
        logger.info(f"  - Generated and saved labels for {len(df_labels)} (ticker, date) pairs to: {output_path}")
        return output_path
