"""Unit tests for prediction_to_orders.py module."""

import pytest
from unittest.mock import MagicMock, patch
import MetaTrader5 as mt5
import math

from src.prediction_to_orders import (
    _compute_sl_tp,
    _check_stops_level,
    _choose_filling,
    _volume_from_budget,
    _calc_vol,
    prediction_to_orders
)
from src.infra.PredictionData import PredictionData
from src.infra.OrderData import OrderData
from src.infra.mtBase import mtBase


class TestComputeSlTp:
    """Test cases for _compute_sl_tp function."""
    
    def test_compute_sl_tp_with_both_percentages(self):
        """Test _compute_sl_tp with both stop loss and take profit percentages."""
        price = 100.0
        sl_pct = 0.02  # 2%
        tp_pct = 0.03  # 3%
        digits = 2
        
        sl, tp = _compute_sl_tp(price, sl_pct, tp_pct, digits)
        
        # For buy position: SL = price * (1 - sl_pct), TP = price * (1 + tp_pct)
        expected_sl = round(price * (1 - sl_pct), digits)  # 98.00
        expected_tp = round(price * (1 + tp_pct), digits)  # 103.00
        
        assert sl == expected_sl
        assert tp == expected_tp
    
    def test_compute_sl_tp_with_no_percentages(self):
        """Test _compute_sl_tp with no stop loss or take profit percentages."""
        price = 150.0
        sl_pct = None
        tp_pct = None
        digits = 4
        
        sl, tp = _compute_sl_tp(price, sl_pct, tp_pct, digits)
        
        assert sl is None
        assert tp is None
    
    def test_compute_sl_tp_with_zero_percentages(self):
        """Test _compute_sl_tp with zero percentages."""
        price = 200.0
        sl_pct = 0.0
        tp_pct = 0.0
        digits = 3
        
        sl, tp = _compute_sl_tp(price, sl_pct, tp_pct, digits)
        
        assert sl is None
        assert tp is None
    
    def test_compute_sl_tp_only_stop_loss(self):
        """Test _compute_sl_tp with only stop loss percentage."""
        price = 75.5
        sl_pct = 0.015  # 1.5%
        tp_pct = None
        digits = 3
        
        sl, tp = _compute_sl_tp(price, sl_pct, tp_pct, digits)
        
        expected_sl = round(price * (1 - sl_pct), digits)
        assert sl == expected_sl
        assert tp is None
    
    def test_compute_sl_tp_only_take_profit(self):
        """Test _compute_sl_tp with only take profit percentage."""
        price = 50.25
        sl_pct = None
        tp_pct = 0.025  # 2.5%
        digits = 2
        
        sl, tp = _compute_sl_tp(price, sl_pct, tp_pct, digits)
        
        expected_tp = round(price * (1 + tp_pct), digits)
        assert sl is None
        assert tp == expected_tp
    
    def test_compute_sl_tp_rounding_precision(self):
        """Test _compute_sl_tp with different digit precision."""
        price = 123.456789
        sl_pct = 0.01
        tp_pct = 0.02
        
        # Test with 2 digits
        sl_2, tp_2 = _compute_sl_tp(price, sl_pct, tp_pct, 2)
        assert sl_2 == round(123.456789 * 0.99, 2)
        assert tp_2 == round(123.456789 * 1.02, 2)
        
        # Test with 5 digits
        sl_5, tp_5 = _compute_sl_tp(price, sl_pct, tp_pct, 5)
        assert sl_5 == round(123.456789 * 0.99, 5)
        assert tp_5 == round(123.456789 * 1.02, 5)
    
    def test_compute_sl_tp_negative_percentages(self):
        """Test _compute_sl_tp with negative percentages (should return None)."""
        price = 100.0
        sl_pct = -0.01  # Negative percentage
        tp_pct = -0.02  # Negative percentage
        digits = 2
        
        sl, tp = _compute_sl_tp(price, sl_pct, tp_pct, digits)
        
        # Negative percentages should result in None
        assert sl is None
        assert tp is None
    
    def test_compute_sl_tp_very_small_percentages(self):
        """Test _compute_sl_tp with very small percentages."""
        price = 1000.0
        sl_pct = 0.0001  # 0.01%
        tp_pct = 0.0002  # 0.02%
        digits = 6
        
        sl, tp = _compute_sl_tp(price, sl_pct, tp_pct, digits)
        
        expected_sl = round(1000.0 * (1 - 0.0001), 6)
        expected_tp = round(1000.0 * (1 + 0.0002), 6)
        
        assert sl == expected_sl
        assert tp == expected_tp
    
    def test_compute_sl_tp_extreme_digits(self):
        """Test _compute_sl_tp with extreme digit precision."""
        price = 1.23456789
        sl_pct = 0.1
        tp_pct = 0.1
        
        # Test with 0 digits (integer rounding)
        sl_0, tp_0 = _compute_sl_tp(price, sl_pct, tp_pct, 0)
        assert sl_0 == round(1.23456789 * 0.9, 0)
        assert tp_0 == round(1.23456789 * 1.1, 0)
        
        # Test with 10 digits (high precision)
        sl_10, tp_10 = _compute_sl_tp(price, sl_pct, tp_pct, 10)
        assert sl_10 == round(1.23456789 * 0.9, 10)
        assert tp_10 == round(1.23456789 * 1.1, 10)


