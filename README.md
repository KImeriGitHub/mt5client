# DarwinEx Client

A Python client library for connecting to and interacting with Darwinex MetaTrader 5 platform for algorithmic trading.

## Description

DarwinExClient is a Python wrapper around MetaTrader 5 (MT5) that provides easy-to-use functions for connecting to Darwinex Zero accounts and performing trading operations. The library offers both headless and GUI modes for MT5 initialization, and uses modern data processing libraries like Polars for efficient data handling.

### Features

- **Secure Connection Management**: Uses YAML-based credential storage for secure account authentication
- **Flexible Initialization**: Supports both headless and GUI modes for MT5 connection
- **Modern Data Handling**: Leverages Polars DataFrames for fast and efficient data processing
- **Comprehensive Trading Actions**: Get positions, orders, and perform various trading operations
- **Robust Testing**: Includes comprehensive test suite with pytest
- **Type Safety**: Uses type hints for better code reliability

## Requirements

- Python 3.8+
- Windows OS (MetaTrader 5 requirement)
- Darwinex MetaTrader 5 installed
- Valid Darwinex Zero account credentials

## Installation

1. Clone this repository:
```bash
git clone https://gitlab.com/kimeri/darwinexclient.git
cd darwinexclient
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your credentials:
   - Create a `secrets/mt5_acc_cred.yaml` file
   - Add your account credentials:
   ```yaml
   darwinexzero_acc:
     apilogin: "your_login_number"
     apipw: "your_password"
     server: "your_server"
   ```

## Usage

### Basic Connection

```python
from src.mt_init import mt5_init

# Initialize MT5 connection in headless mode
if mt5_init(headless=True):
    print("Connected successfully!")
else:
    print("Connection failed!")
```

### Getting Market Data

```python
from src.mt_actions import get_position_df, get_orders_df

# Get current positions as Polars DataFrame
positions = get_position_df()
print(positions)

# Get pending orders
orders = get_orders_df()
print(orders)
```

### Alternative Import (using package)

```python
# Import from the package directly
from src import mt5_init, get_position_df, get_orders_df

# Use the functions
if mt5_init(headless=True):
    positions = get_position_df()
    orders = get_orders_df()
```

### Project Structure

```
darwinexclient/
├── src/                # Source code package
│   ├── __init__.py    # Package initialization
│   ├── mt_init.py     # MT5 initialization and connection management
│   └── mt_actions.py  # Trading actions and data retrieval functions
├── tests/             # Test suite
│   ├── __init__.py
│   ├── conftest.py    # Shared test fixtures
│   ├── test_mt_init.py      # MT5 initialization tests
│   └── test_mt_actions.py   # Trading actions tests
├── logs/              # Test run logs (timestamped)
├── secrets/           # Credential storage (not tracked in git)
│   ├── mt5_acc_cred.yaml
│   └── mt5_config.ini
├── run_tests.py       # Enhanced test runner with logging
├── requirements.txt   # Python dependencies
├── pytest.ini        # Test configuration
└── README.md          # Project documentation
```

## Testing

The project includes comprehensive unit tests for all major components with integrated logging functionality.

### Logging

The test runner automatically creates detailed logs for each test run:
- **Log Location**: `logs/test_run_YYYYMMDD_HHMMSS.log`
- **Dual Output**: Logs appear both in console and log file
- **Structured Format**: Timestamped entries with log levels
- **Complete Coverage**: Captures all pytest output and custom test messages

### Running Tests

**Option 1: Using the test runner script (Recommended)**
```bash
python run_tests.py                        # Run all tests with logging
python run_tests.py test_mt_init.py       # Run specific test file
python run_tests.py tests/test_mt_actions.py  # Also accepts full path
python run_tests.py -k "pattern" -- -x    # Pass extra pytest args after '--'
```

**Option 2: Using pytest directly**
```bash
pytest                                     # Run all tests
pytest -v                                  # Run with verbose output
pytest tests/test_mt_init.py -v           # Run specific test file
```

### Test Structure

- `tests/test_mt_init.py` - Tests for MT5 initialization and connection
- `tests/test_mt_actions.py` - Tests for data retrieval functions  
- `tests/conftest.py` - Shared test configuration and fixtures
- `run_tests.py` - Enhanced test runner script with logging
- `logs/` - Test run logs with timestamps

### Test Features

- **Comprehensive Logging**: All test runs are logged to timestamped files in `logs/` folder
- **Mocking**: Tests use mock objects to simulate MetaTrader5 without requiring installation
- **Fixtures**: Reusable test data and configuration via pytest fixtures
- **Conditional Tests**: Real credential tests are skipped if secrets file is missing
- **Error Handling**: Tests verify proper error handling and edge cases
- **In-Process Execution**: Test runner uses in-process pytest execution for better integration

## Configuration

The library uses a YAML configuration file for storing credentials securely. Make sure to:

1. Never commit your `secrets/` folder to version control
2. Update the MT5 installation path in `secrets/`.

## Dependencies

Key dependencies include:
- `MetaTrader5`: Official MT5 Python API
- `polars`: Fast DataFrame library for data processing
- `pandas`: Alternative DataFrame library
- `PyYAML`: YAML file parsing
- `pytest`: Testing framework

See `requirements.txt` for the complete list.

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

## Support

For issues and questions:
- Open an issue in the GitLab repository
- Check the MetaTrader 5 Python API documentation
- Review the test files for usage examples

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Authors

- **kimeri** - Initial work

## Acknowledgments

- Darwinex for providing the MetaTrader 5 platform
- MetaQuotes Software Corp. for the MT5 Python API
- The Polars team for the excellent DataFrame library
