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
    
    if not "time_msc" in df.columns:
        raise ValueError("Expected 'time_msc' column in non-empty positions DataFrame.")

    df = df.with_columns(
        pl.from_epoch(pl.col("time_msc"), time_unit="ms").alias("time_dt")
    )

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

    if not "time_setup_msc" in df.columns:
        raise ValueError("Expected 'time_setup_msc' column in non-empty orders DataFrame.")
    
    df = df.with_columns(
        pl.from_epoch(pl.col("time_setup_msc"), time_unit="ms").alias("time_dt")
    )

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
def _compute_sl_tp(price, is_buy, sl_pct, tp_pct, digits):
    sl = tp = None
    if sl_pct and sl_pct > 0:
        sl_price = price * (1 - sl_pct) if is_buy else price * (1 + sl_pct)
        sl = round(sl_price, digits)
    if tp_pct and tp_pct > 0:
        tp_price = price * (1 + tp_pct) if is_buy else price * (1 - tp_pct)
        tp = round(tp_price, digits)
    return sl, tp
def _check_stops_level(price, sl, tp, stops_level_pts, point):
    if not stops_level_pts:
        return True
    if sl is not None and abs(price - sl) <= stops_level_pts * point:
        return False
    if tp is not None and abs(tp - price) <= stops_level_pts * point:
        return False
    return True
def _choose_filling(info):
    cat = getattr(info, "category", None)
    if cat is not None and cat == "Exotic":
        print("Exotic symbol: using FOK filling mode.")
        return mt5.ORDER_FILLING_FOK
    allowed = getattr(info, "filling_mode", None)
    if allowed in (mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_RETURN):
        return allowed
    return mt5.ORDER_FILLING_RETURN
def _get_info_tick(symbol):
    if not mt5.symbol_select(symbol, True):
        print(f"Symbol '{symbol}' not available/visible.")
        return None, None
    info = mt5.symbol_info(symbol)
    if info is None:
        print(f"No symbol_info for '{symbol}'.")
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        print(f"No tick for '{symbol}'.")
    return info, tick
def _compute_vol_adjusted(vol, info, symbol):
    vol_step = getattr(info, "volume_step", None)
    vol_min  = getattr(info, "volume_min",  None)
    vol_max  = getattr(info, "volume_max",  None)
    if vol_step is None: print(f"Warning: volume_step not available for '{symbol}'.")
    if vol_min is None:  print(f"Warning: volume_min not available for '{symbol}'.")
    if vol_max is None:  print(f"Warning: volume_max not available for '{symbol}'.")

    if vol_step is not None:
        vol = int(vol/vol_step)*vol_step
    if vol_min is not None and vol_max is not None:
        vol = min(max(vol, vol_min), vol_max)
    return vol

def _volume_from_notional(max_nom_value: float, price: float, info) -> float:
    """
    Convert desired notional (in account currency) into MT5 volume (lots).

    Assumes: notional ≈ price * volume_lots * contract_size * conv
    where conv converts symbol profit currency → account currency.
    Currently conv=1.0 (no conversion). Raise NotImplementedError if currencies differ.
    """
    account_info = mt5.account_info()
    contract_size = getattr(info, "trade_contract_size", None) or getattr(info, "contract_size", None) or 1.0
    profit_base = getattr(info, "currency_base", None)
    acc_cur = getattr(account_info, "currency", None)

    if acc_cur is None or acc_cur != profit_base:
        print(f"Warning: account currency ({acc_cur}) differs from symbol base currency ({profit_base}).")
        raise NotImplementedError("Currency conversion not implemented yet.")

    conv = 1.0 # default (no conversion)

    # volume in lots (may need step/min/max normalization later)
    vol = max_nom_value / (price * contract_size * conv)
    return vol

