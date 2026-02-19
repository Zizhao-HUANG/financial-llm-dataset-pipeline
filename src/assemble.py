import pandas as pd
import os
from typing import Dict, Any, List
import logging
from src.config_models import ProjectConfigs

logger = logging.getLogger(__name__)

class Assembler:
    """
    Assembles the final point-in-time gold feature dataset from all silver data sources.
    Uses 'as-of' joins for low-frequency data to prevent lookahead bias.
    """

    def __init__(self, configs: ProjectConfigs, silver_dir: str, gold_dir: str, inputs_dir: str, raw_data_dir: str):
        self.configs = configs
        self.silver_dir = silver_dir
        self.gold_dir = gold_dir
        self.inputs_dir = inputs_dir
        self.raw_data_dir = raw_data_dir
        self.interfaces_map = {item.id: item for item in configs.interfaces.interfaces}
        os.makedirs(os.path.join(self.gold_dir, 'features'), exist_ok=True)

    def _get_base_grid(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Creates a master grid of (ticker, date) for all trading days and stocks."""
        try:
            csi300_path = os.path.join(self.inputs_dir, 'CSI300.csv')
            df_csi300 = pd.read_csv(csi300_path, sep=';')
            code_col = df_csi300.columns[0]
            def get_exchange(code):
                return 'SH' if str(code).strip().startswith('6') else 'SZ'
            tickers = (df_csi300[code_col].astype(str).str.strip() + '.' + df_csi300[code_col].apply(get_exchange)).tolist()
        except FileNotFoundError:
            logger.error("CSI300 file not found. Cannot create base grid.")
            return pd.DataFrame()

        try:
            calendar_path = os.path.join(self.raw_data_dir, 'bootstrap', 'trading_calendar.csv')
            df_calendar = pd.read_csv(calendar_path)
            trade_dates = df_calendar[(df_calendar['date'] >= start_date) & (df_calendar['date'] <= end_date)]['date']
        except FileNotFoundError:
            logger.error("Trading calendar not found. Cannot create base grid.")
            return pd.DataFrame()

        df_grid = pd.DataFrame([(ticker, date) for ticker in tickers for date in trade_dates], columns=['ticker', 'date'])
        df_grid['date'] = pd.to_datetime(df_grid['date'])
        logger.info(f"Created base grid with {len(df_grid)} rows ({len(tickers)} tickers x {len(trade_dates)} days).")
        return df_grid.sort_values(by=['ticker', 'date'])

    def process(self, silver_data_paths: Dict[str, str], start_date: str, end_date: str) -> str:
        logger.info("--- Assembling silver data to create gold feature layer (Point-in-Time) ---")

        df_gold = self._get_base_grid(start_date, end_date)
        if df_gold.empty:
            raise RuntimeError("Base grid could not be created. Halting assembly.")

        for interface_id, path in silver_data_paths.items():
            iface = self.interfaces_map.get(interface_id)
            if not iface:
                logger.warning(f"No interface config found for '{interface_id}'. Skipping.")
                continue

            logger.info(f"  - Processing and joining silver data for '{interface_id}'...")
            try:
                df_silver = pd.read_parquet(path)
                if df_silver.empty:
                    logger.warning(f"    - Silver data for '{interface_id}' is empty. Skipping.")
                    continue

                # --- Prepare for join ---
                # Prioritize 'effective_date' as the join key, falling back to 'date'.
                if 'effective_date' in df_silver.columns:
                    # Drop original date if effective_date exists to avoid conflicts
                    df_silver = df_silver.drop(columns=['date'], errors='ignore')
                    df_silver = df_silver.rename(columns={'effective_date': 'date'})

                if 'date' not in df_silver.columns:
                    logger.warning(f"    - No date column in '{interface_id}'. Skipping join.")
                    continue

                # Convert join key to datetime
                df_silver['date'] = pd.to_datetime(df_silver['date'])

                # --- Select Join Strategy ---
                # Strategy 1: For daily or static data, use a simple left merge.
                if iface.freq in ['D', 'static']:
                    join_keys = ['ticker', 'date'] if 'ticker' in df_silver.columns else ['date']
                    rename_map = {c: f"feat_{c}_{interface_id}" for c in df_silver.columns if c not in join_keys}
                    df_silver.rename(columns=rename_map, inplace=True)
                    df_gold = pd.merge(df_gold, df_silver, on=join_keys, how='left')

                # Strategy 2: For non-daily (low-frequency) data, use a point-in-time (as-of) merge.
                else:
                    df_silver = df_silver.sort_values(by='date')
                    join_keys = ['ticker', 'date'] if 'ticker' in df_silver.columns else ['date']
                    by_key = 'ticker' if 'ticker' in df_silver.columns else None

                    rename_map = {c: f"{c}_{interface_id}" for c in df_silver.columns if c not in join_keys}
                    df_silver.rename(columns=rename_map, inplace=True)

                    df_gold = pd.merge_asof(df_gold, df_silver, on='date', by=by_key, direction='backward')

                logger.info(f"    - Successfully joined data from '{interface_id}'.")

            except Exception as e:
                logger.error(f"    - Failed to process and join data for '{interface_id}': {e}", exc_info=True)

        output_path = os.path.join(self.gold_dir, 'features', 'features_gold.parquet')
        df_gold.to_parquet(output_path, index=False)
        logger.info(f"  - Assembled final gold feature table with {len(df_gold)} rows and {len(df_gold.columns)} columns.")
        logger.info(f"  - Saved gold features to: {output_path}")

        return output_path
