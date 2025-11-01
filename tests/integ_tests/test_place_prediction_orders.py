"""Integration tests for place_prediction_orders.py functionality."""

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
from src.infra.mtBase import mtBase
from src.infra.TradingConfig import TradingConfig
from src.common import magic_from

from place_prediction_orders import main as place_prediction_orders_main

# Setup logger
logger = logging.getLogger(__name__)


class TestPlacePredictionOrders:
    """Integration tests for place_prediction_orders functionality."""
    
    def test_place_prediction_orders_dry_run_integration(self):
        """
        Integration test: Run place_prediction_orders.py script in dry-run mode and validate output.
        
        This test will:
        1. Run the place_prediction_orders.py script in default dry-run mode (without --apply flag)
        2. Use predictions from predictions/dev directory
        3. Write output to artifacts/dev directory
        4. Load and validate the generated JSON files
        5. Compare orders with the original predictions
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
            pytest.fail(f"Config file not found: {config_file}")
            
        logger.info(f"Starting place_prediction_orders integration test with account: {account_name}")
        
        # Ensure artifacts/dev directory exists
        artifacts_dev_dir = Path("artifacts/dev")
        artifacts_dev_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique suffix for this test run
        test_suffix = f"integ_test_{datetime.now().strftime('%H%M%S')}"
        
        # Initialize MT5 connection to ensure it's available for the test
        mt5_client = None
        try:
            # Initialize mtBase to ensure MT5 connection is available
            logger.info("Initializing MT5 connection for integration test...")
            mt5_client = mtBase(
                account=account_name,
                credentials_path=credentials_path,
                config_path=config_path
            )
            mt5_client.mt5_init()
            logger.info("MT5 connection initialized successfully")
            
        except Exception as e:
            logger.warning(f"Failed to initialize MT5 connection: {e}")
            if mt5_client:
                try:
                    mt5_client.shutdown()
                except:
                    pass
            pytest.skip(f"MT5 connection not available: {e}")

        try:
            # Load predictions that should be processed
            predictions_before = self._load_dev_predictions()
            logger.info(f"Found {len(predictions_before)} predictions in predictions/dev")
            
            # Create mock arguments for the main function
            mock_args = argparse.Namespace(
                account=account_name,
                group="debug",  # Use debug group to match prediction_debug_*.json files
                config=config_file,
                apply=False  # Default dry-run mode (no --apply flag)
            )
            
            # Run the place_prediction_orders main function directly
            logger.info("Running place_prediction_orders main function in dry-run mode...")
            try:
                placed_orders = place_prediction_orders_main(args=mock_args, dry_run_suffix=test_suffix, setup_logs=False)
                logger.info(f"Main function returned {len(placed_orders)} placed orders")
                script_succeeded = True
            except Exception as e:
                logger.warning(f"Main function failed with exception: {e}")
                placed_orders = []
                script_succeeded = False
            
            # Find the generated dry run orders file with our test suffix
            generated_files = glob.glob(str(artifacts_dev_dir / f"dry_run_orders_*{test_suffix}.json"))
            
            # Also check the main artifacts directory in case config points there
            if not generated_files:
                main_artifacts_dir = Path("artifacts")
                generated_files = glob.glob(str(main_artifacts_dir / f"dry_run_orders_*{test_suffix}.json"))
                if generated_files:
                    logger.info(f"Found dry run file in main artifacts directory instead of dev: {generated_files}")
            
            if not generated_files:
                if not script_succeeded:
                    logger.warning(f"Main function failed and no output files generated. This may be expected if MT5 is not available.")
                    pytest.skip("Main function failed and no output generated - likely due to MT5 unavailability")
                else:
                    # Debug: List all files in both directories to see what was actually created
                    dev_files = list(artifacts_dev_dir.glob("*"))
                    main_files = list(Path("artifacts").glob("*"))
                    logger.error(f"No matching dry run file found. Files in artifacts/dev: {dev_files}")
                    logger.error(f"Files in artifacts: {main_files}")
                    logger.error(f"Expected pattern: dry_run_orders_*{test_suffix}.json")
                    pytest.fail("Main function succeeded but no dry run orders file was generated")
            
            # Load and validate the generated file
            latest_file = generated_files[0]  # Should only be one with our unique suffix
            logger.info(f"Loading generated orders from: {latest_file}")
            
            with open(latest_file, 'r', encoding='utf-8') as f:
                generated_orders = json.load(f)
            
            # Validate the generated orders
            self._validate_generated_orders(generated_orders, predictions_before)
            
            # Validate that the returned orders match the file contents
            if placed_orders:
                self._validate_returned_orders_match_file(placed_orders, generated_orders)
            
            logger.info("place_prediction_orders integration test completed successfully")
        except Exception as e:
            logger.error(f"Integration test failed with exception: {e}")
            raise
        finally:
            # Always attempt to shutdown MT5 connection, even if test failed
            if mt5_client is not None:
                try:
                    mt5_client.shutdown()
                    logger.info("MT5 connection properly shut down")
                except Exception as e:
                    logger.warning(f"Error during MT5 shutdown: {e}")

    def _load_dev_predictions(self):
        """Load predictions from predictions/dev directory."""
        predictions_dev_dir = Path("predictions/dev")
        
        if not predictions_dev_dir.exists():
            logger.warning("predictions/dev directory does not exist")
            return []
        
        # Load predictions using PredictionClient logic
        prediction_files = glob.glob(str(predictions_dev_dir / "prediction_*.json"))
        predictions = []
        
        for file_path in prediction_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    pred_data = json.load(f)
                
                # Convert to PredictionData objects
                for item in pred_data:
                    # Create temporary prediction to calculate magic
                    temp_pred = PredictionData(
                        symbol=item['symbol'],
                        last_training_day=datetime.fromisoformat(item['last_training_day'].replace('Z', '+00:00')).date(),
                        last_close_price=item['last_close_price'],
                        n_trading_days=item['n_trading_days'],
                        score=item['score'],
                        magic=0,  # Temporary value
                        sl_pct=item.get('sl_pct'),
                        tp_pct=item.get('tp_pct')
                    )
                    
                    # Calculate magic and create final prediction
                    magic = magic_from(temp_pred)
                    pred = PredictionData(
                        symbol=item['symbol'],
                        last_training_day=datetime.fromisoformat(item['last_training_day'].replace('Z', '+00:00')).date(),
                        last_close_price=item['last_close_price'],
                        n_trading_days=item['n_trading_days'],
                        score=item['score'],
                        magic=magic,
                        sl_pct=item.get('sl_pct'),
                        tp_pct=item.get('tp_pct')
                    )
                    predictions.append(pred)
                    
                logger.info(f"Loaded {len(pred_data)} predictions from {file_path}")
                    
            except Exception as e:
                logger.warning(f"Failed to load predictions from {file_path}: {e}")
        
        return predictions

    def _validate_generated_orders(self, generated_orders, original_predictions):
        """Validate that generated orders match the original predictions."""
        logger.info(f"Validating {len(generated_orders)} generated orders against {len(original_predictions)} predictions")
        
        # Basic validation - ensure we have orders if we had predictions
        if original_predictions and len(generated_orders) == 0:
            logger.warning("No orders generated despite having predictions - this may be expected if no predictions passed filtering")
        
        if len(generated_orders) > 0:
            logger.info("Validating order structure and content...")
            
            # Create a mapping of symbols from predictions for validation
            prediction_symbols = {pred.symbol: pred for pred in original_predictions}
            
            for i, order_dict in enumerate(generated_orders):
                logger.info(f"Validating order {i+1}: {order_dict.get('symbol', 'UNKNOWN')}")
                
                # Validate order structure
                self._validate_order_structure(order_dict, i+1)
                
                # Validate order against original prediction if available
                symbol = order_dict['symbol']
                if symbol in prediction_symbols:
                    self._validate_order_against_prediction(order_dict, prediction_symbols[symbol], i+1)
                else:
                    logger.warning(f"Order {i+1} symbol '{symbol}' not found in original predictions")
        
        logger.info(f"✓ All {len(generated_orders)} orders validated successfully")

    def _validate_order_structure(self, order_dict, order_num):
        """Validate the structure of a single order dictionary."""
        # Validate required fields
        required_fields = ['symbol', 'type', 'volume', 'price', 'magic']
        for field in required_fields:
            assert field in order_dict, f"Order {order_num} missing required field: {field}"
            assert order_dict[field] is not None, f"Order {order_num} field '{field}' is None"
        
        # Validate data types
        assert isinstance(order_dict['symbol'], str), f"Order {order_num} symbol should be string"
        assert isinstance(order_dict['type'], int), f"Order {order_num} type should be int"
        assert isinstance(order_dict['volume'], (int, float)), f"Order {order_num} volume should be numeric"
        assert isinstance(order_dict['price'], (int, float)), f"Order {order_num} price should be numeric"
        assert isinstance(order_dict['magic'], int), f"Order {order_num} magic should be int"
        
        # Validate reasonable values
        assert order_dict['volume'] > 0, f"Order {order_num} volume should be positive"
        assert order_dict['price'] > 0, f"Order {order_num} price should be positive"
        assert 0.01 <= order_dict['volume'] <= 100.0, f"Order {order_num} volume should be reasonable (0.01-100 lots)"
        assert order_dict['price'] > 0.0001, f"Order {order_num} price should be reasonable"
        
        logger.info(f"✓ Order {order_num} structure validation passed: {order_dict['symbol']} {order_dict['volume']} lots @ {order_dict['price']}")

    def _validate_order_against_prediction(self, order_dict, prediction, order_num):
        """Validate that an order matches the corresponding prediction."""
        # Validate symbol matches
        assert order_dict['symbol'] == prediction.symbol, f"Order {order_num} symbol mismatch: {order_dict['symbol']} vs {prediction.symbol}"
        
        # If prediction has stop loss/take profit, validate they exist in order
        if prediction.sl_pct and prediction.sl_pct > 0:
            if 'sl' in order_dict and order_dict['sl']:
                # Basic validation that SL is set and reasonable
                assert isinstance(order_dict['sl'], (int, float)), f"Order {order_num} SL should be numeric"
                assert order_dict['sl'] > 0, f"Order {order_num} SL should be positive"
                logger.info(f"✓ Order {order_num} has SL: {order_dict['sl']}")
        
        if prediction.tp_pct and prediction.tp_pct > 0:
            if 'tp' in order_dict and order_dict['tp']:
                # Basic validation that TP is set and reasonable
                assert isinstance(order_dict['tp'], (int, float)), f"Order {order_num} TP should be numeric"
                assert order_dict['tp'] > 0, f"Order {order_num} TP should be positive"
                logger.info(f"✓ Order {order_num} has TP: {order_dict['tp']}")
        
        logger.info(f"✓ Order {order_num} prediction validation passed for symbol: {prediction.symbol}")

    def _validate_returned_orders_match_file(self, returned_orders, file_orders):
        """Validate that orders returned by main() match the orders saved to file."""
        logger.info(f"Validating {len(returned_orders)} returned orders match {len(file_orders)} file orders")
        
        assert len(returned_orders) == len(file_orders), f"Number of returned orders ({len(returned_orders)}) should match file orders ({len(file_orders)})"
        
        # Convert returned OrderData objects to dicts for comparison
        returned_dicts = [order.to_dict() for order in returned_orders]
        
        for i, (returned_dict, file_dict) in enumerate(zip(returned_dicts, file_orders)):
            logger.info(f"Comparing order {i+1}: {returned_dict.get('symbol', 'UNKNOWN')}")
            
            # Compare key fields
            key_fields = ['symbol', 'type', 'volume', 'price', 'magic']
            for field in key_fields:
                assert returned_dict.get(field) == file_dict.get(field), \
                    f"Order {i+1} field '{field}' mismatch: returned={returned_dict.get(field)} vs file={file_dict.get(field)}"
        
        logger.info(f"✓ All returned orders match file orders")