import os
import pandas as pd
from typing import Dict, Any
import logging
import hashlib
import json
from src.config_models import ProjectConfigs

# Set up a logger for this module
logger = logging.getLogger(__name__)

class ManifestGenerator:
    """
    Generates and manages the task manifest for the data pipeline.
    The manifest is a DataFrame that lists all atomic data processing tasks.
    """

    def __init__(self, configs: ProjectConfigs, manifest_dir: str, raw_data_dir: str):
        """Initializes the ManifestGenerator."""
        self.configs = configs
        self.manifest_dir = manifest_dir
        self.raw_data_dir = raw_data_dir
        os.makedirs(self.manifest_dir, exist_ok=True)
        from src.utils import get_smoke_test_info
        self.smoke_info = get_smoke_test_info(self.raw_data_dir)
        self.interfaces_map = {iface.id: iface for iface in self.configs.interfaces.interfaces}

    def _get_task_id(self, interface_id: str, params: Dict) -> str:
        """Creates a stable, unique identifier for a task."""
        # Use a canonical representation of the params dict
        param_str = json.dumps(params, sort_keys=True)
        return hashlib.sha256(f"{interface_id}-{param_str}".encode()).hexdigest()

    def _enrich_task(self, task: Dict) -> Dict:
        """Adds common metadata like task_id, source_domain, and output_path."""
        iface_id = task['interface_id']
        params = task.get('params', {})
        task_id = self._get_task_id(iface_id, params)

        iface_config = self.interfaces_map.get(iface_id)
        source_domain = iface_config.source_domain if iface_config else 'default'

        # Construct a structured output path
        date_str = params.get('date', 'static')
        if isinstance(date_str, str):
            date_str = date_str.replace('-', '') # Normalize date format

        output_dir = os.path.join(self.raw_data_dir, f"source_domain={source_domain}", f"interface={iface_id}", f"date={date_str}")
        output_path = os.path.join(output_dir, f"part-{task_id[:10]}.parquet")

        task['task_id'] = task_id
        task['source_domain'] = source_domain
        task['output_path'] = output_path
        task.setdefault('status', 'pending')
        return task

    def create_smoke_test_manifest(self) -> pd.DataFrame:
        """Generates a task manifest for the offline smoke test."""
        logger.info("Creating smoke test manifest...")
        # Offline replay doesn't need a full enriched task, but we'll prepare it for consistency
        # In a real scenario, the replay files would also follow the structured path.
        tasks = []
        price_config = self.interfaces_map.get("stock_zh_a_hist")
        if price_config:
            for ticker in self.smoke_info["tickers"]:
                tasks.append({
                    "interface_id": "stock_zh_a_hist", "ticker": ticker, "scope": "smoke_test_price_hist",
                    "replay_path": os.path.join(self.raw_data_dir, 'bootstrap', price_config.bootstrap_source.format(ticker=ticker.replace('.', '')))
                })

        calendar_config = self.interfaces_map.get("tool_trade_date_hist_sina")
        if calendar_config:
            tasks.append({
                "interface_id": "tool_trade_date_hist_sina", "ticker": None, "scope": "market_wide_calendar",
                "replay_path": os.path.join(self.raw_data_dir, 'bootstrap', calendar_config.bootstrap_source)
            })

        enriched_tasks = [self._enrich_task(task) for task in tasks]
        manifest_df = pd.DataFrame(enriched_tasks)
        manifest_path = os.path.join(self.manifest_dir, "tasks_replay.parquet")
        manifest_df.to_parquet(manifest_path, index=False)
        logger.info(f"Replay mode manifest with {len(manifest_df)} tasks saved to {manifest_path}")
        return manifest_df

    def create_online_test_manifest(self) -> pd.DataFrame:
        """Generates a minimal manifest for a single online test task."""
        logger.info("Creating online test manifest...")
        task = {"interface_id": "stock_gpzy_pledge_ratio_em", "params": {"date": "20240906"}}
        enriched_task = self._enrich_task(task)
        manifest_df = pd.DataFrame([enriched_task])
        manifest_path = os.path.join(self.manifest_dir, "tasks_online_test.parquet")
        manifest_df.to_parquet(manifest_path, index=False)
        logger.info(f"Online test manifest with {len(manifest_df)} task saved to {manifest_path}")
        return manifest_df

    def create_full_manifest(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Generates a comprehensive manifest for all configured interfaces."""
        logger.info(f"Creating full manifest for date range: {start_date} to {end_date}...")

        try:
            calendar_path = os.path.join(self.raw_data_dir, 'bootstrap', 'trading_calendar.csv')
            df_calendar = pd.read_csv(calendar_path)
            trade_dates = df_calendar[(df_calendar['date'] >= start_date) & (df_calendar['date'] <= end_date)]['date']
        except FileNotFoundError:
            logger.error(f"Trading calendar not found at {calendar_path}. Cannot generate full manifest.")
            return pd.DataFrame()

        tasks = []
        for iface in self.interfaces_map.values():
            if iface.scope == 'market_wide_single_day':
                for date_str in trade_dates:
                    param_date = date_str.replace('-', '')
                    if 'stock_sse_deal_daily' in iface.id or 'stock_notice_report' in iface.id:
                        param_date = date_str # Some interfaces require hyphens
                    tasks.append({"interface_id": iface.id, "params": {"date": param_date}})

        if not tasks:
            logger.warning("No tasks were generated for the full run.")
            return pd.DataFrame()

        enriched_tasks = [self._enrich_task(task) for task in tasks]
        manifest_df = pd.DataFrame(enriched_tasks)
        manifest_path = os.path.join(self.manifest_dir, "tasks_full_run.parquet")
        manifest_df.to_parquet(manifest_path, index=False)
        logger.info(f"Full run manifest with {len(manifest_df)} tasks saved to {manifest_path}")
        return manifest_df
