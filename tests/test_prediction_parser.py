"""
Unit tests for prediction_parser module.
"""
import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from datetime import date

from src.PredictionParser import (
    PredictionData,
    PredictionParser
)


class TestPredictionData:
    """Tests for PredictionData class."""
    
    def test_init(self):
        """Test PredictionData initialization."""
        pred = PredictionData(
            symbol="EURUSD",
            last_training_day=date(2025, 10, 14),
            last_close_price=1.0845,
            n_trading_days=5,
            score=0.73
        )
        
        assert pred.symbol == "EURUSD"
        assert pred.last_training_day == date(2025, 10, 14)
        assert pred.last_close_price == 1.0845
        assert pred.n_trading_days == 5
        assert pred.score == 0.73
        assert pred.sl_pct is None
        assert pred.tp_pct is None
    
    def test_init_with_optional_fields(self):
        """Test PredictionData initialization with optional sl_pct and tp_pct."""
        pred = PredictionData(
            symbol="EURUSD",
            last_training_day=date(2025, 10, 14),
            last_close_price=1.0845,
            n_trading_days=5,
            score=0.73,
            sl_pct=0.1,
            tp_pct=0.15
        )
        
        assert pred.symbol == "EURUSD"
        assert pred.last_training_day == date(2025, 10, 14)
        assert pred.last_close_price == 1.0845
        assert pred.n_trading_days == 5
        assert pred.score == 0.73
        assert pred.sl_pct == 0.1
        assert pred.tp_pct == 0.15
    
    def test_repr(self):
        """Test string representation."""
        pred = PredictionData("EURUSD", date(2025, 10, 14), 1.0845, 5, 0.73)
        repr_str = repr(pred)
        
        assert "PredictionData" in repr_str
        assert "EURUSD" in repr_str
        assert "0.73" in repr_str
        assert "sl_pct=None" in repr_str
        assert "tp_pct=None" in repr_str
    
    def test_repr_with_optional_fields(self):
        """Test string representation with optional fields."""
        pred = PredictionData("EURUSD", date(2025, 10, 14), 1.0845, 5, 0.73, sl_pct=0.1, tp_pct=0.15)
        repr_str = repr(pred)
        
        assert "PredictionData" in repr_str
        assert "EURUSD" in repr_str
        assert "sl_pct=0.1" in repr_str
        assert "tp_pct=0.15" in repr_str
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        pred = PredictionData("EURUSD", date(2025, 10, 14), 1.0845, 5, 0.73)
        result = pred.to_dict()
        
        expected = {
            'symbol': "EURUSD",
            'last_training_day': "2025-10-14",  # Should be ISO format string
            'last_close_price': 1.0845,
            'n_trading_days': 5,
            'score': 0.73
        }
        
        assert result == expected
    
    def test_to_dict_with_optional_fields(self):
        """Test conversion to dictionary with optional fields."""
        pred = PredictionData("EURUSD", date(2025, 10, 14), 1.0845, 5, 0.73, sl_pct=0.1, tp_pct=0.15)
        result = pred.to_dict()
        
        expected = {
            'symbol': "EURUSD",
            'last_training_day': "2025-10-14",  # Should be ISO format string
            'last_close_price': 1.0845,
            'n_trading_days': 5,
            'score': 0.73,
            'sl_pct': 0.1,
            'tp_pct': 0.15
        }
        
        assert result == expected
    
    def test_to_dict_partial_optional_fields(self):
        """Test conversion to dictionary with only one optional field."""
        pred = PredictionData("EURUSD", date(2025, 10, 14), 1.0845, 5, 0.73, sl_pct=0.1)
        result = pred.to_dict()
        
        expected = {
            'symbol': "EURUSD",
            'last_training_day': "2025-10-14",  
            'last_close_price': 1.0845,
            'n_trading_days': 5,
            'score': 0.73,
            'sl_pct': 0.1
        }
        
        assert result == expected
        assert 'tp_pct' not in result  # Should not include tp_pct when it's None


