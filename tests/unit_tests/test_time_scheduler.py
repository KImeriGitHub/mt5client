import pytest
import time
from unittest.mock import patch, MagicMock
import logging

from src.time_scheduler import parse_and_sleep_until_time


class TestTimeScheduler:
    
    @patch('src.time_scheduler.TimeModule')
    @patch('src.time_scheduler.time.sleep')
    def test_parse_and_sleep_until_time_valid_time_future(self, mock_sleep, mock_time_module_class):
        """Test scheduling for a future time with valid format."""
        # Arrange
        mock_time_module = MagicMock()
        mock_time_module.calc_sec_to_sleep.return_value = 3600.0  # 1 hour
        mock_time_module_class.return_value = mock_time_module
        
        # Act
        parse_and_sleep_until_time("14:30")
        
        # Assert
        mock_time_module_class.assert_called_once()
        mock_time_module.calc_sec_to_sleep.assert_called_once_with(14, 30)
        mock_sleep.assert_called_once_with(3600.0)
    
    @patch('src.time_scheduler.TimeModule')
    @patch('src.time_scheduler.time.sleep')
    def test_parse_and_sleep_until_time_past_time(self, mock_sleep, mock_time_module_class):
        """Test scheduling for a past time (should proceed immediately)."""
        # Arrange
        mock_time_module = MagicMock()
        mock_time_module.calc_sec_to_sleep.return_value = 0.0  # Past time
        mock_time_module_class.return_value = mock_time_module
        
        # Act
        parse_and_sleep_until_time("09:15")
        
        # Assert
        mock_time_module_class.assert_called_once()
        mock_time_module.calc_sec_to_sleep.assert_called_once_with(9, 15)
        mock_sleep.assert_not_called()
    
    @patch('src.time_scheduler.TimeModule')
    @patch('src.time_scheduler.time.sleep')
    def test_parse_and_sleep_until_time_empty_string(self, mock_sleep, mock_time_module_class):
        """Test with empty time string (should proceed immediately)."""
        # Act
        parse_and_sleep_until_time("")
        
        # Assert
        mock_time_module_class.assert_not_called()
        mock_sleep.assert_not_called()
    
    @patch('src.time_scheduler.TimeModule')
    @patch('src.time_scheduler.time.sleep')
    def test_parse_and_sleep_until_time_none(self, mock_sleep, mock_time_module_class):
        """Test with None time string (should proceed immediately)."""
        # Act
        parse_and_sleep_until_time(None)
        
        # Assert
        mock_time_module_class.assert_not_called()
        mock_sleep.assert_not_called()
    
    @patch('src.time_scheduler.TimeModule')
    @patch('src.time_scheduler.time.sleep')
    @patch('src.time_scheduler.logger')
    def test_parse_and_sleep_until_time_invalid_formats(self, mock_logger, mock_sleep, mock_time_module_class):
        """Test with various invalid time formats."""
        invalid_formats = [
            "25:30",     # Invalid hour
            "14:60",     # Invalid minute
            "14",        # Missing minute
            "14:30:45",  # Too many components
            "abc:def",   # Non-numeric
            "14:3a",     # Mixed alphanumeric
        ]
        
        for invalid_format in invalid_formats:
            # Act
            parse_and_sleep_until_time(invalid_format)
            
            # Assert
            mock_time_module_class.assert_not_called()
            mock_sleep.assert_not_called()
            
            # Check that error was logged
            mock_logger.error.assert_called()
            error_call_args = mock_logger.error.call_args[0][0]
            assert "Invalid time format" in error_call_args
            assert invalid_format in error_call_args
            
            # Reset mocks for next iteration
            mock_time_module_class.reset_mock()
            mock_sleep.reset_mock()
            mock_logger.reset_mock()