def place_market_order_helper(
    symbol: str,
    max_nom_value: float,
    buy_sell: Literal["B","S","Buy","Sell","buy","sell","b","s"],
    sl_pct: Optional[float] = None,
    tp_pct: Optional[float] = None,
    deviation_pts: int = 10,
    magic: int = 0,
) -> Any:
    """
    Place a market order with optional SL/TP, sizing by **max notional (account currency)**.

    Args:
        symbol: MT5 symbol (e.g., "EURUSD", "MSFT"). Ensures visibility via `symbol_select`.
        max_nom_value: Maximum position notional in account currency.
        buy_sell: 'B'/'Buy' → BUY, 'S'/'Sell' → SELL (case-insensitive).
        sl_pct: Optional fractional SL distance from entry. None/≤0 → no SL.
        tp_pct: Optional fractional TP distance from entry. None/≤0 → no TP.
        deviation_pts: Max execution deviation in points.
        magic: Magic number to tag the order.

    Behavior:
        - Fetches fresh tick; uses ask for BUY, bid for SELL.
        - Computes SL/TP off the entry price; rounds to `info.digits`.
        - Rejects if SL/TP violate `trade_stops_level` (points).
        - Picks symbol's allowed `type_filling` if available, else `ORDER_FILLING_RETURN`.
        - Calls `mt5.order_check(req)`; proceeds only if `retcode == TRADE_RETCODE_DONE`.

    Returns:
        The result of `mt5.order_send(req)` on success; otherwise `None`
        (with a printed reason).

    Raises:
        None. (Validation failures print a reason and return `None`.)
    """
    # Ensure symbol is selected and info and tick available
    info, tick = _get_info_tick(symbol)
    if info is None or tick is None:
        return None

    # Eval Direction
    side = str(buy_sell).strip().lower()
    if side.startswith("b"):
        is_buy = True
        direction = mt5.ORDER_TYPE_BUY
    elif side.startswith("s"):
        is_buy = False
        direction = mt5.ORDER_TYPE_SELL
    else:
        print(f"Invalid buy_sell value: {buy_sell}")
        return None

    # Fresh prices
    bid, ask = tick.bid, tick.ask
    price = ask if is_buy else bid
    if price <= 1e-8:
        print(f"Bad price for '{symbol}': {price}")
        return None
    
    # Derive volume from target notional (account currency)
    vol = _volume_from_notional(max_nom_value, price, info)
    print(f"Computed volume for {symbol}: {vol} lots for notional {max_nom_value}")
    vol_adj = _compute_vol_adjusted(vol, info, symbol)
    if vol != vol_adj:
        print(f"Adjusted volume from {vol} to {vol_adj} based on symbol constraints.")
        vol = vol_adj

    # SL/TP from % of entry
    sl, tp = _compute_sl_tp(price, is_buy, sl_pct, tp_pct, info.digits)

    # Optional pre-check against stops level
    stops_level  = getattr(info, "trade_stops_level", 0) or 0  # in points
    ok = _check_stops_level(price, sl, tp, stops_level, info.point)
    if not ok:
        print(f"SL/TP too close to price for '{symbol}'.")
        return None

    type_filling = _choose_filling(info)
    req = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(vol),
        "type": direction,
        "price": round(price, info.digits),
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": type_filling,
        "deviation": int(deviation_pts),
        "magic": int(magic),
        "comment": f"darwinexclient script: Market Order {symbol}",
    }
    if sl is not None: req["sl"] = sl
    if tp is not None: req["tp"] = tp

    check = mt5.order_check(req)
    if not check or check.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Order check FAILED for {symbol}. retcode={getattr(check,'retcode',None)} comment={getattr(check,'comment',None)}")
        return None

    print("Market Order Request checked. Sending order ...")
    return mt5.order_send(req)

