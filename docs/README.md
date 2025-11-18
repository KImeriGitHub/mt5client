# DarwinexClient Documentation Index

Welcome to the DarwinexClient documentation. This automated trading system places orders based on machine learning predictions and manages trading positions through their complete lifecycle.

## Documentation Overview

### 🚀 Getting Started
- **[Quick Start Guide](QUICK_START_GUIDE.md)** - Essential setup and basic workflow
  - Initial setup and prerequisites
  - Development vs production environments
  - Common commands and troubleshooting

### ⚙️ Configuration
- **[Configuration System](CONFIGURATION.md)** - Complete configuration reference
  - YAML-based configuration system
  - Environment-specific settings
  - Configuration validation and best practices

### 📊 Data Format
- **[Prediction File Format](PREDICTION_FILE_FORMAT.md)** - JSON structure specification
  - File naming conventions
  - Required and optional fields
  - Validation and troubleshooting

### 🔄 Operations
- **[Cancel Old Positions](CANCEL_OLD_POSITIONS.md)** - Position cleanup process
  - Automated position management
  - Safety features and validation
  - Integration with prediction workflow

## Quick Navigation

### For New Users
1. Start with [Quick Start Guide](QUICK_START_GUIDE.md)
2. Review [Configuration System](CONFIGURATION.md) for setup
3. Understand [Prediction File Format](PREDICTION_FILE_FORMAT.md) for data preparation

### For Existing Users
- **Configuration Issues**: See [Configuration System](CONFIGURATION.md#troubleshooting)
- **Prediction Problems**: Check [Prediction File Format](PREDICTION_FILE_FORMAT.md#troubleshooting)
- **Position Management**: Review [Cancel Old Positions](CANCEL_OLD_POSITIONS.md#safety-features)

### For Developers
- **System Architecture**: Review all documentation for complete understanding
- **Configuration Schema**: See [Configuration System](CONFIGURATION.md#configuration-schema-reference)
- **Testing**: Follow testing procedures in [Quick Start Guide](QUICK_START_GUIDE.md#testing-and-validation)

## System Components

### Core Scripts
- `place_prediction_orders.py` - Main trading script for placing new orders
- `cancel_old_positions.py` - Position cleanup and risk management

### Configuration
- `config/trading_config_dev.yaml` - Development environment settings
- `config/trading_config_prod.yaml` - Production environment settings

### Data Directories
- `predictions/` - Production prediction files
- `predictions/dev/` - Development prediction files
- `artifacts/` - Trading results and logs
- `logs/` - System logs and debugging information

## Environment Setup

### Development Environment
- Safe testing with conservative parameters
- Debug logging for detailed troubleshooting
- Separate directories for predictions and artifacts
- Shorter timeouts for faster iteration

### Production Environment
- Live trading with full parameters
- Standard logging for clean operation
- Production directories for real trading
- Appropriate timeouts for market conditions

## Safety Features

The system includes multiple safety mechanisms:

1. **Dry Run Mode** - Test operations without executing trades
2. **Configuration Validation** - Validate settings before execution
3. **Order Validation** - Check each order before placement
4. **Magic Number Tracking** - Only manage system-created positions
5. **Comprehensive Logging** - Full audit trail of all operations

## Support and Troubleshooting

### Common Issues
- **Market Access**: Ensure MT5 is running and markets are open
- **Configuration**: Run `python test_config.py` to validate setup
- **Predictions**: Verify JSON format and required fields
- **Credentials**: Check account settings in credentials file

### Testing Commands
```bash
# Validate configuration
python test_config.py

# Run unit tests
python run_unit_tests.py

# Run integration tests
python run_integ_tests.py
```

### Debug Mode
Use development configuration for detailed logging:
```bash
python place_prediction_orders.py --account mt5demo_acc_usd --config config/trading_config_dev.yaml
```

## Best Practices

### Development Workflow
1. Always test in development environment first
2. Validate prediction files before use
3. Run dry runs before live execution
4. Monitor logs for any issues

### Production Deployment
1. Thoroughly test all components in development
2. Validate configuration with `test_config.py`
3. Start with small prediction sets
4. Monitor initial trades closely

### Risk Management
1. Use appropriate stop loss and take profit levels
2. Regularly clean up old positions
3. Monitor position sizes and exposure
4. Keep detailed logs for audit purposes

## Version Information

This documentation is current as of November 2025 and reflects the latest system features and configuration options.

## Additional Resources

- **System Tests**: See `tests/` directory for comprehensive test coverage
- **Example Files**: Check `artifacts/dev/` for sample outputs
- **Configuration Examples**: Review existing config files in `config/` directory

---

For technical support, review the relevant documentation section and check the system logs for detailed error information.