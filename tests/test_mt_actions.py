import pytest
import unittest.mock as mock
from collections import namedtuple
import polars as pl
import yaml
from pathlib import Path
import MetaTrader5 as mt5
import logging

from src.mt_actions import (
    _to_df, 
    get_position_helper, 
    get_orders_helper, 
    _norm_price, 
    _latest_prices, 
    place_market_order_helper, 
    place_limit_order_helper,
    get_symbol_price_helper
)
from src.mtBase import mtBase

# Setup logger for tests
logger = logging.getLogger(__name__)


class TestToDF:
    """Test the _to_df helper function."""
    
    def test_to_df_with_empty_tuple(self):
        """Test _to_df returns empty DataFrame for empty tuple."""
        result = _to_df(())
        assert isinstance(result, pl.DataFrame)
        assert result.is_empty()
        logger.info("✓ Empty tuple test passed")
    
    def test_to_df_with_none(self):
        """Test _to_df returns empty DataFrame for None."""
        result = _to_df(None)
        assert isinstance(result, pl.DataFrame)
        assert result.is_empty()
        logger.info("✓ None input test passed")
    
    def test_to_df_with_namedtuples(self):
        """Test _to_df converts namedtuples to Polars DataFrame."""
        Position = namedtuple('Position', ['ticket', 'symbol', 'volume', 'profit'])
        positions = [
            Position(ticket=123, symbol='EURUSD', volume=0.1, profit=10.5),
            Position(ticket=124, symbol='GBPUSD', volume=0.2, profit=-5.3)
        ]
        
        result = _to_df(positions)
        assert isinstance(result, pl.DataFrame)
        assert result.shape == (2, 4)
        assert list(result.columns) == ['ticket', 'symbol', 'volume', 'profit']
        assert result['ticket'].to_list() == [123, 124]
        logger.info("✓ Namedtuple conversion test passed")


class TestGetPositionHelper:
    """Test get_position_helper function."""
    
    @mock.patch('src.mt_actions.mt5')
    def test_get_position_helper_empty(self, mock_mt5):
        """Test get_position_helper returns empty DataFrame when no positions."""
        mock_mt5.positions_get.return_value = ()
        
        result = get_position_helper()
        assert isinstance(result, pl.DataFrame)
        assert result.is_empty()
        mock_mt5.positions_get.assert_called_once()
        logger.info("✓ Empty positions test passed")
    
    @mock.patch('src.mt_actions.mt5')
    def test_get_position_helper_with_positions(self, mock_mt5):
        """Test get_position_helper returns DataFrame with positions."""
        Position = namedtuple('Position', [
            'ticket', 'symbol', 'volume', 'profit', 'time', 
            'time_update', 'time_msc', 'time_update_msc', 'external_id'
        ])
        
        positions = [
            Position(
                ticket=123, symbol='EURUSD', volume=0.1, profit=10.5, 
                time=1697000000, time_update=1697000100, 
                time_msc=1697000000000, time_update_msc=1697000100000,
                external_id='ext123'
            )
        ]
        mock_mt5.positions_get.return_value = positions
        
        result = get_position_helper()
        assert isinstance(result, pl.DataFrame)
        assert result.shape[0] == 1
        assert 'ticket' in result.columns
        assert 'symbol' in result.columns
        assert 'time' in result.columns
        # Check that noisy columns are dropped
        assert 'time_update' not in result.columns
        assert 'time_msc' not in result.columns
        assert 'external_id' not in result.columns
        logger.info("✓ Positions with data test passed")


