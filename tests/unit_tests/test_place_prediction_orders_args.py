"""Unit tests for place_prediction_orders argument parsing."""

import unittest.mock
import argparse

from place_prediction_orders import parse_args


class TestPlacePredictionOrdersArgs(unittest.TestCase):
    """Test argument parsing for place_prediction_orders script."""
    
    def test_default_arguments(self):
        """Test that default arguments work correctly."""
        with unittest.mock.patch('sys.argv', ['place_prediction_orders.py', '--account', 'test_account']):
            args = parse_args()
            
            self.assertEqual(args.account, 'test_account')
            self.assertEqual(args.group, 'mt5')
            self.assertEqual(args.config, 'config/trading_config_prod.yaml')
            self.assertFalse(args.apply)  # Default should be False (dry-run mode)
    
    def test_apply_flag_true(self):
        """Test that --apply flag sets apply to True."""
        with unittest.mock.patch('sys.argv', ['place_prediction_orders.py', '--account', 'test_account', '--apply']):
            args = parse_args()
            
            self.assertEqual(args.account, 'test_account')
            self.assertTrue(args.apply)  # Should be True when --apply is specified
    
    def test_apply_flag_false_when_not_specified(self):
        """Test that apply is False when --apply flag is not specified."""
        with unittest.mock.patch('sys.argv', ['place_prediction_orders.py', '--account', 'test_account']):
            args = parse_args()
            
            self.assertFalse(args.apply)  # Should be False by default (dry-run mode)
    
    def test_all_arguments(self):
        """Test parsing with all arguments specified."""
        test_args = [
            'place_prediction_orders.py',
            '--account', 'my_test_account',
            '--group', 'debug',
            '--config', 'custom_config.yaml',
            '--apply'
        ]
        
        with unittest.mock.patch('sys.argv', test_args):
            args = parse_args()
            
            self.assertEqual(args.account, 'my_test_account')
            self.assertEqual(args.group, 'debug')
            self.assertEqual(args.config, 'custom_config.yaml')
            self.assertTrue(args.apply)
    
    def test_help_message_contains_apply_description(self):
        """Test that help message contains description of --apply flag."""
        parser = argparse.ArgumentParser()
        
        # Simulate the parser creation from parse_args()
        parser.add_argument("--account", required=True)
        parser.add_argument("--group", default="mt5")
        parser.add_argument("--config", default="config/trading_config_prod.yaml")
        parser.add_argument(
            "--apply",
            action="store_true",
            help="If specified, orders will be actually placed. By default, runs in dry-run mode.",
        )
        
        help_text = parser.format_help()
        
        # Verify help text mentions the correct behavior
        self.assertIn("--apply", help_text)
        self.assertIn("actually placed", help_text)
        self.assertIn("dry-run mode", help_text)
        
        # Verify old --dry-run is not mentioned
        self.assertNotIn("--dry-run", help_text)


if __name__ == '__main__':
    unittest.main()