class TestCheckStopsLevel:
    """Test cases for _check_stops_level function."""
    
    def test_check_stops_level_valid_levels(self):
        """Test _check_stops_level with valid stop levels."""
        price = 100.0
        sl = 95.0  # 5 points away
        tp = 105.0  # 5 points away
        stops_level_pts = 3
        point = 1.0
        
        is_valid, sl_adj, tp_adj = _check_stops_level(price, sl, tp, stops_level_pts, point)
        
        assert is_valid is True
        assert sl_adj is None
        assert tp_adj is None
    
    def test_check_stops_level_invalid_sl(self):
        """Test _check_stops_level with invalid stop loss level."""
        price = 100.0
        sl = 98.0  # Only 2 points away, but need 3
        tp = 105.0  # Valid
        stops_level_pts = 3
        point = 1.0
        
        is_valid, sl_adj, tp_adj = _check_stops_level(price, sl, tp, stops_level_pts, point)
        
        assert is_valid is False
        # Should adjust SL to price - (stops_level + buffer) * point
        expected_sl_adj = price - (stops_level_pts + 1) * point  # 96.0
        assert sl_adj == expected_sl_adj
        assert tp_adj is None
    
    def test_check_stops_level_invalid_tp(self):
        """Test _check_stops_level with invalid take profit level."""
        price = 100.0
        sl = 95.0  # Valid
        tp = 102.0  # Only 2 points away, but need 3
        stops_level_pts = 3
        point = 1.0
        
        is_valid, sl_adj, tp_adj = _check_stops_level(price, sl, tp, stops_level_pts, point)
        
        assert is_valid is False
        assert sl_adj is None
        # Should adjust TP to price + (stops_level + buffer) * point
        expected_tp_adj = price + (stops_level_pts + 1) * point  # 104.0
        assert tp_adj == expected_tp_adj
    
    def test_check_stops_level_both_invalid(self):
        """Test _check_stops_level with both stop loss and take profit invalid."""
        price = 100.0
        sl = 99.0  # Only 1 point away
        tp = 101.0  # Only 1 point away
        stops_level_pts = 3
        point = 1.0
        
        is_valid, sl_adj, tp_adj = _check_stops_level(price, sl, tp, stops_level_pts, point)
        
        assert is_valid is False
        expected_sl_adj = price - (stops_level_pts + 1) * point  # 96.0
        expected_tp_adj = price + (stops_level_pts + 1) * point  # 104.0
        assert sl_adj == expected_sl_adj
        assert tp_adj == expected_tp_adj
    
    def test_check_stops_level_none_values(self):
        """Test _check_stops_level with None stop levels."""
        price = 100.0
        sl = None
        tp = None
        stops_level_pts = 3
        point = 1.0
        
        is_valid, sl_adj, tp_adj = _check_stops_level(price, sl, tp, stops_level_pts, point)
        
        assert is_valid is True
        assert sl_adj is None
        assert tp_adj is None
    
    def test_check_stops_level_zero_stops_level(self):
        """Test _check_stops_level with zero stops level."""
        price = 100.0
        sl = 99.0
        tp = 101.0
        stops_level_pts = 0  # No minimum distance required
        point = 1.0
        
        is_valid, sl_adj, tp_adj = _check_stops_level(price, sl, tp, stops_level_pts, point)
        
        # Should be valid since no minimum distance is required
        assert is_valid is True
        assert sl_adj is None
        assert tp_adj is None
    
    def test_check_stops_level_exact_distance(self):
        """Test _check_stops_level when levels are exactly at minimum distance."""
        price = 100.0
        sl = 97.0  # Exactly 3 points away
        tp = 103.0  # Exactly 3 points away
        stops_level_pts = 3
        point = 1.0
        
        is_valid, sl_adj, tp_adj = _check_stops_level(price, sl, tp, stops_level_pts, point)
        
        # Should be invalid because distance equals (not greater than) minimum
        assert is_valid is False
        expected_sl_adj = price - (stops_level_pts + 1) * point  # 96.0
        expected_tp_adj = price + (stops_level_pts + 1) * point  # 104.0
        assert sl_adj == expected_sl_adj
        assert tp_adj == expected_tp_adj
    
    def test_check_stops_level_very_small_point(self):
        """Test _check_stops_level with very small point value (forex)."""
        price = 1.2345
        sl = 1.2340  # 5 pips away
        tp = 1.2350  # 5 pips away
        stops_level_pts = 10  # Need 10 pips minimum
        point = 0.0001  # 1 pip = 0.0001
        
        is_valid, sl_adj, tp_adj = _check_stops_level(price, sl, tp, stops_level_pts, point)
        
        # Distance is 0.0005 (5 pips), need 0.0010 (10 pips)
        assert is_valid is False
        expected_sl_adj = price - (stops_level_pts + 1) * point  # 1.2345 - 0.0011 = 1.2334
        expected_tp_adj = price + (stops_level_pts + 1) * point  # 1.2345 + 0.0011 = 1.2356
        assert sl_adj == expected_sl_adj
        assert tp_adj == expected_tp_adj
    
    def test_check_stops_level_negative_distances(self):
        """Test _check_stops_level with SL/TP on wrong side of price."""
        price = 100.0
        sl = 105.0  # SL above price (wrong for buy order)
        tp = 95.0   # TP below price (wrong for buy order)
        stops_level_pts = 5
        point = 1.0
        
        is_valid, sl_adj, tp_adj = _check_stops_level(price, sl, tp, stops_level_pts, point)
        
        # abs() is used, so even wrong-side levels are checked
        assert is_valid is False
        expected_sl_adj = price - (stops_level_pts + 1) * point  # 94.0
        expected_tp_adj = price + (stops_level_pts + 1) * point  # 106.0
        assert sl_adj == expected_sl_adj
        assert tp_adj == expected_tp_adj
    
    def test_check_stops_level_different_point_values(self):
        """Test _check_stops_level with different point values."""
        price = 1.2345
        sl = 1.2340
        tp = 1.2350
        stops_level_pts = 10
        point = 0.0001  # Common for forex
        
        is_valid, sl_adj, tp_adj = _check_stops_level(price, sl, tp, stops_level_pts, point)
        
        # Distance is 0.0005 (5 points), but need 10 points (0.0010)
        assert is_valid is False
        expected_sl_adj = price - (stops_level_pts + 1) * point
        expected_tp_adj = price + (stops_level_pts + 1) * point
        assert sl_adj == expected_sl_adj
        assert tp_adj == expected_tp_adj


