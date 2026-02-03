"""Check opening price condition for a symbol before placing orders."""

import datetime as dt
import pandas as pd
import numpy as np
import MetaTrader5 as mt5

from src.infra.mtBase import mtBase

import logging
logger = logging.getLogger(__name__)

def evaluate_price_condition(
    ask_prices: np.ndarray,
    df: pd.DataFrame,
    sym: str
):
    """Evaluate whether the price condition is met for opening a position.
    
    This function analyzes price movement patterns to determine if market conditions
    are favorable for placing a buy order. It evaluates price trends, momentum, and
    volatility characteristics over the available data window.
    
    Args:
        ask_prices: Array of ask prices for the symbol. Must contain at least 5 finite
            values. Invalid or NaN values will be filtered out.
        df: DataFrame containing tick data with at least a 'time' column (pd.Timestamp)
            representing the timestamp for each tick. Must have at least 5 rows.
        sym: Trading symbol identifier string, used for logging and error messages.
    
    Returns:
        tuple[int, str]: A tuple containing:
            - status (int): 
                * 0 if price condition is met (proceed with order placement)
                * 1 if condition is not met or an error occurred (reject/requeue)
            - message (str): Detailed explanation of the result, including:
                * For status 0: Return %, slope, quantile level, residual values
                * For status 1: Reason for rejection (low return, high residual, errors)
    
    Logic:
        1. Validates input data has at least 5 data points
        2. Filters out non-finite ask prices
        3. Determines evaluation window:
           - If total data span ≤ 10 minutes: evaluates full window
           - If total data span > 10 minutes: evaluates only last 7 minutes
        4. Delegates to _eval_window for actual condition evaluation
    """
    behaviour_str = f"PRICE-COND {sym}:"

    if len(ask_prices) < 5 or len(df) < 5:
        return 1, f"{behaviour_str} Error: The ask_prices or times contain too few data points."

    current_time = df["time"].iloc[-1]

    y0 = ask_prices
    t0 = df["time"]

    ok = np.isfinite(y0)
    y0 = y0[ok]
    t0 = t0.iloc[np.where(ok)[0]]
    if len(y0) < 5:
        return 1, f"{behaviour_str} Error: The ask prices have too few finite values."

    def _eval_window(t: pd.Series, y: np.ndarray, tag: str):
        """Evaluate price condition for a specific time window.
        
        This nested function performs the core price condition analysis by examining
        price trends, calculating residuals from a linear fit, and applying an adaptive
        threshold based on the return ratio.
        
        Args:
            t: Series of timestamps (pd.Timestamp) for each price observation. Must
                contain at least 5 values. Used as the time axis for analysis.
            y: Array of price values corresponding to timestamps in t. Must contain
                at least 5 finite values. These are typically ask prices.
            tag: String identifier for the window being evaluated (e.g., "full", "7m").
                Used in logging and error messages to distinguish between different
                evaluation windows.
        
        Logic:
            1. Aggregation: Groups prices by per-second mean to normalize tick frequency
            2. Interpolation: Fills gaps to create uniform 1Hz time series
            3. Trend Analysis: Fits linear regression (slope, intercept) to prices
            4. Residual Calculation: Computes deviations from the linear trend
            5. Return Check: Rejects if price return ratio < 0.995 (0.5% decline threshold)
            6. Adaptive Threshold: Calculates quantile level q based on return:
               - q starts at 0.40 for return = 1.000 (flat)
               - q increases linearly with return, capping at 0.90
               - Higher returns allow more tolerance for volatility
            7. Final Check: Compares last residual against threshold from last 60 seconds
               - If r_end ≤ threshold: condition met (status 0)
               - If r_end > threshold: price too high relative to trend (status 1)
        """
        # per-second mean + linear time interpolation -> xp, yp
        ts = t.dt.floor("s")
        s = pd.Series(y, index=ts).groupby(level=0).mean()
        if len(s) < 5:
            return 1, f"{behaviour_str} Error: Window too few pts after per-second mean. len={len(s)}. Window tag={tag}"

        full_idx = pd.date_range(s.index[0], s.index[-1], freq="1s")
        s = s.reindex(full_idx).interpolate(method="time", limit_direction="both")
        yp = s.to_numpy()
        if len(yp) < 5 or not np.isfinite(yp).all() or yp[0] == 0:
            return 1, f"{behaviour_str} Error: Window bad after interpolation. len={len(yp)}. Window tag={tag}"

        xp = (full_idx - full_idx[0]).total_seconds().to_numpy()

        slope, intercept = np.polyfit(xp, yp, 1)
        yhat = slope * xp + intercept
        resid = yp - yhat

        ret = yp[-1] / yp[0]  # ratio
        if ret < 0.995:
            return 1, f"{behaviour_str} Rejecting: Return too low. Window tag={tag}:ret={ret:.6f} ({(ret-1)*100:+.3f}%)<0.995"

        # q is a clipped quantile level: it rises linearly with ret, 
        # with q=0.40 at ret=1.000 and reaching up to q=0.90 by ret≈1.0087 
        # (lower values clamp to 0.40).
        q = float(np.clip(0.37 + 0.3 * (ret - 1.000) / 0.005, 0.4, 0.90))

        m = min(len(resid), 30)  # last seconds (1 Hz)
        resids = resid[-m:]
        if len(resids) < 5:
            return 1, f"{behaviour_str} Error: Window too few pts in last minute resid. len={len(resids)}. Window tag={tag}"

        thr = float(np.quantile(resids, q))
        r_end = float(resids[-1])

        if r_end <= thr:
            msg = (
                f"{behaviour_str} -BUY- ret={ret:.6f}({(ret-1)*100:+.3f}%) "
                f"slope={slope:.3g} q={q:.2f} r_end={r_end:.3g} thr={thr:.3g} Window tag={tag}. "
            )
            return 0, msg

        return 1, f"{behaviour_str} Rejecting: End residual too high. Window tag={tag}: r_end={r_end:.3g} > thr={thr:.3g} q={q:.2f} ret={ret:.6f}"

    # Use the full available window when it spans 10 minutes or less; 
    # if the history is longer, evaluate only the most recent `ival_minutes` window.
    elapsed = (t0.iloc[-1] - t0.iloc[0]).total_seconds()
    if elapsed <= 600:
        ok1, msg1 = _eval_window(t0, y0, "full")
        return ok1, msg1

    # If more than 10 minutes of data is available, evaluate only 
    # the last `ival_minutes` minutes (recent window).
    ival_minutes = 7
    cutoff_recent = current_time - pd.Timedelta(minutes=ival_minutes)
    maskp = df["time"] >= cutoff_recent
    if maskp.sum() >= 5:
        yival = ask_prices[maskp.to_numpy()]
        tival = df.loc[maskp, "time"]
        ok = np.isfinite(yival)
        yival = yival[ok]
        tival = tival.iloc[np.where(ok)[0]]
        if len(yival) >= 5:
            ok2, msg2 = _eval_window(tival, yival, f"{ival_minutes}m")
            return ok2, msg2
        else:
            return 1, f"{behaviour_str} Error: Not enough finite data in last {ival_minutes} minutes. Window tag={ival_minutes}m."
    else:
        return 1, f"{behaviour_str} Error: Not enough data in last {ival_minutes} minutes. Window tag={ival_minutes}m."


