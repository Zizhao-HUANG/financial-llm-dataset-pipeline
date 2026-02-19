import pandas as pd
import os
import json
import numpy as np
from typing import Dict, Any
import logging

# Set up a logger for this module
logger = logging.getLogger(__name__)

class Exporter:
    """
    Exports the final gold data into various formats for model training and review.
    """

    def __init__(self, configs: Dict[str, Any], gold_dir: str, exports_dir: str):
        """
        Initializes the Exporter.

        Args:
            configs: The loaded configuration dictionary.
            gold_dir: The directory where gold data is stored.
            exports_dir: The root directory where exported files will be saved.
        """
        self.configs = configs
        self.gold_dir = gold_dir
        self.exports_dir = exports_dir
        # Ensure export directories exist
        os.makedirs(os.path.join(self.exports_dir, 'cpt'), exist_ok=True)
        os.makedirs(os.path.join(self.exports_dir, 'sft'), exist_ok=True)
        os.makedirs(os.path.join(self.exports_dir, 'txt'), exist_ok=True)

    def _load_and_merge_gold_data(self) -> pd.DataFrame:
        """Loads and merges the gold features and labels into a single DataFrame."""
        features_path = os.path.join(self.gold_dir, 'features', 'features_gold.parquet')
        labels_path = os.path.join(self.gold_dir, 'labels', 'labels_gold.parquet')

        if not os.path.exists(features_path) or not os.path.exists(labels_path):
            raise FileNotFoundError("Gold features or labels file not found. Cannot proceed with export.")

        df_features = pd.read_parquet(features_path)
        df_labels = pd.read_parquet(labels_path)

        df_merged = pd.merge(df_features, df_labels, on=['ticker', 'date'])
        logger.info(f"  - Loaded and merged {len(df_merged)} rows of gold data for export.")
        return df_merged

    def export_all(self, filename_suffix: str = "smoke"):
        """
        Runs all export processes, generating CPT, SFT, and TXT files.

        Args:
            filename_suffix: A suffix to append to the output filenames.
        """
        logger.info("Exporting gold data to final formats...")
        df = self._load_and_merge_gold_data()

        target_horizon = 1 # Using 1-day return for this example
        label_col = f'r_{target_horizon}d'
        na_col = f'label_na_{target_horizon}d'

        cpt_path = os.path.join(self.exports_dir, 'cpt', f'finset_cpt_{filename_suffix}.jsonl')
        sft_path = os.path.join(self.exports_dir, 'sft', f'finset_sft_{filename_suffix}.jsonl')
        txt_path = os.path.join(self.exports_dir, 'txt', f'finset_{filename_suffix}_preview.txt')

        with open(cpt_path, 'w', encoding='utf-8') as f_cpt, \
             open(sft_path, 'w', encoding='utf-8') as f_sft, \
             open(txt_path, 'w', encoding='utf-8') as f_txt:

            for _, row in df.iterrows():
                # 1. Format the features into a text block
                feature_lines = []
                feature_cols = ['open', 'high', 'low', 'close', 'volume', 'amount', 'turnover', 'adj_close_hfq', 'is_member', 'is_suspended']
                for col in feature_cols:
                    value = row.get(col)
                    if pd.notna(value):
                        # Format floats to 6 decimal places, otherwise convert to string
                        formatted_value = f"{value:.6f}" if isinstance(value, (float, np.floating)) else str(value)
                        feature_lines.append(f"{col}={formatted_value}")
                features_text = "\n".join(feature_lines)

                # 2. Format the output/target
                if row[na_col] == 1 or pd.isna(row[label_col]):
                    output_text = "LABEL_NA=1"
                else:
                    output_text = str(int(row[label_col]))

                # 3. Construct and write the different formats

                # TXT format (human-readable)
                txt_full_block = (
                    f"TICKER={row['ticker']}\nDATE={row['date']}\n\n"
                    f"FEATURES:\n{features_text}\n\n"
                    f"TARGET_RETURN_BPS_NEXT_{target_horizon}D:\n{output_text}\n"
                )
                f_txt.write(txt_full_block + "\n---\n\n")

                # CPT format (JSONL)
                cpt_text = (
                    f"TICKER={row['ticker']}\nDATE={row['date']}\n"
                    f"FEATURES:\n{features_text}\n"
                    f"TARGET_RETURN_BPS_NEXT_{target_horizon}D:\n{output_text}"
                )
                cpt_record = {"text": cpt_text}
                f_cpt.write(json.dumps(cpt_record, ensure_ascii=False) + "\n")

                # SFT format (Alpaca style JSONL)
                sft_instruction = f"Based on the provided market data for a stock on a given day, predict the future return in basis points (bps) for the next {target_horizon} trading day(s)."
                sft_input = f"TICKER={row['ticker']}\nDATE={row['date']}\nFEATURES:\n{features_text}"
                sft_record = {
                    "Instruction": sft_instruction,
                    "Input": sft_input,
                    "Output": output_text,
                }
                f_sft.write(json.dumps(sft_record, ensure_ascii=False) + "\n")

        logger.info(f"  - Exported CPT data to: {cpt_path}")
        logger.info(f"  - Exported SFT data to: {sft_path}")
        logger.info(f"  - Exported TXT preview to: {txt_path}")
