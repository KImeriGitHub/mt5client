"""Unit tests for place_order.py module."""

import pytest
from unittest.mock import MagicMock, patch
import MetaTrader5 as mt5

from src.place_order import place_order
from src.infra.OrderClient import OrderClient
from src.infra.OrderData import OrderData
from src.infra.mtBase import mtBase


class TestPlaceOrder:
    """Test cases for place_order function."""
    
    def test_place_order_successful(self):
        """Test place_order with successful order placement."""
        # Create mock order
        mock_order = MagicMock(spec=OrderData)
        mock_order.symbol = "AAPL"
        
        # Create mock order client
        mock_order_client = MagicMock(spec=OrderClient)
        mock_request_dict = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": "AAPL",
            "volume": 1.0,
            "type": mt5.ORDER_TYPE_BUY,
            "price": 150.0
        }
        mock_order_client.to_request_dict.return_value = mock_request_dict
        
        # Create mock base
        mock_base = MagicMock(spec=mtBase)
        
        # Mock successful order check
        mock_check_result = MagicMock()
        mock_check_result.retcode = 0
        mock_base.order_check.return_value = mock_check_result
        
        # Mock successful order placement
        mock_place_result = MagicMock()
        mock_place_result.retcode = mt5.TRADE_RETCODE_DONE
        mock_place_result._asdict.return_value = {"retcode": mt5.TRADE_RETCODE_DONE}
        mock_base.place_market_order.return_value = mock_place_result
        
        result_code, message = place_order(mock_order, mock_order_client, mock_base, is_dry_run=False)
        
        # Verify calls
        mock_order_client.to_request_dict.assert_called_once_with(mock_order)
        mock_base.order_check.assert_called_once_with(mock_request_dict)
        mock_base.place_market_order.assert_called_once_with(mock_request_dict)
        
        # Verify successful result
        assert result_code == 0
        assert "Order placed successfully for AAPL" in message
        assert str(mock_place_result) in message
    
    def test_place_order_check_failed(self):
        """Test place_order when order check fails."""
        # Create mock order
        mock_order = MagicMock(spec=OrderData)
        mock_order.symbol = "AAPL"
        
        # Create mock order client
        mock_order_client = MagicMock(spec=OrderClient)
        mock_request_dict = {"symbol": "AAPL"}
        mock_order_client.to_request_dict.return_value = mock_request_dict
        
        # Create mock base
        mock_base = MagicMock(spec=mtBase)
        
        # Mock failed order check
        mock_check_result = MagicMock()
        mock_check_result.retcode = 10013  # TRADE_RETCODE_INVALID_REQUEST
        mock_base.order_check.return_value = mock_check_result
        
        result_code, message = place_order(mock_order, mock_order_client, mock_base, is_dry_run=False)
        
        # Verify calls
        mock_order_client.to_request_dict.assert_called_once_with(mock_order)
        mock_base.order_check.assert_called_once_with(mock_request_dict)
        mock_base.place_market_order.assert_not_called()  # Should not be called after check failure
        
        # Verify failure result
        assert result_code == 1
        assert "Order check failed for AAPL" in message
        assert str(mock_check_result) in message
    
    def test_place_order_placement_returns_none(self):
        """Test place_order when order placement returns None."""
        # Create mock order
        mock_order = MagicMock(spec=OrderData)
        mock_order.symbol = "GOOGL"
        
        # Create mock order client
        mock_order_client = MagicMock(spec=OrderClient)
        mock_request_dict = {"symbol": "GOOGL"}
        mock_order_client.to_request_dict.return_value = mock_request_dict
        
        # Create mock base
        mock_base = MagicMock(spec=mtBase)
        
        # Mock successful order check
        mock_check_result = MagicMock()
        mock_check_result.retcode = 0
        mock_base.order_check.return_value = mock_check_result
        
        # Mock order placement returning None
        mock_base.place_market_order.return_value = None
        
        result_code, message = place_order(mock_order, mock_order_client, mock_base, is_dry_run=False)
        
        # Verify calls
        mock_order_client.to_request_dict.assert_called_once_with(mock_order)
        mock_base.order_check.assert_called_once_with(mock_request_dict)
        mock_base.place_market_order.assert_called_once_with(mock_request_dict)
        
        # Verify failure result
        assert result_code == 1
        assert "Order placement returned None for GOOGL" in message
    
    def test_place_order_placement_no_retcode(self):
        """Test place_order when order placement result has no retcode."""
        # Create mock order
        mock_order = MagicMock(spec=OrderData)
        mock_order.symbol = "MSFT"
        
        # Create mock order client
        mock_order_client = MagicMock(spec=OrderClient)
        mock_request_dict = {"symbol": "MSFT"}
        mock_order_client.to_request_dict.return_value = mock_request_dict
        
        # Create mock base
        mock_base = MagicMock(spec=mtBase)
        
        # Mock successful order check
        mock_check_result = MagicMock()
        mock_check_result.retcode = 0
        mock_base.order_check.return_value = mock_check_result
        
        # Mock order placement with missing retcode
        mock_place_result = MagicMock()
        mock_place_result._asdict.return_value = {}  # No retcode key
        mock_base.place_market_order.return_value = mock_place_result
        
        result_code, message = place_order(mock_order, mock_order_client, mock_base, is_dry_run=False)
        
        # Verify calls
        mock_order_client.to_request_dict.assert_called_once_with(mock_order)
        mock_base.order_check.assert_called_once_with(mock_request_dict)
        mock_base.place_market_order.assert_called_once_with(mock_request_dict)
        
        # Verify failure result
        assert result_code == 1
        assert "Order placement returned unknown result for MSFT" in message
        assert str(mock_place_result) in message
    
    def test_place_order_placement_failed_retcode(self):
        """Test place_order when order placement fails with error retcode."""
        # Create mock order
        mock_order = MagicMock(spec=OrderData)
        mock_order.symbol = "TSLA"
        
        # Create mock order client
        mock_order_client = MagicMock(spec=OrderClient)
        mock_request_dict = {"symbol": "TSLA"}
        mock_order_client.to_request_dict.return_value = mock_request_dict
        
        # Create mock base
        mock_base = MagicMock(spec=mtBase)
        
        # Mock successful order check
        mock_check_result = MagicMock()
        mock_check_result.retcode = 0
        mock_base.order_check.return_value = mock_check_result
        
        # Mock failed order placement
        mock_place_result = MagicMock()
        mock_place_result.retcode = 10015  # TRADE_RETCODE_INVALID_PRICE
        mock_place_result._asdict.return_value = {"retcode": 10015}
        mock_base.place_market_order.return_value = mock_place_result
        
        result_code, message = place_order(mock_order, mock_order_client, mock_base, is_dry_run=False)
        
        # Verify calls
        mock_order_client.to_request_dict.assert_called_once_with(mock_order)
        mock_base.order_check.assert_called_once_with(mock_request_dict)
        mock_base.place_market_order.assert_called_once_with(mock_request_dict)
        
        # Verify failure result
        assert result_code == 1
        assert "Order placement failed for TSLA" in message
        assert str(mock_place_result) in message
    
    def test_place_order_different_symbols(self):
        """Test place_order with different symbols in error messages."""
        symbols_to_test = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]
        
        for symbol in symbols_to_test:
            # Create mock order
            mock_order = MagicMock(spec=OrderData)
            mock_order.symbol = symbol
            
            # Create mock order client
            mock_order_client = MagicMock(spec=OrderClient)
            mock_request_dict = {"symbol": symbol}
            mock_order_client.to_request_dict.return_value = mock_request_dict
            
            # Create mock base
            mock_base = MagicMock(spec=mtBase)
            
            # Mock failed order check
            mock_check_result = MagicMock()
            mock_check_result.retcode = 10013
            mock_base.order_check.return_value = mock_check_result
            
            result_code, message = place_order(mock_order, mock_order_client, mock_base, is_dry_run=False)
            
            # Verify symbol appears in error message
            assert result_code == 1
            assert f"Order check failed for {symbol}" in message
    
    @patch('src.place_order.logger')
    def test_place_order_logging(self, mock_logger):
        """Test place_order logging behavior."""
        # Create mock order
        mock_order = MagicMock(spec=OrderData)
        mock_order.symbol = "AAPL"
        
        # Create mock order client
        mock_order_client = MagicMock(spec=OrderClient)
        mock_request_dict = {"symbol": "AAPL"}
        mock_order_client.to_request_dict.return_value = mock_request_dict
        
        # Create mock base
        mock_base = MagicMock(spec=mtBase)
        
        # Mock successful order check
        mock_check_result = MagicMock()
        mock_check_result.retcode = 0
        mock_base.order_check.return_value = mock_check_result
        
        # Mock successful order placement
        mock_place_result = MagicMock()
        mock_place_result.retcode = mt5.TRADE_RETCODE_DONE
        mock_place_result._asdict.return_value = {"retcode": mt5.TRADE_RETCODE_DONE}
        mock_base.place_market_order.return_value = mock_place_result
        
        result_code, message = place_order(mock_order, mock_order_client, mock_base, is_dry_run=False)
        
        # Verify logging was called
        mock_logger.info.assert_called_with("Placing order for AAPL...")
        
        # Verify successful result
        assert result_code == 0