"""Unit tests for finalize_positions_to_close.py functions."""

import pytest
from datetime import date, datetime
from unittest.mock import MagicMock, patch

from src.finalize_positions_to_close import (
    _create_prediction_lookup,
    _is_position_expired,
    _find_expired_positions,
    _calculate_positions_value,
    _get_oldest_positions,
    _add_positions_until_budget_met,
    get_positions_to_close
)
from src.infra.PositionData import PositionData
from src.infra.PredictionData import PredictionData
from src.infra.BudgetMgmt import BudgetMgmt


class TestCreatePredictionLookup:
    """Test cases for _create_prediction_lookup function."""
    
    def test_create_lookup_basic(self):
        """Test creating prediction lookup with multiple predictions."""
        pred1 = MagicMock(spec=PredictionData)
        pred1.magic = 12345
        pred2 = MagicMock(spec=PredictionData) 
        pred2.magic = 67890
        predictions = [pred1, pred2]
        
        result = _create_prediction_lookup(predictions)
        
        assert len(result) == 2
        assert result[12345] == pred1
        assert result[67890] == pred2
    
    def test_create_lookup_empty(self):
        """Test creating prediction lookup with empty list."""
        result = _create_prediction_lookup([])
        assert len(result) == 0
        assert result == {}
    
    def test_create_lookup_single(self):
        """Test creating prediction lookup with single prediction."""
        pred = MagicMock(spec=PredictionData)
        pred.magic = 12345
        predictions = [pred]
        
        result = _create_prediction_lookup(predictions)
        
        assert len(result) == 1
        assert result[12345] == pred


class TestIsPositionExpired:
    """Test cases for _is_position_expired function."""
    
    @patch('src.finalize_positions_to_close.calculate_trading_day')
    def test_position_expired(self, mock_calculate_trading_day):
        """Test when position is expired."""
        position = MagicMock(spec=PositionData)
        position.ticket = 123456
        position.time = MagicMock()
        position.time.date.return_value = date(2025, 11, 1)
        
        prediction = MagicMock(spec=PredictionData)
        prediction.last_training_day = date(2025, 11, 1)
        prediction.n_trading_days = 5
        prediction.magic = 12345
        
        # Mock expiration date to be before today
        mock_calculate_trading_day.return_value = date(2025, 11, 10)
        today = date(2025, 11, 12)
        
        result = _is_position_expired(position, prediction, today)
        
        assert result is True
        mock_calculate_trading_day.assert_called_once_with(date(2025, 11, 1), 5)
    
    @patch('src.finalize_positions_to_close.calculate_trading_day')
    def test_position_not_expired(self, mock_calculate_trading_day):
        """Test when position is not expired."""
        position = MagicMock(spec=PositionData)
        position.ticket = 123456
        position.time = MagicMock()
        position.time.date.return_value = date(2025, 11, 1)
        
        prediction = MagicMock(spec=PredictionData)
        prediction.last_training_day = date(2025, 11, 1)
        prediction.n_trading_days = 5
        prediction.magic = 12345
        
        # Mock expiration date to be after today
        mock_calculate_trading_day.return_value = date(2025, 11, 15)
        today = date(2025, 11, 12)
        
        result = _is_position_expired(position, prediction, today)
        
        assert result is False
        mock_calculate_trading_day.assert_called_once_with(date(2025, 11, 1), 5)
    
    @patch('src.finalize_positions_to_close.calculate_trading_day')
    def test_position_expired_exact_date(self, mock_calculate_trading_day):
        """Test when position expires exactly on today."""
        position = MagicMock(spec=PositionData)
        position.ticket = 123456
        position.time = MagicMock()
        position.time.date.return_value = date(2025, 11, 1)
        
        prediction = MagicMock(spec=PredictionData)
        prediction.last_training_day = date(2025, 11, 1)
        prediction.n_trading_days = 5
        prediction.magic = 12345
        
        # Mock expiration date to be exactly today
        today = date(2025, 11, 12)
        mock_calculate_trading_day.return_value = today
        
        result = _is_position_expired(position, prediction, today)
        
        assert result is True  # today >= expiration_date
    
    def test_invalid_n_trading_days(self):
        """Test with invalid n_trading_days values."""
        position = MagicMock(spec=PositionData)
        position.ticket = 123456
        position.time = MagicMock()
        position.time.date.return_value = date(2025, 11, 1)
        
        prediction = MagicMock(spec=PredictionData)
        prediction.last_training_day = date(2025, 11, 1)
        prediction.magic = 12345
        today = date(2025, 11, 12)
        
        # Test None value
        prediction.n_trading_days = None
        with pytest.raises(ValueError, match="Invalid n_trading_days"):
            _is_position_expired(position, prediction, today)
        
        # Test zero value
        prediction.n_trading_days = 0
        with pytest.raises(ValueError, match="Invalid n_trading_days"):
            _is_position_expired(position, prediction, today)
        
        # Test negative value
        prediction.n_trading_days = -5
        with pytest.raises(ValueError, match="Invalid n_trading_days"):
            _is_position_expired(position, prediction, today)
    
    @patch('src.finalize_positions_to_close.calculate_trading_day')
    def test_calculate_trading_day_error(self, mock_calculate_trading_day):
        """Test when calculate_trading_day raises an exception."""
        position = MagicMock(spec=PositionData)
        position.ticket = 123456
        position.time = MagicMock()
        position.time.date.return_value = date(2025, 11, 1)
        
        prediction = MagicMock(spec=PredictionData)
        prediction.last_training_day = date(2025, 11, 1)
        prediction.n_trading_days = 5
        prediction.magic = 12345
        
        mock_calculate_trading_day.side_effect = Exception("Test error")
        today = date(2025, 11, 12)
        
        with pytest.raises(RuntimeError, match="Error calculating expiration date"):
            _is_position_expired(position, prediction, today)


