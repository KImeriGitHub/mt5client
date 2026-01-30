"""Unit tests for check_closing_price_conditions module."""

import numpy as np
import pandas as pd
from unittest.mock import Mock

from src.check_closing_price_conditions import (
    evaluate_closing_condition,
    check_closing_time_window,
    calculate_lookback,
    check_closing_price_condition,
)


class TestEvaluateClosingCondition:
    """Tests for evaluate_closing_condition function."""
    
    def test_too_few_data_points(self):
        """Test error handling when inputs have too few points."""
        bid_prices = np.array([1.0, 2.0, 3.0])  # Less than 5
        df = pd.DataFrame({
            'time': pd.date_range('2026-01-30 12:54:00', periods=3, freq='1s', tz='UTC')
        })
        
        status, msg = evaluate_closing_condition(bid_prices, df, "TEST")
        
        assert status == 1
        assert "too few data points" in msg.lower()
    
    def test_price_declining_cut_losses(self):
        """Test that declining prices (ret < 0.995) trigger position closure."""
        # Create declining price series (1.5% drop)
        base_price = 100.0
        n_points = 60
        bid_prices = np.linspace(base_price, base_price * 0.985, n_points)
        
        df = pd.DataFrame({
            'time': pd.date_range('2026-01-30 12:54:00', periods=n_points, freq='1s', tz='UTC')
        })
        
        status, msg = evaluate_closing_condition(bid_prices, df, "MU")
        
        assert status == 0  # Should close position
        assert "-CLOSE-" in msg
        assert "Cut losses" in msg
    
    def test_price_increasing_keep_open(self):
        """Test that rising prices (ret > 1.005) keep position open."""
        # Create rising price series (1.2% gain)
        base_price = 100.0
        n_points = 60
        bid_prices = np.linspace(base_price, base_price * 1.012, n_points)
        
        df = pd.DataFrame({
            'time': pd.date_range('2026-01-30 12:54:00', periods=n_points, freq='1s', tz='UTC')
        })
        
        status, msg = evaluate_closing_condition(bid_prices, df, "MU")
        
        assert status == 1  # Should keep position open
        assert "-KEEP OPEN-" in msg
        assert "Price rising" in msg
    
    def test_price_stable_high_residual(self):
        """Test stable price with high residual triggers closure."""
        # Create stable price with an upward spike at the end
        base_price = 100.0
        n_points = 120
        bid_prices = np.full(n_points, base_price)
        bid_prices = bid_prices + np.random.normal(0, 0.01, n_points)
        bid_prices[-1] = base_price + 0.15  # Add spike
        
        df = pd.DataFrame({
            'time': pd.date_range('2026-01-30 12:54:00', periods=n_points, freq='1s', tz='UTC')
        })
        
        status, msg = evaluate_closing_condition(bid_prices, df, "MU")
        
        assert status == 0  # Should close due to high residual
        assert "-CLOSE-" in msg
        assert "High residual" in msg


class TestCheckClosingTimeWindow:
    """Tests for check_closing_time_window function."""
    
    def test_end_of_windows_trigger_closure(self):
        """Test that minutes 27-29 and 57-59 trigger immediate closure."""
        for minute in [27, 28, 29, 57, 58, 59]:
            curtime = pd.Timestamp(f'2026-01-30 12:{minute}:30', tz='UTC')
            result = check_closing_time_window(curtime, "TEST")
            
            assert result is not None
            status, msg = result
            assert status == 0  # Close immediately
            assert "end of time window" in msg.lower()
    
    def test_valid_processing_windows(self):
        """Test that valid processing windows return None (continue)."""
        for minute in [3, 10, 15, 20, 26, 33, 40, 45, 50, 54, 56]:
            curtime = pd.Timestamp(f'2026-01-30 12:{minute}:30', tz='UTC')
            result = check_closing_time_window(curtime, "TEST")
            
            assert result is None  # Continue with normal processing


class TestCalculateLookback:
    """Tests for calculate_lookback function."""
    
    def test_lookback_calculations(self):
        """Test lookback calculation for various minute values."""
        curtime = pd.Timestamp('2026-01-30 12:54:00', tz='UTC')
        
        seconds_back, from_time = calculate_lookback(curtime, 10)
        assert seconds_back == 600
        assert from_time == pd.Timestamp('2026-01-30 12:44:00', tz='UTC')


