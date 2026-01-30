"""Check closing price condition for a symbol before closing positions."""

import datetime as dt
import pandas as pd
import numpy as np
import MetaTrader5 as mt5

from src.infra.mtBase import mtBase

import logging
logger = logging.getLogger(__name__)

def evaluate_closing_condition(
    bid_prices: np.ndarray,
    df: pd.DataFrame,
    sym: str
):
    """Evaluate whether the price condition is met for closing a position.
    
    This function analyzes price movement patterns to determine if market conditions
    are favorable for closing a buy position. It evaluates price trends, momentum, and
    volatility characteristics over the available data window.
    
    Args:
        bid_prices: Array of bid prices for the symbol. Must contain at least 5 finite
            values. Invalid or NaN values will be filtered out.
        df: DataFrame containing tick data with at least a 'time' column (pd.Timestamp)
            representing the timestamp for each tick. Must have at least 5 rows.
        sym: Trading symbol identifier string, used for logging and error messages.
    
    Returns:
        tuple[int, str]: A tuple containing:
            - status (int): 
                * 0 if price condition is met (proceed with closing position)
                * 1 if condition is not met (keep position open)
            - message (str): Detailed explanation of the result, including:
                * Return %, slope, quantile level (if applicable), residual values
    
    Logic:
        1. Validates input data has at least 5 data points
        2. Filters out non-finite prices
        3. Performs per-second aggregation and interpolation
        4. Fits linear trend and calculates residuals
        5. Decision logic:
           - If ret < 0.995: Close position (cut losses)
           - If ret > 1.005: Keep position open (let it run)
           - Otherwise: Check if last residual exceeds adaptive threshold
    """
    behaviour_str = f"CLOSE-COND {sym}:"

    if len(bid_prices) < 5 or len(df) < 5:
        return 1, f"{behaviour_str} Error: The bid_prices or times contain too few data points."

    y_bid = bid_prices
    t = df["time"]

    # Filter out non-finite values
    ok = np.isfinite(y_bid)
    y_bid = y_bid[ok]
    t = t.iloc[np.where(ok)[0]]
    
    if len(y_bid) < 5:
        return 1, f"{behaviour_str} Error: Too few finite values after filtering."

    # Per-second mean + linear time interpolation
    ts = t.dt.floor("s")
    s_bid = pd.Series(y_bid, index=ts).groupby(level=0).mean()
    
    if len(s_bid) < 5:
        return 1, f"{behaviour_str} Error: Too few pts after per-second mean. len={len(s_bid)}"

    full_idx = pd.date_range(s_bid.index[0], s_bid.index[-1], freq="1s")
    s_bid = s_bid.reindex(full_idx).interpolate(method="time", limit_direction="both")
    yp = s_bid.to_numpy()
    
    if len(yp) < 5 or not np.isfinite(yp).all() or yp[0] == 0:
        return 1, f"{behaviour_str} Error: Bad data after interpolation. len={len(yp)}"

    xp = (full_idx - full_idx[0]).total_seconds().to_numpy()

    # Fit linear trend
    slope, intercept = np.polyfit(xp, yp, 1)
    yhat = slope * xp + intercept
    resid = yp - yhat

    # Calculate return ratio
    ret = yp[-1] / yp[0]
    
    # Decision logic based on price movement
    
    # Scenario 1: Price declining - cut losses
    if ret < 0.995:
        msg = (
            f"{behaviour_str} -CLOSE- Cut losses: ret={ret:.6f}({(ret-1)*100:+.3f}%) "
            f"slope={slope:.3g}"
        )
        return 0, msg
    
    # Scenario 2: Price increasing - keep position open
    if ret > 1.005:
        msg = (
            f"{behaviour_str} -KEEP OPEN-: Price rising ret={ret:.6f}({(ret-1)*100:+.3f}%) "
            f"slope={slope:.3g}"
        )
        return 1, msg
    
    # Scenario 3: Price stable - check residual threshold
    # Linear interpolation for q:
    # q = 0.64 at ret = 0.995
    # q = 0.9 at ret = 1.005
    # q = 0.64 + (ret - 0.995) * (0.9 - 0.64) / (1.005 - 0.995)
    q = 0.64 + (ret - 0.995) * (0.9 - 0.64) / 0.01
    q = float(np.clip(q, 0.64, 0.9))
    
    # Get last minute of residuals (1 Hz sampling)
    m = min(len(resid), 60)
    resid_1m = resid[-m:]
    
    if len(resid_1m) < 5:
        return 1, f"{behaviour_str} Error: Too few pts in last minute resid. len={len(resid_1m)}"
    
    thr = float(np.quantile(resid_1m, q))
    r_end = float(resid[-1])
    
    # Close if last residual is high enough
    if r_end > thr:
        msg = (
            f"{behaviour_str} -CLOSE- High residual: ret={ret:.6f}({(ret-1)*100:+.3f}%) "
            f"slope={slope:.3g} q={q:.2f} r_end={r_end:.3g} > thr={thr:.3g}"
        )
        return 0, msg
    
    # Keep position open
    msg = (
        f"{behaviour_str} -KEEP OPEN-: ret={ret:.6f}({(ret-1)*100:+.3f}%) "
        f"slope={slope:.3g} q={q:.2f} r_end={r_end:.3g} <= thr={thr:.3g}"
    )
    return 1, msg