class TestGetOrdersHelper:
    """Test get_orders_helper function."""
    
    @mock.patch('src.mt_actions.mt5')
    def test_get_orders_helper_empty(self, mock_mt5):
        """Test get_orders_helper returns empty DataFrame when no orders."""
        mock_mt5.orders_get.return_value = ()
        
        result = get_orders_helper()
        assert isinstance(result, pl.DataFrame)
        assert result.is_empty()
        mock_mt5.orders_get.assert_called_once()
        logger.info("✓ Empty orders test passed")
    
    @mock.patch('src.mt_actions.mt5')
    def test_get_orders_helper_with_orders(self, mock_mt5):
        """Test get_orders_helper returns DataFrame with orders."""
        Order = namedtuple('Order', ['ticket', 'symbol', 'volume', 'time_setup', 'type'])
        
        orders = [
            Order(ticket=456, symbol='GBPUSD', volume=0.2, time_setup=1697000000, type=2)
        ]
        mock_mt5.orders_get.return_value = orders
        
        result = get_orders_helper()
        assert isinstance(result, pl.DataFrame)
        assert result.shape[0] == 1
        assert 'ticket' in result.columns
        assert 'symbol' in result.columns
        assert 'time_setup' in result.columns
        logger.info("✓ Orders with data test passed")


class TestNormPrice:
    """Test _norm_price helper function."""
    
    @mock.patch('src.mt_actions.mt5')
    def test_norm_price_valid_symbol(self, mock_mt5):
        """Test _norm_price rounds price to symbol's precision."""
        SymbolInfo = namedtuple('SymbolInfo', ['digits'])
        mock_mt5.symbol_info.return_value = SymbolInfo(digits=5)
        
        result = _norm_price('EURUSD', 1.123456789)
        assert result == 1.12346
        mock_mt5.symbol_info.assert_called_once_with('EURUSD')
        logger.info("✓ Valid symbol price normalization test passed")
    
    @mock.patch('src.mt_actions.mt5')
    def test_norm_price_invalid_symbol(self, mock_mt5):
        """Test _norm_price raises error for invalid symbol."""
        mock_mt5.symbol_info.return_value = None
        
        with pytest.raises(ValueError, match="Unknown symbol"):
            _norm_price('INVALID', 1.23)
        logger.info("✓ Invalid symbol error test passed")


class TestLatestPrices:
    """Test _latest_prices helper function."""
    
    @mock.patch('src.mt_actions.mt5')
    def test_latest_prices_valid_symbol(self, mock_mt5):
        """Test _latest_prices returns bid and ask."""
        Tick = namedtuple('Tick', ['bid', 'ask'])
        mock_mt5.symbol_info_tick.return_value = Tick(bid=1.12345, ask=1.12355)
        
        bid, ask = _latest_prices('EURUSD')
        assert bid == 1.12345
        assert ask == 1.12355
        mock_mt5.symbol_info_tick.assert_called_once_with('EURUSD')
        logger.info("✓ Valid symbol latest prices test passed")
    
    @mock.patch('src.mt_actions.mt5')
    def test_latest_prices_no_tick(self, mock_mt5):
        """Test _latest_prices raises error when no tick available."""
        mock_mt5.symbol_info_tick.return_value = None
        
        with pytest.raises(RuntimeError, match="No tick for"):
            _latest_prices('EURUSD')
        logger.info("✓ No tick error test passed")


class TestGetSymbolPriceHelper:
    """Test get_symbol_price_helper function."""
    
    @mock.patch('src.mt_actions.mt5')
    def test_get_symbol_price_helper_valid_symbol(self, mock_mt5):
        """Test get_symbol_price_helper returns price information."""
        Tick = namedtuple('Tick', ['bid', 'ask', 'last', 'time'])
        mock_mt5.symbol_info_tick.return_value = Tick(
            bid=1.12345, ask=1.12355, last=1.12350, time=1697000000
        )
        
        result = get_symbol_price_helper('EURUSD')
        assert isinstance(result, dict)
        assert result['symbol'] == 'EURUSD'
        assert abs(result['bid'] - 1.12345) < 1e-5
        assert abs(result['ask'] - 1.12355) < 1e-5
        assert abs(result['last'] - 1.12350) < 1e-5
        assert abs(result['spread'] - 0.0001) < 1e-5
        assert result['time'] == 1697000000
        assert 'spread_pct' in result
        mock_mt5.symbol_info_tick.assert_called_once_with('EURUSD')
        logger.info("✓ Valid symbol price helper test passed")
    
    @mock.patch('src.mt_actions.mt5')
    def test_get_symbol_price_helper_no_tick(self, mock_mt5):
        """Test get_symbol_price_helper returns empty dict when no tick available."""
        mock_mt5.symbol_info_tick.return_value = None
        
        result = get_symbol_price_helper('INVALID')
        assert isinstance(result, dict)
        assert result == {}
        mock_mt5.symbol_info_tick.assert_called_once_with('INVALID')
        logger.info("✓ No tick price helper test passed")


