"""Configuration loader for trading application."""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any, Dict, Optional
import yaml


class TradingConfig:
    """Configuration loader and validator for trading parameters."""
    
    def __init__(self, config_path: str | Path) -> None:
        """Initialize configuration loader.
        
        Args:
            config_path: Path to the YAML configuration file
        """
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                self._config = yaml.safe_load(file)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML configuration: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to load configuration: {e}") from e
    
    def _get_nested(self, keys: str, default: Any = None) -> Any:
        """Get nested configuration value using dot notation.
        
        Args:
            keys: Dot-separated key path (e.g., 'trading.max_working_duration_minutes')
            default: Default value if key is not found
            
        Returns:
            Configuration value or default
        """
        value = self._config
        for key in keys.split('.'):
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    # Path properties
    @property
    def credentials_path(self) -> str:
        """Path to MT5 credentials YAML file."""
        return self._get_nested('paths.credentials', 'secrets/mt5_acc_cred.yaml')
    
    @property
    def mt5_config_path(self) -> str:
        """Path to MT5 configuration INI file."""
        return self._get_nested('paths.mt5_config', 'secrets/mt5_config.ini')
    
    @property
    def predictions_dir(self) -> str:
        """Directory containing prediction files."""
        return self._get_nested('paths.predictions_dir', 'predictions')
    
    @property
    def artifacts_dir(self) -> str:
        """Directory for storing output artifacts."""
        return self._get_nested('paths.artifacts_dir', 'artifacts')
    
    # Trading properties
    @property
    def max_working_duration(self) -> datetime.timedelta:
        """Maximum time to work on placing orders."""
        minutes = self._get_nested('trading.max_working_duration_minutes', 30)
        return datetime.timedelta(minutes=minutes)
    
    @property
    def per_day_divisor(self) -> int:
        """Maximum number of days to divide equity across."""
        return self._get_nested('trading.per_day_divisor', 3)
    
    @property
    def max_budget_discrepancy(self) -> float:
        """Maximum allowed budget discrepancy tolerance."""
        return self._get_nested('trading.max_budget_discrepancy', 0.1)
    
    # Market access properties
    @property
    def max_market_access_duration_seconds(self) -> int:
        """Maximum time to wait for market access."""
        return self._get_nested('market_access.max_market_access_duration_seconds', 5)
    
    @property
    def max_tick_age_seconds(self) -> int:
        """Maximum age of tick data to consider valid."""
        return self._get_nested('market_access.max_tick_age_seconds', 5)
    
    # Logging properties
    @property
    def log_level(self) -> str:
        """Logging level."""
        return self._get_nested('logging.level', 'INFO')
    
    @property
    def log_format(self) -> str:
        """Logging format string."""
        return self._get_nested('logging.format', '%(asctime)s - %(levelname)s - %(message)s')
    
    @property
    def log_datefmt(self) -> str:
        """Logging date format."""
        return self._get_nested('logging.datefmt', '%Y-%m-%d %H:%M')
    
    @property
    def log_dir(self) -> str:
        """Log file directory."""
        return self._get_nested('logging.log_dir', 'logs')
    
    def validate(self) -> None:
        """Validate configuration values."""
        # Validate paths exist
        credentials_path = Path(self.credentials_path)
        if not credentials_path.exists():
            raise FileNotFoundError(f"Credentials file not found: {credentials_path}")
        
        mt5_config_path = Path(self.mt5_config_path)
        if not mt5_config_path.exists():
            raise FileNotFoundError(f"MT5 config file not found: {mt5_config_path}")
        
        predictions_dir = Path(self.predictions_dir)
        if not predictions_dir.exists():
            raise FileNotFoundError(f"Predictions directory not found: {predictions_dir}")
        
        # Validate numeric values
        if self.per_day_divisor <= 0:
            raise ValueError("per_day_divisor must be positive")
        
        if self.max_budget_discrepancy < 0:
            raise ValueError("max_budget_discrepancy must be non-negative")
        
        if self.max_market_access_duration_seconds <= 0:
            raise ValueError("max_market_access_duration_seconds must be positive")
        
        if self.max_tick_age_seconds <= 0:
            raise ValueError("max_tick_age_seconds must be positive")
        
    def __repr__(self) -> str:
        """String representation of configuration."""
        return f"TradingConfig(config_path='{self.config_path}')"