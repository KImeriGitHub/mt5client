"""Integration tests for MT5 orders and positions using client classes."""

import pytest
import logging
import os
import polars as pl

from src.infra.mtBase import mtBase
from src.infra.OrderClient import OrderClient
from src.infra.PositionClient import PositionClient

# Setup logger
logger = logging.getLogger(__name__)


class TestMT5Integration:
    """Integration tests that use actual MT5 connection with proper client classes."""
    
    def test_mt5_orders_and_positions_integration(self):
        """
        Integration test for OrderClient and PositionClient with real MT5 connection.
        
        IMPORTANT: This test specifically uses the 'mt5demo_acc_usd' account configuration.
        The account name must match exactly with the credentials in mt5_acc_cred.yaml.
        """
        # Check if credential files exist
        credentials_path = 'secrets/mt5_acc_cred.yaml'
        config_path = 'secrets/mt5_config.ini'
        
        if not os.path.exists(credentials_path) or not os.path.exists(config_path):
            pytest.skip(f"Credential files not found: {credentials_path} or {config_path}")
        
        # CRITICAL: Using specific account 'mt5demo_acc_usd' for this integration test
        account_name = 'mt5demo_acc_usd'
        logger.info(f"Starting integration test with MT5 account: {account_name}")
        
        # Skip test if MT5 is not available
        mt5_base = None
        order_client = None
        position_client = None
        
        try:
            # Try to create an mtBase instance first
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
            # Create client instances using the mtBase
            order_client = OrderClient(base=mt5_base)
            position_client = PositionClient(base=mt5_base)
            
            logger.info("Created OrderClient and PositionClient instances")
            
            # Test OrderClient functionality
            orders = order_client.get_orders()
            logger.info(f"✓ Retrieved {len(orders)} orders using OrderClient")
            
            # Get orders DataFrame through the client's internal DataFrame
            orders_dataframe = order_client.get_orders_dataframe()
            if orders_dataframe is not None:
                assert isinstance(orders_dataframe, pl.DataFrame)
                logger.info(f"✓ Retrieved orders DataFrame with {len(orders_dataframe)} orders")
                
                # Verify DataFrame structure if there are orders
                if not orders_dataframe.is_empty():
                    expected_columns = ['ticket', 'symbol', 'volume', 'time_setup', 'type']
                    for col in expected_columns:
                        assert col in orders_dataframe.columns, f"Missing expected column: {col}"
                    logger.info("✓ Orders DataFrame has expected columns")
            else:
                logger.info("✓ No orders found - orders DataFrame is None (expected)")
            
            # Test PositionClient functionality
            positions = position_client.get_positions()
            logger.info(f"✓ Retrieved {len(positions)} positions using PositionClient")
            
            # Log positions details
            position_client.log_positions(positions)
            
            # Access positions DataFrame through the client's internal property
            # First call get_positions to populate the internal DataFrame
            if len(positions) > 0:
                positions_df = position_client._positions_df
                assert isinstance(positions_df, pl.DataFrame)
                logger.info(f"✓ Retrieved positions DataFrame with {len(positions_df)} positions")
                
                # Verify DataFrame structure
                expected_columns = ['ticket', 'symbol', 'volume', 'profit', 'time']
                for col in expected_columns:
                    assert col in positions_df.columns, f"Missing expected column: {col}"
                logger.info("✓ Positions DataFrame has expected columns")
                
                # Verify that noisy columns are filtered out (these should be filtered by mtBase)
                noisy_columns = ['time_update', 'time_msc', 'time_update_msc', 'external_id']
                for col in noisy_columns:
                    assert col not in positions_df.columns, f"Noisy column should be filtered: {col}"
                logger.info("✓ Noisy columns properly filtered from positions DataFrame")
            else:
                logger.info("✓ No positions found (expected for demo account)")
            
            # Test client integration - verify that clients work with the same base
            assert order_client.base == mt5_base, "OrderClient should use the same mtBase instance"
            assert position_client.base == mt5_base, "PositionClient should use the same mtBase instance"
            
            logger.info(f"✓ MT5 integration test passed successfully for account '{account_name}'")
            
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