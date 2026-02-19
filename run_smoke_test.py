import logging
import sys

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
    This script runs the offline smoke test for the data pipeline.
    It uses the Orchestrator to run the pipeline in 'replay' mode, which
    processes the pre-saved bootstrap data end-to-end to ensure all
    components (normalize, assemble, label, export, audit) are working correctly.
    """
    setup_logging()
    logger = logging.getLogger("SmokeTestRunner")

    try:
        orchestrator = Orchestrator()
        # The smoke test always runs in replay mode.
        orchestrator.run(mode='replay')
        logger.info("Smoke test completed successfully.")
    except Exception as e:
        logger.error(f"An error occurred during the smoke test: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
