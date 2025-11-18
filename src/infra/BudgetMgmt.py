from .mtBase import mtBase

import logging
logger = logging.getLogger(__name__)

class BudgetMgmt:
    def __init__(self, 
            base: mtBase, 
            per_day_divisor: float = 1.0, 
            max_budget_discrepancy: float = 0.1
        ) -> None:
        self._base = base
        self.per_day_divisor = per_day_divisor
        self.max_budget_discrepancy = max_budget_discrepancy
        account_info = self._base.get_account_info()
        if account_info is None:
            raise RuntimeError("Acount Info not available.")
        self.free_margin = self._get_free_margin()
        self.total_capital = self._get_total_capital()

    @property
    def base(self) -> mtBase:
        return self._base

    @base.setter
    def base(self, value: mtBase) -> None:
        self._base = value

    def _get_free_margin(self) -> float:
        account_info = self._base.get_account_info()

        margin_free = getattr(account_info, "margin_free", None)
        if margin_free is None or margin_free <= 1e-6:
            raise RuntimeError("Account has no margin_free information.")
        return margin_free
    
    def _get_total_capital(self) -> float:
        account_info = self._base.get_account_info()

        total_capital = getattr(account_info, "equity", None)
        if total_capital is None:
            logger.warning("Warning: equity is unavailable; falling back to balance.")
            total_capital = getattr(account_info, "balance", None)

        if total_capital is None or total_capital <= 1e-6:
            raise RuntimeError("Account has no total capital information.")
        
        return total_capital
    
    def refresh(self) -> None:
        """Refresh account information."""
        self.free_margin = self._get_free_margin()
        self.total_capital = self._get_total_capital()
    
    def calc_daily_budget(self) -> float:
        """
        Calculate the total available budget for trading operations.
        
        Determines the maximum expenditure allowed by taking the minimum of:
        1. Available free margin in the trading account
        2. Daily capital allocation (total capital divided by per-day divisor)
        
        This ensures trading operations don't exceed account limits or daily risk parameters.
        
        Returns:
            Maximum budget available for trading as a float
        """
        # Calculate daily capital allocation based on risk management divisor
        total_cap_per_day = self.total_capital / self.per_day_divisor

        # Use the more restrictive of free margin or daily allocation
        budget = min(self.free_margin, total_cap_per_day)
        return budget
