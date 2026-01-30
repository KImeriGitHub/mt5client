import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
import datetime as dt

from src.check_opening_price_condition import (
    calculate_timeinterval,
    evaluate_price_condition,
    check_opening_price_condition
)

class TestCheckOpeningPriceCondition(unittest.TestCase):
    def setUp(self):
        # Recreate a dataframe similar to the sandbox output
        # Sandbox Start: 2026-01-28 16:32:00, Ask ~422.12
        # Sandbox End: 2026-01-28 16:39:22, Ask ~429.72
        # Sample count: 1283
        
        start_time = pd.Timestamp("2026-01-28 16:32:00", tz="UTC")
        end_time = pd.Timestamp("2026-01-28 16:39:22", tz="UTC")
        
        # Create time range
        periods = 1283
        # Use valid date_range
        times = pd.date_range(start=start_time, end=end_time, periods=periods)
        
        # Create linear price trend
        start_price = 422.12
        end_price = 429.72
        
        # Add some noise to make it realistic
        np.random.seed(42) # For reproducibility
        noise = np.random.normal(0, 0.05, periods) # Smaller noise to ensure linearity checks pass
        prices = np.linspace(start_price, end_price, periods) + noise
        
        self.mock_df = pd.DataFrame({
            "time": times,
            "ask": prices,
            "bid": prices - 0.1, # Arbitrary spread
            "last": 0.0,
            "volume": 0,
            "time_msc": times, # approximating msc with same time
            "flags": 1028,
            "volume_real": 0.0
        })
        
        self.mock_ask_prices = self.mock_df['ask'].to_numpy()

    def test_calculate_timeinterval(self):
        # Case 1: Target minute in current hour (e.g. now 10:45, target 30 -> 15 min back)
        curtime = pd.Timestamp("2026-01-28 10:45:15", tz="UTC")
        target_minute = 30
        seconds_back, from_time = calculate_timeinterval(curtime, target_minute)
        
        expected_minutes_back = 45 - 30
        expected_seconds_back = expected_minutes_back * 60 + 15
        self.assertEqual(seconds_back, expected_seconds_back)
        self.assertEqual(from_time, curtime - pd.Timedelta(seconds=expected_seconds_back))

        # Case 2: Target minute in previous hour (e.g. now 10:15, target 30 -> 45 min back)
        curtime = pd.Timestamp("2026-01-28 10:15:15", tz="UTC")
        target_minute = 30
        seconds_back, from_time = calculate_timeinterval(curtime, target_minute)
        
        expected_minutes_back = (60 - 30) + 15 # 30 + 15 = 45
        expected_seconds_back = expected_minutes_back * 60 + 15
        self.assertEqual(seconds_back, expected_seconds_back)
        self.assertEqual(from_time, curtime - pd.Timedelta(seconds=expected_seconds_back))

        # Case 3: Exact match (should look back 60 mins)
        curtime = pd.Timestamp("2026-01-28 10:30:00", tz="UTC")
        target_minute = 30
        seconds_back, from_time = calculate_timeinterval(curtime, target_minute)
        
        self.assertEqual(seconds_back, 3600)
        self.assertEqual(from_time, curtime - pd.Timedelta(hours=1))

    def test_evaluate_price_condition_success(self):
        # The mock data represents a steady increase (~1.8%) which is > 0.995
        # It has enough data points and duration
        
        status, msg = evaluate_price_condition(self.mock_ask_prices, self.mock_df)
        
        # Given the linear trend + small noise, this should likely pass (status 0)
        if status != 0:
            print(f"Test Failed Message: {msg}")
            
        self.assertEqual(status, 0, f"Expected success but got failure: {msg}")
        self.assertIn("BUY", msg)

    def test_evaluate_price_condition_too_few_data(self):
        # Create tiny dataframe
        tiny_df = self.mock_df.head(4)
        tiny_ask = tiny_df['ask'].to_numpy()
        
        status, msg = evaluate_price_condition(tiny_ask, tiny_df)
        self.assertEqual(status, 1)
        self.assertIn("no_data", msg)

    def test_evaluate_price_condition_low_return(self):
        # Create a flat or declining trend
        prices_flat = np.linspace(100, 99, 1283) # 1% drop
        df_flat = self.mock_df.copy()
        df_flat['ask'] = prices_flat
        ask_flat = df_flat['ask'].to_numpy()
        
        status, msg = evaluate_price_condition(ask_flat, df_flat)
        self.assertEqual(status, 1)
        self.assertIn("Return too low", msg)

    def test_check_opening_price_condition_integration(self):
        # This tests the main function check_opening_price_condition
        
        # Mock mtBase object
        mock_base = MagicMock()
        
        # Mock get_symbol_info
        mock_base.get_symbol_info.return_value = {
            "time": self.mock_df["time"].iloc[-1].timestamp()
        }
        
        # Prepare valid raw data (timestamps as floats)
        mock_ticks_raw = self.mock_df.copy()
        mock_ticks_raw['time'] = mock_ticks_raw['time'].apply(lambda x: x.timestamp()) # Convert to seconds
        mock_ticks_raw['time_msc'] = mock_ticks_raw['time_msc'].apply(lambda x: x.timestamp() * 1000) # milliseconds
        
        ticks_data = mock_ticks_raw.to_dict('records')
        mock_base.copy_ticks_range.return_value = ticks_data
        
        # Run function
        symbol = "MU"
        result, msg = check_opening_price_condition(symbol, mock_base, target_minute=30)
        
        self.assertEqual(result, 0)
        self.assertIn("BUY", msg)

    def test_evaluate_price_condition_insufficient_time_span(self):
        # Case where elapsed time > 600s but last 10 mins is empty
        
        times = [
            pd.Timestamp("2026-01-28 16:00:00", tz="UTC"),
            pd.Timestamp("2026-01-28 16:01:00", tz="UTC"),
            pd.Timestamp("2026-01-28 16:02:00", tz="UTC"),
            pd.Timestamp("2026-01-28 16:03:00", tz="UTC"),
            pd.Timestamp("2026-01-28 16:04:00", tz="UTC"),
            # BIG GAP
            pd.Timestamp("2026-01-28 16:15:00", tz="UTC") # Current time
        ]
        
        prices = [100.0] * 6
        
        df = pd.DataFrame({"time": times, "ask": prices})
        
        status, msg = evaluate_price_condition(df['ask'].to_numpy(), df)
        self.assertEqual(status, 1)
        # Should fail on 10m check
        self.assertTrue("Not enough" in msg or "no_data" in msg)
