# Configuration System Documentation

## Overview

The trading application now uses a YAML-based configuration system that replaces all hard-coded constants. This makes the application more flexible, maintainable, and environment-specific.

## Configuration File Location

The default configuration file is located at:
```
config/trading_config.yaml
```

You can specify a custom configuration file using the `--config` command line argument:
```bash
python place_prediction_orders.py --account mt5demo_acc --config /path/to/custom_config.yaml
```

## Configuration Structure

### File Paths
```yaml
paths:
  credentials: "secrets/mt5_acc_cred.yaml"       # MT5 credentials file
  mt5_config: "secrets/mt5_config.ini"          # MT5 terminal configuration
  predictions_dir: "predictions"                # Directory containing predictions
```

### Trading Parameters
```yaml
trading:
  max_working_duration_minutes: 30              # Maximum time to place orders (minutes)
  per_day_divisor: 3                           # Equity divisor for position sizing
```

### Market Access Parameters
```yaml
market_access:
  max_market_access_duration_seconds: 5       # Max wait time for market access
```

### Logging Configuration
```yaml
logging:
  level: "INFO"                                # Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  format: "%(asctime)s - %(levelname)s - %(message)s"  # Log format
  datefmt: "%Y-%m-%d %H:%M"                    # Date format for logs
  log_dir: "logs"                              # Log file directory
```

## Using the Configuration

### In Python Code
```python
from src.infra.TradingConfig import TradingConfig

# Load configuration
config = TradingConfig("path/to/config.yaml")  # Config path is required

# Validate configuration
config.validate()

# Access configuration values
print(f"Max wait time: {config.max_market_access_duration_seconds}")
print(f"Log level: {config.log_level}")
```

### Command Line Usage
```bash
# Use default configuration
python place_prediction_orders.py --account mt5demo_acc

# Use custom configuration
python place_prediction_orders.py --account mt5demo_acc --config my_config.yaml
```

## Configuration Properties

The `TradingConfig` class provides the following properties:

### Path Properties
- `credentials_path`: Path to MT5 credentials YAML file
- `mt5_config_path`: Path to MT5 configuration INI file  
- `predictions_dir`: Directory containing prediction files

### Trading Properties
- `max_working_duration`: Maximum time to work on placing orders (timedelta)
- `per_day_divisor`: Maximum number of days to divide equity across (int)

### Market Access Properties
- `max_market_access_duration_seconds`: Maximum time to wait for market access (int)

### Logging Properties
- `log_level`: Logging level (str)
- `log_format`: Logging format string (str)
- `log_datefmt`: Logging date format (str)
- `log_dir`: Log file directory (str)

## Validation

The configuration system includes validation to ensure:

1. Required files exist (credentials, MT5 config, predictions directory)
2. Numeric values are positive
3. Configuration structure is valid

Call `config.validate()` to perform validation checks.

## Error Handling

The configuration system provides clear error messages for:

- Missing configuration files
- Invalid YAML syntax
- Missing required configuration sections
- Invalid configuration values
- Missing dependency files

## Migration from Hard-coded Values

### Before (Hard-coded)
```python
MAX_MARKET_ACCESS_DURATION_SECONDS = 5
CREDENTIALS_PATH = "secrets/mt5_acc_cred.yaml"
# ... other constants
```

### After (Configuration-based)
```python
config = TradingConfig()
max_wait = config.max_market_access_duration_seconds
credentials = config.credentials_path
```

## Benefits

1. **Flexibility**: Easy to change parameters without code modification
2. **Environment Support**: Different configs for dev/test/prod
3. **Validation**: Built-in validation prevents configuration errors
4. **Documentation**: Self-documenting YAML structure
5. **Maintainability**: Centralized configuration management

## Testing Configuration

Use the provided test script to verify your configuration:
```bash
python test_config.py
```

This will load and validate your configuration, displaying all current values.