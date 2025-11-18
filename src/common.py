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
    if not isinstance(n_days, int) or n_days < 0:
        raise ValueError("n_days must be a non-negative integer.")
    if not isinstance(market, str) or not market:
        raise ValueError("market must be a non-empty string.")

    if n_days == 0:
        return input_date

    # Normalize to naïve midnight for safe comparisons
    input_ts = pd.Timestamp(input_date).normalize()

    cal = mcal.get_calendar(market)

    # Wide enough window to safely index forward n_days from the base trading day
    buffer = 30 + n_days
    start_range = input_ts - pd.Timedelta(days=buffer)
    end_range   = input_ts + pd.Timedelta(days=buffer)

    # Get valid trading days, force naïve normalized timestamps
    td = cal.valid_days(start_date=start_range, end_date=end_range)
    td = pd.DatetimeIndex(td)  # ensure DatetimeIndex
    if td.tz is not None:
        td = td.tz_localize(None)
    td = td.normalize()

    # If input date isn't a trading day, anchor to the previous trading day
    if input_ts in td:
        base_ts = input_ts
    else:
        past = td[td <= input_ts]
        if len(past) == 0:
            raise RuntimeError("No past trading days found in range. Increase buffer or check calendar.")
        base_ts = past[-1]

    # Locate base index and move forward n_days
    base_idx = td.get_indexer([base_ts])[0]
    if base_idx == -1:
        raise RuntimeError("Base trading day unexpectedly not found in trading days index.")

    target_idx = base_idx + n_days
    if target_idx >= len(td):
        raise RuntimeError("Target index out of range. Increase buffer.")

    return td[target_idx].date()