class TestChooseFilling:
    """Test cases for _choose_filling function."""
    
    def test_choose_filling_exotic_category(self):
        """Test _choose_filling with exotic symbol category."""
        info = {
            "category": "Exotic",
            "filling_mode": mt5.ORDER_FILLING_IOC
        }
        
        result = _choose_filling(info)
        
        assert result == mt5.ORDER_FILLING_FOK
    
    def test_choose_filling_fok_mode(self):
        """Test _choose_filling with FOK filling mode."""
        info = {
            "category": "Major",
            "filling_mode": mt5.ORDER_FILLING_FOK
        }
        
        result = _choose_filling(info)
        
        assert result == mt5.ORDER_FILLING_FOK
    
    def test_choose_filling_unknown_mode(self):
        """Test _choose_filling with unknown filling mode."""
        info = {
            "category": "Minor",
            "filling_mode": mt5.ORDER_FILLING_IOC  # Not FOK
        }
        
        result = _choose_filling(info)
        
        assert result == mt5.ORDER_FILLING_FOK  # Defaults to FOK
    
    def test_choose_filling_return_mode(self):
        """Test _choose_filling with RETURN filling mode."""
        info = {
            "category": "Major",
            "filling_mode": mt5.ORDER_FILLING_RETURN
        }
        
        result = _choose_filling(info)
        
        assert result == mt5.ORDER_FILLING_FOK  # Defaults to FOK
    
    @patch('src.prediction_to_orders.logger')
    def test_choose_filling_logging_exotic(self, mock_logger):
        """Test _choose_filling logs warning for exotic symbols."""
        info = {
            "category": "Exotic",
            "filling_mode": mt5.ORDER_FILLING_IOC
        }
        
        _choose_filling(info)
        
        mock_logger.warning.assert_called_with("Warning: Exotic symbol: using FOK filling mode.")
    
    @patch('src.prediction_to_orders.logger')
    def test_choose_filling_logging_unknown(self, mock_logger):
        """Test _choose_filling logs warning for unknown filling modes."""
        info = {
            "category": "Major",
            "filling_mode": mt5.ORDER_FILLING_IOC
        }
        
        _choose_filling(info)
        
        mock_logger.info.assert_called_with("Standard Filling mode is not FOK: using ORDER_FILLING_FOK.")