def place_limit_order_helper(
    symbol: str,
    max_nom_value: float,
    buy_sell: Literal["B","S","Buy","Sell","buy","sell","b","s"],
    pct_away: float,
    sl_pct: Optional[float] = None,
    tp_pct: Optional[float] = None,
    magic: int = 0,
) -> Any:
    """
    Place a pending LIMIT order sized by **max notional (account currency)**.

    Args:
        symbol: MT5 symbol (e.g., "EURUSD", "MSFT"). Ensures visibility via `symbol_select`.
        max_nom_value: Maximum position notional in account currency.
        buy_sell: 'B'/'Buy' → Buy Limit (below ask), 'S'/'Sell' → Sell Limit (above bid).
        pct_away: Fractional offset from the relevant quote (e.g., 0.005 = 0.5%).
                  Buy Limit price = ask * (1 - pct_away)
                  Sell Limit price = bid * (1 + pct_away)
        sl_pct: Optional fractional SL distance from order price. None/≤0 → no SL.
        tp_pct: Optional fractional TP distance from order price. None/≤0 → no TP.
        magic: Magic number to tag the order.

    Behavior:
        - Computes and rounds limit price to `info.digits`.
        - Verifies price is on the correct side of market (Buy < ask, Sell > bid).
        - Rejects if SL/TP violate `trade_stops_level` (points).
        - Uses `ORDER_FILLING_RETURN` for pending orders.
        - Calls `mt5.order_check(req)`; proceeds only if `retcode == TRADE_RETCODE_DONE`.

    Returns:
        The result of `mt5.order_send(req)` on success; otherwise `None`
        (with a printed reason).

    Raises:
        ValueError: If `pct_away <= 0`.
    """
    if pct_away <= 0:
        raise ValueError("pct_away must be > 0")

    # Ensure symbol selected / info / tick available
    info, tick = _get_info_tick(symbol)
    if info is None or tick is None:
        return None

    # Eval Direction
    side = str(buy_sell).strip().lower()
    if side.startswith("b"):
        is_buy = True
        order_type = mt5.ORDER_TYPE_BUY_LIMIT
    elif side.startswith("s"):
        is_buy = False
        order_type = mt5.ORDER_TYPE_SELL_LIMIT
    else:
        print(f"Invalid buy_sell value: {buy_sell!r}")
        return None

    # Fresh prices
    bid, ask = tick.bid, tick.ask
    if bid <= 0 or ask <= 0:
        print(f"Bad prices for '{symbol}': bid={bid}, ask={ask}")
        return None

    # Compute limit price
    raw_price = ask * (1 - pct_away) if is_buy else bid * (1 + pct_away)
    price = round(raw_price, info.digits)

    # Derive volume from target notional (account currency)
    vol = _volume_from_notional(max_nom_value, price, info)
    print(f"Computed volume for {symbol}: {vol} lots for notional {max_nom_value}")
    vol_adj = _compute_vol_adjusted(vol, info, symbol)
    if vol != vol_adj:
        print(f"Adjusted volume from {vol} to {vol_adj} based on symbol constraints.")
        vol = vol_adj

    # SL/TP from % of entry
    sl, tp = _compute_sl_tp(price, is_buy, sl_pct, tp_pct, info.digits)

    # Optional pre-check against stops level
    stops_level  = getattr(info, "trade_stops_level", 0) or 0  # in points
    ok = _check_stops_level(price, sl, tp, stops_level, info.point)
    if not ok:
        print(f"SL/TP too close to price for '{symbol}'.")
        return None

    # Sanity: ensure correct side of market
    if is_buy and not (price < ask):
        print(f"Buy Limit must be below ask ({ask}), got {price}.")
        return None
    if (not is_buy) and not (price > bid):
        print(f"Sell Limit must be above bid ({bid}), got {price}.")
        return None

    type_filling = mt5.ORDER_FILLING_RETURN
    req = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": float(vol),
        "type": order_type,
        "price": price,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": type_filling,
        "magic": int(magic),
        "comment": f"darwinexclient script: Limit Order {symbol}",
    }
    if sl is not None: req["sl"] = sl
    if tp is not None: req["tp"] = tp

    check = mt5.order_check(req)
    if not check or check.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Order check FAILED for {symbol}. retcode={getattr(check,'retcode',None)} comment={getattr(check,'comment',None)}")
        return None

    print("Limit Order Request checked. It will be placed ...")
    return mt5.order_send(req)

def close_position_helper(
    ticket: Optional[int] = None,
    deviation_pts: int = 10,
    magic: int = 0,
) -> Any:
    """
    Close an open position (full or partial). Provide `ticket`.
    - Uses opposite side at current Bid/Ask, applies symbol filling mode, runs order_check first.
    """
    # Locate the position
    pos = None
    if ticket is not None:
        matches = mt5.positions_get(ticket=ticket)
        if matches: pos = matches[0]
    else:
        print("No ticket provided.")
        return None

    if pos is None:
        print("No position for ticket found.")
        return None

    symbol = pos.symbol  # ensure exact symbol from position

    # Ensure tradable & get info/tick
    info, tick = _get_info_tick(symbol)
    if info is None or tick is None:
        return None

    # Determine close direction & price
    is_long = (pos.type == mt5.POSITION_TYPE_BUY)
    order_type = mt5.ORDER_TYPE_SELL if is_long else mt5.ORDER_TYPE_BUY
    price = tick.bid if is_long else tick.ask
    if price <= 1e-8:
        print(f"Bad price for '{symbol}': {price}")
        return None

    # get Volume
    vol = pos.volume

    # Build request
    type_filling = _choose_filling(info)
    req = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(vol),
        "type": order_type,
        "price": round(price, info.digits),
        "deviation": int(deviation_pts),
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": type_filling,
        "position": int(pos.ticket),  # ensures close of this position (hedging-safe)
        "magic": int(magic),
        "comment": f"darwinexclient script: Closing Position {symbol}",
    }

    # Validate then send
    check = mt5.order_check(req)
    if not check or check.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Close check FAILED for {symbol}. retcode={getattr(check,'retcode',None)} comment={getattr(check,'comment',None)}")
        return None

    print("Close Order Request checked. It will be placed ...")
    return mt5.order_send(req)
