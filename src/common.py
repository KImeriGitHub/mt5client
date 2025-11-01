from datetime import date, datetime, timezone
import hashlib
import pandas as pd
import pandas_market_calendars as mcal

def magic_from(prediction_data) -> int:
    parts = [
        prediction_data.symbol.upper(),
        f"{prediction_data.last_training_day:%Y%m%d}",
        str(prediction_data.n_trading_days),
    ]
    key = "|".join(parts).encode()

    h = hashlib.blake2b(key, digest_size=8).digest()  # 8 bytes = 64 bits
    val = int.from_bytes(h, "big")
    return val & 0x7FFFFFFFFFFFFFFF   # keep it non-negative (63-bit signed)


def calculate_trading_day(input_date: date, n_days: int, market: str = 'NYSE') -> date:
    """
    Calculate the trading day that is n trading days from the input date according to market calendar.
    
    Args:
        input_date: Starting date (date)
        n_days: >=0. Number of trading days to add.
        market: Market calendar to use (default: 'NYSE')
        
    Returns:
        date: The calculated trading day

    Return the trading day that is n trading days from input_date on the given market.
    For n_days == 0, return input_date as is.
    """

    if not isinstance(input_date, date):
        raise ValueError("input_date must be a datetime.date.")
    if n_days < 0:
        raise ValueError("n_days must be a non-negative integer.")
    if n_days == 0:
        return input_date

    input_dt = pd.to_datetime(input_date).tz_localize(None)
    
    # Get the market calendar
    calendar = mcal.get_calendar(market)
    
    # Get trading days around the input date
    # We need a wider range to ensure we capture enough trading days
    buffer = 30
    start_range = input_dt - pd.Timedelta(days=buffer)
    end_range = input_dt + pd.Timedelta(days=abs(n_days) + buffer)
    
    # Get valid trading days
    trading_days = calendar.valid_days(start_date=start_range, end_date=end_range, tz="UTC")
    
    # If input_dt is not a trading day, find the previous trading day
    input_is_trading_day = input_dt in trading_days
    base_trading_day = input_dt
    if not input_is_trading_day:
        # Find the last trading day before input_dt
        past_days = trading_days[trading_days <= input_dt]
        base_trading_day = past_days[-1]
    
    base_idx = trading_days.get_loc(base_trading_day)
    target_idx = base_idx + n_days

    return trading_days[target_idx].date()