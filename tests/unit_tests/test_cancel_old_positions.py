"""Unit tests for cancel_old_positions.py functionality."""

import pytest
import argparse
import json
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open, call

from cancel_old_positions import parse_args, main
from src.infra.PositionData import PositionData
from src.infra.PredictionData import PredictionData
from src.infra.BudgetMgmt import BudgetMgmt
from src.infra.PredictionClient import PredictionClient
from src.infra.PositionClient import PositionClient
from src.infra.mtBase import mtBase
from src.infra.TradingConfig import TradingConfig


class TestParseArgs:
    """Test cases for parse_args function."""
    
    def test_parse_args_required_only(self):
        """Test parsing with only required arguments."""
        with patch('sys.argv', ['cancel_old_positions.py', '--account', 'test_account']):
            args = parse_args()
            assert args.account == 'test_account'
            assert args.group == 'mt5'
            assert args.config == 'config/trading_config_prod.yaml'
            assert args.apply is False
    
    def test_parse_args_all_options(self):
        """Test parsing with all arguments provided."""
        with patch('sys.argv', [
            'cancel_old_positions.py',
            '--account', 'demo_account',
            '--group', 'custom_group',
            '--config', 'custom_config.yaml',
            '--apply'
        ]):
            args = parse_args()
            assert args.account == 'demo_account'
            assert args.group == 'custom_group'
            assert args.config == 'custom_config.yaml'
            assert args.apply is True
    
    def test_parse_args_missing_account(self):
        """Test that missing required account argument raises error."""
        with patch('sys.argv', ['cancel_old_positions.py']):
            with pytest.raises(SystemExit):
                parse_args()


