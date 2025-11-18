#!/usr/bin/env python3
"""
Example usage of the new configuration system for place_prediction_orders.py

This script demonstrates how to use the trading configuration system.
"""

from src.infra.TradingConfig import TradingConfig

def main():
    """Demonstrate configuration usage."""
    
    # Load configuration
    try:
        config = TradingConfig("config/trading_config_prod.yaml")
        print("✅ Configuration loaded successfully!")
        
        # Display configuration values
        print("\n📁 File Paths:")
        print(f"  Credentials: {config.credentials_path}")
        print(f"  MT5 Config: {config.mt5_config_path}")
        print(f"  Predictions: {config.predictions_dir}")
        print(f"  Artifacts: {config.artifacts_dir}")
        
        print("\n📊 Trading Parameters:")
        print(f"  Max working duration: {config.max_working_duration}")
        print(f"  Per day divisor: {config.per_day_divisor}")
        print(f"  Position expiry (trading days): {config.n_expiry_tdays}")
        print(f"  Max budget discrepancy: {config.max_budget_discrepancy}")
        
        print("\n🏪 Market Access:")
        print(f"  Max wait time: {config.max_market_access_duration_seconds}s")
        print(f"  Max tick age: {config.max_tick_age_seconds}s")
        print(f"  Retry wait time: {config.retry_wait_sec}s")
        
        print("\n📝 Logging:")
        print(f"  Level: {config.log_level}")
        print(f"  Directory: {config.log_dir}")
        print(f"  Format: {config.log_format}")
        print(f"  Date format: {config.log_datefmt}")
        
        # Test __repr__ method
        print(f"\n🔍 Configuration representation:")
        print(f"  {repr(config)}")
        
        # Validate configuration
        config.validate()
        print("\n✅ Configuration validation passed!")
        
        # Test all properties are accessible and return expected types
        print("\n🧪 Property type validation:")
        assert isinstance(config.credentials_path, str), "credentials_path should be string"
        assert isinstance(config.mt5_config_path, str), "mt5_config_path should be string"
        assert isinstance(config.predictions_dir, str), "predictions_dir should be string"
        assert isinstance(config.artifacts_dir, str), "artifacts_dir should be string"
        assert isinstance(config.per_day_divisor, int), "per_day_divisor should be int"
        assert isinstance(config.max_budget_discrepancy, float), "max_budget_discrepancy should be float"
        assert isinstance(config.n_expiry_tdays, int), "n_expiry_tdays should be int"
        assert isinstance(config.max_market_access_duration_seconds, int), "max_market_access_duration_seconds should be int"
        assert isinstance(config.max_tick_age_seconds, int), "max_tick_age_seconds should be int"
        assert isinstance(config.retry_wait_sec, (int, float)), f"retry_wait_sec should be numeric, got {type(config.retry_wait_sec)}"
        assert isinstance(config.log_level, str), "log_level should be string"
        assert isinstance(config.log_format, str), "log_format should be string"
        assert isinstance(config.log_datefmt, str), "log_datefmt should be string"
        assert isinstance(config.log_dir, str), "log_dir should be string"
        print("  ✅ All property types are correct!")
        
    except FileNotFoundError as e:
        print(f"❌ Configuration file not found: {e}")
        print("💡 Make sure config/trading_config.yaml exists")
        
    except ValueError as e:
        print(f"❌ Configuration validation failed: {e}")
        print("💡 Check your configuration values")
        
    except Exception as e:
        print(f"❌ Configuration error: {e}")

if __name__ == "__main__":
    main()