def check_closing_time_window(curtime: pd.Timestamp, symbol: str) -> tuple[int, str] | None:
    """
    Check if current time falls in a special window requiring immediate action.
    
    Validates time window constraints:
    - Valid processing windows: 03-27 (first half hour) or 33-57 (second half hour)
    - Immediate close windows: 27-30 or 57-60 (end of each half hour)
    - Invalid windows: 00-03 or 30-33 (beginning of each half hour, shouldn't occur)
    
    Args:
        curtime: Current timestamp
        symbol: Trading symbol (for logging)
    
    Returns:
        (status, message) tuple if we should return immediately:
            - (0, msg): Close position now (end of window shortcut)
            - (1, msg): Error, keep position open (invalid time)
        None: Continue normal processing
    """
    current_minute = curtime.minute
    
    # End of window - shortcut and close position immediately
    if (27 <= current_minute < 30) or (57 <= current_minute < 60):
        return 0, f"CLOSE-COND {symbol}: Closing at end of time window (minute={current_minute})"
    
    # Beginning of window - error, shouldn't occur
    if (0 <= current_minute < 3) or (30 <= current_minute < 33):
        return 1, f"Error: {symbol} closure attempted at invalid time (minute={current_minute}). Should not occur before minute 03 or 33."
    
    # Validate we're in a valid processing window (03-27 or 33-57)
    if not ((3 <= current_minute < 27) or (33 <= current_minute < 57)):
        return 1, f"Error: {symbol} closure attempted at invalid minute={current_minute}"
    
    # All checks passed, proceed with normal price evaluation
    return None


def calculate_lookback(curtime: pd.Timestamp, lookback_minutes: int) -> tuple[int, pd.Timestamp]:
    """
    Calculate lookback duration and from_time based on lookback minutes.
    
    Args:
        curtime: Current timestamp
        lookback_minutes: Number of minutes to look back (e.g., 30 for 30 minutes)
        
    Returns:
        tuple: (seconds_back, from_time)
    """
    seconds_back = lookback_minutes * 60
    from_time = curtime - pd.Timedelta(minutes=lookback_minutes)
    
    return seconds_back, from_time


def check_closing_price_condition(symbol: str, base: mtBase, lookback_minutes: int = 10) -> tuple[int, str]:
    """
    Check if the closing price condition is met for a symbol.
    
    Args:
        symbol: Trading symbol to check
        base: mtBase instance for MT5 operations
        lookback_minutes: Number of minutes to look back for price data (default: 10)
        
    Returns:
        tuple: (status, message)
            - status 0: Condition met, proceed with closing position
            - status 1: Condition not met, keep position open
    """
    try:
        # Get symbol info
        syminfo = base.get_symbol_info(symbol)
        if syminfo is None:
            return 1, f"Error: Unable to get symbol info for {symbol}"
        
        # Get current time from symbol info
        curtime: pd.Timestamp = pd.to_datetime(syminfo["time"], unit="s", utc=True)
        
        # Check for special time windows (immediate close or error conditions)
        timing_decision = check_closing_time_window(curtime, symbol)
        if timing_decision is not None:
            timing_status, timing_message = timing_decision
            return timing_status, timing_message
        
        # Valid processing window (03-27 or 33-57) - proceed with normal logic
        from_time = curtime - pd.Timedelta(minutes=lookback_minutes)
        
        # Get ticks in that range
        ticks_range = base.copy_ticks_range(symbol, from_time, curtime, mt5.COPY_TICKS_ALL)
        if ticks_range is None or len(ticks_range) == 0:
            return 1, f"Error: No tick data available for {symbol} in the last {lookback_minutes * 60} seconds"
        
        # Create DataFrame
        df = pd.DataFrame(ticks_range)

        # Convert time column robustly
        if "time" not in df.columns:
            return 1, f"Error: No time column found in tick data for {symbol}"

        if np.issubdtype(df["time"].dtype, np.number):
            df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
        else:
            df["time"] = pd.to_datetime(df["time"], utc=True)

        # Extract bid prices
        if 'bid' not in df.columns:
            return 1, f"Error: No bid prices found in tick data for {symbol}"
        
        bid_prices = df['bid'].to_numpy()
        df = df.sort_values("time")

        # Evaluate closing condition
        condition_result, condition_msg = evaluate_closing_condition(
            bid_prices, df, symbol
        )
        
        return condition_result, condition_msg
        
    except Exception as e:
        logger.error(f"Error checking closing price condition for {symbol}: {e}")
        return 1, f"Error checking closing condition for {symbol}: {str(e)}"
