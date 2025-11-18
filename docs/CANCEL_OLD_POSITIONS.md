# Cancel Old Positions Script

## Table of Contents
- [Overview](#overview)
- [Purpose](#purpose)
- [Usage](#usage)
- [How It Works](#how-it-works)
- [Safety Features](#safety-features)
- [Output Files](#output-files)
- [Testing](#testing)
- [Integration](#integration-with-existing-workflow)

## Overview

This script (`cancel_old_positions.py`) automatically closes trading positions that are based on old or expired predictions. It provides a safe and automated way to clean up positions that are no longer aligned with the latest trading predictions.

## Purpose

The script identifies and closes positions that meet these criteria:
- Positions with magic numbers (indicating they were created by the prediction system)
- Positions whose symbols are **NOT** present in the latest prediction set
- This indicates the position is from an old prediction that's no longer active

## Usage

### Dry Run (Safe Testing)
```bash
# Development environment (uses dev predictions and artifacts)
python cancel_old_positions.py --account mt5demo_acc_usd --config config/trading_config_dev.yaml

# Production environment (dry run)
python cancel_old_positions.py --account mt5demo_acc_usd --config config/trading_config_prod.yaml
```

### Live Execution (Actually Close Positions)
```bash
# Production environment (live execution)
python cancel_old_positions.py --account mt5demo_acc_usd --config config/trading_config_prod.yaml --apply
```

### PowerShell Execution
```powershell
# From PowerShell (Windows)
python .\cancel_old_positions.py --account mt5demo_acc_usd --config config\trading_config_prod.yaml --apply
```

### Parameters

- `--account`: **Required** - Account key from credentials YAML file (e.g., 'mt5demo_acc_usd')
- `--group`: Optional - Group filter for predictions (default: 'mt5')
- `--config`: Configuration file path (default: 'config/trading_config_prod.yaml')
- `--apply`: If specified, positions will actually be closed. Without this flag, runs in dry-run mode

## How It Works

1. **Initialize MT5 Connection**: Connects to MetaTrader 5 using the specified account
2. **Load Current Positions**: Gets all open positions from MT5
3. **Load Latest Predictions**: Loads the newest prediction files
4. **Identify Candidates**: Finds positions whose symbols are not in latest predictions
5. **Validate Orders**: Uses `mtBase.order_check()` to validate closure requests
6. **Close Positions**: Uses `mtBase.place_market_order()` to execute closures (if `--apply` is used)
7. **Save Results**: Saves a JSON file with closure results in the artifacts directory

## Safety Features

- **Dry Run by Default**: Without `--apply` flag, no actual positions are closed
- **Order Validation**: Each closure request is validated before execution
- **Comprehensive Logging**: All actions are logged with detailed information
- **Result Tracking**: Results are saved to JSON files for audit trail
- **Magic Number Filtering**: Only closes positions created by the prediction system

## Output Files

Results are saved in the `artifacts/` directory:
- Dry run: `dry_run_closures_YYYYMMDD_HHMMSS[_suffix].json`
- Live run: `closed_positions_YYYYMMDD_HHMMSS[_suffix].json`

## Testing

The script includes comprehensive integration tests:

```bash
# Run integration tests
python run_integ_tests.py

# Run unit tests
python run_unit_tests.py

# Run specific cancel old positions tests
python -m pytest tests/integ_tests/test_cancel_old_positions.py -v
```

## Troubleshooting

### Common Issues

1. **"No market access"**: Ensure MT5 is running and markets are open
2. **"Invalid account"**: Check your credentials in `secrets/mt5_acc_cred.yaml`
3. **"No positions found"**: Verify you have open positions with magic numbers
4. **"Configuration error"**: Validate your config file using `python test_config.py`

### Debug Mode

For detailed debugging, use the development configuration which includes DEBUG logging:
```bash
python cancel_old_positions.py --account mt5demo_acc_usd --config config/trading_config_dev.yaml
```

## Integration with Existing Workflow

This script complements `place_prediction_orders.py`:
- `place_prediction_orders.py` - Opens new positions for current predictions
- `cancel_old_positions.py` - Closes old positions that are no longer relevant

Run this script periodically (e.g., daily) to clean up old positions before placing new ones.