class TestFindExpiredPositions:
    """Test cases for _find_expired_positions function."""
    
    @patch('src.finalize_positions_to_close._is_position_expired')
    def test_find_expired_positions_basic(self, mock_is_expired):
        """Test finding expired positions with mixed results."""
        # Create positions
        pos1 = MagicMock(spec=PositionData)
        pos1.ticket = 111
        pos1.magic = 12345
        pos1.symbol = "EURUSD"
        
        pos2 = MagicMock(spec=PositionData)
        pos2.ticket = 222
        pos2.magic = 67890
        pos2.symbol = "GBPUSD"
        
        pos3 = MagicMock(spec=PositionData)
        pos3.ticket = 333
        pos3.magic = 11111
        pos3.symbol = "USDJPY"
        
        positions = [pos1, pos2, pos3]
        
        # Create predictions
        pred1 = MagicMock(spec=PredictionData)
        pred1.magic = 12345
        pred2 = MagicMock(spec=PredictionData) 
        pred2.magic = 67890
        pred3 = MagicMock(spec=PredictionData)
        pred3.magic = 11111
        
        prediction_by_magic = {12345: pred1, 67890: pred2, 11111: pred3}
        
        # Mock expiration results: pos1 and pos3 are expired
        mock_is_expired.side_effect = [True, False, True]
        
        today = date(2025, 11, 12)
        result = _find_expired_positions(positions, prediction_by_magic, today)
        
        assert len(result) == 2
        assert pos1 in result
        assert pos3 in result
        assert pos2 not in result
        
        # Verify _is_position_expired was called correctly
        assert mock_is_expired.call_count == 3
    
    def test_find_expired_positions_no_magic(self):
        """Test positions without magic numbers are skipped."""
        pos1 = MagicMock(spec=PositionData)
        pos1.ticket = 111
        pos1.magic = None  # No magic number
        pos1.symbol = "EURUSD"
        
        pos2 = MagicMock(spec=PositionData)
        pos2.ticket = 222
        pos2.magic = 0  # Empty magic number
        pos2.symbol = "GBPUSD"
        
        positions = [pos1, pos2]
        prediction_by_magic = {}
        today = date(2025, 11, 12)
        
        with patch('src.finalize_positions_to_close._is_position_expired') as mock_is_expired:
            result = _find_expired_positions(positions, prediction_by_magic, today)
            
            assert len(result) == 0
            mock_is_expired.assert_not_called()
    
    def test_find_expired_positions_no_prediction_match(self):
        """Test positions with no matching prediction data."""
        pos1 = MagicMock(spec=PositionData)
        pos1.ticket = 111
        pos1.magic = 12345
        pos1.symbol = "EURUSD"
        
        positions = [pos1]
        prediction_by_magic = {67890: MagicMock()}  # Different magic number
        today = date(2025, 11, 12)
        
        with patch('src.finalize_positions_to_close._is_position_expired') as mock_is_expired:
            # Mock that position is expired when no prediction match
            mock_is_expired.return_value = True
            result = _find_expired_positions(positions, prediction_by_magic, today)
            
            assert len(result) == 1
            assert result[0] == pos1
            # Should be called once with position, None (no prediction), today, 0
            mock_is_expired.assert_called_once_with(pos1, None, today, 0)
    
    def test_find_expired_positions_empty_lists(self):
        """Test with empty positions and predictions."""
        result = _find_expired_positions([], {}, date(2025, 11, 12))
        assert result == []


