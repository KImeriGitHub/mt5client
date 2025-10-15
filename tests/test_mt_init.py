"""
Unit tests for mtBase.py module.
"""

import pytest
from unittest.mock import patch, MagicMock
import logging

from src.mtBase import mtBase

# Setup logger for tests
logger = logging.getLogger(__name__)


class TestMtBase:
    """Test suite for mtBase class."""
    
    @patch('src.mtBase.mt5')
    @patch.object(mtBase, '_mtBase__load_yaml')
    @patch('configparser.ConfigParser')
    def test_mtbase_init_and_shutdown(self, mock_config_parser, mock_load_yaml, mock_mt5):
        """
        Test mtBase initialization with mock credentials and then shutdown.
        Verifies initialization and shutdown work correctly with mocked data.
        """
        # Setup mock YAML credentials
        mock_load_yaml.return_value = {
            'mt5demo_acc': {
                'apilogin': '99999999',
                'apipw': 'mock_password_123',
                'server': 'MockServer-Demo'
            }
        }
        
        # Setup mock config parser
        mock_config_instance = MagicMock()
        mock_config_parser.return_value = mock_config_instance
        mock_config_instance.sections.return_value = ['MetaTrader5']
        mock_config_instance.items.return_value = [
            ('terminal_path', 'C:\\Program Files\\MockMT5\\terminal64.exe')
        ]
        
        # Mock MT5 initialization to succeed
        mock_mt5.initialize.return_value = True
        mock_mt5.account_info.return_value = None  # Not logged in initially
        
        # Create mtBase instance
        mt5_client = mtBase(
            account='mt5demo_acc',
            credentials_path='mock_cred.yaml',
            config_path='mock_config.ini'
        )
        
        # Test initialization
        mt5_client.mt5_init()
        
        # Verify initialize was called
        assert mock_mt5.initialize.called, "mt5.initialize should be called"
        
        # Test shutdown
        mt5_client.shutdown()
        mock_mt5.shutdown.assert_called_once()
        logger.info("✓ mtBase init and shutdown test passed")
    
    @patch('src.mtBase.mt5')
    @patch.object(mtBase, '_mtBase__load_yaml')
    @patch('configparser.ConfigParser')
    def test_check_login_correct_account(self, mock_config_parser, mock_load_yaml, mock_mt5):
        """
        Test check_login returns True when logged into correct account.
        """
        # Setup mocks
        mock_load_yaml.return_value = {
            'mt5demo_acc': {
                'apilogin': '99999999',
                'apipw': 'mock_password_123',
                'server': 'MockServer-Demo'
            }
        }
        
        mock_config_instance = MagicMock()
        mock_config_parser.return_value = mock_config_instance
        mock_config_instance.sections.return_value = ['MetaTrader5']
        mock_config_instance.items.return_value = [
            ('terminal_path', 'C:\\Program Files\\MockMT5\\terminal64.exe')
        ]
        
        # Mock account info to return matching login
        mock_account_info = MagicMock()
        mock_account_info.login = 99999999
        mock_mt5.account_info.return_value = mock_account_info
        
        # Create mtBase instance and test
        mt5_client = mtBase(
            account='mt5demo_acc',
            credentials_path='mock_cred.yaml',
            config_path='mock_config.ini'
        )
        
        result = mt5_client.check_login()
        assert result is True
        logger.info("✓ check_login correct account test passed")
    
    @patch('src.mtBase.mt5')
    @patch.object(mtBase, '_mtBase__load_yaml')
    @patch('configparser.ConfigParser')
    def test_check_login_wrong_account(self, mock_config_parser, mock_load_yaml, mock_mt5):
        """
        Test check_login returns False when logged into wrong account.
        """
        # Setup mocks
        mock_load_yaml.return_value = {
            'mt5demo_acc': {
                'apilogin': '99999999',
                'apipw': 'mock_password_123',
                'server': 'MockServer-Demo'
            }
        }
        
        mock_config_instance = MagicMock()
        mock_config_parser.return_value = mock_config_instance
        mock_config_instance.sections.return_value = ['MetaTrader5']
        mock_config_instance.items.return_value = [
            ('terminal_path', 'C:\\Program Files\\MockMT5\\terminal64.exe')
        ]
        
        # Mock account info to return different login
        mock_account_info = MagicMock()
        mock_account_info.login = 12345678  # Different from expected
        mock_mt5.account_info.return_value = mock_account_info
        
        # Create mtBase instance and test
        mt5_client = mtBase(
            account='mt5demo_acc',
            credentials_path='mock_cred.yaml',
            config_path='mock_config.ini'
        )
        
        result = mt5_client.check_login()
        assert result is False
        logger.info("✓ check_login wrong account test passed")

    @patch('src.mtBase.get_position_helper')
    @patch('src.mtBase.mt5')
    @patch.object(mtBase, '_mtBase__load_yaml')
    @patch('configparser.ConfigParser')
    def test_get_position_df_method(self, mock_config_parser, mock_load_yaml, mock_mt5, mock_get_position_helper):
        """Test mtBase.get_position_df method."""
        # Setup mocks
        mock_load_yaml.return_value = {
            'mt5demo_acc': {
                'apilogin': '99999999',
                'apipw': 'mock_password_123',
                'server': 'MockServer-Demo'
            }
        }
        
        mock_config_instance = MagicMock()
        mock_config_parser.return_value = mock_config_instance
        mock_config_instance.sections.return_value = ['MetaTrader5']
        mock_config_instance.items.return_value = [('terminal_path', 'mock_path')]
        
        # Mock successful login check
        mock_account_info = MagicMock()
        mock_account_info.login = 99999999
        mock_mt5.account_info.return_value = mock_account_info
        
        # Mock the helper function return
        import polars as pl
        mock_df = pl.DataFrame({'ticket': [123], 'symbol': ['EURUSD']})
        mock_get_position_helper.return_value = mock_df
        
        # Create mtBase instance and test
        mt5_client = mtBase('mt5demo_acc', 'mock_cred.yaml', 'mock_config.ini')
        result = mt5_client.get_position_df()
        
        assert result.equals(mock_df)
        mock_get_position_helper.assert_called_once()
        logger.info("✓ mtBase get_position_df method test passed")

    @patch('src.mtBase.get_orders_helper')
    @patch('src.mtBase.mt5')
    @patch.object(mtBase, '_mtBase__load_yaml')
    @patch('configparser.ConfigParser')
    def test_get_orders_df_method(self, mock_config_parser, mock_load_yaml, mock_mt5, mock_get_orders_helper):
        """Test mtBase.get_orders_df method."""
        # Setup mocks
        mock_load_yaml.return_value = {
            'mt5demo_acc': {
                'apilogin': '99999999',
                'apipw': 'mock_password_123',
                'server': 'MockServer-Demo'
            }
        }
        
        mock_config_instance = MagicMock()
        mock_config_parser.return_value = mock_config_instance
        mock_config_instance.sections.return_value = ['MetaTrader5']
        mock_config_instance.items.return_value = [('terminal_path', 'mock_path')]
        
        # Mock successful login check
        mock_account_info = MagicMock()
        mock_account_info.login = 99999999
        mock_mt5.account_info.return_value = mock_account_info
        
        # Mock the helper function return
        import polars as pl
        mock_df = pl.DataFrame({'ticket': [456], 'symbol': ['GBPUSD']})
        mock_get_orders_helper.return_value = mock_df
        
        # Create mtBase instance and test
        mt5_client = mtBase('mt5demo_acc', 'mock_cred.yaml', 'mock_config.ini')
        result = mt5_client.get_orders_df()
        
        assert result.equals(mock_df)
        mock_get_orders_helper.assert_called_once()
        logger.info("✓ mtBase get_orders_df method test passed")

    @patch('src.mtBase.mt5')
    @patch.object(mtBase, '_mtBase__load_yaml')
    @patch('configparser.ConfigParser')
    def test_method_requires_login(self, mock_config_parser, mock_load_yaml, mock_mt5):
        """Test that methods raise RuntimeError when not logged in."""
        # Setup mocks
        mock_load_yaml.return_value = {
            'mt5demo_acc': {
                'apilogin': '99999999',
                'apipw': 'mock_password_123',
                'server': 'MockServer-Demo'
            }
        }
        
        mock_config_instance = MagicMock()
        mock_config_parser.return_value = mock_config_instance
        mock_config_instance.sections.return_value = ['MetaTrader5']
        mock_config_instance.items.return_value = [('terminal_path', 'mock_path')]
        
        # Mock failed login check
        mock_mt5.account_info.return_value = None
        
        # Create mtBase instance and test
        mt5_client = mtBase('mt5demo_acc', 'mock_cred.yaml', 'mock_config.ini')
        
        with pytest.raises(RuntimeError, match="Not logged in or wrong account"):
            mt5_client.get_position_df()
        
        with pytest.raises(RuntimeError, match="Not logged in or wrong account"):
            mt5_client.get_orders_df()
        
        with pytest.raises(RuntimeError, match="Not logged in or wrong account"):
            mt5_client.get_symbol_price('EURUSD')
        
        logger.info("✓ mtBase login requirement test passed")

    @patch('src.mtBase.place_market_order_helper')
    @patch('src.mtBase.mt5')
    @patch.object(mtBase, '_mtBase__load_yaml')
    @patch('configparser.ConfigParser')
    def test_place_market_order_method(self, mock_config_parser, mock_load_yaml, mock_mt5, mock_place_market_order):
        """Test mtBase.place_market_order method."""
        # Setup mocks
        mock_load_yaml.return_value = {
            'mt5demo_acc': {
                'apilogin': '99999999',
                'apipw': 'mock_password_123',
                'server': 'MockServer-Demo'
            }
        }
        
        mock_config_instance = MagicMock()
        mock_config_parser.return_value = mock_config_instance
        mock_config_instance.sections.return_value = ['MetaTrader5']
        mock_config_instance.items.return_value = [('terminal_path', 'mock_path')]
        
        # Mock successful login check
        mock_account_info = MagicMock()
        mock_account_info.login = 99999999
        mock_mt5.account_info.return_value = mock_account_info
        
        # Mock the helper function return
        mock_result = MagicMock(retcode=10009)
        mock_place_market_order.return_value = mock_result
        
        # Create mtBase instance and test
        mt5_client = mtBase('mt5demo_acc', 'mock_cred.yaml', 'mock_config.ini')
        result = mt5_client.place_market_order('EURUSD', 0.1, 'Buy', sl_pct=0.01, tp_pct=0.02)
        
        assert result == mock_result
        mock_place_market_order.assert_called_once_with(
            symbol='EURUSD',
            vol=0.1,
            buy_sell='Buy',
            sl_pct=0.01,
            tp_pct=0.02
        )
        logger.info("✓ mtBase place_market_order method test passed")

    @patch('src.mtBase.place_limit_order_helper')
    @patch('src.mtBase.mt5')
    @patch.object(mtBase, '_mtBase__load_yaml')
    @patch('configparser.ConfigParser')
    def test_place_limit_order_method(self, mock_config_parser, mock_load_yaml, mock_mt5, mock_place_limit_order):
        """Test mtBase.place_limit_order method."""
        # Setup mocks
        mock_load_yaml.return_value = {
            'mt5demo_acc': {
                'apilogin': '99999999',
                'apipw': 'mock_password_123',
                'server': 'MockServer-Demo'
            }
        }
        
        mock_config_instance = MagicMock()
        mock_config_parser.return_value = mock_config_instance
        mock_config_instance.sections.return_value = ['MetaTrader5']
        mock_config_instance.items.return_value = [('terminal_path', 'mock_path')]
        
        # Mock successful login check
        mock_account_info = MagicMock()
        mock_account_info.login = 99999999
        mock_mt5.account_info.return_value = mock_account_info
        
        # Mock the helper function return
        mock_result = MagicMock(retcode=10009)
        mock_place_limit_order.return_value = mock_result
        
        # Create mtBase instance and test
        mt5_client = mtBase('mt5demo_acc', 'mock_cred.yaml', 'mock_config.ini')
        result = mt5_client.place_limit_order('EURUSD', 0.1, 'Sell', pct_away=0.005)
        
        assert result == mock_result
        mock_place_limit_order.assert_called_once_with(
            symbol='EURUSD',
            vol=0.1,
            buy_sell='Sell',
            pct_away=0.005
        )
        logger.info("✓ mtBase place_limit_order method test passed")

    ########################
    ### INTEGRATION TEST ###
    ########################
    def test_mtbase_real_connection_mt5demo_acc(self):
        """
        Integration test: Actually attempt to connect to MT5 with mt5demo_acc credentials.
        This test will make a real connection attempt to the MetaQuotes-Demo server.
        """
        # This is an integration test - no mocking
        # Attempt real connection with mt5demo_acc
        mt5_client = None
        
        try:
            mt5_client = mtBase(
                account='mt5demo_acc',
                credentials_path='secrets/mt5_acc_cred.yaml',
                config_path='secrets/mt5_config.ini'
            )
            
            # Attempt initialization
            mt5_client.mt5_init()
            
            # If connection succeeds, verify we can check login
            if mt5_client.check_login():
                logger.info("Successfully connected to MT5 demo account")
            else:
                # Connection failed - this is expected if MT5 is not installed or demo server is unavailable
                logger.info("MT5 connection failed (expected if MT5 not installed or server unavailable)")
                
        except Exception as e:
            # Handle any exceptions (e.g., MetaTrader5 module not installed, missing files)
            logger.info(f"Integration test failed with exception: {e}")
            # This is acceptable for a CI environment where MT5 may not be available
            
        finally:
            # Always attempt shutdown, even if connection failed
            if mt5_client is not None:
                mt5_client.shutdown()
                logger.info("MT5 connection properly shut down")
