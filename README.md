# DarwinexClient - Automated Trading System

An automated trading system that places orders based on machine learning predictions and manages trading positions through their complete lifecycle using the Darwinex MetaTrader 5 platform.

## Description

DarwinexClient is a comprehensive automated trading system that connects to Darwinex MetaTrader 5 accounts to execute trades based on machine learning predictions. The system automatically places orders for new predictions, manages existing positions, and closes outdated positions to maintain a clean and efficient trading portfolio.

### Features

- **Automated Trading**: Places orders based on machine learning predictions automatically
- **Position Management**: Tracks and manages trading positions through their lifecycle
- **Risk Management**: Built-in stop loss and take profit handling
- **Configuration System**: YAML-based configuration for different environments (dev/prod)
- **Safety Features**: Dry-run mode, order validation, and comprehensive logging
- **Environment Separation**: Separate configurations for development and production
- **Prediction Processing**: Handles JSON prediction files with validation
- **Position Cleanup**: Automatically closes old positions that are no longer relevant
- **Comprehensive Testing**: Unit and integration tests with pytest
- **Audit Trail**: Detailed logging and artifact generation for all operations

## Requirements

- Python 3.8+
- Windows OS (MetaTrader 5 requirement)
- Darwinex MetaTrader 5 installed and configured
- Valid Darwinex account credentials
- Machine learning prediction files in JSON format
- Virtual environment (recommended)

## Installation

1. Clone this repository:
```bash
git clone https://gitlab.com/kimeri/darwinexclient.git
cd darwinexclient
```

2. Create and activate a virtual environment:
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

3. Install the required dependencies:
```bash
pip install -r requirements.txt
```

4. Set up your credentials:
   - Create a `secrets/mt5_acc_cred.yaml` file
   - Add your account credentials:
   ```yaml
   mt5demo_acc_usd:
     server: "DarwinexZero-MT5Demo"
     login: your_login_number
     password: "your_password"
   ```

5. Configure MetaTrader 5:
   - Create `secrets/mt5_config.ini` with your MT5 terminal settings

6. Verify installation:
```bash
python test_config.py
```

## Usage

### Quick Start

**📚 For detailed instructions, see [docs/QUICK_START_GUIDE.md](docs/QUICK_START_GUIDE.md)**

### Basic Workflow

1. **Prepare Predictions**: Place your prediction JSON files in the appropriate directory
   - Development: `predictions/dev/`
   - Production: `predictions/`

2. **Test with Development Configuration**:
```bash
# Dry run (safe testing)
python place_prediction_orders.py --account mt5demo_acc_usd --config config/trading_config_dev.yaml
```

3. **Execute Live Trades**:
```bash
# Live trading (production)
python place_prediction_orders.py --account mt5demo_acc_usd --config config/trading_config_prod.yaml --apply
```

4. **Clean Up Old Positions**:
```bash
# Remove outdated positions
python cancel_old_positions.py --account mt5demo_acc_usd --config config/trading_config_prod.yaml --apply
```

### Key Commands

```bash
# Configuration validation
python test_config.py

# Run all tests
python run_unit_tests.py
python run_integ_tests.py

# Development dry run
python place_prediction_orders.py --account mt5demo_acc_usd --config config/trading_config_dev.yaml

# Production execution
python place_prediction_orders.py --account mt5demo_acc_usd --config config/trading_config_prod.yaml --apply
```

### Project Structure

```
darwinexclient/
├── src/                     # Core system modules
│   ├── infra/              # Infrastructure components
│   │   ├── OrderClient.py  # Order management
│   │   ├── PositionClient.py # Position management
│   │   ├── PredictionClient.py # Prediction processing
│   │   ├── TradingConfig.py # Configuration management
│   │   └── mtBase.py       # MetaTrader 5 interface
│   ├── common.py           # Common utilities
│   ├── finalize_predictions.py # Prediction processing
│   └── place_order.py      # Order execution
├── config/                  # Configuration files
│   ├── trading_config_dev.yaml  # Development settings
│   └── trading_config_prod.yaml # Production settings
├── docs/                    # Comprehensive documentation
│   ├── README.md           # Documentation index
│   ├── QUICK_START_GUIDE.md # Getting started guide
│   ├── CONFIGURATION.md    # Configuration reference
│   ├── PREDICTION_FILE_FORMAT.md # Data format specification
│   └── CANCEL_OLD_POSITIONS.md # Position management
├── predictions/             # Trading predictions
│   └── dev/                # Development predictions
├── artifacts/               # Trading results and logs
│   └── dev/                # Development artifacts
├── tests/                   # Comprehensive test suite
│   ├── unit_tests/         # Unit tests
│   └── integ_tests/        # Integration tests
├── secrets/                 # Credentials (not in git)
│   ├── mt5_acc_cred.yaml   # Account credentials
│   └── mt5_config.ini      # MT5 configuration
├── logs/                    # System logs
├── place_prediction_orders.py # Main trading script
├── cancel_old_positions.py    # Position cleanup script
├── run_unit_tests.py       # Unit test runner
├── run_integ_tests.py      # Integration test runner
└── test_config.py          # Configuration validator
```

## Testing

