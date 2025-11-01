"""Unit tests for divisors_for_max_volume function (now in finalize_predictions.py)."""

import pytest
from unittest.mock import MagicMock

from src.finalize_predictions import divisors_for_max_volume
from src.infra.PredictionData import PredictionData
from src.infra.mtBase import mtBase


class TestDivisorsForMaxVolume:
    """Test cases for divisors_for_max_volume function."""
    
    def test_divisors_for_max_volume_basic_case(self):
        """Test divisors_for_max_volume with basic valid inputs."""
        # Create mock predictions
        pred1 = MagicMock(spec=PredictionData)
        pred1.symbol = "AAPL"
        pred1.last_close_price = 150.0
        
        pred2 = MagicMock(spec=PredictionData)
        pred2.symbol = "GOOGL"
        pred2.last_close_price = 2500.0
        
        predictions = [pred1, pred2]
        budget_list = [10000.0, 20000.0]
        
        # Create mock base
        mock_base = MagicMock(spec=mtBase)
        
        # Mock symbol info for AAPL
        aapl_info = {
            "volume_max": 100.0,
            "trade_contract_size": 100.0
        }
        
        # Mock symbol info for GOOGL
        googl_info = {
            "volume_max": 50.0,
            "trade_contract_size": 100.0
        }
        
        # Configure get_symbol_info to return different info based on symbol
        def mock_get_symbol_info(symbol, wait_sec=0.5):
            if symbol == "AAPL":
                return aapl_info
            elif symbol == "GOOGL":
                return googl_info
            return {}
        
        mock_base.get_symbol_info.side_effect = mock_get_symbol_info
        
        # Mock get_symbol_price to return None (so it falls back to last_close_price)
        mock_base.get_symbol_price.return_value = None
        
        result = divisors_for_max_volume(predictions, budget_list, mock_base)
        
        # Verify the function was called with correct parameters
        assert mock_base.get_symbol_info.call_count == 2
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(div, int) for div in result)
        assert all(div >= 1 for div in result)
    
    def test_divisors_for_max_volume_within_limit(self):
        """Test divisors_for_max_volume when affordable volume is within limits."""
        # Create mock prediction
        pred = MagicMock(spec=PredictionData)
        pred.symbol = "AAPL"
        pred.last_close_price = 100.0
        
        predictions = [pred]
        budget_list = [1000.0]  # Small budget
        
        # Create mock base
        mock_base = MagicMock(spec=mtBase)
        
        # Mock symbol info with high max volume
        symbol_info = {
            "volume_max": 1000.0,  # Very high limit
            "trade_contract_size": 100.0
        }
        
        mock_base.get_symbol_info.return_value = symbol_info
        mock_base.get_symbol_price.return_value = None
        
        result = divisors_for_max_volume(predictions, budget_list, mock_base)
        
        # Should return divisor of 1 since affordable volume is well within limits
        assert result == [1]
    
    def test_divisors_for_max_volume_exceeds_limit(self):
        """Test divisors_for_max_volume when affordable volume exceeds limits."""
        # Create mock prediction
        pred = MagicMock(spec=PredictionData)
        pred.symbol = "AAPL"
        pred.last_close_price = 10.0  # Low price
        
        predictions = [pred]
        budget_list = [10000.0]  # High budget
        
        # Create mock base
        mock_base = MagicMock(spec=mtBase)
        
        # Mock symbol info with low max volume
        symbol_info = {
            "volume_max": 1.0,  # Very low limit
            "trade_contract_size": 10.0
        }
        
        mock_base.get_symbol_info.return_value = symbol_info
        mock_base.get_symbol_price.return_value = None
        
        result = divisors_for_max_volume(predictions, budget_list, mock_base)
        
        # Should return a divisor > 1 since we exceed the limit
        assert result[0] > 1
        assert isinstance(result[0], int)
    
    def test_divisors_for_max_volume_mismatched_lengths(self):
        """Test divisors_for_max_volume with mismatched input lengths."""
        pred = MagicMock(spec=PredictionData)
        predictions = [pred]
        budget_list = [1000.0, 2000.0]  # Different length
        mock_base = MagicMock(spec=mtBase)
        
        with pytest.raises(ValueError, match="predictions and budget_list must have the same length"):
            divisors_for_max_volume(predictions, budget_list, mock_base)
    
    def test_divisors_for_max_volume_invalid_symbol_info(self):
        """Test divisors_for_max_volume with invalid symbol info."""
        pred = MagicMock(spec=PredictionData)
        pred.symbol = "INVALID"
        pred.last_close_price = 100.0
        
        predictions = [pred]
        budget_list = [1000.0]
        
        mock_base = MagicMock(spec=mtBase)
        
        # Mock invalid symbol info (missing required fields)
        mock_base.get_symbol_info.return_value = {}
        mock_base.get_symbol_price.return_value = None
        
        # With current implementation, this should cause division by None/zero issues
        # The function will try to access None values and fail
        with pytest.raises((TypeError, ZeroDivisionError)):
            divisors_for_max_volume(predictions, budget_list, mock_base)
    
    def test_divisors_for_max_volume_zero_budget(self):
        """Test divisors_for_max_volume with zero budget."""
        pred = MagicMock(spec=PredictionData)
        pred.symbol = "AAPL"
        pred.last_close_price = 100.0
        
        predictions = [pred]
        budget_list = [0.0]  # Zero budget
        
        mock_base = MagicMock(spec=mtBase)
        
        symbol_info = {
            "volume_max": 100.0,
            "trade_contract_size": 100.0
        }
        
        mock_base.get_symbol_info.return_value = symbol_info
        mock_base.get_symbol_price.return_value = None
        
        # Zero budget means affordable_vol = 0, which should result in divisor 1
        result = divisors_for_max_volume(predictions, budget_list, mock_base)
        assert result == [1]  # Zero volume is within any max volume limit
    
    def test_divisors_for_max_volume_none_last_close_price(self):
        """Test divisors_for_max_volume with None last_close_price."""
        pred = MagicMock(spec=PredictionData)
        pred.symbol = "AAPL"
        pred.last_close_price = None
        
        predictions = [pred]
        budget_list = [1000.0]
        
        mock_base = MagicMock(spec=mtBase)
        
        symbol_info = {
            "volume_max": 100.0,
            "trade_contract_size": 100.0
        }
        
        mock_base.get_symbol_info.return_value = symbol_info
        mock_base.get_symbol_price.return_value = None
        
        # None price will cause TypeError when trying to do arithmetic
        with pytest.raises(TypeError):
            divisors_for_max_volume(predictions, budget_list, mock_base)
    
    def test_divisors_for_max_volume_custom_buffer_factor(self):
        """Test divisors_for_max_volume with custom buffer factor."""
        pred = MagicMock(spec=PredictionData)
        pred.symbol = "AAPL"
        pred.last_close_price = 100.0
        
        predictions = [pred]
        budget_list = [5000.0]
        
        mock_base = MagicMock(spec=mtBase)
        
        symbol_info = {
            "volume_max": 10.0,
            "trade_contract_size": 100.0
        }
        
        mock_base.get_symbol_info.return_value = symbol_info
        mock_base.get_symbol_price.return_value = None
        
        # Test with custom buffer factor
        result = divisors_for_max_volume(predictions, budget_list, mock_base, buffer_factor=1.5)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], int)
        assert result[0] >= 1
    
    def test_divisors_for_max_volume_empty_inputs(self):
        """Test divisors_for_max_volume with empty inputs."""
        predictions = []
        budget_list = []
        mock_base = MagicMock(spec=mtBase)
        
        result = divisors_for_max_volume(predictions, budget_list, mock_base)
        
        assert result == []