class TestCalculatePositionsValue:
    """Test cases for _calculate_positions_value function."""
    
    def test_calculate_value_single_position(self):
        """Test calculating value for single position."""
        position = MagicMock(spec=PositionData)
        position.price_current = 1.2345
        position.volume = 2.0
        positions = [position]
        
        result = _calculate_positions_value(positions)
        
        assert result == 2.469  # 1.2345 * 2.0
    
    def test_calculate_value_multiple_positions(self):
        """Test calculating value for multiple positions."""
        pos1 = MagicMock(spec=PositionData)
        pos1.price_current = 1.0
        pos1.volume = 100.0
        
        pos2 = MagicMock(spec=PositionData)
        pos2.price_current = -2.0  # Negative price
        pos2.volume = 50.0
        
        positions = [pos1, pos2]
        result = _calculate_positions_value(positions)
        
        # Should use absolute values: |1.0*100| + |-2.0*50| = 100 + 100 = 200
        assert result == 200.0
    
    def test_calculate_value_empty_list(self):
        """Test calculating value for empty list."""
        result = _calculate_positions_value([])
        assert result == 0.0
    
    def test_calculate_value_zero_values(self):
        """Test calculating value with zero price and volume."""
        pos1 = MagicMock(spec=PositionData)
        pos1.price_current = 0.0
        pos1.volume = 100.0
        
        pos2 = MagicMock(spec=PositionData)
        pos2.price_current = 1.5
        pos2.volume = 0.0
        
        positions = [pos1, pos2]
        result = _calculate_positions_value(positions)
        
        assert result == 0.0  # 0.0*100 + 1.5*0.0 = 0


class TestGetOldestPositions:
    """Test cases for _get_oldest_positions function."""
    
    def test_get_oldest_positions_basic(self):
        """Test getting oldest positions excluding specified ones."""
        # Create positions with different times
        pos1 = MagicMock(spec=PositionData)
        pos1.magic = 12345
        pos1.time = datetime(2025, 11, 10, 10, 0, 0)  # Oldest
        
        pos2 = MagicMock(spec=PositionData)
        pos2.magic = 67890
        pos2.time = datetime(2025, 11, 12, 10, 0, 0)  # Newest
        
        pos3 = MagicMock(spec=PositionData)
        pos3.magic = 11111
        pos3.time = datetime(2025, 11, 11, 10, 0, 0)  # Middle
        
        positions = [pos2, pos1, pos3]  # Unsorted input
        exclude = [pos2]  # Exclude newest
        
        result = _get_oldest_positions(positions, exclude)
        
        assert len(result) == 2
        assert result[0] == pos1  # Oldest first
        assert result[1] == pos3  # Then middle
        assert pos2 not in result
    
    def test_get_oldest_positions_no_magic(self):
        """Test positions without magic numbers are excluded."""
        pos1 = MagicMock(spec=PositionData)
        pos1.magic = None
        pos1.time = datetime(2025, 11, 10, 10, 0, 0)
        
        pos2 = MagicMock(spec=PositionData)
        pos2.magic = 12345
        pos2.time = datetime(2025, 11, 11, 10, 0, 0)
        
        positions = [pos1, pos2]
        exclude = []
        
        result = _get_oldest_positions(positions, exclude)
        
        assert len(result) == 1
        assert result[0] == pos2
    
    def test_get_oldest_positions_all_excluded(self):
        """Test when all positions are excluded."""
        pos1 = MagicMock(spec=PositionData)
        pos1.magic = 12345
        pos1.time = datetime(2025, 11, 10, 10, 0, 0)
        
        positions = [pos1]
        exclude = [pos1]
        
        result = _get_oldest_positions(positions, exclude)
        
        assert len(result) == 0
    
    def test_get_oldest_positions_empty_input(self):
        """Test with empty positions list."""
        result = _get_oldest_positions([], [])
        assert result == []


