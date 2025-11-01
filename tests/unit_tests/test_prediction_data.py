"""Unit tests for PredictionData class."""

import pytest
from datetime import date
from unittest.mock import MagicMock

from src.infra.PredictionData import PredictionData


class TestPredictionData:
    """Test cases for PredictionData class."""
    
    def test_init_required_params_only(self):
        """Test initialization with only required parameters."""
        symbol = "EURUSD"
        last_training_day = date(2025, 10, 14)
        last_close_price = 1.0845
        n_trading_days = 5
        score = 0.73
        magic = 12345678901234567890
        
        pred = PredictionData(
            symbol=symbol,
            last_training_day=last_training_day,
            last_close_price=last_close_price,
            n_trading_days=n_trading_days,
            score=score,
            magic=magic
        )
        
        assert pred.symbol == symbol
        assert pred.last_training_day == last_training_day
        assert pred.last_close_price == last_close_price
        assert pred.n_trading_days == n_trading_days
        assert pred.score == score
        assert pred.magic == magic
        assert pred.sl_pct is None
        assert pred.tp_pct is None
        assert pred.source is None
    
    def test_init_all_params(self):
        """Test initialization with all parameters."""
        symbol = "NVDA"
        last_training_day = date(2025, 10, 15)
        last_close_price = 875.23
        n_trading_days = 3
        score = 0.82
        magic = 98765432109876543210
        sl_pct = 0.05
        tp_pct = 0.15
        source = "prediction_debug_15oct2025_001.json"
        
        pred = PredictionData(
            symbol=symbol,
            last_training_day=last_training_day,
            last_close_price=last_close_price,
            n_trading_days=n_trading_days,
            score=score,
            magic=magic,
            sl_pct=sl_pct,
            tp_pct=tp_pct,
            source=source
        )
        
        assert pred.symbol == symbol
        assert pred.last_training_day == last_training_day
        assert pred.last_close_price == last_close_price
        assert pred.n_trading_days == n_trading_days
        assert pred.score == score
        assert pred.magic == magic
        assert pred.sl_pct == sl_pct
        assert pred.tp_pct == tp_pct
        assert pred.source == source
    
    def test_init_partial_optional_params(self):
        """Test initialization with some optional parameters."""
        pred = PredictionData(
            symbol="MU",
            last_training_day=date(2025, 10, 16),
            last_close_price=92.45,
            n_trading_days=7,
            score=0.65,
            magic=555666777888999000,
            sl_pct=0.08,
            source="test_source.json"
            # tp_pct intentionally omitted
        )
        
        assert pred.symbol == "MU"
        assert pred.sl_pct == 0.08
        assert pred.tp_pct is None
        assert pred.source == "test_source.json"
    
    def test_repr(self):
        """Test string representation."""
        pred = PredictionData(
            symbol="GBPJPY",
            last_training_day=date(2025, 10, 17),
            last_close_price=189.45,
            n_trading_days=2,
            score=0.78,
            magic=111222333444555666,
            sl_pct=0.03,
            tp_pct=0.06,
            source="test.json"
        )
        
        expected = ("PredictionData(symbol='GBPJPY', "
                   "last_training_day='2025-10-17', "
                   "last_close_price=189.45, "
                   "n_trading_days=2, "
                   "score=0.78, "
                   "magic=111222333444555666, "
                   "sl_pct=0.03, "
                   "tp_pct=0.06, "
                   "source=test.json)")
        
        assert repr(pred) == expected
    
    def test_repr_with_none_values(self):
        """Test string representation with None values."""
        pred = PredictionData(
            symbol="AUDUSD",
            last_training_day=date(2025, 10, 18),
            last_close_price=0.6789,
            n_trading_days=4,
            score=0.71,
            magic=777888999000111222
        )
        
        expected = ("PredictionData(symbol='AUDUSD', "
                   "last_training_day='2025-10-18', "
                   "last_close_price=0.6789, "
                   "n_trading_days=4, "
                   "score=0.71, "
                   "magic=777888999000111222, "
                   "sl_pct=None, "
                   "tp_pct=None, "
                   "source=None)")
        
        assert repr(pred) == expected
    
    def test_to_dict_required_only(self):
        """Test to_dict with only required parameters."""
        pred = PredictionData(
            symbol="USDJPY",
            last_training_day=date(2025, 10, 19),
            last_close_price=150.25,
            n_trading_days=6,
            score=0.69,
            magic=333444555666777888
        )
        
        result = pred.to_dict()
        
        expected = {
            'symbol': 'USDJPY',
            'last_training_day': '2025-10-19',
            'last_close_price': 150.25,
            'n_trading_days': 6,
            'score': 0.69,
            'magic': 333444555666777888
        }
        
        assert result == expected
    
    def test_to_dict_all_params(self):
        """Test to_dict with all parameters."""
        pred = PredictionData(
            symbol="EURGBP",
            last_training_day=date(2025, 10, 20),
            last_close_price=0.8654,
            n_trading_days=1,
            score=0.88,
            magic=999000111222333444,
            sl_pct=0.02,
            tp_pct=0.04,
            source="comprehensive_test.json"
        )
        
        result = pred.to_dict()
        
        expected = {
            'symbol': 'EURGBP',
            'last_training_day': '2025-10-20',
            'last_close_price': 0.8654,
            'n_trading_days': 1,
            'score': 0.88,
            'magic': 999000111222333444,
            'sl_pct': 0.02,
            'tp_pct': 0.04,
            'source': 'comprehensive_test.json'
        }
        
        assert result == expected
    
    def test_to_dict_partial_optional(self):
        """Test to_dict with some optional parameters."""
        pred = PredictionData(
            symbol="CHFJPY",
            last_training_day=date(2025, 10, 21),
            last_close_price=165.89,
            n_trading_days=8,
            score=0.75,
            magic=123456789012345678,
            tp_pct=0.12,
            source="partial_test.json"
            # sl_pct intentionally omitted
        )
        
        result = pred.to_dict()
        
        expected = {
            'symbol': 'CHFJPY',
            'last_training_day': '2025-10-21',
            'last_close_price': 165.89,
            'n_trading_days': 8,
            'score': 0.75,
            'magic': 123456789012345678,
            'tp_pct': 0.12,
            'source': 'partial_test.json'
        }
        
        assert result == expected
        assert 'sl_pct' not in result  # Should not be included when None
    
    def test_edge_case_zero_values(self):
        """Test with edge case zero values."""
        pred = PredictionData(
            symbol="TEST",
            last_training_day=date(2025, 1, 1),
            last_close_price=0.0,
            n_trading_days=0,
            score=0.0,
            magic=0,
            sl_pct=0.0,
            tp_pct=0.0
        )
        
        assert pred.last_close_price == 0.0
        assert pred.n_trading_days == 0
        assert pred.score == 0.0
        assert pred.magic == 0
        assert pred.sl_pct == 0.0
        assert pred.tp_pct == 0.0
        
        # Check that zero values are included in dict (not treated as None)
        result = pred.to_dict()
        assert 'sl_pct' in result
        assert 'tp_pct' in result
        assert result['sl_pct'] == 0.0
        assert result['tp_pct'] == 0.0
    
    def test_negative_values(self):
        """Test with negative values where applicable."""
        pred = PredictionData(
            symbol="NEGATIVE",
            last_training_day=date(2025, 12, 31),
            last_close_price=-1.0,  # Unusual but technically possible
            n_trading_days=1,
            score=-0.5,  # Negative score
            magic=1,
            sl_pct=-0.1,  # Negative percentages (unusual but not invalid)
            tp_pct=-0.2
        )
        
        assert pred.last_close_price == -1.0
        assert pred.score == -0.5
        assert pred.sl_pct == -0.1
        assert pred.tp_pct == -0.2
    
    def test_large_values(self):
        """Test with large values."""
        large_magic = 2**63 - 1  # Maximum 64-bit signed integer
        
        pred = PredictionData(
            symbol="LARGE" * 10,  # Long symbol name
            last_training_day=date(9999, 12, 31),  # Far future date
            last_close_price=1e10,  # Very large price
            n_trading_days=1000,  # Large number of days
            score=100.0,  # Large score
            magic=large_magic
        )
        
        assert pred.symbol == "LARGE" * 10
        assert pred.last_training_day == date(9999, 12, 31)
        assert pred.last_close_price == 1e10
        assert pred.n_trading_days == 1000
        assert pred.score == 100.0
        assert pred.magic == large_magic