class TestPlaceMarketOrderHelper:
    """Test place_market_order_helper function."""
    
    @mock.patch('src.mt_actions.mt5')
    def test_place_market_order_helper_buy_no_sl_tp(self, mock_mt5):
        """Test placing a buy market order without SL/TP."""
        # Setup mocks
        Tick = namedtuple('Tick', ['bid', 'ask'])
        SymbolInfo = namedtuple('SymbolInfo', ['digits'])
        mock_mt5.symbol_info_tick.return_value = Tick(bid=1.12345, ask=1.12355)
        mock_mt5.symbol_info.return_value = SymbolInfo(digits=5)
        mock_mt5.order_send.return_value = mock.MagicMock(retcode=10009)
        mock_mt5.order_check.return_value = mock.MagicMock(retcode=10009)  # TRADE_RETCODE_DONE
        mock_mt5.ORDER_TYPE_BUY = 0
        mock_mt5.TRADE_ACTION_DEAL = 1
        mock_mt5.ORDER_TIME_GTC = 0
        mock_mt5.ORDER_FILLING_RETURN = 1
        mock_mt5.TRADE_RETCODE_DONE = 10009
        
        result = place_market_order_helper('EURUSD', 0.1, 'Buy')
        
        mock_mt5.order_send.assert_called_once()
        call_args = mock_mt5.order_send.call_args[0][0]
        assert call_args['symbol'] == 'EURUSD'
        assert call_args['volume'] == 0.1
        assert call_args['type'] == 0  # ORDER_TYPE_BUY
        assert 'sl' not in call_args
        assert 'tp' not in call_args
        logger.info("✓ Buy order without SL/TP test passed")
    
    @mock.patch('src.mt_actions.mt5')
    def test_place_market_order_helper_sell_with_sl_tp(self, mock_mt5):
        """Test placing a sell market order with SL/TP."""
        # Setup mocks
        Tick = namedtuple('Tick', ['bid', 'ask'])
        SymbolInfo = namedtuple('SymbolInfo', ['digits'])
        mock_mt5.symbol_info_tick.return_value = Tick(bid=1.12345, ask=1.12355)
        mock_mt5.symbol_info.return_value = SymbolInfo(digits=5)
        mock_mt5.order_send.return_value = mock.MagicMock(retcode=10009)
        mock_mt5.order_check.return_value = mock.MagicMock(retcode=10009)
        mock_mt5.ORDER_TYPE_SELL = 1
        mock_mt5.TRADE_ACTION_DEAL = 1
        mock_mt5.ORDER_TIME_GTC = 0
        mock_mt5.ORDER_FILLING_RETURN = 1
        mock_mt5.TRADE_RETCODE_DONE = 10009
        
        result = place_market_order_helper('EURUSD', 0.1, 'Sell', sl_pct=0.01, tp_pct=0.02)
        
        mock_mt5.order_send.assert_called_once()
        call_args = mock_mt5.order_send.call_args[0][0]
        assert call_args['symbol'] == 'EURUSD'
        assert call_args['volume'] == 0.1
        assert call_args['type'] == 1  # ORDER_TYPE_SELL
        assert 'sl' in call_args
        assert 'tp' in call_args
        logger.info("✓ Sell order with SL/TP test passed")
    
    @mock.patch('src.mt_actions.mt5')
    def test_place_market_order_helper_buy_sell_variations(self, mock_mt5):
        """Test that various buy/sell string formats work."""
        Tick = namedtuple('Tick', ['bid', 'ask'])
        SymbolInfo = namedtuple('SymbolInfo', ['digits'])
        mock_mt5.symbol_info_tick.return_value = Tick(bid=1.12345, ask=1.12355)
        mock_mt5.symbol_info.return_value = SymbolInfo(digits=5)
        mock_mt5.order_send.return_value = mock.MagicMock(retcode=10009)
        mock_mt5.order_check.return_value = mock.MagicMock(retcode=10009)
        mock_mt5.ORDER_TYPE_BUY = 0
        mock_mt5.ORDER_TYPE_SELL = 1
        mock_mt5.TRADE_ACTION_DEAL = 1
        mock_mt5.ORDER_TIME_GTC = 0
        mock_mt5.ORDER_FILLING_RETURN = 1
        mock_mt5.TRADE_RETCODE_DONE = 10009
        
        # Test various buy formats
        for buy_str in ['B', 'b', 'Buy', 'buy']:
            place_market_order_helper('EURUSD', 0.1, buy_str)
            call_args = mock_mt5.order_send.call_args[0][0]
            assert call_args['type'] == 0, f"Failed for buy string: {buy_str}"
        
        # Test various sell formats
        for sell_str in ['S', 's', 'Sell', 'sell']:
            place_market_order_helper('EURUSD', 0.1, sell_str)
            call_args = mock_mt5.order_send.call_args[0][0]
            assert call_args['type'] == 1, f"Failed for sell string: {sell_str}"
        
        logger.info("✓ Buy/sell string variations test passed")