class TestCheckClosingPriceCondition:
    """Tests for check_closing_price_condition function (integration with mocks)."""
    
    def create_mock_tick_data(self, n_points=600, base_price=100.0, trend=0.0):
        """Helper to create realistic mock tick data starting at :54.
        
        Returns list of dicts that can be converted to DataFrame, 
        mimicking MT5 copy_ticks_range behavior.
        """
        np.random.seed(42)
        
        # Generate timestamps starting at :54
        timestamps = pd.date_range('2026-01-30 12:54:00', periods=n_points, freq='1s', tz='UTC')
        
        # Generate prices with trend and noise
        time_seconds = np.arange(n_points)
        prices = base_price * (1 + trend * time_seconds / n_points) + np.random.normal(0, 0.01, n_points)
        
        # Return list of dicts similar to MT5 tick data format
        ticks = []
        for i, ts in enumerate(timestamps):
            tick = {
                'time': int(ts.timestamp()),
                'bid': float(prices[i]),
                'ask': float(prices[i] + 0.01),
                'last': float(prices[i]),
                'volume': 100,
                'flags': 6,
                'time_msc': int(ts.timestamp() * 1000)
            }
            ticks.append(tick)
        
        return ticks
    
    def test_declining_price_closes_position(self):
        """Test declining price pattern triggers closure."""
        mock_base = Mock()
        curtime = pd.Timestamp('2026-01-30 12:54:00', tz='UTC')
        mock_base.get_symbol_info.return_value = {'time': int(curtime.timestamp())}
        mock_base.copy_ticks_range.return_value = self.create_mock_tick_data(
            n_points=600, base_price=100.0, trend=-0.02
        )
        
        status, msg = check_closing_price_condition("MU", mock_base, lookback_minutes=10)
        
        assert status == 0  # Should close
        assert "-CLOSE-" in msg
        mock_base.get_symbol_info.assert_called_once_with("MU")
    
    def test_rising_price_keeps_open(self):
        """Test rising price pattern keeps position open."""
        mock_base = Mock()
        curtime = pd.Timestamp('2026-01-30 12:54:00', tz='UTC')
        mock_base.get_symbol_info.return_value = {'time': int(curtime.timestamp())}
        mock_base.copy_ticks_range.return_value = self.create_mock_tick_data(
            n_points=600, base_price=100.0, trend=0.015
        )
        
        status, msg = check_closing_price_condition("MU", mock_base, lookback_minutes=10)
        
        assert status == 1  # Should keep open
        assert "-KEEP OPEN-" in msg
    
    def test_end_of_window_immediate_close(self):
        """Test end of window (minute 58) triggers immediate closure."""
        mock_base = Mock()
        curtime = pd.Timestamp('2026-01-30 12:58:00', tz='UTC')
        mock_base.get_symbol_info.return_value = {'time': int(curtime.timestamp())}
        
        status, msg = check_closing_price_condition("MU", mock_base, lookback_minutes=10)
        
        assert status == 0  # Should close immediately
        assert "end of time window" in msg.lower()
        mock_base.copy_ticks_range.assert_not_called()  # Should shortcut
    
    def test_no_symbol_info_error(self):
        """Test error handling when symbol info is unavailable."""
        mock_base = Mock()
        mock_base.get_symbol_info.return_value = None
        
        status, msg = check_closing_price_condition("INVALID", mock_base, lookback_minutes=10)
        
        assert status == 1
        assert "unable to get symbol info" in msg.lower()
    
    def test_no_tick_data_error(self):
        """Test error handling when tick data is unavailable."""
        mock_base = Mock()
        curtime = pd.Timestamp('2026-01-30 12:54:00', tz='UTC')
        mock_base.get_symbol_info.return_value = {'time': int(curtime.timestamp())}
        mock_base.copy_ticks_range.return_value = None
        
        status, msg = check_closing_price_condition("MU", mock_base, lookback_minutes=10)
        
        assert status == 1
        assert "no tick data available" in msg.lower()
