"""Unit tests for TradingConfig.py TradingConfig class."""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, mock_open
import datetime

from src.infra.TradingConfig import TradingConfig


class TestTradingConfig:
    """Test cases for TradingConfig class."""
    
    def test_init_file_not_found(self):
        """Test initialization with non-existent config file."""
        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            TradingConfig("nonexistent.yaml")
    
    def test_init_invalid_yaml(self):
        """Test initialization with invalid YAML content."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content:")
            config_path = f.name
        
        try:
            with pytest.raises(ValueError, match="Invalid YAML configuration"):
                TradingConfig(config_path)
        finally:
            Path(config_path).unlink()
    
    def test_init_valid_config(self):
        """Test initialization with valid config file."""
        config_data = {
            'paths': {
                'credentials': 'test_creds.yaml',
                'mt5_config': 'test_mt5.ini'
            },
            'trading': {
                'max_working_duration_minutes': 45,
                'per_day_divisor': 5
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            config = TradingConfig(config_path)
            assert config.config_path == Path(config_path)
            assert config._config == config_data
        finally:
            Path(config_path).unlink()
    
    def test_get_nested_existing_key(self):
        """Test _get_nested with existing nested key."""
        config_data = {
            'level1': {
                'level2': {
                    'value': 'test_value'
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            config = TradingConfig(config_path)
            result = config._get_nested('level1.level2.value')
            assert result == 'test_value'
        finally:
            Path(config_path).unlink()
    
    def test_get_nested_missing_key_with_default(self):
        """Test _get_nested with missing key and default value."""
        config_data = {'existing': 'value'}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            config = TradingConfig(config_path)
            result = config._get_nested('missing.key', 'default_value')
            assert result == 'default_value'
        finally:
            Path(config_path).unlink()
    
    def test_get_nested_missing_key_no_default(self):
        """Test _get_nested with missing key and no default."""
        config_data = {'existing': 'value'}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            config = TradingConfig(config_path)
            result = config._get_nested('missing.key')
            assert result is None
        finally:
            Path(config_path).unlink()
    
    def test_credentials_path_property(self):
        """Test credentials_path property."""
        config_data = {
            'paths': {
                'credentials': 'custom_creds.yaml'
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            config = TradingConfig(config_path)
            assert config.credentials_path == 'custom_creds.yaml'
        finally:
            Path(config_path).unlink()
    
    def test_credentials_path_property_default(self):
        """Test credentials_path property with default value."""
        config_data = {}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            config = TradingConfig(config_path)
            assert config.credentials_path == 'secrets/mt5_acc_cred.yaml'
        finally:
            Path(config_path).unlink()
    
    def test_max_working_duration_property(self):
        """Test max_working_duration property."""
        config_data = {
            'trading': {
                'max_working_duration_minutes': 45
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            config = TradingConfig(config_path)
            expected = datetime.timedelta(minutes=45)
            assert config.max_working_duration == expected
        finally:
            Path(config_path).unlink()
    
    def test_max_working_duration_property_default(self):
        """Test max_working_duration property with default value."""
        config_data = {}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            config = TradingConfig(config_path)
            expected = datetime.timedelta(minutes=30)
            assert config.max_working_duration == expected
        finally:
            Path(config_path).unlink()
    
    def test_per_day_divisor_property(self):
        """Test per_day_divisor property."""
        config_data = {
            'trading': {
                'per_day_divisor': 7
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            config = TradingConfig(config_path)
            assert config.per_day_divisor == 7
        finally:
            Path(config_path).unlink()
    
    def test_max_budget_discrepancy_property(self):
        """Test max_budget_discrepancy property."""
        config_data = {
            'trading': {
                'max_budget_discrepancy': 0.25
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            config = TradingConfig(config_path)
            assert config.max_budget_discrepancy == 0.25
        finally:
            Path(config_path).unlink()
    
    def test_logging_properties(self):
        """Test logging-related properties."""
        config_data = {
            'logging': {
                'level': 'DEBUG',
                'format': 'custom format',
                'datefmt': '%Y-%m-%d',
                'log_dir': 'custom_logs'
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            config = TradingConfig(config_path)
            assert config.log_level == 'DEBUG'
            assert config.log_format == 'custom format'
            assert config.log_datefmt == '%Y-%m-%d'
            assert config.log_dir == 'custom_logs'
        finally:
            Path(config_path).unlink()
    
    def test_validate_missing_files(self):
        """Test validate method with missing files."""
        config_data = {
            'paths': {
                'credentials': 'nonexistent_creds.yaml',
                'mt5_config': 'nonexistent_mt5.ini',
                'predictions_dir': 'nonexistent_dir'
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            config = TradingConfig(config_path)
            with pytest.raises(FileNotFoundError, match="Credentials file not found"):
                config.validate()
        finally:
            Path(config_path).unlink()
    
    def test_validate_invalid_numeric_values(self):
        """Test validate method with invalid numeric values."""
        config_data = {
            'trading': {
                'per_day_divisor': -1
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            config = TradingConfig(config_path)
            with pytest.raises(ValueError, match="per_day_divisor must be positive"):
                config.validate()
        finally:
            Path(config_path).unlink()
    
    def test_validate_negative_max_budget_discrepancy(self):
        """Test validate method with negative max_budget_discrepancy."""
        config_data = {
            'trading': {
                'max_budget_discrepancy': -0.1
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            config = TradingConfig(config_path)
            with pytest.raises(ValueError, match="max_budget_discrepancy must be non-negative"):
                config.validate()
        finally:
            Path(config_path).unlink()
    
    def test_repr(self):
        """Test string representation."""
        config_data = {}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            config = TradingConfig(config_path)
            expected = f"TradingConfig(config_path='{config_path}')"
            assert repr(config) == expected
        finally:
            Path(config_path).unlink()
    
    def test_pathlib_path_input(self):
        """Test initialization with pathlib.Path input."""
        config_data = {'test': 'value'}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)
        
        try:
            config = TradingConfig(config_path)
            assert config.config_path == config_path
            assert config._config == config_data
        finally:
            config_path.unlink()
    
    @patch('builtins.open', side_effect=IOError("Permission denied"))
    def test_init_file_access_error(self, mock_file):
        """Test initialization with file access error."""
        # Create a real file first to pass the exists() check
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_path = f.name
        
        try:
            with pytest.raises(RuntimeError, match="Failed to load configuration"):
                TradingConfig(config_path)
        finally:
            Path(config_path).unlink()