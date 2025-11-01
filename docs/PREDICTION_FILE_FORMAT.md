# Prediction File Format Specification

This document describes the expected format and structure of prediction JSON files used by the DarwinexClient trading system.

## Overview

Prediction files contain machine learning model predictions for financial instruments that will be used to place automated trades. These files are stored in the `predictions/` directory and must follow a specific JSON format to be properly parsed by the system.

## File Naming Convention

Prediction files must follow this naming pattern:
```
prediction_<group>_<date>_<sequence>.json
```

**Components:**
- `<group>`: Optional group identifier (e.g., "debug", "production", "backtest")
- `<date>`: Date in format `ddmmmyyyy` (e.g., "14oct2025", "15nov2025")
- `<sequence>`: 3-digit sequence number (e.g., "001", "002", "003")

**Examples:**
- `prediction_debug_14oct2025_002.json`
- `prediction_prod_15nov2025_001.json`
- `prediction_backtest_20dec2025_003.json`

## JSON File Structure

### Root Structure

Prediction files can contain either:
1. **Single prediction object** - A single JSON object
2. **Array of predictions** - A JSON array containing multiple prediction objects

### Required Fields

Each prediction object **must** contain these fields:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `symbol` | string | Trading instrument symbol | `"EURUSD"`, `"AUDUSD"`, `"NVDA"` |
| `last_training_day` | string | Last day used in model training (ISO 8601 format) | `"2025-10-14T00:00:00Z"` |
| `last_close_price` | number | Closing price on the last training day | `1.0845`, `0.6785` |
| `n_trading_days` | integer | Number of trading days in prediction horizon | `5`, `10`, `3` |
| `score` | number | Model confidence score (typically 0-1) | `0.73`, `0.81` |

### Optional Fields

These fields are optional but recommended for risk management:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `sl_pct` | number | Stop loss percentage (as decimal) | `0.1` (10%), `0.05` (5%) |
| `tp_pct` | number | Take profit percentage (as decimal) | `0.15` (15%), `0.08` (8%) |

## Field Specifications

### Date Format

The `last_training_day` field must use **ISO 8601 format** with timezone information:

**Accepted formats:**
- `"2025-10-14T00:00:00Z"` (UTC with Z suffix)
- `"2025-10-14T00:00:00+00:00"` (UTC with explicit offset)
- `"2025-10-14T09:30:00-05:00"` (With timezone offset)

**Invalid formats:**
- `"2025-10-14"` (missing time and timezone)
- `"2025-10-14T00:00:00"` (missing timezone)
- `"10/14/2025"` (wrong date format)

### Symbol Naming

Symbols should follow standard conventions:
- **Forex pairs**: `"EURUSD"`, `"GBPUSD"`, `"AUDUSD"`
- **Stocks**: `"NVDA"`, `"MSFT"`, `"AAPL"`

### Risk Management Fields

- **Stop Loss (`sl_pct`)**: Positive decimal representing maximum acceptable loss
  - `0.05` = 5% stop loss
  - `0.1` = 10% stop loss
  
- **Take Profit (`tp_pct`)**: Positive decimal representing profit target
  - `0.08` = 8% take profit
  - `0.15` = 15% take profit

## Example Files

### Single Prediction Object

```json
{
    "symbol": "EURUSD",
    "last_training_day": "2025-10-14T00:00:00Z",
    "last_close_price": 1.0845,
    "n_trading_days": 5,
    "score": 0.73,
    "sl_pct": 0.05,
    "tp_pct": 0.08
}
```

### Multiple Predictions Array

```json
[
    {
        "symbol": "AUDUSD",
        "last_training_day": "2025-10-13T00:00:00Z",
        "last_close_price": 0.6785,
        "n_trading_days": 4,
        "score": 0.76,
        "sl_pct": 0.1,
        "tp_pct": 0.05
    },
    {
        "symbol": "NZDUSD",
        "last_training_day": "2025-10-13T00:00:00Z",
        "last_close_price": 0.6142,
        "n_trading_days": 6,
        "score": 0.71
    },
    {
        "symbol": "GBPUSD",
        "last_training_day": "2025-10-14T00:00:00Z",
        "last_close_price": 1.2976,
        "n_trading_days": 3,
        "score": 0.68,
        "sl_pct": 0.08
    }
]
```

### Mixed Risk Management

It's acceptable to have some predictions with risk management fields and others without:

```json
[
    {
        "symbol": "EURUSD",
        "last_training_day": "2025-10-14T00:00:00Z",
        "last_close_price": 1.0845,
        "n_trading_days": 5,
        "score": 0.73
    },
    {
        "symbol": "USDJPY",
        "last_training_day": "2025-10-14T00:00:00Z",
        "last_close_price": 149.82,
        "n_trading_days": 7,
        "score": 0.81,
        "sl_pct": 0.06,
        "tp_pct": 0.12
    }
]
```

## Processing Behavior

### Magic Number Generation

The system automatically generates a unique `magic` number for each prediction based on:
- Symbol
- Last training day
- Number of trading days

This ensures each prediction can be uniquely identified in the trading system.

## File Schema Summary

```json
{
  "type": "array",
  "items": {
    "type": "object",
    "required": ["symbol", "last_training_day", "last_close_price", "n_trading_days", "score"],
    "properties": {
      "symbol": {"type": "string"},
      "last_training_day": {"type": "string", "format": "date-time"},
      "last_close_price": {"type": "number"},
      "n_trading_days": {"type": "integer", "minimum": 1},
      "score": {"type": "number"},
      "sl_pct": {"type": "number", "minimum": 0},
      "tp_pct": {"type": "number", "minimum": 0}
    }
  }
}
```