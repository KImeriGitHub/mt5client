"""Unit tests for cancel_lastdate_positions.py functionality."""

import pytest
import argparse
import json
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open, call

from cancel_lastdate_positions import parse_args, main, get_positions_by_date, get_last_n_dates_positions
from src.infra.PositionData import PositionData
from src.infra.PredictionData import PredictionData
from src.infra.BudgetMgmt import BudgetMgmt
from src.infra.PositionClient import PositionClient
from src.infra.mtBase import mtBase
from src.infra.TradingConfig import TradingConfig


class TestParseArgs:
    """Test cases for parse_args function."""
    
    def test_parse_args_required_only(self):
        """Test parsing with only required arguments."""
        with patch('sys.argv', ['cancel_lastdate_positions.py', '--account', 'test_account']):
            args = parse_args()
            assert args.account == 'test_account'
            assert args.n_dates == 1
            assert args.config == 'config/trading_config_prod.yaml'
            assert args.apply is False
    
    def test_parse_args_with_n_dates(self):
        """Test parsing with n_dates argument."""
        with patch('sys.argv', [
            'cancel_lastdate_positions.py',
            '--account', 'demo_account',
            '--n_dates', '3',
            '--config', 'custom_config.yaml',
            '--apply'
        ]):
            args = parse_args()
            assert args.account == 'demo_account'
            assert args.n_dates == 3
            assert args.config == 'custom_config.yaml'
            assert args.apply is True
    
    def test_parse_args_missing_account(self):
        """Test that missing required account argument raises error."""
        with patch('sys.argv', ['cancel_lastdate_positions.py']):
            with pytest.raises(SystemExit):
                parse_args()


class TestGetPositionsByDate:
    """Test cases for get_positions_by_date function."""
    
    def test_get_positions_by_date_single_date(self):
        """Test grouping positions when all are from the same date."""
        positions = [
            PositionData(
                ticket=123,
                time=datetime(2025, 11, 10, 10, 0, tzinfo=timezone.utc),
                time_msc=1699614000000,
                type=0,
                magic=11111,
                reason=0,
                volume=0.1,
                price_open=100.0,
                price_current=102.0,
                profit=20.0,
                symbol='EURUSD'
            ),
            PositionData(
                ticket=456,
                time=datetime(2025, 11, 10, 14, 30, tzinfo=timezone.utc),
                time_msc=1699630200000,
                type=1,
                magic=22222,
                reason=0,
                volume=0.2,
                price_open=1.2000,
                price_current=1.1980,
                profit=40.0,
                symbol='GBPUSD'
            )
        ]
        
        result = get_positions_by_date(positions)
        
        assert len(result) == 1
        assert date(2025, 11, 10) in result
        assert len(result[date(2025, 11, 10)]) == 2
    
    def test_get_positions_by_date_multiple_dates(self):
        """Test grouping positions from multiple dates."""
        positions = [
            PositionData(
                ticket=123,
                time=datetime(2025, 11, 10, 10, 0, tzinfo=timezone.utc),
                time_msc=1699614000000,
                type=0,
                magic=11111,
                reason=0,
                volume=0.1,
                price_open=100.0,
                price_current=102.0,
                profit=20.0,
                symbol='EURUSD'
            ),
            PositionData(
                ticket=456,
                time=datetime(2025, 11, 11, 14, 30, tzinfo=timezone.utc),
                time_msc=1699714800000,
                type=1,
                magic=22222,
                reason=0,
                volume=0.2,
                price_open=1.2000,
                price_current=1.1980,
                profit=40.0,
                symbol='GBPUSD'
            ),
            PositionData(
                ticket=789,
                time=datetime(2025, 11, 11, 16, 0, tzinfo=timezone.utc),
                time_msc=1699720400000,
                type=0,
                magic=33333,
                reason=0,
                volume=0.15,
                price_open=1.5000,
                price_current=1.5020,
                profit=30.0,
                symbol='USDCHF'
            )
        ]
        
        result = get_positions_by_date(positions)
        
        assert len(result) == 2
        assert date(2025, 11, 10) in result
        assert date(2025, 11, 11) in result
        assert len(result[date(2025, 11, 10)]) == 1
        assert len(result[date(2025, 11, 11)]) == 2


