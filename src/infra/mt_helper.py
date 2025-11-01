import math
from typing import Literal, Any, Optional
import MetaTrader5 as mt5
import polars as pl
import time

import logging
logger = logging.getLogger(__name__)

###################
### GET ACTIONS ###
###################
def _to_df(namedtuples: Any) -> pl.DataFrame:
    """Convert MT5 namedtuples to a Polars DataFrame."""
    if not namedtuples:  # handles None and empty tuple
        return pl.DataFrame()
    rows = [nt._asdict() for nt in namedtuples]
    return pl.DataFrame(rows)

def get_positions_helper() -> pl.DataFrame | None:
    """
    Return current open positions as a Polars DataFrame.

    Returns:
        pl.DataFrame | None: DataFrame containing current open positions with columns
            converted from MT5 namedtuples, or None if no positions exist.
            Includes a `time_dt` column with timestamps converted to Datetime format.

    Raises:
        ValueError: If expected 'time_msc' column is missing from non-empty positions.
    """
    positions = mt5.positions_get()
    if positions is None:
        return None
    
    df = _to_df(positions)
    if df.is_empty():
        return df
    
    if not "time_msc" in df.columns:
        raise ValueError("Expected 'time_msc' column in non-empty positions DataFrame.")

    df = df.with_columns(
        pl.from_epoch(pl.col("time_msc"), time_unit="ms").alias("time_dt")
    )

    return df

def get_orders_helper() -> pl.DataFrame | None:
    """
    Return current pending orders as a Polars DataFrame.

    Returns:
        pl.DataFrame | None: DataFrame containing current pending orders with columns
            converted from MT5 namedtuples, or None if no orders exist.
            Includes a `time_dt` column with timestamps converted to Datetime format.

    Raises:
        ValueError: If expected 'time_setup_msc' column is missing from non-empty orders.
    """
    orders = mt5.orders_get()
    if orders is None:
        return None
    
    df = _to_df(orders)
    if df.is_empty():
        return df

    if not "time_setup_msc" in df.columns:
        raise ValueError("Expected 'time_setup_msc' column in non-empty orders DataFrame.")
    
    df = df.with_columns(
        pl.from_epoch(pl.col("time_setup_msc"), time_unit="ms").alias("time_dt")
    )

    return df

def _get_tick(symbol: str, wait_sec: float = 0.05) -> Any:
    """
    Ensure symbol is selected and poll for a non-empty tick.

    Args:
        symbol: The MT5 symbol to get tick data for.
        wait_sec: Maximum time to wait for a valid tick in seconds.

    Returns:
        MT5 Tick object with valid bid, ask, or last price data.

    Raises:
        RuntimeError: If symbol cannot be selected or no fresh tick received within timeout.
    """

    info = mt5.symbol_info(symbol)
    was_visible = bool(info and info.visible)
    if not was_visible and not mt5.symbol_select(symbol, True):
        return None

    time.sleep(wait_sec)

    tick = mt5.symbol_info_tick(symbol)
    
    time.sleep(wait_sec)

    if not was_visible:
        mt5.symbol_select(symbol, False)

    return tick

def _get_info(symbol: str, wait_sec: float = 0.2) -> Any:
    """
    Ensure symbol is selected and poll for SymbolInfo with populated live price fields.

    Args:
        symbol: The MT5 symbol to get info for.
        wait_step_sec: Sleep interval between polling attempts in seconds.
        max_wait_sec: Maximum time to wait for valid symbol info in seconds.

    Returns:
        MT5 SymbolInfo object with populated live price data (bid, ask, or last).

    Raises:
        RuntimeError: If symbol cannot be selected or no live symbol info received within timeout.
    """

    info = mt5.symbol_info(symbol)
    was_visible = bool(info and info.visible)
    if not was_visible and not mt5.symbol_select(symbol, True):
        return None

    time.sleep(wait_sec)

    info = mt5.symbol_info(symbol)

    time.sleep(wait_sec)

    if not was_visible:
        mt5.symbol_select(symbol, False)

    return info

def get_symbol_price_helper(symbol: str, wait_sec: float = 0.2) -> dict | None:
    """
    Return a compact price dictionary using the freshest tick data.

    Args:
        symbol: The MT5 symbol to get price data for.
        wait_step_sec: Sleep interval between polling attempts in seconds.
        max_wait_sec: Maximum time to wait for valid tick data in seconds.

    Returns:
        dict: Price information containing bid, ask, last, spread, spread_rel,
            time, time_msc, volume, volume_real, and flags.

    Raises:
        RuntimeError: If unable to get tick data or extract required fields.
    """
    tick = _get_tick(symbol, wait_sec=wait_sec)

    if tick is None:
        return None
    
    if (getattr(tick, "bid", None) is None 
        or getattr(tick, "ask", None) is None 
        or getattr(tick, "last", None) is None):
        return None

    bid = tick.bid
    ask = tick.ask
    last = tick.last
    spread = ask - bid
    spread_rel = (spread / (bid + 1e-8))

    try:
        res = {
            "symbol": symbol,
            "bid": bid,
            "ask": ask,
            "last": last,
            "spread": spread,
            "spread_rel": spread_rel,
            "time": getattr(tick, "time"),
            "time_msc": getattr(tick, "time_msc"),
            "volume": getattr(tick, "volume"),
            "volume_real": getattr(tick, "volume_real"),
            "flags": getattr(tick, "flags"),
        }
    except:
        raise RuntimeError(f"Error extracting tick data for '{symbol}'.")
    
    return res

def get_symbol_info_helper(symbol: str, wait_sec: float = 0.05) -> dict | None:
    """
    Return comprehensive symbol information including static and live price data.

    Args:
        symbol: The MT5 symbol to get information for.
        wait_step_sec: Sleep interval between polling attempts in seconds.
        max_wait_sec: Maximum time to wait for valid symbol info in seconds.

    Returns:
        dict: Complete symbol information including trading parameters, price data,
            contract specifications, and currency information.

    Raises:
        RuntimeError: If unable to get symbol info or extract required fields.
    """
    info = _get_info(symbol, wait_sec=wait_sec)

    if info is None:
        return None
    
    try:
        res = {
            "symbol": symbol,
            "visible": bool(info.visible),
            "trade_mode": int(info.trade_mode),
            "digits": int(info.digits),
            "point": float(info.point),
            "time": getattr(info, "time"),
            "volume": getattr(info, "volume"),
            "volume_real": getattr(info, "volume_real"),
            "trade_contract_size": getattr(info, "trade_contract_size"),
            "volume_min": getattr(info, "volume_min"),
            "volume_max": getattr(info, "volume_max"),
            "volume_step": getattr(info, "volume_step"),
            "currency_base": getattr(info, "currency_base"),
            "currency_profit": getattr(info, "currency_profit"),
            "currency_margin": getattr(info, "currency_margin"),
            "trade_stops_level": getattr(info, "trade_stops_level"),
            "trade_freeze_level": getattr(info, "trade_freeze_level"),
            "filling_mode": getattr(info, "filling_mode"),
            "expiration_mode": getattr(info, "expiration_mode"),
            "category": getattr(info, "category"),
        }
    except Exception as e:
        raise RuntimeError(f"Error extracting symbol info for '{symbol}': {e}")
    
    return res