class TestCancelOldPositionsMain:
    """Test cases for main function."""
    
    def setup_method(self):
        """Set up common test fixtures."""
        # Create mock arguments
        self.mock_args = MagicMock()
        self.mock_args.account = 'test_account'
        self.mock_args.group = 'mt5'
        self.mock_args.config = 'config/test_config.yaml'
        self.mock_args.apply = False
        
        # Create sample positions
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
        
        # Create sample predictions
        self.sample_predictions = [
            PredictionData(
                symbol='EURUSD',
                last_training_day=date(2025, 11, 1),
                last_close_price=100.0,
                n_trading_days=5,
                score=0.75,
                magic=11111,
                sl_pct=0.05,
                tp_pct=0.05
            ),
            PredictionData(
                symbol='GBPUSD',
                last_training_day=date(2025, 11, 2),
                last_close_price=1.2000,
                n_trading_days=7,
                score=0.68,
                magic=22222,
                sl_pct=0.04,
                tp_pct=0.06
            )
        ]
    
    @patch('cancel_old_positions.setup_console_and_file_logging')
    @patch('cancel_old_positions.time.sleep')
    @patch('cancel_old_positions.Path')
    @patch('cancel_old_positions.TradingConfig')
    @patch('cancel_old_positions.mtBase')
    @patch('cancel_old_positions.PredictionClient')        
    @patch('cancel_old_positions.PositionClient')
    @patch('cancel_old_positions.BudgetMgmt')
    @patch('cancel_old_positions.get_positions_to_close')
    def test_main_dry_run_success(self, mock_get_positions, mock_budget_mgmt, 
                                  mock_pos_client, mock_pred_client, mock_mt_base,
                                  mock_config, mock_path, mock_sleep, mock_setup_logging):
        """Test successful dry run execution."""
        # Setup mocks
        mock_config_instance = MagicMock()
        mock_config_instance.log_dir = 'logs'
        mock_config_instance.log_level = 'INFO'
        mock_config_instance.log_format = '%(message)s'
        mock_config_instance.log_datefmt = '%Y-%m-%d %H:%M:%S'
        mock_config_instance.predictions_dir = 'predictions'
        mock_config_instance.artifacts_dir = 'artifacts'
        mock_config_instance.credentials_path = 'secrets/creds.yaml'
        mock_config_instance.mt5_config_path = 'secrets/mt5.ini'
        mock_config_instance.per_day_divisor = 3
        mock_config_instance.max_budget_discrepancy = 0.1
        mock_config_instance.max_working_duration = timedelta(minutes=30)
        mock_config.return_value = mock_config_instance
        
        mock_base_instance = MagicMock()
        mock_mt_base.return_value = mock_base_instance
        
        mock_pred_client_instance = MagicMock()
        mock_pred_client_instance.load_predictions.return_value = self.sample_predictions
        mock_pred_client.return_value = mock_pred_client_instance
        
        mock_pos_client_instance = MagicMock()
        mock_pos_client_instance.get_positions.return_value = self.sample_positions
        mock_pos_client_instance.log_positions = MagicMock()
        mock_pos_client_instance.close_position_request.return_value = {'symbol': 'EURUSD'}
        mock_pos_client.return_value = mock_pos_client_instance
        
        mock_budget_instance = MagicMock()
        mock_budget_instance.free_margin = 5000.0
        mock_budget_instance.calc_daily_budget.return_value = 1000.0
        mock_budget_mgmt.return_value = mock_budget_instance
        
        # Return first position to close
        mock_get_positions.return_value = [self.sample_positions[0]]
        
        # Mock Path for artifacts - need to mock the path creation and file operations
        mock_results_path = MagicMock()
        mock_results_path.open.return_value.__enter__ = MagicMock()
        mock_results_path.open.return_value.__exit__ = MagicMock(return_value=None)
        mock_path_instance = MagicMock()
        mock_path_instance.__truediv__.return_value = mock_results_path  # Mock the / operator
        mock_path.return_value = mock_path_instance
        
        # Mock place_order_req to return success
        with patch('cancel_old_positions.place_order_req') as mock_place_order:
            mock_place_order.return_value = (0, "DRY RUN: Order check passed for EURUSD.")
            
            # Mock json.dump
            with patch('cancel_old_positions.json.dump') as mock_json_dump:
                result = main(self.mock_args, setup_logs=False)
        
        # Assertions
        assert len(result) == 1
        assert result[0] == self.sample_positions[0]
        
        # Verify mocks were called correctly
        mock_config_instance.validate.assert_called_once()
        mock_base_instance.mt5_init.assert_called_once()
        mock_pred_client_instance.load_predictions.assert_called_once_with('mt5')
        mock_pos_client_instance.get_positions.assert_called_once()
        mock_get_positions.assert_called_once()
        mock_place_order.assert_called_once()
        
        # Verify file operations
        mock_results_path.open.assert_called_once_with("w", encoding="utf-8")
        mock_json_dump.assert_called_once()
    
    @patch('cancel_old_positions.setup_console_and_file_logging')
    @patch('cancel_old_positions.time.sleep')
    @patch('cancel_old_positions.Path')
    @patch('cancel_old_positions.TradingConfig')
    @patch('cancel_old_positions.mtBase')
    @patch('cancel_old_positions.PredictionClient')        
    @patch('cancel_old_positions.PositionClient')
    @patch('cancel_old_positions.BudgetMgmt')
    @patch('cancel_old_positions.get_positions_to_close')
    def test_main_no_positions_to_close(self, mock_get_positions, mock_budget_mgmt, 
                                       mock_pos_client, mock_pred_client, mock_mt_base,
                                       mock_config, mock_path, mock_sleep, mock_setup_logging):
        """Test when no positions need to be closed - should return early without creating files."""
        # Setup basic mocks
        mock_config_instance = MagicMock()
        mock_config_instance.predictions_dir = 'predictions'
        mock_config_instance.artifacts_dir = 'artifacts'
        mock_config_instance.credentials_path = 'secrets/creds.yaml'
        mock_config_instance.mt5_config_path = 'secrets/mt5.ini'
        mock_config_instance.per_day_divisor = 3
        mock_config_instance.max_budget_discrepancy = 0.1
        mock_config_instance.max_working_duration = timedelta(minutes=30)
        mock_config.return_value = mock_config_instance
        
        mock_base_instance = MagicMock()
        mock_mt_base.return_value = mock_base_instance
        
        mock_pred_client_instance = MagicMock()
        mock_pred_client_instance.load_predictions.return_value = self.sample_predictions
        mock_pred_client.return_value = mock_pred_client_instance
        
        mock_pos_client_instance = MagicMock()
        mock_pos_client_instance.get_positions.return_value = self.sample_positions
        mock_pos_client_instance.log_positions = MagicMock()
        mock_pos_client.return_value = mock_pos_client_instance
        
        mock_budget_instance = MagicMock()
        mock_budget_instance.free_margin = 5000.0
        mock_budget_instance.calc_daily_budget.return_value = 1000.0
        mock_budget_mgmt.return_value = mock_budget_instance
        
        # No positions to close
        mock_get_positions.return_value = []
        
        # Mock Path for artifacts - need to mock Path() call and the / operator
        mock_results_path = MagicMock()
        mock_results_path.open.return_value.__enter__ = MagicMock()
        mock_results_path.open.return_value.__exit__ = MagicMock(return_value=None)
        
        mock_artifacts_path = MagicMock()
        mock_artifacts_path.__truediv__.return_value = mock_results_path
        mock_path.return_value = mock_artifacts_path
        
        with patch('cancel_old_positions.json.dump') as mock_json_dump:
            result = main(self.mock_args, setup_logs=False)
        
        # Should return empty list and NOT create artifacts file (early return)
        assert result == []
        mock_results_path.open.assert_not_called()  # Early return, no file created
        mock_json_dump.assert_not_called()  # Early return, no JSON written
    
    @patch('cancel_old_positions.setup_console_and_file_logging')
    @patch('cancel_old_positions.time.sleep')
    @patch('cancel_old_positions.Path')
    @patch('cancel_old_positions.TradingConfig')
    @patch('cancel_old_positions.mtBase')
    @patch('cancel_old_positions.PredictionClient')        
    @patch('cancel_old_positions.PositionClient')
    @patch('cancel_old_positions.BudgetMgmt')
    def test_main_empty_positions_early_return(self, mock_budget_mgmt, mock_pos_client, 
                                              mock_pred_client, mock_mt_base, mock_config, 
                                              mock_path, mock_sleep, mock_setup_logging):
        """Test early return when no positions or predictions exist."""
        # Setup basic mocks
        mock_config_instance = MagicMock()
        mock_config_instance.predictions_dir = 'predictions'
        mock_config_instance.artifacts_dir = 'artifacts'
        mock_config_instance.credentials_path = 'secrets/creds.yaml'
        mock_config_instance.mt5_config_path = 'secrets/mt5.ini'
        mock_config_instance.per_day_divisor = 3
        mock_config_instance.max_budget_discrepancy = 0.1
        mock_config_instance.n_expiry_tdays = 0
        mock_config.return_value = mock_config_instance
        
        mock_base_instance = MagicMock()
        mock_mt_base.return_value = mock_base_instance
        
        mock_pred_client_instance = MagicMock()
        mock_pred_client_instance.load_predictions.return_value = []  # Empty predictions
        mock_pred_client.return_value = mock_pred_client_instance
        
        mock_pos_client_instance = MagicMock()
        mock_pos_client_instance.get_positions.return_value = []  # Empty positions
        mock_pos_client.return_value = mock_pos_client_instance
        
        mock_budget_instance = MagicMock()
        mock_budget_mgmt.return_value = mock_budget_instance
        
        # Mock get_positions_to_close - it will be called but should return empty list
        with patch('cancel_old_positions.get_positions_to_close') as mock_get_positions:
            mock_get_positions.return_value = []  # Return empty list
            result = main(self.mock_args, setup_logs=False)
        
        # Should return empty list, get_positions_to_close should be called but with empty inputs
        assert result == []
        mock_get_positions.assert_called_once_with([], [], mock_budget_instance, 0)
    
    @patch('cancel_old_positions.setup_console_and_file_logging')
    @patch('cancel_old_positions.time.sleep')
    @patch('cancel_old_positions.Path')
    @patch('cancel_old_positions.TradingConfig')
    @patch('cancel_old_positions.mtBase')
    @patch('cancel_old_positions.PredictionClient')        
    @patch('cancel_old_positions.PositionClient')
    @patch('cancel_old_positions.BudgetMgmt')
    @patch('cancel_old_positions.get_positions_to_close')
    def test_main_insufficient_budget(self, mock_get_positions, mock_budget_mgmt, 
                                     mock_pos_client, mock_pred_client, mock_mt_base,
                                     mock_config, mock_path, mock_sleep, mock_setup_logging):
        """Test early return when insufficient budget to close positions."""
        # Setup mocks
        mock_config_instance = MagicMock()
        mock_config_instance.predictions_dir = 'predictions'
        mock_config_instance.artifacts_dir = 'artifacts'
        mock_config_instance.credentials_path = 'secrets/creds.yaml'
        mock_config_instance.mt5_config_path = 'secrets/mt5.ini'
        mock_config_instance.per_day_divisor = 3
        mock_config_instance.max_budget_discrepancy = 0.1
        mock_config_instance.n_expiry_tdays = 0
        mock_config.return_value = mock_config_instance
        mock_config.return_value = mock_config_instance
        mock_config.return_value = mock_config_instance
        mock_config.return_value = mock_config_instance
        mock_config.return_value = mock_config_instance
        mock_config.return_value = mock_config_instance
        
        mock_base_instance = MagicMock()
        mock_mt_base.return_value = mock_base_instance
        
        mock_pred_client_instance = MagicMock()
        mock_pred_client_instance.load_predictions.return_value = self.sample_predictions
        mock_pred_client.return_value = mock_pred_client_instance
        
        mock_pos_client_instance = MagicMock()
        mock_pos_client_instance.get_positions.return_value = self.sample_positions
        mock_pos_client_instance.log_positions = MagicMock()
        mock_pos_client.return_value = mock_pos_client_instance
        
        # Set up budget scenario where closing would exceed budget
        mock_budget_instance = MagicMock()
        mock_budget_instance.free_margin = 100.0  # Low free margin
        mock_budget_instance.calc_daily_budget.return_value = 1000.0  # High daily budget
        mock_budget_mgmt.return_value = mock_budget_instance
        
        # Positions to close with high price_current
        positions_to_close = [self.sample_positions[0]]  # price_current = 102.0
        mock_get_positions.return_value = positions_to_close
        
        result = main(self.mock_args, setup_logs=False)
        
        # Should return empty list due to budget constraint
        assert result == []
    
    @patch('cancel_old_positions.setup_console_and_file_logging')
    @patch('cancel_old_positions.time.sleep')
    @patch('cancel_old_positions.Path')
    @patch('cancel_old_positions.TradingConfig')
    @patch('cancel_old_positions.mtBase')
    @patch('cancel_old_positions.PredictionClient')        
    @patch('cancel_old_positions.PositionClient')
    @patch('cancel_old_positions.BudgetMgmt')
    @patch('cancel_old_positions.get_positions_to_close')
    def test_main_apply_mode_success(self, mock_get_positions, mock_budget_mgmt, 
                                    mock_pos_client, mock_pred_client, mock_mt_base,
                                    mock_config, mock_path, mock_sleep, mock_setup_logging):
        """Test successful execution in apply mode (live trading)."""
        self.mock_args.apply = True  # Enable live trading
        
        # Setup mocks similar to dry run test
        mock_config_instance = MagicMock()
        mock_config_instance.predictions_dir = 'predictions'
        mock_config_instance.artifacts_dir = 'artifacts'
        mock_config_instance.credentials_path = 'secrets/creds.yaml'
        mock_config_instance.mt5_config_path = 'secrets/mt5.ini'
        mock_config_instance.per_day_divisor = 3
        mock_config_instance.max_budget_discrepancy = 0.1
        mock_config_instance.max_working_duration = timedelta(minutes=30)
        mock_config.return_value = mock_config_instance
        
        mock_base_instance = MagicMock()
        mock_mt_base.return_value = mock_base_instance
        
        mock_pred_client_instance = MagicMock()
        mock_pred_client_instance.load_predictions.return_value = self.sample_predictions
        mock_pred_client.return_value = mock_pred_client_instance
        
        mock_pos_client_instance = MagicMock()
        mock_pos_client_instance.get_positions.return_value = self.sample_positions
        mock_pos_client_instance.log_positions = MagicMock()
        mock_pos_client_instance.close_position_request.return_value = {'symbol': 'EURUSD'}
        mock_pos_client.return_value = mock_pos_client_instance
        
        mock_budget_instance = MagicMock()
        mock_budget_instance.free_margin = 5000.0
        mock_budget_instance.calc_daily_budget.return_value = 1000.0
        mock_budget_mgmt.return_value = mock_budget_instance
        
        mock_get_positions.return_value = [self.sample_positions[0]]
        
        # Mock Path for artifacts
        mock_results_path = MagicMock()
        mock_results_path.open.return_value.__enter__ = MagicMock()
        mock_results_path.open.return_value.__exit__ = MagicMock(return_value=None)
        mock_path_instance = MagicMock()
        mock_path_instance.__truediv__.return_value = mock_results_path
        mock_path.return_value = mock_path_instance
        
        # Mock successful live order placement
        with patch('cancel_old_positions.place_order_req') as mock_place_order:
            mock_place_order.return_value = (0, "Order placed successfully for EURUSD.")
            
            with patch('cancel_old_positions.json.dump') as mock_json_dump:
                result = main(self.mock_args, setup_logs=False)
        
        # Verify live trading was executed
        assert len(result) == 1
        mock_place_order.assert_called_once_with({'symbol': 'EURUSD'}, mock_base_instance, is_dry_run=False)
    
    @patch('cancel_old_positions.setup_console_and_file_logging')
    @patch('cancel_old_positions.time.sleep')
    @patch('cancel_old_positions.Path')
    @patch('cancel_old_positions.TradingConfig')
    @patch('cancel_old_positions.mtBase')
    @patch('cancel_old_positions.PredictionClient')        
    @patch('cancel_old_positions.PositionClient')
    @patch('cancel_old_positions.BudgetMgmt')
    @patch('cancel_old_positions.get_positions_to_close')
    def test_main_order_placement_failure(self, mock_get_positions, mock_budget_mgmt, 
                                         mock_pos_client, mock_pred_client, mock_mt_base,
                                         mock_config, mock_path, mock_sleep, mock_setup_logging):
        """Test handling of order placement failures."""
        # Setup mocks
        mock_config_instance = MagicMock()
        mock_config_instance.predictions_dir = 'predictions'
        mock_config_instance.artifacts_dir = 'artifacts'
        mock_config_instance.credentials_path = 'secrets/creds.yaml'
        mock_config_instance.mt5_config_path = 'secrets/mt5.ini'
        mock_config_instance.per_day_divisor = 3
        mock_config_instance.max_budget_discrepancy = 0.1
        mock_config_instance.max_working_duration = timedelta(minutes=30)
        mock_config.return_value = mock_config_instance
        
        mock_base_instance = MagicMock()
        mock_base_instance.last_error.return_value = (1, "Test error")
        mock_mt_base.return_value = mock_base_instance
        
        mock_pred_client_instance = MagicMock()
        mock_pred_client_instance.load_predictions.return_value = self.sample_predictions
        mock_pred_client.return_value = mock_pred_client_instance
        
        mock_pos_client_instance = MagicMock()
        mock_pos_client_instance.get_positions.return_value = self.sample_positions
        mock_pos_client_instance.log_positions = MagicMock()
        mock_pos_client_instance.close_position_request.return_value = {'symbol': 'EURUSD'}
        mock_pos_client.return_value = mock_pos_client_instance
        
        mock_budget_instance = MagicMock()
        mock_budget_instance.free_margin = 5000.0
        mock_budget_instance.calc_daily_budget.return_value = 1000.0
        mock_budget_mgmt.return_value = mock_budget_instance
        
        mock_get_positions.return_value = [self.sample_positions[0]]
        
        # Mock Path for artifacts
        mock_results_path = MagicMock()
        mock_results_path.open.return_value.__enter__ = MagicMock()
        mock_results_path.open.return_value.__exit__ = MagicMock(return_value=None)
        mock_path_instance = MagicMock()
        mock_path_instance.__truediv__.return_value = mock_results_path
        mock_path.return_value = mock_path_instance
        
        # Mock failed order placement
        with patch('cancel_old_positions.place_order_req') as mock_place_order:
            mock_place_order.return_value = (1, "Order placement failed.")
            
            with patch('cancel_old_positions.json.dump') as mock_json_dump:
                result = main(self.mock_args, setup_logs=False)
        
        # Should return empty list when order placement fails
        assert result == []
        mock_base_instance.last_error.assert_called_once()
    
    @patch('cancel_old_positions.setup_console_and_file_logging')
    @patch('cancel_old_positions.time.sleep')
    @patch('cancel_old_positions.Path')
    @patch('cancel_old_positions.TradingConfig')
    @patch('cancel_old_positions.mtBase')
    @patch('cancel_old_positions.PredictionClient')        
    @patch('cancel_old_positions.PositionClient')
    @patch('cancel_old_positions.BudgetMgmt')
    @patch('cancel_old_positions.get_positions_to_close')
    @patch('cancel_old_positions.dt')
    def test_main_max_working_duration_exceeded(self, mock_dt, mock_get_positions, mock_budget_mgmt, 
                                               mock_pos_client, mock_pred_client, mock_mt_base,
                                               mock_config, mock_path, mock_sleep, mock_setup_logging):
        """Test that processing stops when max working duration is exceeded."""
        # Setup mocks
        mock_config_instance = MagicMock()
        mock_config_instance.predictions_dir = 'predictions'
        mock_config_instance.artifacts_dir = 'artifacts'
        mock_config_instance.credentials_path = 'secrets/creds.yaml'
        mock_config_instance.mt5_config_path = 'secrets/mt5.ini'
        mock_config_instance.per_day_divisor = 3
        mock_config_instance.max_budget_discrepancy = 0.1
        mock_config_instance.max_working_duration = timedelta(seconds=1)  # Very short duration
        mock_config.return_value = mock_config_instance
        
        mock_base_instance = MagicMock()
        mock_mt_base.return_value = mock_base_instance
        
        mock_pred_client_instance = MagicMock()
        mock_pred_client_instance.load_predictions.return_value = self.sample_predictions
        mock_pred_client.return_value = mock_pred_client_instance
        
        mock_pos_client_instance = MagicMock()
        mock_pos_client_instance.get_positions.return_value = self.sample_positions
        mock_pos_client_instance.log_positions = MagicMock()
        mock_pos_client_instance.close_position_request.return_value = {'symbol': 'EURUSD'}
        mock_pos_client.return_value = mock_pos_client_instance
        
        mock_budget_instance = MagicMock()
        mock_budget_instance.free_margin = 5000.0
        mock_budget_instance.calc_daily_budget.return_value = 1000.0
        mock_budget_mgmt.return_value = mock_budget_instance
        
        # Multiple positions to close
        mock_get_positions.return_value = self.sample_positions
        
        # Mock Path for artifacts
        mock_results_path = MagicMock()
        mock_results_path.open.return_value.__enter__ = MagicMock()
        mock_results_path.open.return_value.__exit__ = MagicMock(return_value=None)
        mock_path_instance = MagicMock()
        mock_path_instance.__truediv__.return_value = mock_results_path
        mock_path.return_value = mock_path_instance
        
        # Mock datetime to simulate time passing
        start_time = datetime.now(timezone.utc)
        later_time = start_time + timedelta(seconds=2)  # Exceeds max duration
        
        # Mock datetime.now to return start_time first, then later_time
        mock_datetime_now = MagicMock()
        mock_datetime_now.side_effect = [start_time, later_time, later_time]  # Extra later_time for safety
        mock_dt.datetime.now = mock_datetime_now
        mock_dt.timezone.utc = timezone.utc
        
        with patch('cancel_old_positions.place_order_req') as mock_place_order:
            mock_place_order.return_value = (0, "Order placed successfully.")
            
            with patch('cancel_old_positions.json.dump') as mock_json_dump:
                result = main(self.mock_args, setup_logs=False)
        
        # Should stop processing due to time limit
        assert len(result) == 0  # No positions closed due to timeout
    
    def test_main_with_none_args(self):
        """Test main function with None args defaults to parse_args()."""
        with patch('cancel_old_positions.parse_args') as mock_parse_args:
            mock_parse_args.return_value = self.mock_args
            
            with patch('cancel_old_positions.TradingConfig'):
                with patch('cancel_old_positions.mtBase'):
                    with patch('cancel_old_positions.PredictionClient'):
                        with patch('cancel_old_positions.PositionClient'):
                            with patch('cancel_old_positions.BudgetMgmt'):
                                with patch('cancel_old_positions.get_positions_to_close', return_value=[]):
                                    with patch('cancel_old_positions.Path') as mock_path:
                                        # Mock Path for artifacts
                                        mock_results_path = MagicMock()
                                        mock_results_path.open.return_value.__enter__ = MagicMock()
                                        mock_results_path.open.return_value.__exit__ = MagicMock(return_value=None)
                                        mock_path_instance = MagicMock()
                                        mock_path_instance.__truediv__.return_value = mock_results_path
                                        mock_path.return_value = mock_path_instance
                                        
                                        with patch('cancel_old_positions.json.dump'):
                                            main(args=None, setup_logs=False)
            
            mock_parse_args.assert_called_once()
    
    def test_main_setup_logs_default_true(self):
        """Test that logging is set up by default."""
        with patch('cancel_old_positions.setup_console_and_file_logging') as mock_setup_logging:
            with patch('cancel_old_positions.TradingConfig'):
                with patch('cancel_old_positions.mtBase'):
                    with patch('cancel_old_positions.PredictionClient'):
                        with patch('cancel_old_positions.PositionClient'):
                            with patch('cancel_old_positions.BudgetMgmt'):
                                with patch('cancel_old_positions.get_positions_to_close', return_value=[]):
                                    with patch('cancel_old_positions.Path') as mock_path:
                                        # Mock Path for artifacts
                                        mock_results_path = MagicMock()
                                        mock_results_path.open.return_value.__enter__ = MagicMock()
                                        mock_results_path.open.return_value.__exit__ = MagicMock(return_value=None)
                                        mock_path_instance = MagicMock()
                                        mock_path_instance.__truediv__.return_value = mock_results_path
                                        mock_path.return_value = mock_path_instance
                                        
                                        with patch('cancel_old_positions.json.dump'):
                                            main(self.mock_args)  # setup_logs defaults to True
            
            mock_setup_logging.assert_called_once()


