from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Tuple
import MetaTrader5 as mt5

from .mtBase import mtBase

import logging
logger = logging.getLogger(__name__)

class MarketAccessClient:
    """High level utilities for checking market availability."""

    def __init__(self, base: mtBase) -> None:
        self._base = base

    def is_market_open(self, symbol: str, max_tick_age_seconds: int) -> int:
        """Check whether trading is currently possible for the symbol.
        Input:
            symbol: Symbol to check.
            max_tick_age_seconds: Maximum age of the latest tick data to consider
                the market open.
        """
        if not self._base.select_symbol(symbol, True):
            logger.info("Access Market: Symbol selection not available: %s", symbol)
            return 1

        info = self._base.get_symbol_info(symbol)
        if info is None:
            logger.info("Access Market: Symbol info unavailable: %s", symbol)
            return 1

        if info.trade_mode == mt5.SYMBOL_TRADE_MODE_DISABLED:
            logger.info("Access Market: Trade mode disabled: %s", symbol)
            return 1

        tick = self._base.get_symbol_tick(symbol)
        if tick is None:
            logger.info("Access Market: No tick data available: %s", symbol)
            return 1

        tick_time = getattr(tick, "time", None)
        if tick_time is None:
            logger.info("Access Market: Tick time unavailable: %s", symbol)
            return 1
        tick_dt = datetime.fromtimestamp(tick_time, tz=timezone.utc)
        age_seconds = (datetime.now(timezone.utc) - tick_dt).total_seconds()
        if age_seconds > max_tick_age_seconds:
            logger.info(f"Access Market: Tick data too old ({age_seconds}s): %s", symbol)
            return 2

        return 0

    def wait_for_market_access(
        self,
        symbol: str,
        max_wait_seconds: int,
        check_interval_seconds: int,
        max_tick_age_seconds: int,
    ) -> bool:
        """Poll until the market opens or the deadline passes.
        Input:
            symbol: Symbol to check.
            max_wait_seconds: Maximum seconds to wait for the market to open
            check_interval_seconds: Seconds between market-open checks when waiting.
            max_tick_age_minutes: Maximum age in minutes for the latest tick before
                considering the market closed.
        """
        assert max_wait_seconds > 0, "max_wait_seconds must be positive"

        deadline = time.time() + max_wait_seconds
        while True:
            status = self.is_market_open(symbol, max_tick_age_seconds)
            if status == 0:
                logger.info("Market open for symbol: %s", symbol)
                return 0

            if status == 2:
                logger.warning("Market closed due to stale tick data for symbol: %s", symbol)
                return 2

            if time.time() >= deadline:
                logger.info("Market did not open in time for symbol: %s", symbol)
                return 1

            time.sleep(max(check_interval_seconds, 5))
