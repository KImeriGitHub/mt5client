from typing import Literal, Any, Optional
import MetaTrader5 as mt5
import polars as pl

###################
### GET ACTIONS ###
###################
def _to_df(namedtuples: Any) -> pl.DataFrame:
    """Convert MT5 namedtuples to a Polars DataFrame."""
    if not namedtuples:  # handles None and empty tuple
        return pl.DataFrame()
    rows = [nt._asdict() for nt in namedtuples]
    return pl.DataFrame(rows)

def get_position_helper() -> pl.DataFrame:
    """
    Return current open positions as a Polars DataFrame.

    - Converts MT5 namedtuples to rows.
    - Casts `time` (epoch seconds) to pl.Datetime.
    - Drops noisy/duplicated timing fields.
    """
    positions = mt5.positions_get()
    df = _to_df(positions)
    if df.is_empty():
        return df

    df = df.with_columns(
        pl.col("time").dt.epoch(time_unit="ms")
    ).drop(["time_update", "time_msc", "time_update_msc", "external_id"], strict=False)

    return df

def get_orders_helper() -> pl.DataFrame:
    """
    Return current pending orders as a Polars DataFrame.

    - Converts MT5 namedtuples to rows.
    - Casts `time_setup` (epoch seconds) to pl.Datetime.
    """
    orders = mt5.orders_get()
    df = _to_df(orders)
    if df.is_empty():
        return df

    if "time_setup" in df.columns:
        df = df.with_columns(pl.col("time_setup").dt.epoch(time_unit="ms"))

    return df

def get_symbol_price_helper(symbol: str) -> dict:
    """
    Get current price information for a symbol.

    Args:
        symbol: MT5 symbol (e.g., 'EURUSD').

    Returns:
        dict: Dictionary containing 'bid', 'ask', 'last', 'spread', and 'spread_pct'.
              Returns empty dict if symbol not found or no tick data.
    """
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return {}
    
    bid = float(tick.bid)
    ask = float(tick.ask)
    last = float(tick.last)
    spread = ask - bid
    spread_pct = (spread / ask) * 100 if ask > 0 else 0
    
    return {
        'symbol': symbol,
        'bid': bid,
        'ask': ask,
        'last': last,
        'spread': spread,
        'spread_pct': spread_pct,
        'time': tick.time
    }

#####################
### PLACE ACTIONS ###
#####################
def _norm_price(symbol: str, price: float) -> float:
    """Round price to the symbol's precision."""
    info = mt5.symbol_info(symbol)
    if info is None:
        raise ValueError(f"Unknown symbol: {symbol}")
    return round(price, info.digits)

def _latest_prices(symbol: str) -> tuple[float, float]:
    """Return (bid, ask) for symbol."""
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise RuntimeError(f"No tick for {symbol}")
    return float(tick.bid), float(tick.ask)

def place_market_order_helper(
    symbol: str,
    vol: float,
    buy_sell: Literal["B","S","Buy","Sell","buy","sell","b","s"],
    sl_pct: Optional[float] = None,
    tp_pct: Optional[float] = None,
) -> Any:
    """
    Place a market order with optional stop-loss / take-profit in *percent* of entry price.

    Args:
        symbol: MT5 symbol (e.g., 'EURUSD').
        vol: Trade volume (lots).
        buy_sell: 'B'/'Buy' for long, 'S'/'Sell' for short.
        sl_pct: Stop-loss distance as a fraction of price (e.g., 0.01 = 1%). None = no SL.
        tp_pct: Take-profit distance as a fraction of price (e.g., 0.02 = 2%). None = no TP.

    Returns:
        The result of mt5.order_send(request).
    """
    is_buy = str(buy_sell).strip().lower().startswith("b")
    direction = mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL

    bid, ask = _latest_prices(symbol)
    price = ask if is_buy else bid

    # Compute SL/TP from percent distances (relative to entry price)
    sl = None
    tp = None
    if sl_pct is not None and sl_pct > 0:
        sl_price = price * (1 - sl_pct) if is_buy else price * (1 + sl_pct)
        sl = _norm_price(symbol, sl_price)
    if tp_pct is not None and tp_pct > 0:
        tp_price = price * (1 + tp_pct) if is_buy else price * (1 - tp_pct)
        tp = _norm_price(symbol, tp_price)

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(vol),
        "type": direction,
        "price": _norm_price(symbol, price),
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_RETURN,
    }
    if sl is not None:
        request["sl"] = sl
    if tp is not None:
        request["tp"] = tp

    # Validate the order before sending
    check_result = mt5.order_check(request)
    if check_result is None or check_result.retcode != mt5.TRADE_RETCODE_DONE:
        return None

    return mt5.order_send(request)

def place_limit_order_helper(
    symbol: str,
    vol: float,
    buy_sell: Literal["B","S","Buy","Sell","buy","sell","b","s"],
    pct_away: float,
) -> Any:
    """
    Place a pending LIMIT order at a percentage offset from current price.

    Args:
        symbol: MT5 symbol (e.g., 'EURUSD').
        vol: Trade volume (lots).
        buy_sell: 'B'/'Buy' for Buy Limit (below ask), 'S'/'Sell' for Sell Limit (above bid).
        pct_away: Fraction of current price for the offset (e.g., 0.005 = 0.5%).
                  Buy Limit price = ask * (1 - pct_away); Sell Limit price = bid * (1 + pct_away).

    Returns:
        The result of mt5.order_send(request).
    """
    if pct_away <= 0:
        raise ValueError("pct_away must be > 0")

    is_buy = str(buy_sell).strip().lower().startswith("b")
    direction = mt5.ORDER_TYPE_BUY_LIMIT if is_buy else mt5.ORDER_TYPE_SELL_LIMIT

    bid, ask = _latest_prices(symbol)
    raw_price = ask * (1 - pct_away) if is_buy else bid * (1 + pct_away)
    price = _norm_price(symbol, raw_price)

    request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": float(vol),
        "type": direction,
        "price": price,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_RETURN,
    }
    
    # Validate the order before sending
    check_result = mt5.order_check(request)
    if check_result is None or check_result.retcode != mt5.TRADE_RETCODE_DONE:
        return None
        
    return mt5.order_send(request)