class TestVolumeFromBudget:
    """Test cases for _volume_from_budget function."""
    
    def test_volume_from_budget_basic_case(self):
        """Test _volume_from_budget with matching currencies."""
        budget = 10000.0
        price = 100.0
        info = {
            "trade_contract_size": 100.0,
            "currency_base": "USD"
        }
        
        # Create mock base and account info
        mock_base = MagicMock()
        mock_account_info = MagicMock()
        mock_account_info.currency = "USD"
        mock_base.get_account_info.return_value = mock_account_info
        
        result = _volume_from_budget(budget, price, info, mock_base)
        
        # Expected: budget / (price * contract_size * conversion_rate)
        # 10000 / (100 * 100 * 1.0) = 1.0
        expected = 10000.0 / (100.0 * 100.0 * 1.0)
        assert result == expected
    
    def test_volume_from_budget_different_currencies(self):
        """Test _volume_from_budget with different account and base currencies."""
        budget = 5000.0
        price = 1.2345
        info = {
            "trade_contract_size": 100000.0,
            "currency_base": "EUR"
        }
        
        # Create mock base and account info
        mock_base = MagicMock()
        mock_account_info = MagicMock()
        mock_account_info.currency = "USD"  # Different from symbol base currency
        mock_base.get_account_info.return_value = mock_account_info
        
        # Should raise NotImplementedError for currency conversion
        with pytest.raises(NotImplementedError, match="Currency conversion not implemented yet."):
            _volume_from_budget(budget, price, info, mock_base)
    
    def test_volume_from_budget_none_account_currency(self):
        """Test _volume_from_budget with None account currency."""
        budget = 1000.0
        price = 50.0
        info = {
            "trade_contract_size": 1.0,
            "currency_base": "USD"
        }
        
        # Create mock base and account info
        mock_base = MagicMock()
        mock_account_info = MagicMock()
        mock_account_info.currency = None
        mock_base.get_account_info.return_value = mock_account_info
        
        # Should raise NotImplementedError when account currency is None
        with pytest.raises(NotImplementedError, match="Currency conversion not implemented yet."):
            _volume_from_budget(budget, price, info, mock_base)
    
    @patch('src.prediction_to_orders.logger')
    def test_volume_from_budget_currency_warning(self, mock_logger):
        """Test _volume_from_budget logs warning for currency mismatch."""
        budget = 2000.0
        price = 25.0
        info = {
            "trade_contract_size": 10.0,
            "currency_base": "GBP"
        }
        
        # Create mock base and account info
        mock_base = MagicMock()
        mock_account_info = MagicMock()
        mock_account_info.currency = "USD"
        mock_base.get_account_info.return_value = mock_account_info
        
        with pytest.raises(NotImplementedError):
            _volume_from_budget(budget, price, info, mock_base)
        
        expected_warning = "Warning: account currency (USD) differs from symbol base currency (GBP)."
        mock_logger.warning.assert_called_with(expected_warning)
    
    def test_volume_from_budget_zero_values(self):
        """Test _volume_from_budget with edge case values."""
        budget = 0.0
        price = 100.0
        info = {
            "trade_contract_size": 100.0,
            "currency_base": "USD"
        }
        
        # Create mock base and account info
        mock_base = MagicMock()
        mock_account_info = MagicMock()
        mock_account_info.currency = "USD"
        mock_base.get_account_info.return_value = mock_account_info
        
        result = _volume_from_budget(budget, price, info, mock_base)
        
        assert result == 0.0
    
    def test_volume_from_budget_large_values(self):
        """Test _volume_from_budget with large budget and small price."""
        budget = 1000000.0
        price = 0.01
        info = {
            "trade_contract_size": 1000.0,
            "currency_base": "USD"
        }
        
        # Create mock base and account info
        mock_base = MagicMock()
        mock_account_info = MagicMock()
        mock_account_info.currency = "USD"
        mock_base.get_account_info.return_value = mock_account_info
        
        result = _volume_from_budget(budget, price, info, mock_base)
        
        expected = 1000000.0 / (0.01 * 1000.0 * 1.0)
        assert result == expected


class TestCalcVol:
    """Test cases for _calc_vol function."""
    
    def test_calc_vol_even_division(self):
        """Test _calc_vol with volume that divides evenly."""
        vol = 4.0
        info = {"volume_step": 0.5}
        div = 2
        
        result = _calc_vol(vol, info, div)
        
        # 4.0 / 0.5 = 8 units
        # 8 units / 2 = 4 units each
        # 4 units * 0.5 = 2.0 volume each
        expected = [2.0, 2.0]
        assert result == expected
        assert sum(result) <= vol
    
    def test_calc_vol_uneven_division(self):
        """Test _calc_vol with volume that doesn't divide evenly."""
        vol = 3.0
        info = {"volume_step": 0.4}
        div = 3
        
        result = _calc_vol(vol, info, div)
        
        # 3.0 / 0.4 = 7.5 -> floor = 7 units
        # 7 units / 3 = 2 units base, 1 remainder
        # Base: [2 * 0.4, 2 * 0.4, 2 * 0.4] = [0.8, 0.8, 0.8]
        # Add remainder to first part: [0.8 + 0.4, 0.8, 0.8] = [1.2, 0.8, 0.8]
        expected = [1.2, 0.8, 0.8]
        assert result == pytest.approx(expected, rel=1e-9)
        assert abs(sum(result) - 2.8) < 1e-10  # Should be close to 7 * 0.4 = 2.8
    
    def test_calc_vol_single_division(self):
        """Test _calc_vol with division by 1."""
        vol = 5.5
        info = {"volume_step": 0.1}
        div = 1
        
        result = _calc_vol(vol, info, div)
        
        # 5.5 / 0.1 = 55 units
        # 55 units / 1 = 55 units
        # 55 units * 0.1 = 5.5
        expected = [5.5]
        assert result == pytest.approx(expected, rel=1e-9)
    
    def test_calc_vol_large_divisor(self):
        """Test _calc_vol with divisor larger than available units."""
        vol = 1.0
        info = {"volume_step": 0.5}
        div = 5
        
        result = _calc_vol(vol, info, div)
        
        # 1.0 / 0.5 = 2 units
        # 2 units / 5 = 0 base, 2 remainder
        # Base: [0, 0, 0, 0, 0]
        # Add remainder to first 2: [0.5, 0.5, 0, 0, 0]
        expected = [0.5, 0.5, 0.0, 0.0, 0.0]
        assert result == pytest.approx(expected, rel=1e-9)
        assert len(result) == div
    
    def test_calc_vol_zero_volume(self):
        """Test _calc_vol with zero volume."""
        vol = 0.0
        info = {"volume_step": 0.1}
        div = 3
        
        result = _calc_vol(vol, info, div)
        
        # 0.0 / 0.1 = 0 units
        # All parts should be 0
        expected = [0.0, 0.0, 0.0]
        assert result == expected
    
    def test_calc_vol_invalid_volume_step_none(self):
        """Test _calc_vol with None volume step."""
        vol = 2.0
        info = {"volume_step": None}
        div = 2
        
        with pytest.raises(RuntimeError, match="Invalid volume_step in symbol info."):
            _calc_vol(vol, info, div)
    
    def test_calc_vol_invalid_volume_step_zero(self):
        """Test _calc_vol with zero volume step."""
        vol = 2.0
        info = {"volume_step": 0.0}
        div = 2
        
        with pytest.raises(RuntimeError, match="Invalid volume_step in symbol info."):
            _calc_vol(vol, info, div)
    
    def test_calc_vol_invalid_volume_step_too_small(self):
        """Test _calc_vol with very small volume step."""
        vol = 2.0
        info = {"volume_step": 1e-9}  # Smaller than 1e-8 threshold
        div = 2
        
        with pytest.raises(RuntimeError, match="Invalid volume_step in symbol info."):
            _calc_vol(vol, info, div)
    
    def test_calc_vol_precision_handling(self):
        """Test _calc_vol handles floating point precision correctly."""
        vol = 1.3
        info = {"volume_step": 0.1}
        div = 4
        
        result = _calc_vol(vol, info, div)
        
        # 1.3 / 0.1 = 13 units
        # 13 units / 4 = 3 base, 1 remainder
        # Base: [0.3, 0.3, 0.3, 0.3]
        # Add remainder: [0.4, 0.3, 0.3, 0.3]
        expected = [0.4, 0.3, 0.3, 0.3]
        assert len(result) == 4
        # Use pytest.approx for floating point comparison
        assert result == pytest.approx(expected, rel=1e-9)
    
    def test_calc_vol_step_larger_than_volume(self):
        """Test _calc_vol when volume step is larger than total volume."""
        vol = 0.05
        info = {"volume_step": 0.1}
        div = 2
        
        result = _calc_vol(vol, info, div)
        
        # 0.05 / 0.1 = 0.5 -> floor = 0 units
        # 0 units distributed = all zeros
        expected = [0.0, 0.0]
        assert result == expected


