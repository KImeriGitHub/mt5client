"""Unit tests for PredictionParser class."""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import date, datetime, timezone
from unittest.mock import patch, MagicMock
import glob

from src.infra.PredictionParser import PredictionParser
from src.infra.PredictionData import PredictionData


class TestPredictionParser:
    """Test cases for PredictionParser class."""
    
    def test_init_default_dir(self):
        """Test initialization with default directory."""
        parser = PredictionParser()
        assert parser.predictions_dir == Path("predictions")
    
    def test_init_custom_dir_str(self):
        """Test initialization with custom directory as string."""
        parser = PredictionParser("custom_predictions")
        assert parser.predictions_dir == Path("custom_predictions")
    
    def test_init_custom_dir_path(self):
        """Test initialization with custom directory as Path."""
        custom_path = Path("custom/path/predictions")
        parser = PredictionParser(custom_path)
        assert parser.predictions_dir == custom_path
    
    def test_parse_iso_date_valid_z_format(self):
        """Test _parse_iso_date with valid Z format."""
        date_str = "2025-10-14T00:00:00Z"
        result = PredictionParser._parse_iso_date(date_str)
        expected = date(2025, 10, 14)
        assert result == expected
    
    def test_parse_iso_date_valid_offset_format(self):
        """Test _parse_iso_date with valid timezone offset format."""
        date_str = "2025-10-14T12:00:00+00:00"
        result = PredictionParser._parse_iso_date(date_str)
        expected = date(2025, 10, 14)
        assert result == expected
    
    def test_parse_iso_date_different_timezone(self):
        """Test _parse_iso_date with different timezone."""
        date_str = "2025-10-14T23:30:00+05:00"
        result = PredictionParser._parse_iso_date(date_str)
        # Should be normalized to UTC, so still October 14th in this case
        expected = date(2025, 10, 14)
        assert result == expected
    
    def test_parse_iso_date_invalid_format(self):
        """Test _parse_iso_date with invalid format."""
        date_str = "2025-10-14"  # No timezone info
        with pytest.raises(ValueError, match="Timezone offset or 'Z' is required"):
            PredictionParser._parse_iso_date(date_str)
    
    def test_parse_iso_date_malformed(self):
        """Test _parse_iso_date with malformed date string."""
        date_str = "invalid-date-string"
        with pytest.raises(ValueError, match="Failed to parse ISO 8601 date"):
            PredictionParser._parse_iso_date(date_str)
    
    def test_parse_iso_date_empty_string(self):
        """Test _parse_iso_date with empty string."""
        date_str = ""
        with pytest.raises(ValueError, match="Failed to parse ISO 8601 date"):
            PredictionParser._parse_iso_date(date_str)
    
    def test_parse_iso_date_none(self):
        """Test _parse_iso_date with None input."""
        date_str = None
        with pytest.raises(ValueError, match="Failed to parse ISO 8601 date"):
            PredictionParser._parse_iso_date(date_str)
    
    @patch('glob.glob')
    def test_find_prediction_files_no_group(self, mock_glob):
        """Test find_prediction_files without group filter."""
        mock_glob.return_value = [
            "/predictions/prediction_debug_01.json",
            "/predictions/prediction_debug_02.json",
            "/predictions/prediction_live_01.json"
        ]
        
        parser = PredictionParser("predictions")
        result = parser.find_prediction_files()
        
        expected = [
            Path("/predictions/prediction_debug_01.json"),
            Path("/predictions/prediction_debug_02.json"),
            Path("/predictions/prediction_live_01.json")
        ]
        assert result == expected
        expected_glob_pattern = str(Path("predictions") / "prediction_*.json")
        mock_glob.assert_called_once_with(expected_glob_pattern)
    
    @patch('glob.glob')
    def test_find_prediction_files_with_group(self, mock_glob):
        """Test find_prediction_files with group filter."""
        mock_glob.return_value = [
            "/predictions/prediction_debug_01.json",
            "/predictions/prediction_debug_02.json"
        ]
        
        parser = PredictionParser("predictions")
        result = parser.find_prediction_files("debug")
        
        expected = [
            Path("/predictions/prediction_debug_01.json"),
            Path("/predictions/prediction_debug_02.json")
        ]
        assert result == expected
        expected_glob_pattern = str(Path("predictions") / "prediction_debug_*.json")
        mock_glob.assert_called_once_with(expected_glob_pattern)
    
    @patch('glob.glob')
    def test_find_prediction_files_no_matches(self, mock_glob):
        """Test find_prediction_files with no matching files."""
        mock_glob.return_value = []
        
        parser = PredictionParser("predictions")
        result = parser.find_prediction_files()
        
        assert result == []
    
    def test_parse_json_file_single_prediction(self):
        """Test parse_json_file with single prediction."""
        prediction_data = {
            "symbol": "EURUSD",
            "last_training_day": "2025-10-14T00:00:00Z",
            "last_close_price": 1.0845,
            "n_trading_days": 5,
            "score": 0.73,
            "sl_pct": 0.05,
            "tp_pct": 0.10
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(prediction_data, f)
            file_path = f.name
        
        try:
            parser = PredictionParser()
            with patch('src.infra.PredictionParser.magic_from') as mock_magic:
                mock_magic.return_value = 123456789
                
                result = parser.parse_json_file(file_path)
                
                assert len(result) == 1
                pred = result[0]
                assert pred.symbol == "EURUSD"
                assert pred.last_training_day == date(2025, 10, 14)
                assert pred.last_close_price == 1.0845
                assert pred.n_trading_days == 5
                assert pred.score == 0.73
                assert pred.magic == 123456789
                assert pred.sl_pct == 0.05
                assert pred.tp_pct == 0.10
                assert pred.source == Path(file_path).name
        finally:
            Path(file_path).unlink()
    
    def test_parse_json_file_multiple_predictions(self):
        """Test parse_json_file with multiple predictions."""
        prediction_data = [
            {
                "symbol": "EURUSD",
                "last_training_day": "2025-10-14T00:00:00Z",
                "last_close_price": 1.0845,
                "n_trading_days": 5,
                "score": 0.73
            },
            {
                "symbol": "GBPJPY",
                "last_training_day": "2025-10-15T00:00:00Z",
                "last_close_price": 189.45,
                "n_trading_days": 3,
                "score": 0.82
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(prediction_data, f)
            file_path = f.name
        
        try:
            parser = PredictionParser()
            with patch('src.infra.PredictionParser.magic_from') as mock_magic:
                mock_magic.side_effect = [123456789, 987654321]
                
                result = parser.parse_json_file(file_path)
                
                assert len(result) == 2
                
                pred1 = result[0]
                assert pred1.symbol == "EURUSD"
                assert pred1.magic == 123456789
                
                pred2 = result[1]
                assert pred2.symbol == "GBPJPY"
                assert pred2.magic == 987654321
        finally:
            Path(file_path).unlink()
    
    def test_parse_json_file_missing_required_field(self):
        """Test parse_json_file with missing required field."""
        prediction_data = {
            "symbol": "EURUSD",
            # Missing last_training_day
            "last_close_price": 1.0845,
            "n_trading_days": 5,
            "score": 0.73
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(prediction_data, f)
            file_path = f.name
        
        try:
            parser = PredictionParser()
            
            with pytest.raises(ValueError, match="Missing required fields: \\['last_training_day'\\]"):
                parser.parse_json_file(file_path)
        finally:
            Path(file_path).unlink()
    
    def test_parse_json_file_multiple_missing_fields(self):
        """Test parse_json_file with multiple missing required fields."""
        prediction_data = {
            "symbol": "EURUSD",
            # Missing last_training_day, n_trading_days, score
            "last_close_price": 1.0845
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(prediction_data, f)
            file_path = f.name
        
        try:
            parser = PredictionParser()
            
            with pytest.raises(ValueError, match="Missing required fields"):
                parser.parse_json_file(file_path)
        finally:
            Path(file_path).unlink()
    
    def test_parse_json_file_nonexistent_file(self):
        """Test parse_json_file with nonexistent file."""
        parser = PredictionParser()
        
        with pytest.raises(FileNotFoundError, match="Prediction file not found"):
            parser.parse_json_file("nonexistent_file.json")
    
    def test_parse_json_file_invalid_json(self):
        """Test parse_json_file with invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{ invalid json content")
            file_path = f.name
        
        try:
            parser = PredictionParser()
            
            with pytest.raises(json.JSONDecodeError):
                parser.parse_json_file(file_path)
        finally:
            Path(file_path).unlink()
    
    def test_parse_json_file_invalid_data_type(self):
        """Test parse_json_file with invalid data type (not dict or list)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump("invalid_string_data", f)
            file_path = f.name
        
        try:
            parser = PredictionParser()
            
            with pytest.raises(ValueError, match="JSON data must be a dict or list of dicts"):
                parser.parse_json_file(file_path)
        finally:
            Path(file_path).unlink()
    
    def test_parse_json_file_list_with_invalid_item(self):
        """Test parse_json_file with list containing invalid item."""
        prediction_data = [
            {
                "symbol": "EURUSD",
                "last_training_day": "2025-10-14T00:00:00Z",
                "last_close_price": 1.0845,
                "n_trading_days": 5,
                "score": 0.73
            },
            "invalid_string_item"  # Invalid item type
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(prediction_data, f)
            file_path = f.name
        
        try:
            parser = PredictionParser()
            
            with pytest.raises(ValueError, match="Each prediction must be a dict"):
                parser.parse_json_file(file_path)
        finally:
            Path(file_path).unlink()
    
    def test_parse_json_file_optional_fields_none(self):
        """Test parse_json_file with optional fields set to None."""
        prediction_data = {
            "symbol": "EURUSD",
            "last_training_day": "2025-10-14T00:00:00Z",
            "last_close_price": 1.0845,
            "n_trading_days": 5,
            "score": 0.73,
            "sl_pct": None,
            "tp_pct": None
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(prediction_data, f)
            file_path = f.name
        
        try:
            parser = PredictionParser()
            with patch('src.infra.PredictionParser.magic_from') as mock_magic:
                mock_magic.return_value = 123456789
                
                result = parser.parse_json_file(file_path)
                
                assert len(result) == 1
                pred = result[0]
                assert pred.sl_pct is None
                assert pred.tp_pct is None
        finally:
            Path(file_path).unlink()
    
    def test_parse_json_file_optional_fields_as_strings(self):
        """Test parse_json_file with optional fields as string numbers."""
        prediction_data = {
            "symbol": "EURUSD",
            "last_training_day": "2025-10-14T00:00:00Z",
            "last_close_price": 1.0845,
            "n_trading_days": 5,
            "score": 0.73,
            "sl_pct": "0.05",  # String number
            "tp_pct": "0.10"   # String number
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(prediction_data, f)
            file_path = f.name
        
        try:
            parser = PredictionParser()
            with patch('src.infra.PredictionParser.magic_from') as mock_magic:
                mock_magic.return_value = 123456789
                
                result = parser.parse_json_file(file_path)
                
                assert len(result) == 1
                pred = result[0]
                assert pred.sl_pct == 0.05
                assert pred.tp_pct == 0.10
        finally:
            Path(file_path).unlink()
    
    def test_parse_json_file_pathlib_path_input(self):
        """Test parse_json_file with pathlib.Path input."""
        prediction_data = {
            "symbol": "EURUSD",
            "last_training_day": "2025-10-14T00:00:00Z",
            "last_close_price": 1.0845,
            "n_trading_days": 5,
            "score": 0.73
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(prediction_data, f)
            file_path = Path(f.name)
        
        try:
            parser = PredictionParser()
            with patch('src.infra.PredictionParser.magic_from') as mock_magic:
                mock_magic.return_value = 123456789
                
                result = parser.parse_json_file(file_path)
                
                assert len(result) == 1
                pred = result[0]
                assert pred.symbol == "EURUSD"
                assert pred.source == file_path.name
        finally:
            file_path.unlink()
    
    def test_parse_json_file_edge_case_zero_values(self):
        """Test parse_json_file with zero values."""
        prediction_data = {
            "symbol": "TEST",
            "last_training_day": "2025-01-01T00:00:00Z",
            "last_close_price": 0.0,
            "n_trading_days": 0,
            "score": 0.0,
            "sl_pct": 0.0,
            "tp_pct": 0.0
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(prediction_data, f)
            file_path = f.name
        
        try:
            parser = PredictionParser()
            with patch('src.infra.PredictionParser.magic_from') as mock_magic:
                mock_magic.return_value = 0
                
                result = parser.parse_json_file(file_path)
                
                assert len(result) == 1
                pred = result[0]
                assert pred.symbol == "TEST"
                assert pred.last_close_price == 0.0
                assert pred.n_trading_days == 0
                assert pred.score == 0.0
                assert pred.sl_pct == 0.0
                assert pred.tp_pct == 0.0
        finally:
            Path(file_path).unlink()