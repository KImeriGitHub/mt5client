"""Unit tests for common.py functions."""

import pytest
from datetime import date, datetime
from unittest.mock import patch, MagicMock
import pandas as pd
import pandas_market_calendars as mcal

from src.common import magic_from, calculate_trading_day
from src.infra.PredictionData import PredictionData


class TestMagicFrom:
    """Test cases for magic_from function."""
    
    def test_magic_from_basic(self):
        """Test basic magic generation."""
        # Create a mock prediction data
        prediction = MagicMock()
        prediction.symbol = "EURUSD"
        prediction.last_training_day = date(2025, 10, 14)
        prediction.n_trading_days = 5
        
        magic = magic_from(prediction)
        
        # Magic should be a positive integer
        assert isinstance(magic, int)
        assert magic > 0
        assert magic <= 0x7FFFFFFFFFFFFFFF  # 63-bit signed max
    
    def test_magic_from_consistency(self):
        """Test that same input produces same magic."""
        prediction1 = MagicMock()
        prediction1.symbol = "GBPJPY"
        prediction1.last_training_day = date(2025, 10, 15)
        prediction1.n_trading_days = 3
        
        prediction2 = MagicMock()
        prediction2.symbol = "GBPJPY"
        prediction2.last_training_day = date(2025, 10, 15)
        prediction2.n_trading_days = 3
        
        magic1 = magic_from(prediction1)
        magic2 = magic_from(prediction2)
        
        assert magic1 == magic2
    
    def test_magic_from_different_inputs(self):
        """Test that different inputs produce different magics."""
        prediction1 = MagicMock()
        prediction1.symbol = "EURUSD"
        prediction1.last_training_day = date(2025, 10, 14)
        prediction1.n_trading_days = 5
        
        prediction2 = MagicMock()
        prediction2.symbol = "GBPJPY"
        prediction2.last_training_day = date(2025, 10, 14)
        prediction2.n_trading_days = 5
        
        prediction3 = MagicMock()
        prediction3.symbol = "EURUSD"
        prediction3.last_training_day = date(2025, 10, 15)
        prediction3.n_trading_days = 5
        
        prediction4 = MagicMock()
        prediction4.symbol = "EURUSD"
        prediction4.last_training_day = date(2025, 10, 14)
        prediction4.n_trading_days = 3
        
        magic1 = magic_from(prediction1)
        magic2 = magic_from(prediction2)
        magic3 = magic_from(prediction3)
        magic4 = magic_from(prediction4)
        
        # All should be different
        assert len({magic1, magic2, magic3, magic4}) == 4
    
    def test_magic_from_case_insensitive_symbol(self):
        """Test that symbol case doesn't affect magic generation."""
        prediction1 = MagicMock()
        prediction1.symbol = "eurusd"
        prediction1.last_training_day = date(2025, 10, 14)
        prediction1.n_trading_days = 5
        
        prediction2 = MagicMock()
        prediction2.symbol = "EURUSD"
        prediction2.last_training_day = date(2025, 10, 14)
        prediction2.n_trading_days = 5
        
        magic1 = magic_from(prediction1)
        magic2 = magic_from(prediction2)
        
        assert magic1 == magic2


