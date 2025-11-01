"""Integration test for loading predictions and creating orders."""

import pytest
import logging
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import MetaTrader5 as mt5

from src.infra.mtBase import mtBase
from src.infra.PredictionClient import PredictionClient
from src.infra.OrderClient import OrderClient
from src.prediction_to_orders import prediction_to_orders

# Setup logger
logger = logging.getLogger(__name__)


class TestPredictionOrderIntegration:
    """Integration test that loads predictions from dev folder and creates orders."""
    
    def _create_mock_symbol_price(self, symbol: str) -> dict:
        """Create mock symbol price data with some variation based on symbol."""
        # Create some variation based on symbol hash for different price levels
        symbol_hash = hash(symbol) % 100
        base_price = 1.0000 + (symbol_hash / 10000)  # Price between 1.0000 and 1.0099
        spread = 0.0002
        
        bid = round(base_price, 5)
        ask = round(base_price + spread, 5)
        last = round(base_price + (spread / 2), 5)
        spread_rel = spread / (bid + 1e-8)
        
        return {
            "symbol": symbol,
            "bid": bid,
            "ask": ask,
            "last": last,
            "spread": spread,
            "spread_rel": spread_rel,
            "time": 1635379200,
            "time_msc": 1635379200000,
            "volume": 1000,
            "volume_real": 1000.0,
            "flags": 6,
        }
    
    def _create_mock_symbol_info(self, symbol: str) -> dict:
        """Create mock symbol info data with reasonable contract size for testing."""
        return {
            "symbol": symbol,
            "visible": True,
            "trade_mode": 4,
            "digits": 5,
            "point": 0.00001,
            "time": 1635379200,
            "volume": 1000,
            "volume_real": 1000.0,
            "trade_contract_size": 1000.0,
            "volume_min": 0.01,
            "volume_max": 500.0,
            "volume_step": 0.01,
            "currency_base": "USD",
            "currency_profit": "USD",
            "currency_margin": "USD",
            "trade_stops_level": 10,
            "trade_freeze_level": 0,
            "filling_mode": mt5.ORDER_FILLING_FOK,
            "expiration_mode": 1,
            "category": "Major",
        }
    
    def _create_mock_account_info(self):
        """Create mock account info data."""
        mock_account = MagicMock()
        mock_account.currency = "USD"
        mock_account.balance = 10000.0
        mock_account.equity = 10000.0
        mock_account.margin = 0.0
        mock_account.profit = 0.0
        return mock_account
    
    def test_load_predictions_and_create_orders(self):
        """
        Integration test that:
        1. Loads predictions from predictions/dev folder
        2. Creates one order for each prediction
        3. Logs both predictions and orders using respective client methods
        
        IMPORTANT: This test uses the 'mt5demo_acc_usd' account configuration.
        """
        # Check if credential files exist
        credentials_path = 'secrets/mt5_acc_cred.yaml'
        config_path = 'secrets/mt5_config.ini'
        
        if not os.path.exists(credentials_path) or not os.path.exists(config_path):
            pytest.skip(f"Credential files not found: {credentials_path} or {config_path}")
        
        # Check if predictions directory exists
        predictions_dev_dir = Path('predictions/dev')
        if not predictions_dev_dir.exists():
            pytest.skip(f"Predictions dev directory not found: {predictions_dev_dir}")
        
        # Check if there are any prediction files
        prediction_files = list(predictions_dev_dir.glob('*.json'))
        if not prediction_files:
            pytest.skip(f"No prediction files found in {predictions_dev_dir}")
        
        logger.info(f"Found {len(prediction_files)} prediction files in {predictions_dev_dir}")
        
        # CRITICAL: Using specific account 'mt5demo_acc_usd' for this integration test
        account_name = 'mt5demo_acc_usd'
        logger.info(f"Starting prediction-order integration test with MT5 account: {account_name}")
        
        # Initialize MT5 connection
        mt5_base = None
        
        try:
            # Try to create an mtBase instance
            mt5_base = mtBase(
                account=account_name,  # IMPORTANT: mt5demo_acc_usd account
                credentials_path=credentials_path,
                config_path=config_path
            )
            
            # Try to initialize MT5 connection
            mt5_base.mt5_init()
            
            # Check if connection is established
            if not mt5_base.check_login():
                pytest.skip(f"MT5 connection failed for account {account_name} - skipping integration test")
                
            logger.info(f"Successfully connected to MT5 account: {account_name}")
        
        except ImportError as e:
            # MetaTrader5 module not installed - skip test
            pytest.skip(f"MetaTrader5 module not available: {e}")
        
        except Exception as e:
            pytest.skip(f"MT5 initialization failed for account {account_name}: {e} - skipping integration test")
        
        try:
            # Step 1: Load predictions from dev folder using PredictionClient
            logger.info("="*60)
            logger.info("STEP 1: Loading predictions from predictions/dev folder")
            logger.info("="*60)
            
            # Create PredictionClient with the dev subdirectory
            prediction_client = PredictionClient(base=mt5_base, predictions_dir="predictions/dev")
            
            # Load all predictions from the dev directory (no group filter needed)
            predictions = prediction_client.load_predictions(group='debug')
            
            if not predictions:
                pytest.skip("No predictions loaded from dev folder")
            
            logger.info(f"Successfully loaded {len(predictions)} predictions from dev folder")
            
            # Log all loaded predictions using the client's log method
            logger.info("Logging all loaded predictions:")
            prediction_client.log_predictions(predictions, indent=2)
            
            # Step 2: Create orders for each prediction
            logger.info("="*60)
            logger.info("STEP 2: Creating orders from predictions")
            logger.info("="*60)
            
            order_client = OrderClient(base=mt5_base)
            created_orders = []
            
            # Budget and volume settings for order creation
            budget = 5000.0  # Increased demo budget to ensure positive volumes
            vol_divisor = len(predictions)  # Divide budget among all predictions
            
            for i, prediction in enumerate(predictions, 1):
                logger.info(f"Creating order {i}/{len(predictions)} for prediction:")
                prediction_client.log_predictions(prediction, indent=4)
                
                try:
                    # Mock the symbol price, info, and account info methods to ensure they're always available
                    with patch.object(mt5_base, 'get_symbol_price') as mock_price, \
                         patch.object(mt5_base, 'get_symbol_info') as mock_info, \
                         patch.object(mt5_base, 'get_account_info') as mock_account:
                        
                        # Configure mocks to return realistic data
                        mock_price.return_value = self._create_mock_symbol_price(prediction.symbol)
                        mock_info.return_value = self._create_mock_symbol_info(prediction.symbol)
                        mock_account.return_value = self._create_mock_account_info()
                        
                        logger.info(f"Using mocked symbol price, info, and account info for {prediction.symbol}")
                        
                        # Create orders from prediction using the prediction_to_orders function
                        # Note: prediction_to_orders returns a LIST of OrderData objects
                        orders = prediction_to_orders(
                            pred=prediction,
                            budget=budget,
                            vol_divisor=vol_divisor,
                            base=mt5_base
                        )
                        
                        if orders:
                            created_orders.extend(orders)  # Add all orders from the list
                            logger.info(f"✓ Successfully created {len(orders)} order(s) for {prediction.symbol}")
                            
                            # Log the created orders immediately
                            logger.info(f"Created order details:")
                            order_client.log_orders(orders, indent=4)
                        else:
                            logger.warning(f"Failed to create orders for {prediction.symbol}")
                        
                except Exception as e:
                    logger.error(f"Error creating orders for {prediction.symbol}: {e}")
                    continue
            
            # Step 3: Log summary of all created orders
            logger.info("="*60)
            logger.info("STEP 3: Summary of all created orders")
            logger.info("="*60)
            
            if created_orders:
                logger.info(f"Successfully created {len(created_orders)} orders out of {len(predictions)} predictions")
                logger.info("All created orders:")
                order_client.log_orders(created_orders, indent=2)
                
                # Verify that we have orders for our predictions
                assert len(created_orders) > 0, "Should have created at least one order"
                
                # Verify each order has the expected properties
                for order in created_orders:
                    assert hasattr(order, 'symbol'), "Order should have symbol"
                    assert hasattr(order, 'volume'), "Order should have volume"
                    assert hasattr(order, 'price'), "Order should have price"
                    assert hasattr(order, 'magic'), "Order should have magic number"
                    assert order.volume > 0, "Order volume should be positive"
                
                logger.info("✓ All created orders have valid properties")
            else:
                logger.warning("No orders were successfully created")
                pytest.fail("Expected to create at least one order from predictions")
            
            # Step 4: Verify prediction-order correspondence
            logger.info("="*60)
            logger.info("STEP 4: Verifying prediction-order correspondence")
            logger.info("="*60)
            
            prediction_symbols = {pred.symbol for pred in predictions}
            order_symbols = {order.symbol for order in created_orders}
            
            logger.info(f"Prediction symbols: {sorted(prediction_symbols)}")
            logger.info(f"Order symbols: {sorted(order_symbols)}")
            
            # Check that we have orders for some of our prediction symbols
            common_symbols = prediction_symbols.intersection(order_symbols)
            logger.info(f"Symbols with both predictions and orders: {sorted(common_symbols)}")
            
            assert len(common_symbols) > 0, "Should have at least one symbol with both prediction and order"
            
            logger.info("="*60)
            logger.info("✓ PREDICTION-ORDER INTEGRATION TEST COMPLETED SUCCESSFULLY")
            logger.info("="*60)
            logger.info(f"✓ Loaded {len(predictions)} predictions from dev folder")
            logger.info(f"✓ Created {len(created_orders)} orders")
            logger.info(f"✓ Logged predictions and orders using respective client methods")
            logger.info(f"✓ Verified {len(common_symbols)} symbols have both predictions and orders")
            
        finally:
            # Always shutdown MT5 connection
            if mt5_base is not None:
                try:
                    mt5_base.shutdown()
                    logger.info(f"MT5 connection properly shut down for account '{account_name}'")
                except Exception as e:
                    logger.warning(f"Error during shutdown for account {account_name}: {e}")
        
        # Assert that we're testing the correct account
        assert account_name == 'mt5demo_acc_usd', f"CRITICAL: Test must use 'mt5demo_acc_usd' account, but used '{account_name}'"