class TestAddPositionsUntilBudgetMet:
    """Test cases for _add_positions_until_budget_met function."""
    
    def test_add_positions_until_budget_met_basic(self):
        """Test adding positions until budget requirement is met."""
        # Expired positions
        expired_pos = MagicMock(spec=PositionData)
        expired_pos.price_current = 1.0
        expired_pos.volume = 300.0
        expired_pos.ticket = 111
        expired_positions = [expired_pos]
        
        # Available positions sorted by age
        avail_pos1 = MagicMock(spec=PositionData)
        avail_pos1.price_current = 1.0
        avail_pos1.volume = 200.0
        avail_pos1.ticket = 222
        avail_pos1.time = datetime(2025, 11, 10, 10, 0, 0)  # Older
        
        avail_pos2 = MagicMock(spec=PositionData)
        avail_pos2.price_current = 1.0
        avail_pos2.volume = 500.0
        avail_pos2.ticket = 333
        avail_pos2.time = datetime(2025, 11, 11, 10, 0, 0)  # Newer
        
        available_positions = [avail_pos1, avail_pos2]  # Sorted by age
        
        available_free_margin = 100.0
        required_budget = 700.0  # Need 700, have 100 + 300 = 400, need 300 more
        
        result = _add_positions_until_budget_met(
            expired_positions, available_positions, available_free_margin, required_budget
        )
        
        # Should add expired + first available (100 + 300 + 200 = 600 < 700)
        # Then add second available (100 + 300 + 200 + 500 = 1100 >= 700)
        assert len(result) == 3
        assert expired_pos in result
        assert avail_pos1 in result
        assert avail_pos2 in result
    
    def test_add_positions_budget_met_early(self):
        """Test when budget requirement is met before all positions are added."""
        expired_pos = MagicMock(spec=PositionData)
        expired_pos.price_current = 1.0
        expired_pos.volume = 300.0
        expired_pos.ticket = 111
        expired_positions = [expired_pos]
        
        avail_pos1 = MagicMock(spec=PositionData)
        avail_pos1.price_current = 1.0
        avail_pos1.volume = 400.0  # This alone will meet the requirement
        avail_pos1.ticket = 222
        avail_pos1.time = datetime(2025, 11, 10, 10, 0, 0)
        
        avail_pos2 = MagicMock(spec=PositionData)
        avail_pos2.price_current = 1.0
        avail_pos2.volume = 200.0  # Should not be added
        avail_pos2.ticket = 333
        avail_pos2.time = datetime(2025, 11, 11, 10, 0, 0)
        
        available_positions = [avail_pos1, avail_pos2]
        
        available_free_margin = 100.0
        required_budget = 700.0  # Need 700, have 100 + 300 + 400 = 800 >= 700
        
        result = _add_positions_until_budget_met(
            expired_positions, available_positions, available_free_margin, required_budget
        )
        
        assert len(result) == 2
        assert expired_pos in result
        assert avail_pos1 in result
        assert avail_pos2 not in result  # Should not be added
    
    def test_add_positions_unsorted_available(self):
        """Test that unsorted available positions get sorted."""
        expired_positions = []
        
        # Create positions in unsorted order
        avail_pos1 = MagicMock(spec=PositionData)
        avail_pos1.price_current = 1.0
        avail_pos1.volume = 100.0
        avail_pos1.ticket = 111
        avail_pos1.time = datetime(2025, 11, 12, 10, 0, 0)  # Newer
        
        avail_pos2 = MagicMock(spec=PositionData)
        avail_pos2.price_current = 1.0
        avail_pos2.volume = 100.0
        avail_pos2.ticket = 222
        avail_pos2.time = datetime(2025, 11, 10, 10, 0, 0)  # Older - should be first
        
        available_positions = [avail_pos1, avail_pos2]  # Unsorted
        
        available_free_margin = 0.0
        required_budget = 150.0  # Need one position
        
        with patch('src.finalize_positions_to_close.logger') as mock_logger:
            result = _add_positions_until_budget_met(
                expired_positions, available_positions, available_free_margin, required_budget
            )
            
            # Should add the older position first. Each position is worth 100,
            # so to reach required_budget (150) both positions are needed.
            assert len(result) == 2
            assert result[0] == avail_pos2  # Older position added first
            assert result[1] == avail_pos1  # Then the newer position
            mock_logger.warning.assert_called_once()
    
    def test_add_positions_no_available(self):
        """Test with no available positions."""
        expired_pos = MagicMock(spec=PositionData)
        expired_pos.price_current = 1.0
        expired_pos.volume = 100.0
        expired_positions = [expired_pos]
        
        result = _add_positions_until_budget_met(
            expired_positions, [], 0.0, 1000.0
        )
        
        assert result == expired_positions


