# DarwinexClient Quick Start Guide

## Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Initial Setup](#initial-setup)
- [Configuration](#configuration)
- [Basic Workflow](#basic-workflow)
- [Development vs Production](#development-vs-production)
- [Common Commands](#common-commands)
- [Troubleshooting](#troubleshooting)
- [Next Steps](#next-steps)

## Overview

The DarwinexClient is an automated trading system that places orders based on machine learning predictions and manages positions through their lifecycle. The system consists of two main operations:

1. **Place Prediction Orders** - Creates new positions based on latest predictions
2. **Cancel Old Positions** - Closes positions that are no longer relevant

## Prerequisites

Before you begin, ensure you have:

- Python 3.8+ installed
- Windows OS (required for MetaTrader 5)
- DarwinEx MetaTrader 5 platform installed
- Valid DarwinEx account credentials
- Trading predictions in the correct JSON format

## Initial Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Credentials
Create your credentials file at `secrets/mt5_acc_cred.yaml`:
```yaml
mt5demo_acc_usd:
  server: "DarwinexZero-MT5Demo"
  login: your_login_number
  password: "your_password"
```

### 3. Configure MT5 Terminal
Ensure your MT5 configuration file exists at `secrets/mt5_config.ini` with appropriate settings.

### 4. Verify Installation
```bash
python test_config.py
```

## Configuration

The system uses YAML configuration files for different environments:

### Development Configuration
- File: `config/trading_config_dev.yaml`
- Purpose: Safe testing and development
- Features: Debug logging, conservative sizing, shorter timeouts

### Production Configuration
- File: `config/trading_config_prod.yaml`
- Purpose: Live trading
- Features: Standard logging, full sizing, production timeouts

## Basic Workflow

### 1. Prepare Predictions
Create prediction files in JSON format and place them in:
- Development: `predictions/dev/`
- Production: `predictions/`

Example filename: `prediction_mt5_18nov2025_001.json`

### 2. Place Orders (Development Testing)
```bash
# Dry run with development config
python place_prediction_orders.py --account mt5demo_acc_usd --config config/trading_config_dev.yaml
```

### 3. Place Orders (Production)
```bash
# Live trading with production config
python place_prediction_orders.py --account mt5demo_acc_usd --config config/trading_config_prod.yaml --apply
```

### 4. Clean Up Old Positions
```bash
# Cancel old positions (dry run)
python cancel_old_positions.py --account mt5demo_acc_usd --config config/trading_config_prod.yaml

# Cancel old positions (live)
python cancel_old_positions.py --account mt5demo_acc_usd --config config/trading_config_prod.yaml --apply
```

## Development vs Production

| Aspect | Development | Production |
|--------|-------------|------------|
| **Config File** | `trading_config_dev.yaml` | `trading_config_prod.yaml` |
| **Predictions** | `predictions/dev/` | `predictions/` |
| **Artifacts** | `artifacts/dev/` | `artifacts/` |
| **Logging** | DEBUG level | INFO level |
| **Timeouts** | Shorter (15 min) | Standard (30 min) |
| **Position Sizing** | Conservative | Full |
| **Safety** | Extra validation | Production ready |

## Common Commands

### Testing and Validation
```bash
# Run all unit tests
python run_unit_tests.py

# Run integration tests
python run_integ_tests.py

# Validate configuration
python test_config.py

# Validate specific prediction file
python -c "from src.infra.PredictionClient import PredictionClient; pc = PredictionClient('predictions/dev'); print('Validation passed')"
```

### Trading Operations
```bash
# Development dry run
python place_prediction_orders.py --account mt5demo_acc_usd --config config/trading_config_dev.yaml

# Production dry run
python place_prediction_orders.py --account mt5demo_acc_usd --config config/trading_config_prod.yaml

# Production live trading
python place_prediction_orders.py --account mt5demo_acc_usd --config config/trading_config_prod.yaml --apply

# Clean up old positions
python cancel_old_positions.py --account mt5demo_acc_usd --config config/trading_config_prod.yaml --apply
```

### Monitoring and Logs
```bash
# View recent logs
Get-Content logs\*.log -Tail 50

# Monitor artifacts
dir artifacts\*.json | Sort-Object LastWriteTime -Descending | Select-Object -First 5
```

## Troubleshooting

### Common Issues

**"No market access"**
- Ensure MetaTrader 5 is running
- Check markets are open
- Verify account credentials

**"Configuration error"**
- Run `python test_config.py`
- Check file paths in configuration
- Verify all required files exist

**"No predictions found"**
- Check predictions directory contains files
- Verify filename format matches pattern
- Ensure JSON syntax is valid

**"Invalid credentials"**
- Verify credentials file exists: `secrets/mt5_acc_cred.yaml`
- Check account login and password
- Ensure server name is correct

### Debug Mode

For detailed troubleshooting, use development configuration:
```bash
python place_prediction_orders.py --account mt5demo_acc_usd --config config/trading_config_dev.yaml
```

This enables DEBUG logging and provides detailed information about each step.

### Log Files

Logs are stored in the `logs/` directory:
- Development logs: `logs/dev/`
- Production logs: `logs/`

Check these files for detailed error information and system behavior.

## Next Steps

### For New Users
1. Start with development configuration
2. Test with small prediction files
3. Verify orders in MT5 terminal
4. Gradually increase to full predictions

### For Production Use
1. Thoroughly test in development first
2. Validate all prediction files
3. Monitor initial trades closely
4. Set up regular position cleanup

### Advanced Features
- Explore configuration customization
- Set up automated scheduling
- Implement monitoring and alerting
- Review risk management parameters

## Documentation References

- [Configuration System](CONFIGURATION.md) - Detailed configuration options
- [Prediction File Format](PREDICTION_FILE_FORMAT.md) - JSON structure and validation
- [Cancel Old Positions](CANCEL_OLD_POSITIONS.md) - Position cleanup process

For technical support or questions, review the logs and documentation, or run the integration tests to validate your setup.