class TestPredictionToOrders:
    """Test cases for prediction_to_orders function."""
    
    @patch('src.prediction_to_orders._calc_vol')
    @patch('src.prediction_to_orders._volume_from_budget')
    def test_prediction_to_orders_basic_case(self, mock_volume_from_budget, mock_calc_vol):
        """Test prediction_to_orders with basic inputs."""
        # Create mock prediction
        mock_pred = MagicMock(spec=PredictionData)
        mock_pred.symbol = "AAPL"
        mock_pred.sl_pct = 0.02
        mock_pred.tp_pct = 0.03
        mock_pred.magic = 12345
        
        budget = 10000.0
        vol_divisor = 2
        
        # Create mock base
        mock_base = MagicMock(spec=mtBase)
        
        # Mock price tick
        mock_price_tick = {"bid": 149.5, "ask": 150.0}
        mock_base.get_symbol_price.return_value = mock_price_tick
        
        # Mock symbol info
        mock_symbol_info = {
            "digits": 2,
            "trade_stops_level": 10,
            "point": 0.01,
            "category": "Major",
            "filling_mode": mt5.ORDER_FILLING_FOK
        }
        mock_base.get_symbol_info.return_value = mock_symbol_info
        
        # Mock volume calculation functions
        mock_volume_from_budget.return_value = 4.0
        mock_calc_vol.return_value = [2.0, 2.0]  # Split into 2 parts
        
        result = prediction_to_orders(mock_pred, budget, vol_divisor, mock_base)
        
        # Verify calls
        mock_base.get_symbol_price.assert_called_once_with("AAPL", wait_sec=0.02)
        mock_base.get_symbol_info.assert_called_once_with("AAPL", wait_sec=0.02)
        mock_volume_from_budget.assert_called_once_with(budget, 150.0, mock_symbol_info, mock_base)
        mock_calc_vol.assert_called_once_with(4.0, mock_symbol_info, vol_divisor)
        
        # Verify result
        assert isinstance(result, list)
        assert len(result) == 2  # Split into 2 orders
        
        for order in result:
            assert isinstance(order, OrderData)
            assert order.symbol == "AAPL"
            assert order.type == mt5.ORDER_TYPE_BUY
            assert order.price == 150.0
            assert order.magic == 12345
            assert "Darwinexclient" in order.comment
            assert order.action == mt5.TRADE_ACTION_DEAL
            assert order.type_time == mt5.ORDER_TIME_DAY
            assert order.type_filling == mt5.ORDER_FILLING_FOK
            assert order.deviation == 10
        
        # Check volumes
        assert result[0].volume == 2.0
        assert result[1].volume == 2.0
    
    @patch('src.prediction_to_orders._calc_vol')
    @patch('src.prediction_to_orders._volume_from_budget')
    def test_prediction_to_orders_with_sl_tp_adjustment(self, mock_volume_from_budget, mock_calc_vol):
        """Test prediction_to_orders with stop level adjustments."""
        # Create mock prediction
        mock_pred = MagicMock(spec=PredictionData)
        mock_pred.symbol = "GOOGL"
        mock_pred.sl_pct = 0.01
        mock_pred.tp_pct = 0.015
        mock_pred.magic = 67890
        
        budget = 5000.0
        vol_divisor = 1
        
        # Create mock base
        mock_base = MagicMock(spec=mtBase)
        
        # Mock price tick
        mock_price_tick = {"bid": 2499.0, "ask": 2500.0}
        mock_base.get_symbol_price.return_value = mock_price_tick
        
        # Mock symbol info with tight stops level
        mock_symbol_info = {
            "digits": 2,
            "trade_stops_level": 50,  # Requires 50 points minimum
            "point": 1.0,
            "category": "Major",
            "filling_mode": mt5.ORDER_FILLING_FOK
        }
        mock_base.get_symbol_info.return_value = mock_symbol_info
        
        # Mock volume calculation functions
        mock_volume_from_budget.return_value = 1.0
        mock_calc_vol.return_value = [1.0]
        
        result = prediction_to_orders(mock_pred, budget, vol_divisor, mock_base)
        
        # Verify result
        assert len(result) == 1
        order = result[0]
        
        # Original SL/TP would be too close, should be adjusted
        # SL = 2500 * (1 - 0.01) = 2475 (25 points away, needs 50)
        # TP = 2500 * (1 + 0.015) = 2537.5 (37.5 points away, needs 50)
        # Adjusted SL should be 2500 - 51 = 2449
        # Adjusted TP should be 2500 + 51 = 2551
        expected_sl = 2500.0 - 51  # 2449.0
        expected_tp = 2500.0 + 51  # 2551.0
        
        assert order.sl == expected_sl
        assert order.tp == expected_tp
    
    @patch('src.prediction_to_orders._calc_vol')
    @patch('src.prediction_to_orders._volume_from_budget')
    def test_prediction_to_orders_exotic_symbol(self, mock_volume_from_budget, mock_calc_vol):
        """Test prediction_to_orders with exotic symbol."""
        # Create mock prediction
        mock_pred = MagicMock(spec=PredictionData)
        mock_pred.symbol = "USDTRY"
        mock_pred.sl_pct = 0.02
        mock_pred.tp_pct = 0.03
        mock_pred.magic = 11111
        
        budget = 3000.0
        vol_divisor = 3
        
        # Create mock base
        mock_base = MagicMock(spec=mtBase)
        
        # Mock price tick
        mock_price_tick = {"bid": 28.5, "ask": 28.6}
        mock_base.get_symbol_price.return_value = mock_price_tick
        
        # Mock exotic symbol info
        mock_symbol_info = {
            "digits": 4,
            "trade_stops_level": 5,
            "point": 0.0001,
            "category": "Exotic",  # This should trigger FOK filling
            "filling_mode": mt5.ORDER_FILLING_IOC
        }
        mock_base.get_symbol_info.return_value = mock_symbol_info
        
        # Mock volume calculation functions
        mock_volume_from_budget.return_value = 3.0
        mock_calc_vol.return_value = [1.0, 1.0, 1.0]
        
        result = prediction_to_orders(mock_pred, budget, vol_divisor, mock_base)
        
        # Verify result
        assert len(result) == 3
        
        # All orders should use FOK filling due to exotic category
        for order in result:
            assert order.type_filling == mt5.ORDER_FILLING_FOK
            assert order.symbol == "USDTRY"
            assert order.volume == 1.0
    
    @patch('src.prediction_to_orders._calc_vol')
    @patch('src.prediction_to_orders._volume_from_budget')
    @patch('src.prediction_to_orders.logger')
    def test_prediction_to_orders_volume_adjustment_logging(self, mock_logger, mock_volume_from_budget, mock_calc_vol):
        """Test prediction_to_orders logs volume adjustments."""
        # Create mock prediction
        mock_pred = MagicMock(spec=PredictionData)
        mock_pred.symbol = "MSFT"
        mock_pred.sl_pct = 0.01
        mock_pred.tp_pct = 0.02
        mock_pred.magic = 22222
        
        budget = 8000.0
        vol_divisor = 1
        
        # Create mock base
        mock_base = MagicMock(spec=mtBase)
        
        # Mock price tick
        mock_price_tick = {"bid": 399.5, "ask": 400.0}
        mock_base.get_symbol_price.return_value = mock_price_tick
        
        # Mock symbol info
        mock_symbol_info = {
            "digits": 2,
            "trade_stops_level": 10,
            "point": 0.01,
            "category": "Major",
            "filling_mode": mt5.ORDER_FILLING_FOK
        }
        mock_base.get_symbol_info.return_value = mock_symbol_info
        
        # Mock volume calculation - original vs adjusted
        original_volume = 5.0
        adjusted_volumes = [2.5, 2.4]  # Sum = 4.9, different from original
        mock_volume_from_budget.return_value = original_volume
        mock_calc_vol.return_value = adjusted_volumes
        
        result = prediction_to_orders(mock_pred, budget, vol_divisor, mock_base)
        
        # Verify logging calls
        mock_logger.info.assert_any_call(f"PLACE MARKET ORDER: Computed volume for MSFT: {original_volume} lots for budget {budget}.")
        mock_logger.info.assert_any_call(f"PLACE MARKET ORDER: Adjusted volume from {original_volume} to {sum(adjusted_volumes)} based on symbol constraints.")
        
        # Verify result
        assert len(result) == 2
        assert result[0].volume == 2.5
        assert result[1].volume == 2.4
    
    @patch('src.prediction_to_orders._calc_vol')
    @patch('src.prediction_to_orders._volume_from_budget')
    def test_prediction_to_orders_no_sl_tp(self, mock_volume_from_budget, mock_calc_vol):
        """Test prediction_to_orders with no stop loss or take profit."""
        # Create mock prediction
        mock_pred = MagicMock(spec=PredictionData)
        mock_pred.symbol = "TSLA"
        mock_pred.sl_pct = None
        mock_pred.tp_pct = None
        mock_pred.magic = 33333
        
        budget = 6000.0
        vol_divisor = 1
        
        # Create mock base
        mock_base = MagicMock(spec=mtBase)
        
        # Mock price tick
        mock_price_tick = {"bid": 249.5, "ask": 250.0}
        mock_base.get_symbol_price.return_value = mock_price_tick
        
        # Mock symbol info
        mock_symbol_info = {
            "digits": 2,
            "trade_stops_level": 10,
            "point": 0.01,
            "category": "Major",
            "filling_mode": mt5.ORDER_FILLING_FOK
        }
        mock_base.get_symbol_info.return_value = mock_symbol_info
        
        # Mock volume calculation functions
        mock_volume_from_budget.return_value = 2.0
        mock_calc_vol.return_value = [2.0]
        
        result = prediction_to_orders(mock_pred, budget, vol_divisor, mock_base)
        
        # Verify result
        assert len(result) == 1
        order = result[0]
        
        # Should have no SL/TP
        assert order.sl is None
        assert order.tp is None


