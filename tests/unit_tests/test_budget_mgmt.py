"""Unit tests for BudgetMgmt class."""

import pytest
from unittest.mock import MagicMock, patch

from src.infra.BudgetMgmt import BudgetMgmt
from src.infra.mtBase import mtBase


class TestBudgetMgmt:
    """Test cases for BudgetMgmt class."""
    
    def test_init_with_valid_account_info(self):
        """Test initialization with valid account information."""
        # Create mock mtBase
        mock_base = MagicMock(spec=mtBase)
        
        # Create mock account info
        mock_account_info = MagicMock()
        mock_account_info.margin_free = 5000.0
        mock_account_info.equity = 10000.0
        
        mock_base.get_account_info.return_value = mock_account_info
        
        budget = BudgetMgmt(base=mock_base, per_day_divisor=3.0)
        
        assert budget._base == mock_base
        assert budget.per_day_divisor == 3.0
        assert budget.max_budget_discrepancy == 0.1  # Default value
        assert budget.free_margin == 5000.0
        assert budget.total_capital == 10000.0
    
    def test_init_with_default_per_day_divisor(self):
        """Test initialization with default per_day_divisor."""
        # Create mock mtBase
        mock_base = MagicMock(spec=mtBase)
        
        # Create mock account info
        mock_account_info = MagicMock()
        mock_account_info.margin_free = 5000.0
        mock_account_info.equity = 10000.0
        
        mock_base.get_account_info.return_value = mock_account_info
        
        budget = BudgetMgmt(base=mock_base)
        
        assert budget.per_day_divisor == 1.0
        assert budget.max_budget_discrepancy == 0.1  # Default value
    
    def test_init_with_custom_max_budget_discrepancy(self):
        """Test initialization with custom max_budget_discrepancy."""
        # Create mock mtBase
        mock_base = MagicMock(spec=mtBase)
        
        # Create mock account info
        mock_account_info = MagicMock()
        mock_account_info.margin_free = 5000.0
        mock_account_info.equity = 10000.0
        
        mock_base.get_account_info.return_value = mock_account_info
        
        budget = BudgetMgmt(base=mock_base, per_day_divisor=2.0, max_budget_discrepancy=0.15)
        
        assert budget.per_day_divisor == 2.0
        assert budget.max_budget_discrepancy == 0.15
        assert budget.free_margin == 5000.0
        assert budget.total_capital == 10000.0
    
    def test_init_base_is_mandatory(self):
        """Test that base parameter is mandatory for initialization."""
        with pytest.raises(TypeError):
            BudgetMgmt()  # Should fail because base is required
    
    def test_init_account_info_none(self):
        """Test initialization when account info is None."""
        # Create mock mtBase
        mock_base = MagicMock(spec=mtBase)
        mock_base.get_account_info.return_value = None
        
        with pytest.raises(RuntimeError, match="Acount Info not available"):
            BudgetMgmt(base=mock_base)
    
    def test_init_no_margin_free(self):
        """Test initialization when margin_free is None."""
        # Create mock mtBase
        mock_base = MagicMock(spec=mtBase)
        
        # Create mock account info without margin_free
        mock_account_info = MagicMock()
        mock_account_info.margin_free = None
        mock_account_info.equity = 10000.0
        
        mock_base.get_account_info.return_value = mock_account_info
        
        with pytest.raises(RuntimeError, match="Account has no margin_free information"):
            BudgetMgmt(base=mock_base)
    
    def test_init_zero_margin_free(self):
        """Test initialization when margin_free is zero."""
        # Create mock mtBase
        mock_base = MagicMock(spec=mtBase)
        
        # Create mock account info with zero margin_free
        mock_account_info = MagicMock()
        mock_account_info.margin_free = 0.0
        mock_account_info.equity = 10000.0
        
        mock_base.get_account_info.return_value = mock_account_info
        
        with pytest.raises(RuntimeError, match="Account has no margin_free information"):
            BudgetMgmt(base=mock_base)
    
    def test_init_very_small_margin_free(self):
        """Test initialization when margin_free is very small."""
        # Create mock mtBase
        mock_base = MagicMock(spec=mtBase)
        
        # Create mock account info with very small margin_free
        mock_account_info = MagicMock()
        mock_account_info.margin_free = 1e-7  # Smaller than threshold
        mock_account_info.equity = 10000.0
        
        mock_base.get_account_info.return_value = mock_account_info
        
        with pytest.raises(RuntimeError, match="Account has no margin_free information"):
            BudgetMgmt(base=mock_base)
    
    def test_init_no_equity_uses_balance(self):
        """Test initialization when equity is None, falls back to balance."""
        # Create mock mtBase
        mock_base = MagicMock(spec=mtBase)
        
        # Create mock account info without equity but with balance
        mock_account_info = MagicMock()
        mock_account_info.margin_free = 5000.0
        mock_account_info.equity = None
        mock_account_info.balance = 8000.0
        
        mock_base.get_account_info.return_value = mock_account_info
        
        with patch('src.infra.BudgetMgmt.logger') as mock_logger:
            budget = BudgetMgmt(base=mock_base)
            
            assert budget.total_capital == 8000.0
            mock_logger.warning.assert_called_once_with("Warning: equity is unavailable; falling back to balance.")
    
    def test_init_no_equity_no_balance(self):
        """Test initialization when both equity and balance are None."""
        # Create mock mtBase
        mock_base = MagicMock(spec=mtBase)
        
        # Create mock account info without equity or balance
        mock_account_info = MagicMock()
        mock_account_info.margin_free = 5000.0
        mock_account_info.equity = None
        mock_account_info.balance = None
        
        mock_base.get_account_info.return_value = mock_account_info
        
        with pytest.raises(RuntimeError, match="Account has no total capital information"):
            BudgetMgmt(base=mock_base)
    
    def test_init_zero_total_capital(self):
        """Test initialization when total capital is zero."""
        # Create mock mtBase
        mock_base = MagicMock(spec=mtBase)
        
        # Create mock account info with zero equity
        mock_account_info = MagicMock()
        mock_account_info.margin_free = 5000.0
        mock_account_info.equity = 0.0
        
        mock_base.get_account_info.return_value = mock_account_info
        
        with pytest.raises(RuntimeError, match="Account has no total capital information"):
            BudgetMgmt(base=mock_base)
    
    def test_base_property_getter(self):
        """Test base property getter."""
        # Create mock mtBase
        mock_base = MagicMock(spec=mtBase)
        
        # Create mock account info
        mock_account_info = MagicMock()
        mock_account_info.margin_free = 5000.0
        mock_account_info.equity = 10000.0
        
        mock_base.get_account_info.return_value = mock_account_info
        
        budget = BudgetMgmt(base=mock_base)
        
        assert budget.base == mock_base
    
    def test_base_property_setter(self):
        """Test base property setter."""
        # Create initial mock mtBase
        mock_base1 = MagicMock(spec=mtBase)
        mock_account_info = MagicMock()
        mock_account_info.margin_free = 5000.0
        mock_account_info.equity = 10000.0
        mock_base1.get_account_info.return_value = mock_account_info
        
        budget = BudgetMgmt(base=mock_base1)
        
        # Create new mock mtBase
        mock_base2 = MagicMock(spec=mtBase)
        
        # Set new base
        budget.base = mock_base2
        
        assert budget._base == mock_base2
    
    def test_refresh(self):
        """Test refresh method."""
        # Create mock mtBase
        mock_base = MagicMock(spec=mtBase)
        
        # Initial account info
        initial_account_info = MagicMock()
        initial_account_info.margin_free = 5000.0
        initial_account_info.equity = 10000.0
        
        # Updated account info
        updated_account_info = MagicMock()
        updated_account_info.margin_free = 6000.0
        updated_account_info.equity = 12000.0
        
        # Set up mock to return initial values during initialization
        mock_base.get_account_info.return_value = initial_account_info
        
        budget = BudgetMgmt(base=mock_base)
        
        # Verify initial values
        assert budget.free_margin == 5000.0
        assert budget.total_capital == 10000.0
        
        # Now change mock to return updated values for refresh
        mock_base.get_account_info.return_value = updated_account_info
        
        # Call refresh
        budget.refresh()
        
        # Verify updated values
        assert budget.free_margin == 6000.0
        assert budget.total_capital == 12000.0
    
    def test_get_free_margin_private_method(self):
        """Test _get_free_margin private method."""
        # Create mock mtBase
        mock_base = MagicMock(spec=mtBase)
        
        # Create mock account info
        mock_account_info = MagicMock()
        mock_account_info.margin_free = 7500.0
        mock_account_info.equity = 15000.0
        
        mock_base.get_account_info.return_value = mock_account_info
        
        budget = BudgetMgmt(base=mock_base)
        
        # Test the private method
        result = budget._get_free_margin()
        assert result == 7500.0
    
    def test_get_total_capital_private_method(self):
        """Test _get_total_capital private method."""
        # Create mock mtBase
        mock_base = MagicMock(spec=mtBase)
        
        # Create mock account info
        mock_account_info = MagicMock()
        mock_account_info.margin_free = 7500.0
        mock_account_info.equity = 15000.0
        
        mock_base.get_account_info.return_value = mock_account_info
        
        budget = BudgetMgmt(base=mock_base)
        
        # Test the private method
        result = budget._get_total_capital()
        assert result == 15000.0
    

    
    def test_edge_case_margin_free_exactly_threshold(self):
        """Test edge case when margin_free is exactly at the threshold."""
        # Create mock mtBase
        mock_base = MagicMock(spec=mtBase)
        
        # Create mock account info with margin_free exactly at threshold
        mock_account_info = MagicMock()
        mock_account_info.margin_free = 1e-6  # Exactly at threshold
        mock_account_info.equity = 10000.0
        
        mock_base.get_account_info.return_value = mock_account_info
        
        # Should raise error since <= 1e-6
        with pytest.raises(RuntimeError, match="Account has no margin_free information"):
            BudgetMgmt(base=mock_base)
    
    def test_edge_case_total_capital_exactly_threshold(self):
        """Test edge case when total capital is exactly at the threshold."""
        # Create mock mtBase
        mock_base = MagicMock(spec=mtBase)
        
        # Create mock account info with equity exactly at threshold
        mock_account_info = MagicMock()
        mock_account_info.margin_free = 5000.0
        mock_account_info.equity = 1e-6  # Exactly at threshold
        
        mock_base.get_account_info.return_value = mock_account_info
        
        # Should raise error since <= 1e-6
        with pytest.raises(RuntimeError, match="Account has no total capital information"):
            BudgetMgmt(base=mock_base)
    
    def test_calc_daily_budget_basic_functionality(self):
        """Test calc_daily_budget method with basic scenarios."""
        # Create mock mtBase
        mock_base = MagicMock(spec=mtBase)
        
        # Test case where free margin is limiting
        mock_account_info = MagicMock()
        mock_account_info.margin_free = 2000.0  # Lower than daily allocation
        mock_account_info.equity = 12000.0      # 12000 / 3 = 4000 daily
        
        mock_base.get_account_info.return_value = mock_account_info
        
        budget = BudgetMgmt(base=mock_base, per_day_divisor=3.0)
        result = budget.calc_daily_budget()
        
        # Should return free margin as it's smaller
        assert result == 2000.0
    
    def test_calc_daily_budget_daily_allocation_limiting(self):
        """Test calc_daily_budget when daily allocation is the limiting factor."""
        # Create mock mtBase
        mock_base = MagicMock(spec=mtBase)
        
        # Test case where daily allocation is limiting
        mock_account_info = MagicMock()
        mock_account_info.margin_free = 8000.0  # Higher than daily allocation
        mock_account_info.equity = 15000.0      # 15000 / 5 = 3000 daily
        
        mock_base.get_account_info.return_value = mock_account_info
        
        budget = BudgetMgmt(base=mock_base, per_day_divisor=5.0)
        result = budget.calc_daily_budget()
        
        # Should return daily allocation as it's smaller
        assert result == 3000.0
    
    def test_refresh_error_handling(self):
        """Test refresh method error handling."""
        # Create mock mtBase
        mock_base = MagicMock(spec=mtBase)
        
        # Initial account info
        initial_account_info = MagicMock()
        initial_account_info.margin_free = 5000.0
        initial_account_info.equity = 10000.0
        
        mock_base.get_account_info.return_value = initial_account_info
        
        budget = BudgetMgmt(base=mock_base)
        
        # Now simulate account info becoming None
        mock_base.get_account_info.return_value = None
        
        # refresh() should raise RuntimeError
        with pytest.raises(RuntimeError, match="Account has no margin_free information"):
            budget.refresh()