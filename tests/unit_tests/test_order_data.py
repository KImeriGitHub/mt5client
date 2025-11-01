"""Unit tests for OrderData class."""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from src.infra.OrderData import OrderData


class TestOrderData:
    """Test cases for OrderData class."""
    
    def test_init_required_params_only(self):
        """Test initialization with only required parameters."""
        with patch('src.infra.OrderData.mt5') as mock_mt5:
            # Mock MT5 constants
            mock_mt5.ORDER_TYPE_BUY = 0
            mock_mt5.ORDER_TYPE_SELL = 1
            mock_mt5.ORDER_TYPE_BUY_LIMIT = 2
            mock_mt5.ORDER_TYPE_SELL_LIMIT = 3
            mock_mt5.TRADE_ACTION_DEAL = 1
            mock_mt5.TRADE_ACTION_PENDING = 5
            mock_mt5.ORDER_TIME_GTC = 0
            mock_mt5.ORDER_TIME_DAY = 1
            mock_mt5.ORDER_FILLING_FOK = 0
            mock_mt5.ORDER_FILLING_IOC = 1
            mock_mt5.ORDER_FILLING_RETURN = 2
            
            order = OrderData(
                type=0,  # ORDER_TYPE_BUY
                volume=1.0,
                price=1.2345,
                symbol="EURUSD",
                magic=12345
            )
            
            assert order.type == 0
            assert order.volume == 1.0
            assert order.price == 1.2345
            assert order.symbol == "EURUSD"
            assert order.magic == 12345
            assert order.ticket is None
            assert order.time_setup is None
            assert order.sl is None
            assert order.tp is None
            assert order.comment is None
            assert order.action is None
            assert order.type_time is None
            assert order.type_filling is None
            assert order.deviation is None
    
    def test_init_all_params(self):
        """Test initialization with all parameters."""
        with patch('src.infra.OrderData.mt5') as mock_mt5:
            # Mock MT5 constants
            mock_mt5.ORDER_TYPE_BUY = 0
            mock_mt5.ORDER_TYPE_SELL = 1
            mock_mt5.ORDER_TYPE_BUY_LIMIT = 2
            mock_mt5.ORDER_TYPE_SELL_LIMIT = 3
            mock_mt5.TRADE_ACTION_DEAL = 1
            mock_mt5.TRADE_ACTION_PENDING = 5
            mock_mt5.ORDER_TIME_GTC = 0
            mock_mt5.ORDER_TIME_DAY = 1
            mock_mt5.ORDER_FILLING_FOK = 0
            mock_mt5.ORDER_FILLING_IOC = 1
            mock_mt5.ORDER_FILLING_RETURN = 2
            
            ticket = 123456789
            time_setup = datetime(2025, 10, 27, 10, 30, 0)
            
            order = OrderData(
                ticket=ticket,
                time_setup=time_setup,
                type=1,  # ORDER_TYPE_SELL
                volume=0.5,
                price=1.2300,
                sl=1.2400,
                tp=1.2200,
                symbol="EURUSD",
                comment="Test order",
                magic=67890,
                action=1,  # TRADE_ACTION_DEAL
                type_time=0,  # ORDER_TIME_GTC
                type_filling=0,  # ORDER_FILLING_FOK
                deviation=10
            )
            
            assert order.ticket == ticket
            assert order.time_setup == time_setup
            assert order.type == 1
            assert order.volume == 0.5
            assert order.price == 1.2300
            assert order.sl == 1.2400
            assert order.tp == 1.2200
            assert order.symbol == "EURUSD"
            assert order.comment == "Test order"
            assert order.magic == 67890
            assert order.action == 1
            assert order.type_time == 0
            assert order.type_filling == 0
            assert order.deviation == 10
    
    def test_validate_parameters_valid_type(self):
        """Test parameter validation with valid order type."""
        with patch('src.infra.OrderData.mt5') as mock_mt5:
            mock_mt5.ORDER_TYPE_BUY = 0
            mock_mt5.ORDER_TYPE_SELL = 1
            mock_mt5.ORDER_TYPE_BUY_LIMIT = 2
            mock_mt5.ORDER_TYPE_SELL_LIMIT = 3
            mock_mt5.TRADE_ACTION_DEAL = 1
            mock_mt5.TRADE_ACTION_PENDING = 5
            mock_mt5.ORDER_TIME_GTC = 0
            mock_mt5.ORDER_TIME_DAY = 1
            mock_mt5.ORDER_FILLING_FOK = 0
            mock_mt5.ORDER_FILLING_IOC = 1
            mock_mt5.ORDER_FILLING_RETURN = 2
            
            # Should not raise any exception
            order = OrderData(
                type=2,  # ORDER_TYPE_BUY_LIMIT
                volume=1.0,
                price=1.2345,
                symbol="EURUSD",
                magic=12345
            )
            assert order.type == 2
    
    def test_validate_parameters_invalid_type(self):
        """Test parameter validation with invalid order type."""
        with patch('src.infra.OrderData.mt5') as mock_mt5:
            mock_mt5.ORDER_TYPE_BUY = 0
            mock_mt5.ORDER_TYPE_SELL = 1
            mock_mt5.ORDER_TYPE_BUY_LIMIT = 2
            mock_mt5.ORDER_TYPE_SELL_LIMIT = 3
            mock_mt5.TRADE_ACTION_DEAL = 1
            mock_mt5.TRADE_ACTION_PENDING = 5
            mock_mt5.ORDER_TIME_GTC = 0
            mock_mt5.ORDER_TIME_DAY = 1
            mock_mt5.ORDER_FILLING_FOK = 0
            mock_mt5.ORDER_FILLING_IOC = 1
            mock_mt5.ORDER_FILLING_RETURN = 2
            
            with pytest.raises(ValueError, match="Invalid order type"):
                OrderData(
                    type=999,  # Invalid type
                    volume=1.0,
                    price=1.2345,
                    symbol="EURUSD",
                    magic=12345
                )
    
    def test_validate_parameters_invalid_action(self):
        """Test parameter validation with invalid action."""
        with patch('src.infra.OrderData.mt5') as mock_mt5:
            mock_mt5.ORDER_TYPE_BUY = 0
            mock_mt5.ORDER_TYPE_SELL = 1
            mock_mt5.ORDER_TYPE_BUY_LIMIT = 2
            mock_mt5.ORDER_TYPE_SELL_LIMIT = 3
            mock_mt5.TRADE_ACTION_DEAL = 1
            mock_mt5.TRADE_ACTION_PENDING = 5
            mock_mt5.ORDER_TIME_GTC = 0
            mock_mt5.ORDER_TIME_DAY = 1
            mock_mt5.ORDER_FILLING_FOK = 0
            mock_mt5.ORDER_FILLING_IOC = 1
            mock_mt5.ORDER_FILLING_RETURN = 2
            
            with pytest.raises(ValueError, match="Invalid action"):
                OrderData(
                    type=0,
                    volume=1.0,
                    price=1.2345,
                    symbol="EURUSD",
                    magic=12345,
                    action=999  # Invalid action
                )
    
    def test_validate_parameters_invalid_type_time(self):
        """Test parameter validation with invalid type_time."""
        with patch('src.infra.OrderData.mt5') as mock_mt5:
            mock_mt5.ORDER_TYPE_BUY = 0
            mock_mt5.ORDER_TYPE_SELL = 1
            mock_mt5.ORDER_TYPE_BUY_LIMIT = 2
            mock_mt5.ORDER_TYPE_SELL_LIMIT = 3
            mock_mt5.TRADE_ACTION_DEAL = 1
            mock_mt5.TRADE_ACTION_PENDING = 5
            mock_mt5.ORDER_TIME_GTC = 0
            mock_mt5.ORDER_TIME_DAY = 1
            mock_mt5.ORDER_FILLING_FOK = 0
            mock_mt5.ORDER_FILLING_IOC = 1
            mock_mt5.ORDER_FILLING_RETURN = 2
            
            with pytest.raises(ValueError, match="Invalid type_time"):
                OrderData(
                    type=0,
                    volume=1.0,
                    price=1.2345,
                    symbol="EURUSD",
                    magic=12345,
                    type_time=999  # Invalid type_time
                )
    
    def test_validate_parameters_invalid_type_filling(self):
        """Test parameter validation with invalid type_filling."""
        with patch('src.infra.OrderData.mt5') as mock_mt5:
            mock_mt5.ORDER_TYPE_BUY = 0
            mock_mt5.ORDER_TYPE_SELL = 1
            mock_mt5.ORDER_TYPE_BUY_LIMIT = 2
            mock_mt5.ORDER_TYPE_SELL_LIMIT = 3
            mock_mt5.TRADE_ACTION_DEAL = 1
            mock_mt5.TRADE_ACTION_PENDING = 5
            mock_mt5.ORDER_TIME_GTC = 0
            mock_mt5.ORDER_TIME_DAY = 1
            mock_mt5.ORDER_FILLING_FOK = 0
            mock_mt5.ORDER_FILLING_IOC = 1
            mock_mt5.ORDER_FILLING_RETURN = 2
            
            with pytest.raises(ValueError, match="Invalid type_filling"):
                OrderData(
                    type=0,
                    volume=1.0,
                    price=1.2345,
                    symbol="EURUSD",
                    magic=12345,
                    type_filling=999  # Invalid type_filling
                )
    
    def test_validate_parameters_invalid_comment_too_long(self):
        """Test parameter validation with comment longer than 31 characters."""
        with patch('src.infra.OrderData.mt5') as mock_mt5:
            mock_mt5.ORDER_TYPE_BUY = 0
            mock_mt5.ORDER_TYPE_SELL = 1
            mock_mt5.ORDER_TYPE_BUY_LIMIT = 2
            mock_mt5.ORDER_TYPE_SELL_LIMIT = 3
            mock_mt5.TRADE_ACTION_DEAL = 1
            mock_mt5.TRADE_ACTION_PENDING = 5
            mock_mt5.ORDER_TIME_GTC = 0
            mock_mt5.ORDER_TIME_DAY = 1
            mock_mt5.ORDER_FILLING_FOK = 0
            mock_mt5.ORDER_FILLING_IOC = 1
            mock_mt5.ORDER_FILLING_RETURN = 2
            
            long_comment = "This comment is definitely longer than 31 characters and should raise an error"
            
            with pytest.raises(ValueError, match="Comment must be at most 31 characters"):
                OrderData(
                    type=0,
                    volume=1.0,
                    price=1.2345,
                    symbol="EURUSD",
                    magic=12345,
                    comment=long_comment
                )
    
    def test_validate_parameters_valid_comment_max_length(self):
        """Test parameter validation with comment exactly 31 characters."""
        with patch('src.infra.OrderData.mt5') as mock_mt5:
            mock_mt5.ORDER_TYPE_BUY = 0
            mock_mt5.ORDER_TYPE_SELL = 1
            mock_mt5.ORDER_TYPE_BUY_LIMIT = 2
            mock_mt5.ORDER_TYPE_SELL_LIMIT = 3
            mock_mt5.TRADE_ACTION_DEAL = 1
            mock_mt5.TRADE_ACTION_PENDING = 5
            mock_mt5.ORDER_TIME_GTC = 0
            mock_mt5.ORDER_TIME_DAY = 1
            mock_mt5.ORDER_FILLING_FOK = 0
            mock_mt5.ORDER_FILLING_IOC = 1
            mock_mt5.ORDER_FILLING_RETURN = 2
            
            valid_comment = "A" * 31  # Exactly 31 characters
            
            # Should not raise any exception
            order = OrderData(
                type=0,
                volume=1.0,
                price=1.2345,
                symbol="EURUSD",
                magic=12345,
                comment=valid_comment
            )
            assert order.comment == valid_comment
    
    def test_repr(self):
        """Test string representation."""
        with patch('src.infra.OrderData.mt5') as mock_mt5:
            mock_mt5.ORDER_TYPE_BUY = 0
            mock_mt5.ORDER_TYPE_SELL = 1
            mock_mt5.ORDER_TYPE_BUY_LIMIT = 2
            mock_mt5.ORDER_TYPE_SELL_LIMIT = 3
            mock_mt5.TRADE_ACTION_DEAL = 1
            mock_mt5.TRADE_ACTION_PENDING = 5
            mock_mt5.ORDER_TIME_GTC = 0
            mock_mt5.ORDER_TIME_DAY = 1
            mock_mt5.ORDER_FILLING_FOK = 0
            mock_mt5.ORDER_FILLING_IOC = 1
            mock_mt5.ORDER_FILLING_RETURN = 2
            
            order = OrderData(
                ticket=123456,
                type=1,
                volume=0.75,
                price=1.2500,
                symbol="GBPUSD",
                magic=98765,
                sl=1.2600,
                tp=1.2400
            )
            
            expected = ("OrderData(ticket=123456, "
                       "symbol='GBPUSD', "
                       "type=1, "
                       "volume=0.75, "
                       "price=1.25, "
                       "sl=1.26, "
                       "tp=1.24, "
                       "magic=98765)")
            
            assert repr(order) == expected
    
    def test_to_dict_required_only(self):
        """Test to_dict with only required parameters."""
        with patch('src.infra.OrderData.mt5') as mock_mt5:
            mock_mt5.ORDER_TYPE_BUY = 0
            mock_mt5.ORDER_TYPE_SELL = 1
            mock_mt5.ORDER_TYPE_BUY_LIMIT = 2
            mock_mt5.ORDER_TYPE_SELL_LIMIT = 3
            mock_mt5.TRADE_ACTION_DEAL = 1
            mock_mt5.TRADE_ACTION_PENDING = 5
            mock_mt5.ORDER_TIME_GTC = 0
            mock_mt5.ORDER_TIME_DAY = 1
            mock_mt5.ORDER_FILLING_FOK = 0
            mock_mt5.ORDER_FILLING_IOC = 1
            mock_mt5.ORDER_FILLING_RETURN = 2
            
            order = OrderData(
                type=0,
                volume=1.0,
                price=1.2345,
                symbol="EURUSD",
                magic=12345
            )
            
            result = order.to_dict()
            
            expected = {
                'type': 0,
                'volume': 1.0,
                'price': 1.2345,
                'symbol': 'EURUSD',
                'magic': 12345
            }
            
            assert result == expected
    
    def test_to_dict_all_params(self):
        """Test to_dict with all parameters."""
        with patch('src.infra.OrderData.mt5') as mock_mt5:
            mock_mt5.ORDER_TYPE_BUY = 0
            mock_mt5.ORDER_TYPE_SELL = 1
            mock_mt5.ORDER_TYPE_BUY_LIMIT = 2
            mock_mt5.ORDER_TYPE_SELL_LIMIT = 3
            mock_mt5.TRADE_ACTION_DEAL = 1
            mock_mt5.TRADE_ACTION_PENDING = 5
            mock_mt5.ORDER_TIME_GTC = 0
            mock_mt5.ORDER_TIME_DAY = 1
            mock_mt5.ORDER_FILLING_FOK = 0
            mock_mt5.ORDER_FILLING_IOC = 1
            mock_mt5.ORDER_FILLING_RETURN = 2
            
            time_setup = datetime(2025, 10, 27, 10, 30, 0)
            
            order = OrderData(
                ticket=123456,
                time_setup=time_setup,
                type=1,
                volume=0.5,
                price=1.2300,
                sl=1.2400,
                tp=1.2200,
                symbol="EURUSD",
                comment="Test order",
                magic=67890,
                action=1,
                type_time=0,
                type_filling=0,
                deviation=10
            )
            
            result = order.to_dict()
            
            expected = {
                'ticket': 123456,
                'time_setup': '2025-10-27T10:30:00',
                'type': 1,
                'volume': 0.5,
                'price': 1.2300,
                'sl': 1.2400,
                'tp': 1.2200,
                'symbol': 'EURUSD',
                'comment': 'Test order',
                'magic': 67890,
                'action': 1,
                'type_time': 0,
                'type_filling': 0,
                'deviation': 10
            }
            
            assert result == expected
    
    def test_is_buy_order_property(self):
        """Test is_buy_order property."""
        with patch('src.infra.OrderData.mt5') as mock_mt5:
            mock_mt5.ORDER_TYPE_BUY = 0
            mock_mt5.ORDER_TYPE_SELL = 1
            mock_mt5.ORDER_TYPE_BUY_LIMIT = 2
            mock_mt5.ORDER_TYPE_SELL_LIMIT = 3
            mock_mt5.TRADE_ACTION_DEAL = 1
            mock_mt5.TRADE_ACTION_PENDING = 5
            mock_mt5.ORDER_TIME_GTC = 0
            mock_mt5.ORDER_TIME_DAY = 1
            mock_mt5.ORDER_FILLING_FOK = 0
            mock_mt5.ORDER_FILLING_IOC = 1
            mock_mt5.ORDER_FILLING_RETURN = 2
            
            buy_order = OrderData(
                type=0,  # Should be in buy_types [0, 2, 4]
                volume=1.0,
                price=1.2345,
                symbol="EURUSD",
                magic=12345
            )
            
            buy_limit_order = OrderData(
                type=2,  # Should be in buy_types [0, 2, 4]
                volume=1.0,
                price=1.2345,
                symbol="EURUSD",
                magic=12345
            )
            
            sell_order = OrderData(
                type=1,  # Should not be in buy_types
                volume=1.0,
                price=1.2345,
                symbol="EURUSD",
                magic=12345
            )
            
            assert buy_order.is_buy_order is True
            assert buy_limit_order.is_buy_order is True
            assert sell_order.is_buy_order is False
    
    def test_is_sell_order_property(self):
        """Test is_sell_order property."""
        with patch('src.infra.OrderData.mt5') as mock_mt5:
            mock_mt5.ORDER_TYPE_BUY = 0
            mock_mt5.ORDER_TYPE_SELL = 1
            mock_mt5.ORDER_TYPE_BUY_LIMIT = 2
            mock_mt5.ORDER_TYPE_SELL_LIMIT = 3
            mock_mt5.TRADE_ACTION_DEAL = 1
            mock_mt5.TRADE_ACTION_PENDING = 5
            mock_mt5.ORDER_TIME_GTC = 0
            mock_mt5.ORDER_TIME_DAY = 1
            mock_mt5.ORDER_FILLING_FOK = 0
            mock_mt5.ORDER_FILLING_IOC = 1
            mock_mt5.ORDER_FILLING_RETURN = 2
            
            sell_order = OrderData(
                type=1,  # Should be in sell_types [1, 3, 5]
                volume=1.0,
                price=1.2345,
                symbol="EURUSD",
                magic=12345
            )
            
            sell_limit_order = OrderData(
                type=3,  # Should be in sell_types [1, 3, 5]
                volume=1.0,
                price=1.2345,
                symbol="EURUSD",
                magic=12345
            )
            
            buy_order = OrderData(
                type=0,  # Should not be in sell_types
                volume=1.0,
                price=1.2345,
                symbol="EURUSD",
                magic=12345
            )
            
            assert sell_order.is_sell_order is True
            assert sell_limit_order.is_sell_order is True
            assert buy_order.is_sell_order is False