def calculate_timeinterval(curtime: pd.Timestamp, target_minute: int) -> tuple[int, pd.Timestamp]:
    """
    Calculate lookback duration and from_time based on target minute.
    
    Args:
        curtime: Current timestamp
        target_minute: Minute of the hour to look back to (e.g., 30 for xx:30)
        
    Returns:
        tuple: (seconds_back, from_time)
    """
    # Calculate seconds_back: seconds since the last target_minute
    current_minute = curtime.minute
    current_second = curtime.second
    
    if current_minute >= target_minute:
        # Look back to target_minute in current hour
        minutes_back = current_minute - target_minute
        seconds_back = minutes_back * 60 + current_second
    else:
        # Look back to target_minute in previous hour
        minutes_back = (60 - target_minute) + current_minute
        seconds_back = minutes_back * 60 + current_second
    
    # If we're exactly at the target minute, look back 60 minutes
    if seconds_back == 0:
        seconds_back = 3600
    
    # Calculate from_time
    from_time = curtime - pd.Timedelta(seconds=seconds_back)
    
    return seconds_back, from_time


def check_opening_price_condition(symbol: str, base: mtBase, target_minute: int = 30) -> tuple[int, str]:
    """
    Check if the opening price condition is met for a symbol.
    
    Args:
        symbol: Trading symbol to check
        base: mtBase instance for MT5 operations
        target_minute: Minute of the hour to look back to (default: 30)
        
    Returns:
        tuple: (status, message)
            - status 0: Condition met, proceed with order placement
            - status 1: Condition not met, requeue and retry later
    """
    try:
        # Get symbol info
        syminfo = base.get_symbol_info(symbol)
        if syminfo is None:
            return 1, f"Error: Unable to get symbol info for {symbol}"
        
        # Get current time from symbol info
        curtime: pd.Timestamp = pd.to_datetime(syminfo["time"], unit="s", utc=True)
        seconds_back, from_time = calculate_timeinterval(curtime, target_minute)
        
        # Get ticks in that range
        ticks_range = base.copy_ticks_range(symbol, from_time, curtime, mt5.COPY_TICKS_ALL)
        if ticks_range is None or len(ticks_range) == 0:
            return 1, f"Error: No tick data available for {symbol} in the last {seconds_back} seconds"
        
        # Create DataFrame and numpy arrays
        df = pd.DataFrame(ticks_range)
        
        # Convert time column robustly
        if "time" not in df.columns:
            return 1, f"Error: No time column found in tick data for {symbol}"

        if np.issubdtype(df["time"].dtype, np.number):
            df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
        else:
            df["time"] = pd.to_datetime(df["time"], utc=True)

        if 'ask' not in df.columns:
            return 1, f"Error: No ask prices found in tick data for {symbol}"
        ask_prices = df['ask'].to_numpy()
        
        # Evaluate price condition
        condition_result, condition_msg = evaluate_price_condition(ask_prices, df, symbol)
        
        return condition_result, condition_msg
        
    except Exception as e:
        logger.error(f"Error checking opening price condition for {symbol}: {e}")
        return 1, f"Error checking price condition for {symbol}: {str(e)}"