class TestGetPositionsToClose:
    """Test cases for main get_positions_to_close function."""
    
    @patch('src.finalize_positions_to_close.date')
    @patch('src.finalize_positions_to_close._find_expired_positions')
    @patch('src.finalize_positions_to_close._create_prediction_lookup')
    def test_expired_positions_sufficient(
        self, mock_create_lookup, mock_find_expired, mock_date
    ):
        """Test when expired positions meet budget requirement."""
        mock_date.today.return_value = date(2025, 11, 12)
        
        # Mock budget management
        budget_mgmt = MagicMock(spec=BudgetMgmt)
        budget_mgmt.calc_daily_budget.return_value = 1000.0
        budget_mgmt.free_margin = 200.0
        
        # Mock expired position with sufficient value
        expired_pos = MagicMock(spec=PositionData)
        expired_pos.price_current = 1.0
        expired_pos.volume = 900.0  # Value = 900
        mock_find_expired.return_value = [expired_pos]
        mock_create_lookup.return_value = {}
        
        # Required budget = 1000 * 1.05 = 1050
        # Available = 200 + 900 = 1100 (sufficient)
        result = get_positions_to_close([], [], budget_mgmt, 4)
        
        assert len(result) == 1
        assert result[0] == expired_pos
    
    @patch('src.finalize_positions_to_close.date')
    @patch('src.finalize_positions_to_close._add_positions_until_budget_met')
    @patch('src.finalize_positions_to_close._get_oldest_positions')
    @patch('src.finalize_positions_to_close._find_expired_positions')
    @patch('src.finalize_positions_to_close._create_prediction_lookup')
    def test_need_additional_positions(
        self, mock_create_lookup, mock_find_expired, mock_get_oldest, 
        mock_add_positions, mock_date
    ):
        """Test when additional positions needed to meet budget."""
        mock_date.today.return_value = date(2025, 11, 12)
        
        # Mock budget management
        budget_mgmt = MagicMock(spec=BudgetMgmt)
        budget_mgmt.calc_daily_budget.return_value = 1000.0
        budget_mgmt.free_margin = 200.0
        
        # Mock expired positions with insufficient value
        expired_pos = MagicMock(spec=PositionData)
        expired_pos.price_current = 1.0
        expired_pos.volume = 500.0  # Value = 500, insufficient
        mock_find_expired.return_value = [expired_pos]
        
        # Mock additional positions
        additional_pos = MagicMock(spec=PositionData)
        mock_get_oldest.return_value = [additional_pos]
        mock_add_positions.return_value = [expired_pos, additional_pos]
        mock_create_lookup.return_value = {}
        
        # Required budget = 1000 * 1.05 = 1050
        # Available = 200 + 500 = 700 (insufficient)
        result = get_positions_to_close([], [], budget_mgmt, 4)
        
        assert len(result) == 2
        assert expired_pos in result
        assert additional_pos in result
        
        # Verify _get_oldest_positions was called with correct parameters
        mock_get_oldest.assert_called_once()
        positions_arg, exclude_arg = mock_get_oldest.call_args[0]
        assert exclude_arg == [expired_pos]
        
        # Verify _add_positions_until_budget_met was called
        mock_add_positions.assert_called_once()
    
    def test_custom_budget_threshold(self):
        """Test with custom budget threshold."""
        with patch('src.finalize_positions_to_close.date') as mock_date, \
             patch('src.finalize_positions_to_close._find_expired_positions') as mock_find_expired, \
             patch('src.finalize_positions_to_close._create_prediction_lookup') as mock_create_lookup:
            
            mock_date.today.return_value = date(2025, 11, 12)
            mock_find_expired.return_value = []
            mock_create_lookup.return_value = {}
            
            budget_mgmt = MagicMock(spec=BudgetMgmt)
            budget_mgmt.calc_daily_budget.return_value = 1000.0
            budget_mgmt.free_margin = 2000.0  # Sufficient margin
            
            # Custom threshold of 10%
            result = get_positions_to_close([], [], budget_mgmt, 4, budget_threshold=0.10)
            
            assert result == []
    
    @patch('src.finalize_positions_to_close.date')
    @patch('src.finalize_positions_to_close._find_expired_positions')
    @patch('src.finalize_positions_to_close._create_prediction_lookup')
    def test_no_expired_positions_sufficient_margin(
        self, mock_create_lookup, mock_find_expired, mock_date
    ):
        """Test when no expired positions but sufficient margin available."""
        mock_date.today.return_value = date(2025, 11, 12)
        mock_find_expired.return_value = []
        mock_create_lookup.return_value = {}
        
        budget_mgmt = MagicMock(spec=BudgetMgmt)
        budget_mgmt.calc_daily_budget.return_value = 1000.0
        budget_mgmt.free_margin = 1100.0  # More than required budget (1050)
        
        result = get_positions_to_close([], [], budget_mgmt, 4)
        
        assert result == []