class TestPredictionToOrdersEdgeCases:
    """Additional edge case tests for prediction_to_orders function."""
    
    @patch('src.prediction_to_orders._calc_vol')
    @patch('src.prediction_to_orders._volume_from_budget')
    def test_prediction_to_orders_currency_conversion_error(self, mock_volume_from_budget, mock_calc_vol):
        """Test prediction_to_orders when currency conversion fails."""
        # Create mock prediction
        mock_pred = MagicMock(spec=PredictionData)
        mock_pred.symbol = "EURJPY"
        mock_pred.sl_pct = 0.01
        mock_pred.tp_pct = 0.02
        mock_pred.magic = 44444
        
        budget = 3000.0
        vol_divisor = 1
        
        # Create mock base
        mock_base = MagicMock(spec=mtBase)
        
        # Mock price tick
        mock_price_tick = {"bid": 160.5, "ask": 161.0}
        mock_base.get_symbol_price.return_value = mock_price_tick
        
        # Mock symbol info
        mock_symbol_info = {
            "digits": 3,
            "trade_stops_level": 20,
            "point": 0.001,
            "category": "Major",
            "filling_mode": mt5.ORDER_FILLING_FOK
        }
        mock_base.get_symbol_info.return_value = mock_symbol_info
        
        # Mock volume calculation to raise NotImplementedError (currency conversion)
        mock_volume_from_budget.side_effect = NotImplementedError("Currency conversion not implemented yet.")
        
        with pytest.raises(NotImplementedError, match="Currency conversion not implemented yet."):
            prediction_to_orders(mock_pred, budget, vol_divisor, mock_base)
    
    @patch('src.prediction_to_orders._calc_vol')
    @patch('src.prediction_to_orders._volume_from_budget')
    def test_prediction_to_orders_calc_vol_error(self, mock_volume_from_budget, mock_calc_vol):
        """Test prediction_to_orders when _calc_vol raises error."""
        # Create mock prediction
        mock_pred = MagicMock(spec=PredictionData)
        mock_pred.symbol = "NZDUSD"
        mock_pred.sl_pct = 0.015
        mock_pred.tp_pct = 0.025
        mock_pred.magic = 55555
        
        budget = 4000.0
        vol_divisor = 2
        
        # Create mock base
        mock_base = MagicMock(spec=mtBase)
        
        # Mock price tick
        mock_price_tick = {"bid": 0.6150, "ask": 0.6155}
        mock_base.get_symbol_price.return_value = mock_price_tick
        
        # Mock symbol info
        mock_symbol_info = {
            "digits": 5,
            "trade_stops_level": 15,
            "point": 0.00001,
            "category": "Minor",
            "filling_mode": mt5.ORDER_FILLING_FOK
        }
        mock_base.get_symbol_info.return_value = mock_symbol_info
        
        # Mock volume calculations
        mock_volume_from_budget.return_value = 2.0
        mock_calc_vol.side_effect = RuntimeError("Invalid volume_step in symbol info.")
        
        with pytest.raises(RuntimeError, match="Invalid volume_step in symbol info."):
            prediction_to_orders(mock_pred, budget, vol_divisor, mock_base)
    
    @patch('src.prediction_to_orders._calc_vol')
    @patch('src.prediction_to_orders._volume_from_budget')
    def test_prediction_to_orders_extreme_sl_tp_values(self, mock_volume_from_budget, mock_calc_vol):
        """Test prediction_to_orders with extreme SL/TP percentages."""
        # Create mock prediction with extreme values
        mock_pred = MagicMock(spec=PredictionData)
        mock_pred.symbol = "BTCUSD"
        mock_pred.sl_pct = 0.5  # 50% stop loss
        mock_pred.tp_pct = 2.0  # 200% take profit
        mock_pred.magic = 66666
        
        budget = 2000.0
        vol_divisor = 1
        
        # Create mock base
        mock_base = MagicMock(spec=mtBase)
        
        # Mock price tick
        mock_price_tick = {"bid": 65000.0, "ask": 65100.0}
        mock_base.get_symbol_price.return_value = mock_price_tick
        
        # Mock symbol info with very permissive stops level
        mock_symbol_info = {
            "digits": 1,
            "trade_stops_level": 1,  # Very small stops level
            "point": 0.1,
            "category": "Crypto",
            "filling_mode": mt5.ORDER_FILLING_FOK
        }
        mock_base.get_symbol_info.return_value = mock_symbol_info
        
        # Mock volume calculation functions
        mock_volume_from_budget.return_value = 0.1
        mock_calc_vol.return_value = [0.1]
        
        result = prediction_to_orders(mock_pred, budget, vol_divisor, mock_base)
        
        # Verify result
        assert len(result) == 1
        order = result[0]
        
        # Calculate expected SL/TP
        price = 65100.0
        expected_sl = round(price * (1 - 0.5), 1)  # 32550.0
        expected_tp = round(price * (1 + 2.0), 1)  # 195300.0
        
        assert order.sl == expected_sl
        assert order.tp == expected_tp
    
    @patch('src.prediction_to_orders._calc_vol')
    @patch('src.prediction_to_orders._volume_from_budget')
    def test_prediction_to_orders_zero_volume(self, mock_volume_from_budget, mock_calc_vol):
        """Test prediction_to_orders with zero volume calculation."""
        # Create mock prediction
        mock_pred = MagicMock(spec=PredictionData)
        mock_pred.symbol = "XAUUSD"
        mock_pred.sl_pct = 0.01
        mock_pred.tp_pct = 0.02
        mock_pred.magic = 77777
        
        budget = 100.0  # Very small budget
        vol_divisor = 1
        
        # Create mock base
        mock_base = MagicMock(spec=mtBase)
        
        # Mock price tick
        mock_price_tick = {"bid": 2000.0, "ask": 2001.0}
        mock_base.get_symbol_price.return_value = mock_price_tick
        
        # Mock symbol info
        mock_symbol_info = {
            "digits": 2,
            "trade_stops_level": 50,
            "point": 0.01,
            "category": "Precious",
            "filling_mode": mt5.ORDER_FILLING_FOK
        }
        mock_base.get_symbol_info.return_value = mock_symbol_info
        
        # Mock volume calculation functions to return zero
        mock_volume_from_budget.return_value = 0.0
        mock_calc_vol.return_value = [0.0]
        
        result = prediction_to_orders(mock_pred, budget, vol_divisor, mock_base)
        
        # Should still create orders even with zero volume
        assert len(result) == 1
        assert result[0].volume == 0.0
    
    @patch('src.prediction_to_orders._calc_vol')
    @patch('src.prediction_to_orders._volume_from_budget')
    def test_prediction_to_orders_handles_tight_stops(self, mock_volume_from_budget, mock_calc_vol):
        """Test prediction_to_orders handles very tight SL/TP percentages without errors."""
        # Create mock prediction with very tight percentages
        mock_pred = MagicMock(spec=PredictionData)
        mock_pred.symbol = "EURUSD"
        mock_pred.sl_pct = 0.0001  # 0.01% - extremely tight
        mock_pred.tp_pct = 0.0001  # 0.01% - extremely tight
        mock_pred.magic = 88888
        
        budget = 5000.0
        vol_divisor = 1
        
        # Create mock base
        mock_base = MagicMock()
        
        # Use a price that will make calculations easier
        mock_price_tick = {"bid": 1.1000, "ask": 1.1000}
        mock_base.get_symbol_price.return_value = mock_price_tick
        
        # Mock symbol info with stops level that might require adjustments
        mock_symbol_info = {
            "digits": 4,
            "trade_stops_level": 10,  # 10 points minimum
            "point": 0.0001,  # 1 point = 0.0001 for EURUSD
            "category": "Major",
            "filling_mode": mt5.ORDER_FILLING_FOK
        }
        mock_base.get_symbol_info.return_value = mock_symbol_info
        
        # Mock volume calculation functions
        mock_volume_from_budget.return_value = 1.0
        mock_calc_vol.return_value = [1.0]
        
        # This should not raise any exceptions
        result = prediction_to_orders(mock_pred, budget, vol_divisor, mock_base)
        
        # Verify result is valid
        assert len(result) == 1
        assert isinstance(result[0], OrderData)
        assert result[0].symbol == "EURUSD"
        assert result[0].volume == 1.0
        assert result[0].price == 1.1000
        
        # SL and TP should be set to valid values (either original or adjusted)
        assert result[0].sl is not None
        assert result[0].tp is not None
        assert result[0].sl < result[0].price  # SL should be below entry price for buy order
        assert result[0].tp > result[0].price  # TP should be above entry price for buy order