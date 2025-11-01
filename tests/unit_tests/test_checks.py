"""Unit tests for Checks.py class."""

import pytest
from unittest.mock import MagicMock

from src.Checks import Checks
from src.infra.PredictionData import PredictionData
from src.infra.PositionData import PositionData


class TestChecks:
    """Test cases for Checks class."""
    
    def test_init(self):
        """Test Checks initialization."""
        checks = Checks()
        assert isinstance(checks, Checks)
    
    def test_preds_in_positions_no_overlap(self):
        """Test preds_in_positions with no overlapping magic numbers."""
        # Create mock predictions
        pred1 = MagicMock()
        pred1.magic = 12345
        pred2 = MagicMock()
        pred2.magic = 67890
        predictions = [pred1, pred2]
        
        # Create mock positions with different magic numbers
        pos1 = MagicMock()
        pos1.magic = 11111
        pos2 = MagicMock()
        pos2.magic = 22222
        positions = [pos1, pos2]
        
        result = Checks.preds_in_positions(predictions, positions)
        assert result is False
    
    def test_preds_in_positions_with_overlap(self):
        """Test preds_in_positions with overlapping magic numbers."""
        # Create mock predictions
        pred1 = MagicMock()
        pred1.magic = 12345
        pred2 = MagicMock()
        pred2.magic = 67890
        predictions = [pred1, pred2]
        
        # Create mock positions with one overlapping magic number
        pos1 = MagicMock()
        pos1.magic = 12345  # Same as pred1
        pos2 = MagicMock()
        pos2.magic = 22222
        positions = [pos1, pos2]
        
        result = Checks.preds_in_positions(predictions, positions)
        assert result is True
    
    def test_preds_in_positions_multiple_overlaps(self):
        """Test preds_in_positions with multiple overlapping magic numbers."""
        # Create mock predictions
        pred1 = MagicMock()
        pred1.magic = 12345
        pred2 = MagicMock()
        pred2.magic = 67890
        pred3 = MagicMock()
        pred3.magic = 99999
        predictions = [pred1, pred2, pred3]
        
        # Create mock positions with multiple overlapping magic numbers
        pos1 = MagicMock()
        pos1.magic = 12345  # Same as pred1
        pos2 = MagicMock()
        pos2.magic = 67890  # Same as pred2
        pos3 = MagicMock()
        pos3.magic = 33333
        positions = [pos1, pos2, pos3]
        
        result = Checks.preds_in_positions(predictions, positions)
        assert result is True
    
    def test_preds_in_positions_empty_predictions(self):
        """Test preds_in_positions with empty predictions list."""
        predictions = []
        
        # Create mock positions
        pos1 = MagicMock()
        pos1.magic = 12345
        positions = [pos1]
        
        result = Checks.preds_in_positions(predictions, positions)
        assert result is False
    
    def test_preds_in_positions_empty_positions(self):
        """Test preds_in_positions with empty positions list."""
        # Create mock predictions
        pred1 = MagicMock()
        pred1.magic = 12345
        predictions = [pred1]
        
        positions = []
        
        result = Checks.preds_in_positions(predictions, positions)
        assert result is False
    
    def test_preds_in_positions_both_empty(self):
        """Test preds_in_positions with both lists empty."""
        predictions = []
        positions = []
        
        result = Checks.preds_in_positions(predictions, positions)
        assert result is False
    
    def test_preds_in_positions_duplicate_magics_in_predictions(self):
        """Test preds_in_positions with duplicate magic numbers in predictions."""
        # Create mock predictions with duplicate magics
        pred1 = MagicMock()
        pred1.magic = 12345
        pred2 = MagicMock()
        pred2.magic = 12345  # Duplicate
        pred3 = MagicMock()
        pred3.magic = 67890
        predictions = [pred1, pred2, pred3]
        
        # Create mock positions
        pos1 = MagicMock()
        pos1.magic = 12345  # Matches the duplicate magic
        positions = [pos1]
        
        result = Checks.preds_in_positions(predictions, positions)
        assert result is True
    
    def test_preds_in_positions_duplicate_magics_in_positions(self):
        """Test preds_in_positions with duplicate magic numbers in positions."""
        # Create mock predictions
        pred1 = MagicMock()
        pred1.magic = 12345
        predictions = [pred1]
        
        # Create mock positions with duplicate magics
        pos1 = MagicMock()
        pos1.magic = 12345
        pos2 = MagicMock()
        pos2.magic = 12345  # Duplicate
        pos3 = MagicMock()
        pos3.magic = 67890
        positions = [pos1, pos2, pos3]
        
        result = Checks.preds_in_positions(predictions, positions)
        assert result is True
    
    def test_preds_in_positions_large_lists(self):
        """Test preds_in_positions with larger lists for performance."""
        # Create many mock predictions
        predictions = []
        for i in range(100):
            pred = MagicMock()
            pred.magic = i
            predictions.append(pred)
        
        # Create many mock positions with no overlaps
        positions = []
        for i in range(100, 200):
            pos = MagicMock()
            pos.magic = i
            positions.append(pos)
        
        result = Checks.preds_in_positions(predictions, positions)
        assert result is False
        
        # Now add one overlapping magic
        pos_overlap = MagicMock()
        pos_overlap.magic = 50  # This should match one of the predictions
        positions.append(pos_overlap)
        
        result = Checks.preds_in_positions(predictions, positions)
        assert result is True
    
    def test_preds_in_positions_static_method(self):
        """Test that preds_in_positions is properly defined as static method."""
        # Should be callable without instantiating the class
        pred = MagicMock()
        pred.magic = 12345
        predictions = [pred]
        
        pos = MagicMock()
        pos.magic = 67890
        positions = [pos]
        
        result = Checks.preds_in_positions(predictions, positions)
        assert result is False
        
        # Verify it's also callable from an instance
        checks = Checks()
        result = checks.preds_in_positions(predictions, positions)
        assert result is False