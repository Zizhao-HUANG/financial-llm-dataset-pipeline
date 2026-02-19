import pandas as pd
from typing import Dict, Any, List
import logging
import os
import random
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from src.utils import TokenBucket
from src.config_models import ProjectConfigs

# Set up a logger for this module
logger = logging.getLogger(__name__)

class ReplayTransport:
    """
    A transport layer that "fetches" data by replaying from local files.
    This is used for the offline smoke test to read from the bootstrap data,
    simulating the behavior of a live data fetching component.
    """

    def __init__(self, configs: ProjectConfigs):
        """
        Initializes the ReplayTransport.

        Args:
            configs: The validated configuration object.
        """
        self.configs = configs

    def fetch(self, tasks_df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Reads data from local CSV files, saves them to their designated
        Parquet output paths, and returns a list of task-result dicts.
        This mimics the behavior of HttpTransport for a consistent interface.
        """
        logger.info(f"Replaying data from {len(tasks_df)} tasks specified in the manifest...")

        results = []
        for _, task in tasks_df.iterrows():
            replay_path = task["replay_path"]
            output_path = task["output_path"]
            logger.info(f"  - Replaying '{task['interface_id']}' from {replay_path} -> {output_path}")

            try:
                df = pd.read_csv(replay_path)
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                df.to_parquet(output_path, index=False)
                # The result contains the task metadata and the path to the new raw file
                results.append({"task": task, "raw_file_path": output_path})
            except FileNotFoundError:
                logger.error(f"    - Replay file not found: {replay_path}")
            except Exception as e:
                logger.error(f"    - Failed to process replay file {replay_path}: {e}", exc_info=True)

        num_success = len(results)
        num_total = len(tasks_df)
        logger.info(f"Successfully replayed and saved {num_success}/{num_total} data sources.")

        if num_success == 0 and num_total > 0:
            raise RuntimeError("Failed to process any replay data.")

        return results


class HttpTransport:
    """
    A transport layer that fetches data from live akshare endpoints.
    This class handles online data collection, including proxy rotation,
    domain-specific rate limiting, and robust, resumable checkpointing.
    """

    def __init__(self, configs: ProjectConfigs, manifest_dir: str, raw_data_dir: str):
        """Initializes the HttpTransport."""
        self.configs = configs
        self.raw_data_dir = raw_data_dir
        self.checkpoint_path = os.path.join(manifest_dir, "checkpoints.parquet")
        self.checkpoint_lock = threading.Lock()
        try:
            import akshare as ak
            self.ak = ak
        except ImportError:
            logger.error("The 'akshare' library is required for HttpTransport. Please install it.")
            raise

        # Proxy and Rate Limiter setup
        self._setup_proxy()
        self._setup_rate_limiters()

    def _setup_proxy(self):
        """Loads proxy credentials from environment variables."""
        self.BRD_HOST = os.environ.get("BRD_HOST", "brd.superproxy.io")
        self.BRD_PORT = int(os.environ.get("BRD_PORT", 33335))
        self.BRD_USERNAME_BASE = os.environ.get("BRD_USERNAME_BASE")
        self.BRD_PASSWORD = os.environ.get("BRD_PASSWORD")
        if not self.BRD_USERNAME_BASE or not self.BRD_PASSWORD:
            raise ValueError("Missing Bright Data proxy credentials in environment variables.")

    def _setup_rate_limiters(self):
        """Initializes domain-specific rate limiters from config."""
        self.rate_limiters = {}
        for domain_config in self.configs.rate_limits.domains:
            self.rate_limiters[domain_config.domain] = TokenBucket(domain_config.capacity, domain_config.rate)
            logger.info(f"Initialized rate limiter for domain '{domain_config.domain}': {domain_config.rate} req/s")

    def _get_domain_config(self, source_domain: str):
        """Gets the configuration for a specific source domain."""
        domain_configs = self.configs.rate_limits.domains
        config = next((d for d in domain_configs if d.domain == source_domain), None)
        if not config:
            config = next((d for d in domain_configs if d.domain == 'default'), None)
        return config

    def _set_proxy_session(self) -> None:
        """Sets the HTTP/HTTPS proxy with a new random session ID."""
        session_id = str(random.randint(100000, 999999))
        proxy_user = f"{self.BRD_USERNAME_BASE}-session-{session_id}"
        proxy_url = f"http://{proxy_user}:{self.BRD_PASSWORD}@{self.BRD_HOST}:{self.BRD_PORT}"
        os.environ["HTTP_PROXY"] = proxy_url
        os.environ["HTTPS_PROXY"] = proxy_url

    def _fetch_one(self, interface_id: str, params: Dict, source_domain: str) -> pd.DataFrame:
        """
        Fetches data for a single task, wrapped in a retry loop.
        It dynamically gets the akshare function using getattr.
        """
        try:
            ak_func = getattr(self.ak, interface_id)
        except AttributeError:
            logger.error(f"No function named '{interface_id}' found in the akshare library.")
            raise ValueError(f"No function named '{interface_id}' found in the akshare library.")

        domain_config = self._get_domain_config(source_domain)
        max_tries = domain_config.retry if domain_config else 3
        sleep_base = 1.0

        for attempt in range(max_tries):
            try:
                self._set_proxy_session()
                logger.info(f"Calling endpoint: {ak_func.__name__} with params {params} (Attempt {attempt + 1}/{max_tries})")
                df = ak_func(**params)
                return df
            except requests.exceptions.RequestException as e:
                logger.warning(f"  - Network-level error for {interface_id} on attempt {attempt + 1}: {e}")
            except Exception as e:
                logger.warning(f"  - General error for {interface_id} on attempt {attempt + 1}: {e}")

            if attempt + 1 < max_tries:
                time.sleep(sleep_base * (2 ** attempt) + random.random())
            else:
                logger.error(f"  - All {max_tries} attempts failed for {interface_id}. Giving up.")
        return pd.DataFrame()

    def _save_and_checkpoint(self, task: pd.Series, df: pd.DataFrame) -> str:
        """
        Saves the dataframe and atomically updates the checkpoint file using a
        robust read-concat-overwrite pattern.
        """
        output_path = task['output_path']
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df.to_parquet(output_path, index=False)

        with self.checkpoint_lock:
            new_checkpoint = pd.DataFrame([{'task_id': task['task_id']}])
            if os.path.exists(self.checkpoint_path):
                try:
                    existing_checkpoints = pd.read_parquet(self.checkpoint_path)
                    updated_checkpoints = pd.concat([existing_checkpoints, new_checkpoint], ignore_index=True)
                except Exception as e:
                    logger.warning(f"Could not read existing checkpoint file, it might be corrupted. Overwriting. Error: {e}")
                    updated_checkpoints = new_checkpoint
            else:
                updated_checkpoints = new_checkpoint

            updated_checkpoints.to_parquet(self.checkpoint_path, engine='pyarrow', index=False)

        logger.info(f"  - Saved and checkpointed task '{task['task_id'][:10]}' to {output_path}")
        return output_path

    def _fetch_and_save_task(self, task: pd.Series) -> Dict[str, Any]:
        """Wrapper to rate-limit, fetch, save, and checkpoint a single task."""
        source_domain = task.get('source_domain', 'default')
        limiter = self.rate_limiters.get(source_domain, self.rate_limiters.get('default'))

        if limiter:
            limiter.consume()

        df = self._fetch_one(task['interface_id'], task.get('params', {}), source_domain)

        if not df.empty:
            output_path = self._save_and_checkpoint(task, df)
            return {"task": task, "raw_file_path": output_path}
        return {}

    def fetch(self, tasks_df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Processes a manifest of tasks concurrently, with checkpointing."""
        completed_ids = set()
        if os.path.exists(self.checkpoint_path):
            try:
                completed_df = pd.read_parquet(self.checkpoint_path)
                completed_ids = set(completed_df['task_id'])
                logger.info(f"Loaded {len(completed_ids)} completed tasks from checkpoint file.")
            except Exception as e:
                logger.warning(f"Could not load checkpoint file: {e}. Starting from scratch.")

        pending_tasks_df = tasks_df[~tasks_df['task_id'].isin(completed_ids)]
        logger.info(f"Found {len(pending_tasks_df)} pending tasks out of {len(tasks_df)} total.")

        if pending_tasks_df.empty:
            logger.info("No new tasks to run.")
            return []

        results = []
        domain_config = self._get_domain_config('default')
        max_workers = domain_config.concurrency if domain_config else 2

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_task_id = {
                executor.submit(self._fetch_and_save_task, task): task['task_id']
                for _, task in pending_tasks_df.iterrows()
            }
            logger.info(f"Submitted {len(future_to_task_id)} tasks to thread pool with {max_workers} workers.")

            for future in as_completed(future_to_task_id):
                task_id = future_to_task_id[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as exc:
                    logger.error(f"  - Task ID '{task_id[:10]}' generated an exception: {exc}")

        logger.info(f"Completed fetching. {len(results)} new tasks were successful.")
        return results
