import yaml
import os
from typing import Dict, Any, List
import logging

# Set up a logger for this module
logger = logging.getLogger(__name__)

def load_yaml_file(filepath: str) -> Dict[str, Any]:
    """
    Loads a single YAML file and returns its content as a dictionary.

    Args:
        filepath: The path to the YAML file.

    Returns:
        A dictionary containing the parsed YAML content.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {filepath}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML file {filepath}: {e}")
        raise

from pydantic import ValidationError
from src.config_models import ProjectConfigs, InterfacesConfig, RateLimitsConfig, SplitConfig

def load_all_configs(config_dir: str) -> ProjectConfigs:
    """
    Loads all YAML configuration files from a directory and validates them
    using Pydantic models.

    Args:
        config_dir: The directory containing the configuration files.

    Returns:
        A validated ProjectConfigs object containing all configurations.
    """
    logger.info(f"Loading and validating configurations from: {config_dir}")
    if not os.path.isdir(config_dir):
        logger.error(f"Config directory not found: {config_dir}")
        raise FileNotFoundError(f"Config directory not found: {config_dir}")

    # Load raw dictionaries from YAML files
    raw_configs = {}
    for filename in sorted(os.listdir(config_dir)):
        if filename.endswith((".yaml", ".yml")):
            config_name = os.path.splitext(filename)[0]
            filepath = os.path.join(config_dir, filename)
            raw_configs[config_name] = load_yaml_file(filepath)
            logger.info(f"  - Loaded '{filename}'")

    try:
        # Validate and structure the configurations using Pydantic models
        validated_configs = ProjectConfigs(
            interfaces=InterfacesConfig(**raw_configs.get('interfaces', {})),
            rate_limits=RateLimitsConfig(**raw_configs.get('rate_limits', {})),
            split=SplitConfig(**raw_configs.get('split', {}).get('split_boundaries', {})),
            features_schema=raw_configs.get('features_schema', {})
        )
        logger.info("All configurations successfully validated.")
        return validated_configs
    except ValidationError as e:
        logger.error(f"Configuration validation failed: {e}")
        raise

import time
import threading

def get_smoke_test_info(raw_data_dir: str) -> Dict[str, Any]:
    """
    Reads the tickers and dates required for the smoke test from the
    bootstrap data files. This ensures the test runs on the correct data.

    Args:
        raw_data_dir: The root directory for raw data.

    Returns:
        A dictionary containing the list of tickers and dates for the smoke test.
    """
    # Per the prompt, we use two specific stocks for the smoke test.
    tickers = ["600519.SH", "601318.SH"]

    # The smoke test dates are read from a dedicated file.
    smoke_dates_path = os.path.join(raw_data_dir, 'bootstrap', 'smoke_dates.txt')
    try:
        with open(smoke_dates_path, 'r', encoding='utf-8') as f:
            dates = [line.strip() for line in f if line.strip()]
        logger.info(f"Loaded smoke test dates: {dates}")
    except FileNotFoundError:
        logger.error(f"Smoke dates file not found: {smoke_dates_path}")
        # Fallback to default dates from the prompt if the file is missing.
        dates = ["2024-12-30", "2025-08-15"]
        logger.warning(f"Using fallback smoke test dates: {dates}")

    return {
        "tickers": tickers,
        "dates": dates
    }

class TokenBucket:
    """A thread-safe token bucket algorithm for rate limiting."""

    def __init__(self, capacity: float, fill_rate: float):
        """
        Initializes the TokenBucket.
        Args:
            capacity: The maximum number of tokens the bucket can hold.
            fill_rate: The rate at which tokens are added to the bucket (tokens per second).
        """
        self.capacity = float(capacity)
        self.fill_rate = float(fill_rate)
        self.tokens = float(capacity)
        self.last_time = time.monotonic()
        self.lock = threading.Lock()

    def _get_tokens(self) -> None:
        """Calculates and adds new tokens based on elapsed time. Not thread-safe."""
        if self.tokens < self.capacity:
            now = time.monotonic()
            time_passed = now - self.last_time
            self.tokens += time_passed * self.fill_rate
            if self.tokens > self.capacity:
                self.tokens = self.capacity
            self.last_time = now

    def consume(self, tokens: int = 1) -> None:
        """
        Consumes a number of tokens from the bucket. Blocks if not enough tokens are available.
        Args:
            tokens: The number of tokens to consume. Defaults to 1.
        """
        with self.lock:
            self._get_tokens()
            while self.tokens < tokens:
                required = tokens - self.tokens
                sleep_time = required / self.fill_rate
                time.sleep(sleep_time)
                self._get_tokens()
            self.tokens -= tokens
