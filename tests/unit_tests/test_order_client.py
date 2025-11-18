"""Unit tests for OrderClient class."""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from typing import List
import polars as pl

from src.infra.OrderClient import OrderClient
from src.infra.OrderData import OrderData
from src.infra.mtBase import mtBase


class TestOrderClient:
    """Test cases for OrderClient class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_base = MagicMock(spec=mtBase)
        self.client = OrderClient(base=self.mock_base)
    
    def test_init(self):
        """Test OrderClient initialization."""
        assert self.client._base == self.mock_base
        assert self.client._orders == []
        assert self.client._orders_df is None
    
    def test_base_property(self):
        """Test base property getter."""
        assert self.client.base == self.mock_base
    
    def test_base_property_setter(self):
        """Test base property setter."""
        new_base = MagicMock(spec=mtBase)
        self.client.base = new_base
        assert self.client._base == new_base
    
    def test_base_property_none_raises_error(self):
        """Test that base property raises error when None."""
        self.client._base = None
        with pytest.raises(RuntimeError, match="mtBase instance is required"):
            _ = self.client.base
    
    def create_mock_order(self, **kwargs) -> OrderData:
        """Helper to create mock OrderData object."""
        defaults = {
            'type': 0,
            'volume': 1.0,
            'price': 100.0,
            'symbol': 'EURUSD',
            'magic': 12345,
            'ticket': 123456,
            'time_setup': datetime(2023, 1, 15, 10, 30, 45),
            'sl': 99.0,
            'tp': 101.0,
            'comment': 'Test order',
            'action': 1,
            'type_time': 0,
            'type_filling': 0,
            'deviation': 10
        }
        defaults.update(kwargs)
        
        mock_order = MagicMock(spec=OrderData)
        for attr, value in defaults.items():
            setattr(mock_order, attr, value)
        
        return mock_order

    @patch('src.infra.OrderClient.logger')
    def test_log_orders_single_order(self, mock_logger):
        """Test log_orders with a single OrderData object."""
        order = self.create_mock_order()
        
        self.client.log_orders(order, indent=2, add_msg="Test Order")
        
        # Verify logger.info was called
        assert mock_logger.info.call_count >= 2  # At least header and order details
        
        # Check that the header call was made
        header_call = mock_logger.info.call_args_list[0]
        assert "Loaded 1 orders:" in header_call[0][0]
        
        # Check that order details call was made
        details_call = mock_logger.info.call_args_list[1]
        details_msg = details_call[0][0]
        assert "Test Order:" in details_msg
        assert "Ticket: 123456" in details_msg
        assert "Symbol: EURUSD" in details_msg
        assert "Volume: 1.00" in details_msg
        assert "Price: 100.0000" in details_msg
        assert "Magic: 12345" in details_msg

    @patch('src.infra.OrderClient.logger')
    def test_log_orders_multiple_orders(self, mock_logger):
        """Test log_orders with a list of OrderData objects."""
        orders = [
            self.create_mock_order(symbol='EURUSD', ticket=123456),
            self.create_mock_order(symbol='GBPUSD', ticket=789012)
        ]
        
        self.client.log_orders(orders, indent=4, add_msg="Multiple Orders")
        
        # Verify logger.info was called for header + each order
        assert mock_logger.info.call_count >= 3  # Header + 2 orders
        
        # Check header
        header_call = mock_logger.info.call_args_list[0]
        assert "Loaded 2 orders:" in header_call[0][0]
        assert "    " in header_call[0][0]  # Check indent=4
        
        # Check first order details
        first_order_call = mock_logger.info.call_args_list[1]
        first_order_msg = first_order_call[0][0]
        assert "Multiple Orders:" in first_order_msg
        assert "Ticket: 123456" in first_order_msg
        assert "Symbol: EURUSD" in first_order_msg
        
        # Check second order details
        second_order_call = mock_logger.info.call_args_list[2]
        second_order_msg = second_order_call[0][0]
        assert "Multiple Orders:" in second_order_msg
        assert "Ticket: 789012" in second_order_msg
        assert "Symbol: GBPUSD" in second_order_msg

    @patch('src.infra.OrderClient.logger')
    def test_log_orders_empty_list(self, mock_logger):
        """Test log_orders with empty list."""
        self.client.log_orders([], indent=2, add_msg="Empty")
        
        mock_logger.info.assert_called_once_with("No orders to log.")

    @patch('src.infra.OrderClient.logger')
    def test_log_orders_none(self, mock_logger):
        """Test log_orders with None."""
        self.client.log_orders(None, indent=2, add_msg="None")
        
        mock_logger.info.assert_called_once_with("No orders to log.")

    @patch('src.infra.OrderClient.logger')
    def test_log_orders_default_parameters(self, mock_logger):
        """Test log_orders with default parameters."""
        order = self.create_mock_order()
        
        self.client.log_orders(order)  # No indent or add_msg specified
        
        # Verify logger.info was called
        assert mock_logger.info.call_count >= 2
        
        # Check default indent (2 spaces)
        header_call = mock_logger.info.call_args_list[0]
        assert header_call[0][0].startswith("  ")  # Default indent=2
        
        # Check default add_msg (empty string)
        details_call = mock_logger.info.call_args_list[1]
        details_msg = details_call[0][0]
        assert ":" in details_msg  # Empty add_msg results in just ":"

    @patch('src.infra.OrderClient.logger')
    def test_log_orders_missing_attributes(self, mock_logger):
        """Test log_orders with OrderData object missing some attributes."""
        # Create order with minimal attributes
        order = MagicMock(spec=OrderData)
        order.symbol = "EURUSD"
        order.volume = 1.5
        # All other attributes return None or don't exist
        
        self.client.log_orders(order, add_msg="Minimal Order")
        
        # Should not raise an exception and should log with empty strings for missing attrs
        assert mock_logger.info.call_count >= 2
        
        details_call = mock_logger.info.call_args_list[1]
        details_msg = details_call[0][0]
        assert "Symbol: EURUSD" in details_msg
        assert "Volume: 1.50" in details_msg
        assert "Ticket: " in details_msg  # Empty string for None ticket
        assert "Magic: " in details_msg    # Empty string for None magic

    @patch('src.infra.OrderClient.logger')
    def test_log_orders_datetime_formatting(self, mock_logger):
        """Test log_orders properly formats datetime objects."""
        import datetime as dt
        
        # Test with datetime object
        order = self.create_mock_order(
            time_setup=dt.datetime(2023, 5, 15, 14, 30, 45)
        )
        
        self.client.log_orders(order, add_msg="DateTime Test")
        
        details_call = mock_logger.info.call_args_list[1]
        details_msg = details_call[0][0]
        assert "Time setup: 15-May-2023 14:30:45" in details_msg

    @patch('src.infra.OrderClient.logger')
    def test_log_orders_none_datetime(self, mock_logger):
        """Test log_orders with None time_setup."""
        order = self.create_mock_order(time_setup=None)
        
        self.client.log_orders(order, add_msg="No DateTime")
        
        details_call = mock_logger.info.call_args_list[1]
        details_msg = details_call[0][0]
        assert "Time setup: " in details_msg  # Should be empty string

    @patch('src.infra.OrderClient.logger')
    def test_log_orders_numeric_formatting(self, mock_logger):
        """Test log_orders properly formats numeric values."""
        order = self.create_mock_order(
            volume=2.75,
            price=1.23456,
            sl=1.23000,
            tp=1.24567
        )
        
        self.client.log_orders(order, add_msg="Numeric Test")
        
        details_call = mock_logger.info.call_args_list[1]
        details_msg = details_call[0][0]
        assert "Volume: 2.75" in details_msg
        assert "Price: 1.2346" in details_msg  # 4 decimal places
        assert "SL: 1.2300" in details_msg     # 4 decimal places
        assert "TP: 1.2457" in details_msg     # 4 decimal places

    @patch('src.infra.OrderClient.logger')
    def test_log_orders_none_numeric_values(self, mock_logger):
        """Test log_orders with None numeric values."""
        order = self.create_mock_order(
            sl=None,
            tp=None,
            deviation=None
        )
        
        self.client.log_orders(order, add_msg="None Numeric")
        
        details_call = mock_logger.info.call_args_list[1]
        details_msg = details_call[0][0]
        assert "SL: \n" in details_msg        # Empty string for None (space after colon, then newline)
        assert "TP: \n" in details_msg        # Empty string for None  
        assert "Deviation:" in details_msg   # Empty string for None (no space when empty)

    @patch('src.infra.OrderClient.logger')
    def test_log_orders_tuple_input(self, mock_logger):
        """Test log_orders accepts tuple input."""
        orders = (
            self.create_mock_order(symbol='EURUSD'),
            self.create_mock_order(symbol='GBPUSD')
        )
        
        self.client.log_orders(orders, add_msg="Tuple Input")
        
        # Should handle tuple same as list
        assert mock_logger.info.call_count >= 3  # Header + 2 orders

    def test_get_orders_empty(self):
        """Test get_orders with empty orders list."""
        result = self.client.get_orders()
        assert result == []

    def test_get_orders_with_symbol_filter(self):
        """Test get_orders with symbol filter."""
        # Mock orders in client
        order1 = self.create_mock_order(symbol='EURUSD')
        order2 = self.create_mock_order(symbol='GBPUSD')
        self.client._orders = [order1, order2]
        
        result = self.client.get_orders(symbol='EURUSD')
        assert len(result) == 1
        assert result[0].symbol == 'EURUSD'

    def test_get_orders_with_magic_filter(self):
        """Test get_orders with magic number filter."""
        # Mock orders in client
        order1 = self.create_mock_order(magic=12345)
        order2 = self.create_mock_order(magic=67890)
        self.client._orders = [order1, order2]
        
        result = self.client.get_orders(magic=12345)
        assert len(result) == 1
        assert result[0].magic == 12345

    def test_count_orders(self):
        """Test count_orders method."""
        # Mock orders in client
        self.client._orders = [
            self.create_mock_order(),
            self.create_mock_order()
        ]
        
        result = self.client.count_orders()
        assert result == 2

    def test_has_orders(self):
        """Test has_orders method."""
        # Empty orders
        assert not self.client.has_orders()
        
        # With orders
        self.client._orders = [self.create_mock_order()]
        assert self.client.has_orders()

    def test_get_orders_dataframe(self):
        """Test get_orders_dataframe method."""
        # Initially None
        assert self.client.get_orders_dataframe() is None
        
        # Mock DataFrame
        mock_df = MagicMock(spec=pl.DataFrame)
        self.client._orders_df = mock_df
        assert self.client.get_orders_dataframe() == mock_df

    def test_to_order_data(self):
        """Test to_order_data method."""
        import datetime as dt
        
        row = {
            'type': 0,
            'volume_initial': 1.5,
            'price_open': 1.2345,
            'symbol': 'EURUSD',
            'magic': 12345,
            'ticket': 123456,
            'time_dt': dt.datetime(2023, 1, 15, 10, 30),
            'sl': 1.2300,
            'tp': 1.2400,
            'comment': 'Test comment'
        }
        
        with patch('src.infra.OrderClient.OrderData') as mock_order_data_class:
            mock_order = MagicMock()
            mock_order_data_class.return_value = mock_order
            
            result = self.client.to_order_data(row)
            
            # Verify OrderData was called with correct arguments
            mock_order_data_class.assert_called_once_with(
                type=0,
                volume=1.5,
                price=1.2345,
                symbol='EURUSD',
                magic=12345,
                ticket=123456,
                time_setup=dt.datetime(2023, 1, 15, 10, 30),
                sl=1.2300,
                tp=1.2400,
                comment='Test comment'
            )
            assert result == mock_order

    def test_to_order_data_zero_sl_tp(self):
        """Test to_order_data converts zero SL/TP to None."""
        row = {
            'type': 0,
            'volume_initial': 1.0,
            'price_open': 1.2345,
            'symbol': 'EURUSD',
            'magic': 12345,
            'ticket': 123456,
            'sl': 0.0,
            'tp': 0.0,
            'comment': None
        }
        
        with patch('src.infra.OrderClient.OrderData') as mock_order_data_class:
            mock_order = MagicMock()
            mock_order_data_class.return_value = mock_order
            
            result = self.client.to_order_data(row)
            
            # Verify SL/TP are None when zero
            call_args = mock_order_data_class.call_args[1]
            assert call_args['sl'] is None
            assert call_args['tp'] is None

    @patch('builtins.__import__')
    def test_to_request_dict_basic(self, mock_import):
        """Test to_request_dict with basic OrderData."""
        # Create a mock mt5 module
        mock_mt5 = MagicMock()
        mock_mt5.ORDER_TYPE_BUY = 0
        mock_mt5.ORDER_TYPE_SELL = 1
        mock_mt5.TRADE_ACTION_DEAL = 1
        mock_mt5.ORDER_TIME_GTC = 0
        mock_mt5.ORDER_FILLING_FOK = 0
        
        # Mock the import to return our mock mt5
        def import_side_effect(name, *args, **kwargs):
            if name == 'MetaTrader5':
                return mock_mt5
            return __import__(name, *args, **kwargs)
        
        mock_import.side_effect = import_side_effect
        
        order = self.create_mock_order(
            type=0,  # BUY
            volume=1.0,
            price=1.2345,
            symbol='EURUSD',
            magic=12345,
            action=None,  # Should be auto-determined
            type_time=None,  # Should default
            type_filling=None,  # Should default
            sl=None,
            tp=None,
            comment=None,
            deviation=None
        )
        
        result = self.client.to_request_dict(order)
        
        expected = {
            'symbol': 'EURUSD',
            'volume': 1.0,
            'type': 0,
            'price': 1.2345,
            'magic': 12345,
            'action': 1,  # TRADE_ACTION_DEAL
            'type_time': 0,  # ORDER_TIME_GTC
            'type_filling': 0,  # ORDER_FILLING_FOK
            'comment': 'darwinexclient order EURUSD'
        }
        
        assert result == expected

    @patch('builtins.__import__')
    def test_to_request_dict_with_all_fields(self, mock_import):
        """Test to_request_dict with all fields populated."""
        # Create a mock mt5 module
        mock_mt5 = MagicMock()
        mock_mt5.TRADE_ACTION_PENDING = 5
        mock_mt5.ORDER_TIME_DAY = 1
        mock_mt5.ORDER_FILLING_IOC = 1
        
        # Mock the import to return our mock mt5
        def import_side_effect(name, *args, **kwargs):
            if name == 'MetaTrader5':
                return mock_mt5
            return __import__(name, *args, **kwargs)
        
        mock_import.side_effect = import_side_effect
        
        order = self.create_mock_order(
            action=5,
            type_time=1,
            type_filling=1,
            sl=1.2300,
            tp=1.2400,
            comment='Custom comment',
            deviation=20
        )
        
        result = self.client.to_request_dict(order)
        
        assert result['action'] == 5
        assert result['type_time'] == 1
        assert result['type_filling'] == 1
        assert result['sl'] == 1.2300
        assert result['tp'] == 1.2400
        assert result['comment'] == 'Custom comment'
        assert result['deviation'] == 20

    @patch('builtins.__import__')
    def test_to_request_dict_pending_order_defaults(self, mock_import):
        """Test to_request_dict defaults for pending orders."""
        # Create a mock mt5 module
        mock_mt5 = MagicMock()
        mock_mt5.ORDER_TYPE_BUY_LIMIT = 2
        mock_mt5.ORDER_TYPE_BUY = 0
        mock_mt5.ORDER_TYPE_SELL = 1
        mock_mt5.TRADE_ACTION_PENDING = 5
        mock_mt5.ORDER_TIME_GTC = 0
        mock_mt5.ORDER_FILLING_RETURN = 2
        
        # Mock the import to return our mock mt5
        def import_side_effect(name, *args, **kwargs):
            if name == 'MetaTrader5':
                return mock_mt5
            return __import__(name, *args, **kwargs)
        
        mock_import.side_effect = import_side_effect
        
        order = self.create_mock_order(
            type=2,  # BUY_LIMIT (pending order)
            action=None,
            type_time=None,
            type_filling=None
        )
        
        result = self.client.to_request_dict(order)
        
        assert result['action'] == 5  # TRADE_ACTION_PENDING
        assert result['type_filling'] == 2  # ORDER_FILLING_RETURN for pending