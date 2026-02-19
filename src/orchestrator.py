import logging
import os

from src.utils import load_all_configs, get_smoke_test_info
from src.manifest import ManifestGenerator
from src.transport import ReplayTransport, HttpTransport
from src.normalize import Normalizer
from src.assemble import Assembler
from src.label import Labeler
from src.export import Exporter
from src.audit import Auditor

logger = logging.getLogger(__name__)

class Orchestrator:
    """
    Central class to orchestrate the entire financial data pipeline.
    It initializes all components and runs the pipeline based on the specified mode.
    """

    def __init__(self):
        """Initializes the Orchestrator, setting up paths and loading configs."""
        logger.info("Initializing pipeline orchestrator...")

        # --- Path and Config Setup ---
        self.ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.CONFIG_DIR = os.path.join(self.ROOT_DIR, 'config')
        self.INPUTS_DIR = os.path.join(self.ROOT_DIR, 'inputs')
        self.MANIFEST_DIR = os.path.join(self.ROOT_DIR, 'manifests')
        self.RAW_DIR = os.path.join(self.ROOT_DIR, 'data_raw')
        self.SILVER_DIR = os.path.join(self.ROOT_DIR, 'data_silver')
        self.GOLD_DIR = os.path.join(self.ROOT_DIR, 'data_gold')
        self.EXPORTS_DIR = os.path.join(self.ROOT_DIR, 'exports')

        self.configs = load_all_configs(self.CONFIG_DIR)

        # --- Component Initialization ---
        self.manifest_generator = ManifestGenerator(self.configs, self.MANIFEST_DIR, self.RAW_DIR)
        self.normalizer = Normalizer(self.configs, self.SILVER_DIR)
        self.assembler = Assembler(self.configs, self.SILVER_DIR, self.GOLD_DIR, self.INPUTS_DIR, self.RAW_DIR)
        self.labeler = Labeler(self.configs, self.GOLD_DIR, self.SILVER_DIR)
        self.exporter = Exporter(self.configs, self.GOLD_DIR, self.EXPORTS_DIR)
        self.auditor = Auditor(self.configs, self.GOLD_DIR, self.EXPORTS_DIR)

    def run(self, mode: str, full_run: bool = False, start_date: str = '2024-01-01', end_date: str = '2024-01-31'):
        """
        Runs the data pipeline in the specified mode.

        Args:
            mode: The execution mode ('replay' or 'online').
            full_run: Flag to generate a full manifest for a date range in online mode.
            start_date: Start date for the full run.
            end_date: End date for the full run.
        """
        logger.info(f"==================================================")
        logger.info(f"=== Starting Data Pipeline in --mode={mode} ===")
        logger.info(f"==================================================")

        if mode == 'replay':
            self._run_replay_mode()
        elif mode == 'online':
            self._run_online_mode(full_run, start_date, end_date)
        else:
            raise ValueError(f"Invalid mode specified: {mode}")

        logger.info(f"==================================================")
        logger.info(f"=== Pipeline Run in --mode={mode} Finished ===")
        logger.info(f"==================================================")

    def _run_replay_mode(self):
        """Executes the full offline replay (smoke test) pipeline."""
        logger.info("Running full offline replay pipeline...")
        tasks_df = self.manifest_generator.create_smoke_test_manifest()
        transport = ReplayTransport(self.configs)
        fetched_results = transport.fetch(tasks_df)

        if not fetched_results:
            logger.warning("Replay transport returned no data. Skipping further steps.")
            return

        silver_data_paths = self.normalizer.process(fetched_results)

        smoke_info = get_smoke_test_info(self.RAW_DIR)
        gold_features_path = self.assembler.process(silver_data_paths, smoke_info['dates'][0], smoke_info['dates'][-1])
        self.labeler.process(gold_features_path)
        self.exporter.export_all(filename_suffix="smoke")
        self.auditor.run_all_audits(filename_suffix="smoke")

    def _run_online_mode(self, full_run: bool, start_date: str, end_date: str):
        """Executes the online data fetching and processing pipeline."""
        transport = HttpTransport(self.configs, self.MANIFEST_DIR, self.RAW_DIR)

        if full_run:
            logger.info("Running online full run pipeline...")
            tasks_df = self.manifest_generator.create_full_manifest(start_date, end_date)
        else:
            logger.info("Running online test pipeline (fetch only)...")
            tasks_df = self.manifest_generator.create_online_test_manifest()

        if tasks_df.empty:
            logger.warning("Manifest is empty. No tasks to run.")
            return

        # In online mode, we just fetch and save the raw data.
        # Normalization and further steps would be a separate run.
        fetched_results = transport.fetch(tasks_df)

        if fetched_results:
            logger.info(f"Successfully fetched and checkpointed {len(fetched_results)} new raw data files.")
            # The normalization step is now decoupled. A production system might
            # trigger this as a subsequent, separate step. For now, we stop after fetch.
            # silver_data_paths = self.normalizer.process(fetched_results)
            # logger.info("Online data normalization complete.")
        else:
            logger.warning("No new data was fetched from online sources.")
