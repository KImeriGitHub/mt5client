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
        
        print("\n📊 Trading Parameters:")
        print(f"  Max working duration: {config.max_working_duration}")
        print(f"  Per day divisor: {config.per_day_divisor}")
        
        print("\n🏪 Market Access:")
        print(f"  Max wait time: {config.max_market_access_duration_seconds}s")
        print(f"  Max tick age: {config.max_tick_age_seconds}s")
        
        print("\n📝 Logging:")
        print(f"  Level: {config.log_level}")
        print(f"  Directory: {config.log_dir}")
        print(f"  Format: {config.log_format}")
        
        # Validate configuration
        config.validate()
        print("\n✅ Configuration validation passed!")
        
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