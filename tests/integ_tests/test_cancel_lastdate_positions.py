"""Integration tests for cancel_lastdate_positions.py functionality."""

import pytest
import logging
import os
import sys
import json
import glob
import argparse
from pathlib import Path
from datetime import datetime, timezone

from src.infra.PositionData import PositionData
from src.infra.PositionClient import PositionClient
from src.infra.mtBase import mtBase
from src.infra.TradingConfig import TradingConfig

from cancel_lastdate_positions import main as cancel_lastdate_positions_main

# Setup logger
logger = logging.getLogger(__name__)


class TestCancelLastdatePositions:
    """Integration tests for cancel_lastdate_positions functionality."""
    
    def test_cancel_lastdate_positions_dry_run_integration(self):
        """
        Integration test: Run cancel_lastdate_positions.py script in dry-run mode and validate output.
        
        This test will:
        1. Run the cancel_lastdate_positions.py script in default dry-run mode (without --apply flag)
        2. Use default n_dates=1 to cancel positions from the most recent date
        3. Write output to artifacts/dev directory
        4. Load and validate the generated JSON files
        5. Verify that positions from the last date are identified correctly for closure
        """
        # Check if credential files exist
        credentials_path = 'secrets/mt5_acc_cred.yaml'
        config_path = 'secrets/mt5_config.ini'
        
        if not os.path.exists(credentials_path) or not os.path.exists(config_path):
            pytest.skip(f"Credential files not found: {credentials_path} or {config_path}")
        
        # Use demo account for integration test
        account_name = 'mt5demo_acc_usd'
        config_file = 'config/trading_config_dev.yaml'
        
        # Check if config file exists
        if not os.path.exists(config_file):
            pytest.skip(f"Trading config file not found: {config_file}")
        
        # Create mock arguments for testing
        class MockArgs:
            def __init__(self):
                self.account = account_name
                self.n_dates = 1
                self.config = config_file
                self.apply = False  # Always dry-run for testing
                self.place_time = None
        
        args = MockArgs()
        
        # Get timestamp for identifying test artifacts
        test_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dry_run_suffix = f"integ_test_{test_timestamp}"
        
        try:
            # Run cancel_lastdate_positions in dry-run mode with test suffix
            logger.info("Running cancel_lastdate_positions.py integration test...")
            results = cancel_lastdate_positions_main(args, dry_run_suffix=dry_run_suffix, setup_logs=False)
            
            logger.info(f"Integration test completed. {len(results)} positions would be closed.")
            
            # Validate results structure - results are PositionData objects
            assert isinstance(results, list), "Results should be a list"
            
            # Each result should be a PositionData object
            for result in results:
                assert isinstance(result, PositionData), "Each result should be a PositionData object"
                # Validate that the position has required attributes
                assert hasattr(result, 'ticket'), "Position should have ticket"
                assert hasattr(result, 'symbol'), "Position should have symbol"
                assert hasattr(result, 'magic'), "Position should have magic"
                assert hasattr(result, 'volume'), "Position should have volume"
                assert hasattr(result, 'type'), "Position should have type"
                assert hasattr(result, 'time'), "Position should have time"
            
            # Check that artifacts file was created (only if function didn't return early)
            config = TradingConfig(config_file)
            artifacts_dir = Path(config.artifacts_dir)
            
            # Find the generated dry run file
            pattern = f"dry_run_closures_lastdate_*_{dry_run_suffix}.json"
            matching_files = list(artifacts_dir.glob(pattern))
            
            # If no results were returned, the function likely returned early and no artifacts file was created
            if len(results) == 0:
                logger.info("No positions found to close - function returned early, no artifacts file expected")
                assert len(matching_files) == 0, f"Expected no artifacts file when function returns early, found {len(matching_files)}: {[f.name for f in matching_files]}"
                logger.info("✓ Integration test passed: cancel_lastdate_positions dry run validation (early return)")
                return
            else:
                assert len(matching_files) == 1, f"Expected exactly one artifacts file matching {pattern} in {artifacts_dir}, found {len(matching_files)}: {[f.name for f in matching_files]}"
            
            artifacts_file = matching_files[0]
            logger.info(f"Found artifacts file: {artifacts_file}")
            
            # Validate artifacts file contents
            with open(artifacts_file, 'r', encoding='utf-8') as f:
                saved_results = json.load(f)
            
            # Convert PositionData objects to dictionaries for comparison
            results_as_dicts = [pos.to_dict() for pos in results]
            assert saved_results == results_as_dicts, "Saved results should match returned results when serialized"
            
            # Verify all positions are from the same date (or at most n_dates different dates)
            if results:
                dates_in_results = {pos.time.date() for pos in results}
                logger.info(f"Positions are from {len(dates_in_results)} date(s): {sorted(dates_in_results)}")
                assert len(dates_in_results) <= args.n_dates, f"Expected positions from at most {args.n_dates} date(s), found {len(dates_in_results)}"
            
            logger.info("✓ Integration test passed: cancel_lastdate_positions dry run validation successful")
            
            # Clean up test artifacts
            artifacts_file.unlink()
            logger.info(f"Cleaned up test artifacts file: {artifacts_file}")
            
        except Exception as e:
            logger.error(f"Integration test failed: {e}")
            raise