class TestGetLastNDatesPositions:
    """Test cases for get_last_n_dates_positions function."""
    
    def test_get_last_n_dates_single_date(self):
        """Test getting positions from the most recent date."""
        positions = [
            PositionData(
                ticket=123,
                time=datetime(2025, 11, 10, 10, 0, tzinfo=timezone.utc),
                time_msc=1699614000000,
                type=0,
                magic=11111,
                reason=0,
                volume=0.1,
                price_open=100.0,
                price_current=102.0,
                profit=20.0,
                symbol='EURUSD'
            ),
            PositionData(
                ticket=456,
                time=datetime(2025, 11, 11, 14, 30, tzinfo=timezone.utc),
                time_msc=1699714800000,
                type=1,
                magic=22222,
                reason=0,
                volume=0.2,
                price_open=1.2000,
                price_current=1.1980,
                profit=40.0,
                symbol='GBPUSD'
            ),
            PositionData(
                ticket=789,
                time=datetime(2025, 11, 12, 16, 0, tzinfo=timezone.utc),
                time_msc=1699806000000,
                type=0,
                magic=33333,
                reason=0,
                volume=0.15,
                price_open=1.5000,
                price_current=1.5020,
                profit=30.0,
                symbol='USDCHF'
            )
        ]
        
        result = get_last_n_dates_positions(positions, n_dates=1)
        
        # Should only return position from Nov 12 (most recent)
        assert len(result) == 1
        assert result[0].ticket == 789
    
    def test_get_last_n_dates_multiple_dates(self):
        """Test getting positions from the last N dates."""
        positions = [
            PositionData(
                ticket=123,
                time=datetime(2025, 11, 10, 10, 0, tzinfo=timezone.utc),
                time_msc=1699614000000,
                type=0,
                magic=11111,
                reason=0,
                volume=0.1,
                price_open=100.0,
                price_current=102.0,
                profit=20.0,
                symbol='EURUSD'
            ),
            PositionData(
                ticket=456,
                time=datetime(2025, 11, 11, 14, 30, tzinfo=timezone.utc),
                time_msc=1699714800000,
                type=1,
                magic=22222,
                reason=0,
                volume=0.2,
                price_open=1.2000,
                price_current=1.1980,
                profit=40.0,
                symbol='GBPUSD'
            ),
            PositionData(
                ticket=789,
                time=datetime(2025, 11, 12, 16, 0, tzinfo=timezone.utc),
                time_msc=1699806000000,
                type=0,
                magic=33333,
                reason=0,
                volume=0.15,
                price_open=1.5000,
                price_current=1.5020,
                profit=30.0,
                symbol='USDCHF'
            )
        ]
        
        result = get_last_n_dates_positions(positions, n_dates=2)
        
        # Should return positions from Nov 11 and Nov 12
        assert len(result) == 2
        tickets = {pos.ticket for pos in result}
        assert tickets == {456, 789}