class TestCalculateTradingDay:
    """Test cases for calculate_trading_day function."""
    
    def test_calculate_trading_day_zero_days(self):
        """Test that zero days returns the input date."""
        input_date = date(2025, 10, 14)
        result = calculate_trading_day(input_date, 0)
        assert result == input_date
    
    def test_calculate_trading_day_invalid_input_date(self):
        """Test error handling for invalid input date."""
        with pytest.raises(ValueError, match="input_date must be a datetime.date"):
            calculate_trading_day("2025-10-14", 5)
    
    def test_calculate_trading_day_negative_days(self):
        """Test error handling for negative days."""
        input_date = date(2025, 10, 14)
        with pytest.raises(ValueError, match="n_days must be a non-negative integer"):
            calculate_trading_day(input_date, -1)
    
    @patch('pandas_market_calendars.get_calendar')
    def test_calculate_trading_day_basic(self, mock_get_calendar):
        """Test basic trading day calculation."""
        # Mock calendar
        mock_calendar = MagicMock()
        mock_get_calendar.return_value = mock_calendar
        
        # Create mock trading days
        input_date = date(2025, 10, 14)  # Monday
        input_dt = datetime.combine(input_date, datetime.min.time()).replace(tzinfo=None)
        
        # Mock trading days (Monday to Friday for that week)
        trading_days = pd.DatetimeIndex([
            datetime(2025, 10, 13),  # Sunday (not trading)
            datetime(2025, 10, 14),  # Monday
            datetime(2025, 10, 15),  # Tuesday  
            datetime(2025, 10, 16),  # Wednesday
            datetime(2025, 10, 17),  # Thursday
            datetime(2025, 10, 18),  # Friday
            datetime(2025, 10, 20),  # Next Monday
            datetime(2025, 10, 21),  # Next Tuesday
        ])
        
        mock_calendar.valid_days.return_value = trading_days
        
        # Test calculation
        result = calculate_trading_day(input_date, 3)
        
        # Should be 3 trading days after Monday (Thursday)
        expected = date(2025, 10, 17)
        assert result == expected
    
    @patch('pandas_market_calendars.get_calendar')
    def test_calculate_trading_day_weekend_input(self, mock_get_calendar):
        """Test trading day calculation with weekend input date."""
        # Mock calendar
        mock_calendar = MagicMock()
        mock_get_calendar.return_value = mock_calendar
        
        # Create mock trading days
        input_date = date(2025, 10, 12)  # Sunday (non-trading day)
        
        # Mock trading days
        trading_days = pd.DatetimeIndex([
            datetime(2025, 10, 10),  # Friday
            datetime(2025, 10, 13),  # Monday
            datetime(2025, 10, 14),  # Tuesday  
            datetime(2025, 10, 15),  # Wednesday
            datetime(2025, 10, 16),  # Thursday
            datetime(2025, 10, 17),  # Friday
        ])
        
        mock_calendar.valid_days.return_value = trading_days
        
        # Test calculation - should use Friday (last trading day before Sunday)
        result = calculate_trading_day(input_date, 2)
        
        # 2 trading days from Friday should be Tuesday
        expected = date(2025, 10, 14)
        assert result == expected
    
    @patch('pandas_market_calendars.get_calendar')
    def test_calculate_trading_day_different_market(self, mock_get_calendar):
        """Test trading day calculation with different market."""
        # Mock calendar
        mock_calendar = MagicMock()
        mock_get_calendar.return_value = mock_calendar
        
        input_date = date(2025, 10, 14)
        trading_days = pd.DatetimeIndex([
            datetime(2025, 10, 14),
            datetime(2025, 10, 15),
            datetime(2025, 10, 16),
        ])
        
        mock_calendar.valid_days.return_value = trading_days
        
        result = calculate_trading_day(input_date, 1, market='LSE')
        
        # Verify the correct market was requested
        mock_get_calendar.assert_called_once_with('LSE')
        
        expected = date(2025, 10, 15)
        assert result == expected
    
    @patch('pandas_market_calendars.get_calendar')
    def test_calculate_trading_day_edge_case_single_day(self, mock_get_calendar):
        """Test edge case with single trading day available."""
        # Mock calendar
        mock_calendar = MagicMock()
        mock_get_calendar.return_value = mock_calendar
        
        input_date = date(2025, 10, 14)
        trading_days = pd.DatetimeIndex([
            datetime(2025, 10, 14),
            datetime(2025, 10, 15),
        ])
        
        mock_calendar.valid_days.return_value = trading_days
        
        result = calculate_trading_day(input_date, 1)
        expected = date(2025, 10, 15)
        assert result == expected