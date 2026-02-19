import logging
import sys
import argparse

from src.orchestrator import Orchestrator

def setup_logging():
    """Sets up a basic logger."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)-15s - %(levelname)-8s - %(message)s',
        stream=sys.stdout,
    )

def main():
    """
    This script is the main entry point for running the online data pipeline.
    It uses the Orchestrator to fetch and save raw data from live sources.
    """
    parser = argparse.ArgumentParser(description="Online Financial Data Pipeline Runner")
    parser.add_argument(
        '--full-run',
        action='store_true',
        help="Flag to generate a full manifest for a date range. If not set, a small test manifest is used."
    )
    parser.add_argument('--start-date', type=str, default='2024-01-01', help="Start date for full run (YYYY-MM-DD).")
    parser.add_argument('--end-date', type=str, default='2024-01-31', help="End date for full run (YYYY-MM-DD).")
    args = parser.parse_args()

    setup_logging()
    logger = logging.getLogger("OnlinePipelineRunner")

    try:
        orchestrator = Orchestrator()
        # This entry point always runs in online mode.
        orchestrator.run(
            mode='online',
            full_run=args.full_run,
            start_date=args.start_date,
            end_date=args.end_date
        )
        logger.info("Online pipeline run completed successfully.")
    except Exception as e:
        logger.error(f"An error occurred during the online pipeline run: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