class TestPlaceLimitOrderHelper:
    """Test place_limit_order_helper function."""
    
    @mock.patch('src.mt_actions.mt5')
    def test_place_limit_order_helper_buy(self, mock_mt5):
        """Test placing a buy limit order."""
        Tick = namedtuple('Tick', ['bid', 'ask'])
        SymbolInfo = namedtuple('SymbolInfo', ['digits'])
        mock_mt5.symbol_info_tick.return_value = Tick(bid=1.12345, ask=1.12355)
        mock_mt5.symbol_info.return_value = SymbolInfo(digits=5)
        mock_mt5.order_send.return_value = mock.MagicMock(retcode=10009)
        mock_mt5.order_check.return_value = mock.MagicMock(retcode=10009)
        mock_mt5.ORDER_TYPE_BUY_LIMIT = 2
        mock_mt5.TRADE_ACTION_PENDING = 5
        mock_mt5.ORDER_TIME_GTC = 0
        mock_mt5.ORDER_FILLING_RETURN = 1
        mock_mt5.TRADE_RETCODE_DONE = 10009
        
        result = place_limit_order_helper('EURUSD', 0.1, 'Buy', pct_away=0.005)
        
        mock_mt5.order_send.assert_called_once()
        call_args = mock_mt5.order_send.call_args[0][0]
        assert call_args['symbol'] == 'EURUSD'
        assert call_args['volume'] == 0.1
        assert call_args['type'] == 2  # ORDER_TYPE_BUY_LIMIT
        assert call_args['action'] == 5  # TRADE_ACTION_PENDING
        # Buy limit should be below ask
        assert call_args['price'] < 1.12355
        logger.info("✓ Buy limit order test passed")
    
    @mock.patch('src.mt_actions.mt5')
    def test_place_limit_order_helper_sell(self, mock_mt5):
        """Test placing a sell limit order."""
        Tick = namedtuple('Tick', ['bid', 'ask'])
        SymbolInfo = namedtuple('SymbolInfo', ['digits'])
        mock_mt5.symbol_info_tick.return_value = Tick(bid=1.12345, ask=1.12355)
        mock_mt5.symbol_info.return_value = SymbolInfo(digits=5)
        mock_mt5.order_send.return_value = mock.MagicMock(retcode=10009)
        mock_mt5.order_check.return_value = mock.MagicMock(retcode=10009)
        mock_mt5.ORDER_TYPE_SELL_LIMIT = 3
        mock_mt5.TRADE_ACTION_PENDING = 5
        mock_mt5.ORDER_TIME_GTC = 0
        mock_mt5.ORDER_FILLING_RETURN = 1
        mock_mt5.TRADE_RETCODE_DONE = 10009
        
        result = place_limit_order_helper('EURUSD', 0.1, 'Sell', pct_away=0.005)
        
        mock_mt5.order_send.assert_called_once()
        call_args = mock_mt5.order_send.call_args[0][0]
        assert call_args['symbol'] == 'EURUSD'
        assert call_args['volume'] == 0.1
        assert call_args['type'] == 3  # ORDER_TYPE_SELL_LIMIT
        # Sell limit should be above bid
        assert call_args['price'] > 1.12345
        logger.info("✓ Sell limit order test passed")
    
    def test_place_limit_order_helper_invalid_pct(self):
        """Test place_limit_order_helper raises error for invalid pct_away."""
        with pytest.raises(ValueError, match="pct_away must be > 0"):
            place_limit_order_helper('EURUSD', 0.1, 'Buy', pct_away=0)
        
        with pytest.raises(ValueError, match="pct_away must be > 0"):
            place_limit_order_helper('EURUSD', 0.1, 'Buy', pct_away=-0.01)
        
        logger.info("✓ Invalid pct_away error test passed")

