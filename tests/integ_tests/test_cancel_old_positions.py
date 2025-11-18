"""Integration tests for cancel_old_positions.py functionality."""

import pytest
import logging
import os
import sys
import json
import glob
import argparse
from pathlib import Path
from datetime import datetime, timezone

from src.infra.PredictionData import PredictionData
from src.infra.PredictionClient import PredictionClient
from src.infra.PositionClient import PositionClient
from src.infra.mtBase import mtBase
from src.infra.TradingConfig import TradingConfig

from cancel_old_positions import main as cancel_old_positions_main

# Setup logger
logger = logging.getLogger(__name__)


class TestCancelOldPositions:
    """Integration tests for cancel_old_positions functionality."""
    
    def test_cancel_old_positions_dry_run_integration(self):
        """
        Integration test: Run cancel_old_positions.py script in dry-run mode and validate output.
        
        This test will:
        1. Run the cancel_old_positions.py script in default dry-run mode (without --apply flag)
        2. Use predictions from predictions/dev directory
        3. Write output to artifacts/dev directory
        4. Load and validate the generated JSON files
        5. Verify that positions are identified correctly for closure
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
                self.group = "mt5"
                self.config = config_file
                self.apply = False  # Always dry-run for testing
        
        args = MockArgs()
        
        # Get timestamp for identifying test artifacts
        test_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dry_run_suffix = f"integ_test_{test_timestamp}"
        
        try:
            # Run cancel_old_positions in dry-run mode with test suffix
            logger.info("Running cancel_old_positions.py integration test...")
            results = cancel_old_positions_main(args, dry_run_suffix=dry_run_suffix, setup_logs=False)
            
            logger.info(f"Integration test completed. {len(results)} positions would be closed.")
            
            # Validate results structure - results are PositionData objects
            assert isinstance(results, list), "Results should be a list"
            
            # Import PositionData for type checking
            from src.infra.PositionData import PositionData
            
            # Each result should be a PositionData object
            for result in results:
                assert isinstance(result, PositionData), "Each result should be a PositionData object"
                # Validate that the position has required attributes
                assert hasattr(result, 'ticket'), "Position should have ticket"
                assert hasattr(result, 'symbol'), "Position should have symbol"
                assert hasattr(result, 'magic'), "Position should have magic"
                assert hasattr(result, 'volume'), "Position should have volume"
                assert hasattr(result, 'type'), "Position should have type"
            
            # Check that artifacts file was created (only if function didn't return early)
            config = TradingConfig(config_file)
            artifacts_dir = Path(config.artifacts_dir)
            
            # Find the generated dry run file
            pattern = f"dry_run_closures_*_{dry_run_suffix}.json"
            matching_files = list(artifacts_dir.glob(pattern))
            
            # If no results were returned, the function likely returned early and no artifacts file was created
            if len(results) == 0:
                logger.info("No positions found to close - function returned early, no artifacts file expected")
                assert len(matching_files) == 0, f"Expected no artifacts file when function returns early, found {len(matching_files)}: {[f.name for f in matching_files]}"
                logger.info("✓ Integration test passed: cancel_old_positions dry run validation (early return)")
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
            
            logger.info("✓ Integration test passed: cancel_old_positions dry run validation successful")
            
            # Clean up test artifacts
            artifacts_file.unlink()
            logger.info(f"Cleaned up test artifacts file: {artifacts_file}")
            
        except Exception as e:
            logger.error(f"Integration test failed: {e}")
            raise
    
    def test_cancel_old_positions_with_no_positions(self):
        """
        Integration test: Verify behavior when there are no positions to close.
        """
        # Check if credential files exist
        credentials_path = 'secrets/mt5_acc_cred.yaml'
        config_path = 'secrets/mt5_config.ini'
        
        if not os.path.exists(credentials_path) or not os.path.exists(config_path):
            pytest.skip(f"Credential files not found: {credentials_path} or {config_path}")
        
        account_name = 'mt5demo_acc_usd'
        config_file = 'config/trading_config_dev.yaml'
        
        if not os.path.exists(config_file):
            pytest.skip(f"Trading config file not found: {config_file}")
        
        class MockArgs:
            def __init__(self):
                self.account = account_name
                self.group = "mt5"
                self.config = config_file
                self.apply = False
        
        args = MockArgs()
        
        # Get timestamp for identifying test artifacts
        test_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dry_run_suffix = f"integ_test_{test_timestamp}"
        
        try:
            logger.info("Testing cancel_old_positions with no positions scenario...")
            results = cancel_old_positions_main(args, dry_run_suffix=dry_run_suffix, setup_logs=False)
            
            # Results should be a list (might be empty)
            assert isinstance(results, list), "Results should be a list"
            logger.info(f"Test completed. {len(results)} positions identified for closure.")
            
            # Check that artifacts file was created (even if function returned early)
            config = TradingConfig(config_file)
            artifacts_dir = Path(config.artifacts_dir)
            
            pattern = f"dry_run_closures_*_{dry_run_suffix}.json"
            matching_files = list(artifacts_dir.glob(pattern))
            
            # The function might return early without creating an artifacts file if no positions/predictions
            # In that case, we should accept it as valid behavior
            if len(matching_files) == 0:
                logger.info("No artifacts file created - function returned early (no positions or predictions found)")
                logger.info("✓ Integration test passed: cancel_old_positions no positions scenario (early return)")
            else:
                assert len(matching_files) == 1, f"Expected at most one artifacts file, found {len(matching_files)}: {[f.name for f in matching_files]}"
                
                artifacts_file = matching_files[0]
                logger.info(f"Found artifacts file: {artifacts_file}")
                
                # Validate file contents
                with open(artifacts_file, 'r', encoding='utf-8') as f:
                    saved_results = json.load(f)
                
                # Convert PositionData objects to dictionaries for comparison
                from src.infra.PositionData import PositionData
                results_as_dicts = [pos.to_dict() for pos in results] if results else []
                assert saved_results == results_as_dicts, "Saved results should match returned results when serialized"
                
                logger.info("✓ Integration test passed: cancel_old_positions no positions scenario")
                
                # Clean up
                artifacts_file.unlink()
                logger.info(f"Cleaned up test artifacts file: {artifacts_file}")
            
        except Exception as e:
            logger.error(f"Integration test failed: {e}")
            raise
    
    def test_cancel_old_positions_connection_validation(self):
        """
        Integration test: Verify MT5 connection and basic setup work correctly.
        """
        # Check if credential files exist
        credentials_path = 'secrets/mt5_acc_cred.yaml'
        config_path = 'secrets/mt5_config.ini'
        
        if not os.path.exists(credentials_path) or not os.path.exists(config_path):
            pytest.skip(f"Credential files not found: {credentials_path} or {config_path}")
        
        account_name = 'mt5demo_acc_usd'
        config_file = 'config/trading_config_dev.yaml'
        
        if not os.path.exists(config_file):
            pytest.skip(f"Trading config file not found: {config_file}")
        
        try:
            # Test individual components used by cancel_old_positions
            config = TradingConfig(config_file)
            config.validate()
            
            base = mtBase(account_name, config.credentials_path, config.mt5_config_path)
            base.mt5_init()
            
            # Test position client
            pos_client = PositionClient(base=base)
            positions = pos_client.get_positions()
            logger.info(f"Retrieved {len(positions)} positions from MT5")
            
            # Test prediction client
            predictions_dir = Path(config.predictions_dir)
            pred_client = PredictionClient(base=base, predictions_dir=predictions_dir)
            predictions = pred_client.load_predictions("mt5")
            logger.info(f"Loaded {len(predictions)} predictions")
            
            logger.info("✓ Integration test passed: cancel_old_positions connection validation")
            
        except Exception as e:
            logger.error(f"Connection validation test failed: {e}")
            raise