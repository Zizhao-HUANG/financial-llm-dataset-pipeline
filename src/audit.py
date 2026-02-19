import pandas as pd
import os
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class Auditor:
    """
    Performs quality checks and generates statistical reports on the data.
    """

    def __init__(self, configs: Dict[str, Any], gold_dir: str, exports_dir: str):
        self.configs = configs
        self.gold_dir = gold_dir
        self.stats_dir = os.path.join(exports_dir, 'stats')
        os.makedirs(self.stats_dir, exist_ok=True)

    def _load_gold_data(self) -> pd.DataFrame:
        """Loads and merges gold features and labels for a full audit."""
        features_path = os.path.join(self.gold_dir, 'features', 'features_gold.parquet')
        labels_path = os.path.join(self.gold_dir, 'labels', 'labels_gold.parquet')
        df_features = pd.read_parquet(features_path)
        df_labels = pd.read_parquet(labels_path)
        return pd.merge(df_features, df_labels, on=['ticker', 'date'])

    def run_all_audits(self, filename_suffix: str = "smoke"):
        logger.info("--- Step 8: Running audit and generating stats... ---")
        df = self._load_gold_data()

        # 1. Lookahead Audit
        # Dynamically find all effective_date columns and check them
        effective_date_cols = [c for c in df.columns if 'effective_date' in c]
        lookahead_violations = 0
        if not effective_date_cols:
            logger.warning("  - No 'effective_date' columns found to perform lookahead audit.")
        else:
            for ed_col in effective_date_cols:
                # The observation date column is 'date'
                violations = df[pd.to_datetime(df[ed_col]) > pd.to_datetime(df['date'])]
                if not violations.empty:
                    logger.error(f"CRITICAL: Lookahead violation found in {ed_col}! {len(violations)} rows have effective_date > date.")
                    lookahead_violations += len(violations)
            if lookahead_violations == 0:
                logger.info("  - Lookahead audit PASSED. No data from the future was used.")

        # 2. Coverage and Missing Value Report
        missing_report = df.isnull().sum().reset_index()
        missing_report.columns = ['column', 'missing_count']
        missing_report['missing_percentage'] = (missing_report['missing_count'] / len(df) * 100).round(2)

        # 3. Descriptive Statistics
        numeric_df = df.select_dtypes(include='number')
        desc_stats = numeric_df.describe().transpose().reset_index()
        desc_stats.rename(columns={'index': 'column'}, inplace=True)

        # 4. Combine reports
        stats_summary = pd.merge(desc_stats, missing_report, on='column', how='outer')
        summary_path = os.path.join(self.stats_dir, f'stats_summary_{filename_suffix}.csv')
        stats_summary.to_csv(summary_path, index=False)
        logger.info(f"  - Saved stats summary to: {summary_path}")

        # 5. Report on NA labels
        label_na_cols = [col for col in df.columns if 'label_na' in col]
        if label_na_cols:
            na_counts = df[label_na_cols].sum().reset_index()
            na_counts.columns = ['label_horizon', 'na_label_count']
            na_counts_path = os.path.join(self.stats_dir, f'stats_label_na_{filename_suffix}.csv')
            na_counts.to_csv(na_counts_path, index=False)
            logger.info(f"  - Saved label NA counts to: {na_counts_path}")

        logger.info("Auditing process completed.")