########################
### INTEGRATION TEST ###
########################
class TestMT5Integration:
    """Integration tests that use actual MT5 connection."""
    
    def test_mt5_orders_and_positions_integration(self):
        """Integration test for helper functions with real MT5 connection through mtBase."""
        # Skip test if MT5 is not available
        try:
            # Try to create an mtBase instance
            mt5_client = mtBase(
                account='mt5demo_acc',
                credentials_path='secrets/mt5_acc_cred.yaml',
                config_path='secrets/mt5_config.ini'
            )
            
            # Try to initialize MT5 connection
            mt5_client.mt5_init()
            
            # Check if connection is established
            if not mt5_client.check_login():
                pytest.skip("MT5 connection failed - skipping integration test")
        
        except Exception as e:
            pytest.skip(f"MT5 initialization failed: {e} - skipping integration test")
        
        try:
            # Test get_orders_helper through mtBase
            orders_df = mt5_client.get_orders_df()
            assert isinstance(orders_df, pl.DataFrame)
            logger.info(f"✓ Retrieved orders DataFrame with {len(orders_df)} orders")
            
            # Verify DataFrame structure if there are orders
            if not orders_df.is_empty():
                expected_columns = ['ticket', 'symbol', 'volume', 'time_setup', 'type']
                for col in expected_columns:
                    assert col in orders_df.columns, f"Missing expected column: {col}"
                logger.info("✓ Orders DataFrame has expected columns")
            
            # Test get_position_helper through mtBase
            positions_df = mt5_client.get_position_df()
            assert isinstance(positions_df, pl.DataFrame)
            logger.info(f"✓ Retrieved positions DataFrame with {len(positions_df)} positions")
            
            # Verify DataFrame structure if there are positions
            if not positions_df.is_empty():
                expected_columns = ['ticket', 'symbol', 'volume', 'profit', 'time']
                for col in expected_columns:
                    assert col in positions_df.columns, f"Missing expected column: {col}"
                logger.info("✓ Positions DataFrame has expected columns")
                
                # Verify that noisy columns are filtered out
                noisy_columns = ['time_update', 'time_msc', 'time_update_msc', 'external_id']
                for col in noisy_columns:
                    assert col not in positions_df.columns, f"Noisy column should be filtered: {col}"
                logger.info("✓ Noisy columns properly filtered from positions DataFrame")
            
            logger.info("✓ MT5 integration test passed successfully")
            
        finally:
            # Always shutdown MT5 connection
            mt5_client.shutdown()
