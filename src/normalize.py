import pandas as pd
import os
from typing import Dict, Any, List
from collections import defaultdict
import logging
from src.config_models import ProjectConfigs

# Set up a logger for this module
logger = logging.getLogger(__name__)

class Normalizer:
    """
    Handles the transformation of raw data into a standardized "silver" format.
    This version consolidates data for each interface into a single Parquet file
    to avoid creating an excessive number of small files.
    """

    def __init__(self, configs: ProjectConfigs, silver_dir: str):
        """
        Initializes the Normalizer.
        """
        self.configs = configs
        self.silver_dir = silver_dir
        os.makedirs(self.silver_dir, exist_ok=True)
        self.interfaces_map = {
            item.id: item for item in self.configs.interfaces.interfaces
        }

    def process(self, fetched_results: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Processes a list of fetched results, consolidates them by interface, and saves them.

        Args:
            fetched_results: A list of dictionaries, each containing 'task' and 'dataframe'.

        Returns:
            A dictionary mapping each interface_id to the path of its single,
            consolidated silver Parquet file.
        """
        logger.info(f"Normalizing {len(fetched_results)} fetched results to the silver layer...")

        processed_data_map = defaultdict(list)

        # First, normalize each raw dataframe and group them by interface_id
        for result in fetched_results:
            task_info = result['task']
            # Read the raw data from the file path provided by the transport layer
            df_raw = pd.read_parquet(result['raw_file_path'])
            interface_id = task_info['interface_id']
            interface_config = self.interfaces_map.get(interface_id)
            if not interface_config:
                logger.warning(f"No interface config found for '{interface_id}'. Skipping.")
                continue

            logger.info(f"  - Normalizing data for interface '{interface_id}'...")
            df_processed = df_raw.copy()

            if interface_config.columns_map:
                df_processed.rename(columns=interface_config.columns_map, inplace=True)

            # Ensure a single, unambiguous 'effective_date' column
            if 'date' in df_processed.columns:
                df_processed['effective_date'] = pd.to_datetime(df_processed['date']).dt.strftime('%Y-%m-%d')
                # Drop the original 'date' column if it's not the effective_date itself
                if 'date' in df_processed.columns and 'effective_date' in df_processed.columns:
                     df_processed = df_processed.drop(columns=['date'])

            if task_info.get('ticker') and 'ticker' not in df_processed.columns:
                df_processed['ticker'] = task_info['ticker']

            processed_data_map[interface_id].append(df_processed)

        # Now, concatenate the dataframes for each interface and save to a single file
        logger.info("Consolidating and saving normalized data...")
        silver_data_paths = {}
        for interface_id, df_list in processed_data_map.items():
            final_df = pd.concat(df_list, ignore_index=True)

            output_dir = os.path.join(self.silver_dir, f"interface={interface_id}")
            os.makedirs(output_dir, exist_ok=True)

            output_path = os.path.join(output_dir, "data.parquet")
            final_df.to_parquet(output_path, index=False)

            logger.info(f"    - Saved {len(final_df)} consolidated rows for '{interface_id}' to {output_path}")
            silver_data_paths[interface_id] = output_path

        return silver_data_paths