class TestCancelLastdatePositionsMain:
    """Test cases for main function."""
    
    def setup_method(self):
        """Set up common test fixtures."""
        # Create mock arguments
        self.mock_args = MagicMock()
        self.mock_args.account = 'test_account'
        self.mock_args.n_dates = 1
        self.mock_args.config = 'config/test_config.yaml'
        self.mock_args.apply = False
        self.mock_args.place_time = None
        
        # Create sample positions from different dates
        self.sample_positions = [
            PositionData(
                ticket=123456,
                time=datetime(2025, 11, 10, 10, 0, tzinfo=timezone.utc),
                time_msc=1699614000000,
                type=0,  # BUY
                magic=11111,
                reason=0,
                volume=0.1,
                price_open=100.0,
                sl=95.0,
                tp=105.0,
                price_current=102.0,
                profit=20.0,
                symbol='EURUSD',
                comment='test position'
            ),
            PositionData(
                ticket=789012,
                time=datetime(2025, 11, 11, 14, 30, tzinfo=timezone.utc),
                time_msc=1699714800000,
                type=1,  # SELL
                magic=22222,
                reason=0,
                volume=0.2,
                price_open=1.2000,
                sl=1.2050,
                tp=1.1950,
                price_current=1.1980,
                profit=40.0,
                symbol='GBPUSD',
                comment='another test position'
            )
        ]
    
    @patch('cancel_lastdate_positions.setup_console_and_file_logging')
    @patch('cancel_lastdate_positions.time.sleep')
    @patch('cancel_lastdate_positions.Path')
    @patch('cancel_lastdate_positions.TradingConfig')
    @patch('cancel_lastdate_positions.mtBase')
    @patch('cancel_lastdate_positions.PositionClient')
    @patch('cancel_lastdate_positions.BudgetMgmt')
    @patch('cancel_lastdate_positions.parse_and_sleep_until_time')
    def test_main_dry_run_success(self, mock_sleep_until, mock_budget_mgmt, 
                                  mock_pos_client, mock_mt_base,
                                  mock_config, mock_path, mock_sleep, mock_setup_logging):
        """Test successful dry run execution."""
        # Setup mocks
        mock_config_instance = MagicMock()
        mock_config_instance.log_dir = 'logs'
        mock_config_instance.log_level = 'INFO'
        mock_config_instance.log_format = '%(message)s'
        mock_config_instance.log_datefmt = '%Y-%m-%d %H:%M:%S'
        mock_config_instance.artifacts_dir = 'artifacts'
        mock_config_instance.credentials_path = 'secrets/creds.yaml'
        mock_config_instance.mt5_config_path = 'secrets/mt5.ini'
        mock_config_instance.per_day_divisor = 3
        mock_config_instance.max_budget_discrepancy = 0.1
        mock_config_instance.max_working_duration = timedelta(minutes=30)
        mock_config.return_value = mock_config_instance
        
        mock_base_instance = MagicMock()
        mock_mt_base.return_value = mock_base_instance
        
        mock_pos_client_instance = MagicMock()
        mock_pos_client_instance.get_positions.return_value = self.sample_positions
        mock_pos_client_instance.log_positions = MagicMock()
        mock_pos_client_instance.close_position_request.return_value = {'symbol': 'GBPUSD'}
        mock_pos_client.return_value = mock_pos_client_instance
        
        mock_budget_instance = MagicMock()
        mock_budget_instance.free_margin = 5000.0
        mock_budget_instance.total_capital = 10000.0
        mock_budget_instance.calc_daily_budget.return_value = 1000.0
        mock_budget_instance.refresh = MagicMock()
        mock_budget_mgmt.return_value = mock_budget_instance
        
        # Mock Path for artifacts
        mock_results_path = MagicMock()
        mock_results_path.open.return_value.__enter__ = MagicMock()
        mock_results_path.open.return_value.__exit__ = MagicMock(return_value=None)
        mock_path_instance = MagicMock()
        mock_path_instance.__truediv__.return_value = mock_results_path
        mock_path.return_value = mock_path_instance
        
        # Mock check_closing_price_condition to always allow closing
        with patch('cancel_lastdate_positions.check_closing_price_condition') as mock_check_price:
            mock_check_price.return_value = (0, "Price condition met")
            
            # Mock place_order_req to return success
            with patch('cancel_lastdate_positions.place_order_req') as mock_place_order:
                mock_place_order.return_value = (0, "DRY RUN: Order check passed for GBPUSD.")
                
                # Mock json.dump
                with patch('cancel_lastdate_positions.json.dump') as mock_json_dump:
                    result = main(self.mock_args, setup_logs=False)
        
        # Assertions - should only close position from most recent date (Nov 11)
        assert len(result) == 1
        assert result[0] == self.sample_positions[1]  # Position from Nov 11
        
        # Verify mocks were called correctly
        mock_config_instance.validate.assert_called_once()
        mock_base_instance.mt5_init.assert_called_once()
        mock_pos_client_instance.get_positions.assert_called_once()
        mock_place_order.assert_called_once()
        
        # Verify file operations
        mock_results_path.open.assert_called_once_with("w", encoding="utf-8")
        mock_json_dump.assert_called_once()

    @patch('cancel_lastdate_positions.setup_console_and_file_logging')
    @patch('cancel_lastdate_positions.time.sleep')
    @patch('cancel_lastdate_positions.Path')
    @patch('cancel_lastdate_positions.TradingConfig')
    @patch('cancel_lastdate_positions.mtBase')
    @patch('cancel_lastdate_positions.PositionClient')
    @patch('cancel_lastdate_positions.BudgetMgmt')
    @patch('cancel_lastdate_positions.parse_and_sleep_until_time')
    def test_main_requeueing_behavior(self, mock_sleep_until, mock_budget_mgmt, 
                                     mock_pos_client, mock_mt_base,
                                     mock_config, mock_path, mock_sleep, mock_setup_logging):
        """Test requeueing behavior when check_closing_price_condition returns status 1."""
        # Setup mocks
        mock_config_instance = MagicMock()
        mock_config_instance.log_dir = 'logs'
        mock_config_instance.log_level = 'INFO'
        mock_config_instance.log_format = '%(message)s'
        mock_config_instance.log_datefmt = '%Y-%m-%d %H:%M:%S'
        mock_config_instance.artifacts_dir = 'artifacts'
        mock_config_instance.credentials_path = 'secrets/creds.yaml'
        mock_config_instance.mt5_config_path = 'secrets/mt5.ini'
        mock_config_instance.per_day_divisor = 3
        mock_config_instance.max_budget_discrepancy = 0.1
        mock_config_instance.max_working_duration = timedelta(minutes=30)
        mock_config_instance.retry_wait_sec = 0.1
        mock_config.return_value = mock_config_instance
        
        mock_base_instance = MagicMock()
        mock_mt_base.return_value = mock_base_instance
        
        mock_pos_client_instance = MagicMock()
        mock_pos_client_instance.get_positions.return_value = self.sample_positions
        mock_pos_client_instance.log_positions = MagicMock()
        mock_pos_client_instance.close_position_request.return_value = {'symbol': 'GBPUSD'}
        mock_pos_client.return_value = mock_pos_client_instance
        
        mock_budget_instance = MagicMock()
        mock_budget_instance.free_margin = 5000.0
        mock_budget_instance.total_capital = 10000.0
        mock_budget_instance.calc_daily_budget.return_value = 1000.0
        mock_budget_instance.refresh = MagicMock()
        mock_budget_mgmt.return_value = mock_budget_instance
        
        # Mock Path for artifacts
        mock_results_path = MagicMock()
        mock_results_path.open.return_value.__enter__ = MagicMock()
        mock_results_path.open.return_value.__exit__ = MagicMock(return_value=None)
        mock_path_instance = MagicMock()
        mock_path_instance.__truediv__.return_value = mock_results_path
        mock_path.return_value = mock_path_instance
        
        # Create args with apply flag set to True to test requeueing
        args = argparse.Namespace(
            account='test_account',
            n_dates=1,
            config='config/trading_config_prod.yaml',
            apply=True,  # Set to True to test requeueing logic
            place_time=None
        )
        
        # Mock check_closing_price_condition to return status 1 first time, then 0
        with patch('cancel_lastdate_positions.check_closing_price_condition') as mock_check_price:
            mock_check_price.side_effect = [
                (1, "Price condition not met, requeue"),  # First call - requeue
                (0, "Price condition met")  # Second call - proceed
            ]
            
            # Mock place_order_req to return success
            with patch('cancel_lastdate_positions.place_order_req') as mock_place_order:
                mock_place_order.return_value = (0, "Order placed successfully for GBPUSD.")
                
                # Mock json.dump
                with patch('cancel_lastdate_positions.json.dump') as mock_json_dump:
                    result = main(args, setup_logs=False)
        
        # Assertions
        assert len(result) == 1
        assert result[0] == self.sample_positions[1]  # Position from Nov 11
        
        # Verify check_closing_price_condition was called twice (once initially, once after requeue)
        assert mock_check_price.call_count == 2
        
        # Verify sleep was called for requeueing
        assert mock_sleep.call_count > 0
        
        # Verify place_order was called once (after successful price check)
        mock_place_order.assert_called_once()