class TestPredictionParser:
    """Tests for PredictionParser class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.sample_prediction = {
            "symbol": "EURUSD",
            "last_training_day": "2025-10-14T00:00:00Z",
            "last_close_price": 1.0845,
            "n_trading_days": 5,
            "score": 0.73
        }
        
        self.sample_predictions_list = [
            self.sample_prediction,
            {
                "symbol": "GBPUSD",
                "last_training_day": "2025-10-14T00:00:00Z",
                "last_close_price": 1.2976,
                "n_trading_days": 3,
                "score": 0.68
            }
        ]
        
        self.sample_prediction_with_sl_tp = {
            "symbol": "AUDUSD",
            "last_training_day": "2025-10-14T00:00:00Z",
            "last_close_price": 0.6785,
            "n_trading_days": 4,
            "score": 0.76,
            "sl_pct": 0.1,
            "tp_pct": 0.15
        }
    
    def test_init(self):
        """Test PredictionParser initialization."""
        parser = PredictionParser("test_dir")
        assert parser.predictions_dir == Path("test_dir")
        
        parser = PredictionParser()
        assert parser.predictions_dir == Path("predictions")
    
    @patch('glob.glob')
    def test_find_prediction_files_with_group(self, mock_glob):
        """Test finding prediction files with group filter."""
        mock_glob.return_value = [
            "predictions/prediction_debug_15oct2025_001.json",
            "predictions/prediction_debug_14oct2025_002.json"
        ]
        
        parser = PredictionParser("predictions")
        result = parser.find_prediction_files("debug")
        
        # The actual implementation uses Path.joinpath which creates OS-specific paths
        expected_pattern = str(Path("predictions") / "prediction_debug_*.json")
        mock_glob.assert_called_once_with(expected_pattern)
        assert len(result) == 2
        assert all(isinstance(p, Path) for p in result)
    
    @patch('glob.glob')
    def test_find_prediction_files_without_group(self, mock_glob):
        """Test finding all prediction files."""
        mock_glob.return_value = ["predictions/prediction_any_15oct2025_001.json"]
        
        parser = PredictionParser("predictions")
        result = parser.find_prediction_files()
        
        # The actual implementation uses Path.joinpath which creates OS-specific paths
        expected_pattern = str(Path("predictions") / "prediction_*.json")
        mock_glob.assert_called_once_with(expected_pattern)
        assert len(result) == 1
    
    def test_parse_json_file_single_dict(self):
        """Test parsing JSON file with single dictionary."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.sample_prediction, f)
            temp_path = f.name
        
        try:
            parser = PredictionParser()
            result = parser.parse_json_file(temp_path)
            
            assert len(result) == 1
            assert isinstance(result[0], PredictionData)
            assert result[0].symbol == "EURUSD"
            assert result[0].score == 0.73
        finally:
            Path(temp_path).unlink()
    
    def test_parse_json_file_list_of_dicts(self):
        """Test parsing JSON file with list of dictionaries."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.sample_predictions_list, f)
            temp_path = f.name
        
        try:
            parser = PredictionParser()
            result = parser.parse_json_file(temp_path)
            
            assert len(result) == 2
            assert all(isinstance(pred, PredictionData) for pred in result)
            assert result[0].symbol == "EURUSD"
            assert result[1].symbol == "GBPUSD"
        finally:
            Path(temp_path).unlink()
    
    def test_parse_json_file_with_sl_tp(self):
        """Test parsing JSON file with sl_pct and tp_pct fields."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.sample_prediction_with_sl_tp, f)
            temp_path = f.name
        
        try:
            parser = PredictionParser()
            result = parser.parse_json_file(temp_path)
            
            assert len(result) == 1
            assert isinstance(result[0], PredictionData)
            assert result[0].symbol == "AUDUSD"
            assert result[0].score == 0.76
            assert result[0].sl_pct == 0.1
            assert result[0].tp_pct == 0.15
        finally:
            Path(temp_path).unlink()
    
    def test_parse_json_file_mixed_with_without_sl_tp(self):
        """Test parsing JSON file with mixed data (some with sl_pct/tp_pct, some without)."""
        mixed_data = [
            self.sample_prediction,  # No sl_pct/tp_pct
            self.sample_prediction_with_sl_tp,  # With sl_pct/tp_pct
            {
                "symbol": "GBPUSD",
                "last_training_day": "2025-10-14T00:00:00Z",
                "last_close_price": 1.2976,
                "n_trading_days": 3,
                "score": 0.68,
                "sl_pct": 0.08  # Only sl_pct, no tp_pct
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(mixed_data, f)
            temp_path = f.name
        
        try:
            parser = PredictionParser()
            result = parser.parse_json_file(temp_path)
            
            assert len(result) == 3
            
            # First prediction (no sl_pct/tp_pct)
            assert result[0].symbol == "EURUSD"
            assert result[0].sl_pct is None
            assert result[0].tp_pct is None
            
            # Second prediction (both sl_pct and tp_pct)
            assert result[1].symbol == "AUDUSD"
            assert result[1].sl_pct == 0.1
            assert result[1].tp_pct == 0.15
            
            # Third prediction (only sl_pct)
            assert result[2].symbol == "GBPUSD"
            assert result[2].sl_pct == 0.08
            assert result[2].tp_pct is None
        finally:
            Path(temp_path).unlink()
    
    def test_parse_json_file_not_found(self):
        """Test parsing non-existent file."""
        parser = PredictionParser()
        
        with pytest.raises(FileNotFoundError):
            parser.parse_json_file("nonexistent.json")
    
    def test_parse_json_file_invalid_json(self):
        """Test parsing invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            temp_path = f.name
        
        try:
            parser = PredictionParser()
            
            with pytest.raises(json.JSONDecodeError):
                parser.parse_json_file(temp_path)
        finally:
            Path(temp_path).unlink()
    
    def test_parse_json_file_missing_fields(self):
        """Test parsing JSON with missing required fields."""
        incomplete_data = {
            "symbol": "EURUSD",
            "score": 0.73
            # Missing other required fields
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(incomplete_data, f)
            temp_path = f.name
        
        try:
            parser = PredictionParser()
            
            with pytest.raises(ValueError, match="Missing required fields"):
                parser.parse_json_file(temp_path)
        finally:
            Path(temp_path).unlink()
    
    def test_parse_iso_date_valid(self):
        cases = {
            "2025-10-14T00:00:00Z": date(2025, 10, 14),
            "2025-10-14T12:30:45.123Z": date(2025, 10, 14),
            "2025-10-14T08:15:30+01:00": date(2025, 10, 14),
            "2025-10-14T23:59:59-05:00": date(2025, 10, 15),  # UTC-normalized rolls over
        }
        for s, expected in cases.items():
            assert PredictionParser._parse_iso_date(s) == expected
    
    def test_parse_iso_date_invalid_format(self):
        """Test parsing invalid date format strings."""
        invalid_cases = [
            "2025-10-14",  # Missing time
            "10/14/2025",  # Wrong format
            "2025-10-14 00:00:00",  # Missing T
            "not a date",  # Completely invalid
            "2025-13-32T00:00:00Z",  # Invalid date values
            "",  # Empty string
            None  # None value
        ]
        
        for date_str in invalid_cases:
            with pytest.raises(ValueError):
                PredictionParser._parse_iso_date(date_str)


if __name__ == "__main__":
    pytest.main([__file__])