The system includes comprehensive unit and integration tests covering all major components.

### Test Suites

**Unit Tests** - Test individual components in isolation:
```bash
python run_unit_tests.py
```

**Integration Tests** - Test complete workflows with real configurations:
```bash
python run_integ_tests.py
```

**Configuration Tests** - Validate system configuration:
```bash
python test_config.py
```

### Test Structure

- `tests/unit_tests/` - Unit tests for individual components
- `tests/integ_tests/` - Integration tests for complete workflows
- `run_unit_tests.py` - Unit test runner with reporting
- `run_integ_tests.py` - Integration test runner
- `test_config.py` - Configuration validation

### Test Features

- **Environment Testing**: Tests both development and production configurations
- **Prediction Validation**: Tests prediction file processing and validation
- **Order Processing**: Tests order placement and validation logic
- **Position Management**: Tests position tracking and cleanup
- **Configuration Testing**: Validates all configuration parameters
- **Safety Testing**: Tests dry-run modes and validation features
- **Error Handling**: Comprehensive error scenario testing
- **Mock Integration**: Tests system behavior without requiring live MT5 connection

### Running Specific Tests

```bash
# Test specific functionality
python -m pytest tests/unit_tests/test_prediction_client.py -v
python -m pytest tests/integ_tests/test_place_prediction_orders.py -v

# Test with specific patterns
python -m pytest -k "test_order" -v
python -m pytest -k "test_config" -v
```

## Configuration

The system uses YAML-based configuration files for different environments:

### Environment Configurations

- **Development**: `config/trading_config_dev.yaml` - Safe testing with debug logging
- **Production**: `config/trading_config_prod.yaml` - Live trading configuration

### Key Configuration Areas

- **Trading Parameters**: Position sizing, timeouts, risk management
- **File Paths**: Predictions, artifacts, credentials, logs
- **Market Access**: Connection timeouts, retry settings
- **Logging**: Log levels, formats, output directories

### Security Best Practices

1. Never commit your `secrets/` folder to version control
2. Use environment-specific credentials
3. Regularly validate configuration with `python test_config.py`
4. Keep production and development configurations separate

**📚 For detailed configuration information, see [docs/CONFIGURATION.md](docs/CONFIGURATION.md)**

## Dependencies

Key dependencies include:
- `MetaTrader5`: Official MT5 Python API for trading operations
- `polars`: Fast DataFrame library for efficient data processing
- `PyYAML`: YAML configuration file parsing
- `pytest`: Comprehensive testing framework
- `argparse`: Command-line argument parsing
- `pathlib`: Modern path handling
- `datetime`: Date and time operations for trading logic

See `requirements.txt` for the complete list with specific versions.

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Run the test suite: `pytest`
5. Commit your changes: `git commit -am 'Add new feature'`
6. Push to the branch: `git push origin feature-name`
7. Submit a merge request

## Security

- Keep your `secrets/mt5_acc_cred.yaml` file secure and never share it
- Use environment variables or other secure methods for production deployments
- Regularly rotate your API credentials

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- **[Quick Start Guide](docs/QUICK_START_GUIDE.md)** - Get up and running quickly
- **[Configuration Reference](docs/CONFIGURATION.md)** - Complete configuration guide
- **[Prediction File Format](docs/PREDICTION_FILE_FORMAT.md)** - JSON format specification
- **[Position Management](docs/CANCEL_OLD_POSITIONS.md)** - Automated position cleanup
- **[Documentation Index](docs/README.md)** - Complete documentation overview

## Support

For issues and questions:
1. **Check Documentation**: Review the comprehensive docs in `docs/` directory
2. **Run Tests**: Use `python test_config.py` to validate your setup
3. **Check Logs**: Review logs in `logs/` directory for detailed error information
4. **Debug Mode**: Use development configuration for detailed debugging
5. **Integration Tests**: Run `python run_integ_tests.py` to test complete workflows

### Troubleshooting

Common issues and solutions:
- **Configuration errors**: Run `python test_config.py`
- **Market access issues**: Ensure MT5 is running and markets are open
- **Prediction format errors**: See [Prediction File Format docs](docs/PREDICTION_FILE_FORMAT.md)
- **Connection problems**: Verify credentials in `secrets/mt5_acc_cred.yaml`

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Authors

- **kimeri** - Initial work

## System Overview

DarwinexClient is designed for automated trading workflows:

1. **Prediction Processing** - Loads and validates ML prediction files
2. **Order Placement** - Converts predictions to market orders with risk management
3. **Position Management** - Tracks and manages active positions
4. **Position Cleanup** - Automatically closes outdated positions
5. **Risk Management** - Built-in stop loss and take profit handling
6. **Audit Trail** - Comprehensive logging and result tracking

### Workflow Integration

The system is designed to integrate with ML prediction pipelines:
- Accepts standardized JSON prediction format
- Processes predictions automatically
- Manages complete trade lifecycle
- Provides detailed reporting and logging

## Acknowledgments

- Darwinex for providing the MetaTrader 5 platform and Zero accounts
- MetaQuotes Software Corp. for the MT5 Python API
- The Polars team for efficient data processing capabilities
- Python community for excellent libraries and testing frameworks
