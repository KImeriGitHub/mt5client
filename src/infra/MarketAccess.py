from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Tuple
import MetaTrader5 as mt5

from .mtBase import mtBase

import logging
logger = logging.getLogger(__name__)

class MarketAccess:
    """High level utilities for checking market availability."""

    """
        Especially, established that tick data is recent enough to consider the market open.
    """

    def __init__(self, base: mtBase) -> None:
        self._base = base

    def is_market_open(self, symbol: str, max_tick_age_seconds: int) -> int:
        """Check whether trading is currently possible for the symbol.
        Input:
            symbol: Symbol to check.
        """
        info = self._base.get_symbol_info(symbol, wait_sec=0.1)
        if info is None:
            return 1

        if info["trade_mode"] == mt5.SYMBOL_TRADE_MODE_DISABLED:
            logger.warning(f"Symbol '{symbol}' trade mode is disabled.")
            return 1

        pricetick = self._base.get_symbol_price(symbol, wait_sec=0.1)
        if pricetick is None:
            return 1

        pricetick_time = pricetick.get("time_msc")
        if pricetick_time is None:
            return 1
        
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)  # UTC ms
        age_ms = max(0.0, now_ms - pricetick_time)
        if age_ms > max_tick_age_seconds * 1000:
            return 1

        return 0

    def wait_for_low_tick_age(
        self,
        symbol: str,
        max_duration_seconds: int,
        max_tick_age_seconds: int = 10,
    ) -> int:
        """Poll until the market opens or the deadline passes.
        Input:
            symbol: Symbol to check.
            max_duration_seconds: Maximum seconds to wait for the market to open
            max_tick_age_seconds: Maximum age in seconds for the latest tick before
                considering the market closed.
        Returns:
            market access given.
        """
        assert max_duration_seconds > 0, "max_duration_seconds must be positive"

        deadline = time.time() + max_duration_seconds
        while time.time() <= deadline:
            status = self.is_market_open(symbol, max_tick_age_seconds)
            if status == 0:
                return 0

        return 1