class TestCancelOldPositionsIntegration:
    """Integration-style tests that test multiple components together."""
    
    @patch('cancel_old_positions.time.sleep')
    @patch('builtins.open', mock_open())
    @patch('cancel_old_positions.place_order_req')
    def test_full_workflow_dry_run(self, mock_place_order, mock_sleep):
        """Test the complete workflow in dry-run mode with real-ish data flow."""
        mock_place_order.return_value = (0, "DRY RUN: Order check passed.")
        
        # Create a more complete test scenario
        with patch('cancel_old_positions.TradingConfig') as mock_config:
            with patch('cancel_old_positions.mtBase') as mock_base:
                with patch('cancel_old_positions.PredictionClient') as mock_pred_client:
                    with patch('cancel_old_positions.PositionClient') as mock_pos_client:
                        with patch('cancel_old_positions.BudgetMgmt') as mock_budget:
                            with patch('cancel_old_positions.get_positions_to_close') as mock_get_positions:
                                with patch('cancel_old_positions.Path') as mock_path:
                                    with patch('cancel_old_positions.json.dump') as mock_json_dump:
                                        # Setup realistic mock returns
                                        config_instance = MagicMock()
                                        config_instance.artifacts_dir = 'artifacts'
                                        config_instance.max_working_duration = timedelta(minutes=30)
                                        config_instance.credentials_path = 'secrets/creds.yaml'
                                        config_instance.mt5_config_path = 'secrets/mt5.ini'
                                        config_instance.per_day_divisor = 3
                                        config_instance.max_budget_discrepancy = 0.1
                                        config_instance.predictions_dir = 'predictions'
                                        mock_config.return_value = config_instance
                                        
                                        # Mock MT5 base
                                        base_instance = MagicMock()
                                        mock_base.return_value = base_instance
                                        
                                        # Mock prediction client
                                        test_prediction = PredictionData(
                                            symbol='TEST',
                                            last_training_day=date(2025, 11, 1),
                                            last_close_price=1.0,
                                            n_trading_days=5,
                                            score=0.75,
                                            magic=99999,
                                            sl_pct=0.05,
                                            tp_pct=0.05
                                        )
                                        pred_client_instance = MagicMock()
                                        pred_client_instance.load_predictions.return_value = [test_prediction]
                                        mock_pred_client.return_value = pred_client_instance
                                        
                                        budget_instance = MagicMock()
                                        budget_instance.free_margin = 5000.0
                                        budget_instance.calc_daily_budget.return_value = 1000.0
                                        mock_budget.return_value = budget_instance
                                        
                                        test_position = PositionData(
                                            ticket=12345, time=datetime.now(timezone.utc), time_msc=0,
                                            type=0, magic=99999, reason=0, volume=0.1, price_open=1.0,
                                            sl=None, tp=None, price_current=1.1, profit=10.0,
                                            symbol='TEST', comment='test'
                                        )
                                        
                                        pos_client_instance = MagicMock()
                                        pos_client_instance.get_positions.return_value = [test_position]  # Return the test position
                                        pos_client_instance.close_position_request.return_value = {'symbol': 'TEST'}
                                        pos_client_instance.log_positions = MagicMock()
                                        mock_pos_client.return_value = pos_client_instance
                                        
                                        # Mock Path for artifacts - need to mock Path() call and the / operator  
                                        mock_results_path = MagicMock()
                                        mock_results_path.open.return_value.__enter__ = MagicMock()
                                        mock_results_path.open.return_value.__exit__ = MagicMock(return_value=None)
                                        
                                        mock_artifacts_path = MagicMock()
                                        mock_artifacts_path.__truediv__.return_value = mock_results_path
                                        mock_path.return_value = mock_artifacts_path
                                        
                                        mock_get_positions.return_value = [test_position]
                                        
                                        args = MagicMock()
                                        args.apply = False
                                        args.group = 'test'
                                        
                                        result = main(args, setup_logs=False)
                                        
                                        assert len(result) == 1
                                        assert result[0] == test_position
                                        mock_place_order.assert_called_once()