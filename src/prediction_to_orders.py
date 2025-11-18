import datetime
import MetaTrader5 as mt5
import math
from typing import Counter, List, Dict, Tuple, Optional

from .infra.mtBase import mtBase
from .infra.BudgetMgmt import BudgetMgmt
from .infra.OrderData import OrderData
from .infra.PredictionData import PredictionData
from .infra.PredictionClient import PredictionClient

import logging
logger = logging.getLogger(__name__)

def _compute_sl_tp(price, sl_pct, tp_pct, digits):
    """
    Compute stop loss and take profit prices based on entry price and percentages.

    Args:
        price: Entry price for the position.
        is_buy: True for buy positions, False for sell positions.
        sl_pct: Stop loss percentage (fractional, e.g., 0.02 for 2%).
        tp_pct: Take profit percentage (fractional, e.g., 0.03 for 3%).
        digits: Number of decimal places for price rounding.

    Returns:
        tuple: (stop_loss_price, take_profit_price) or (None, None) if not set.
    """
    is_buy = True
    sl = tp = None
    if sl_pct and sl_pct > 0:
        sl_price = price * (1 - sl_pct) if is_buy else price * (1 + sl_pct)
        sl = round(sl_price, digits)
    if tp_pct and tp_pct > 0:
        tp_price = price * (1 + tp_pct) if is_buy else price * (1 - tp_pct)
        tp = round(tp_price, digits)
    return sl, tp

def _check_stops_level(price, sl, tp, stops_level_pts, point):
    """
    Check if stop loss and take profit levels comply with broker's minimum distance requirements.

    Args:
        price: Entry price for the position.
        sl: Stop loss price (can be None).
        tp: Take profit price (can be None).
        stops_level_pts: Minimum distance in points required by broker.
        point: Point value for the symbol.

    Returns:
        tuple: (is_valid, adjusted_sl, adjusted_tp) where is_valid indicates
            if original levels are acceptable, and adjusted values are suggested corrections.
    """
    res = True
    sl_adj = None
    tp_adj = None
    buffer_stop_level = 1 # extra buffer in points
    if sl is not None and abs(price - sl) <= stops_level_pts * point:
        res = False
        sl_adj = price - (stops_level_pts + buffer_stop_level) * point
    if tp is not None and abs(tp - price) <= stops_level_pts * point:
        res = False
        tp_adj = price + (stops_level_pts + buffer_stop_level) * point

    return res, sl_adj, tp_adj

def _choose_filling(info):
    """
    Select appropriate order filling mode based on symbol characteristics.

    Args:
        info: Symbol information dictionary containing category and filling_mode.

    Returns:
        int: MT5 order filling mode constant (FOK, IOC, or RETURN).
    """
    cat = info["category"]
    if cat == "Exotic":
        logger.warning("Warning: Exotic symbol: using FOK filling mode.")
        return mt5.ORDER_FILLING_FOK
    
    filling_mode = info["filling_mode"]
    if filling_mode == mt5.ORDER_FILLING_FOK:
        return mt5.ORDER_FILLING_FOK
    
    logger.info("Standard Filling mode is not FOK: using ORDER_FILLING_FOK.")
    return mt5.ORDER_FILLING_FOK

def _volume_from_budget(budget: float, price: float, info: dict, base: mtBase) -> float:
    """
    Convert desired notional amount (in account currency) into MT5 volume (lots).
    Args:
        budget: Maximum position notional value in account currency.
        price: Current price of the symbol.
        info: Symbol information dictionary containing contract size and currency details.
    Returns:
        float: Volume in lots corresponding to the desired notional amount.
    Raises:
        NotImplementedError: If account currency differs from symbol base currency
            (currency conversion not yet implemented).
    Note:
        Formula: volume = expenditure / (price * trade_contract_size * conversion_rate)
        Currently assumes conversion_rate = 1.0 (no currency conversion).
    """
    
    trade_contract_size = info["trade_contract_size"]
    currency_base = info["currency_base"]
    account_info = base.get_account_info()
    acc_cur = getattr(account_info, "currency")
    if acc_cur is None or acc_cur != currency_base:
        msg = (f"Warning: account currency ({acc_cur}) differs from symbol base currency ({currency_base}).")
        logger.warning(msg)
        raise NotImplementedError("Currency conversion not implemented yet.")
    conv = 1.0 # default (no conversion)
    # volume in lots (may need step/min/max normalization later)
    logger.info(f"Calculating volume from budget: {budget} / (price: {price} * contract_size: {trade_contract_size} * conv: {conv})")
    vol = budget / (price * trade_contract_size * conv)
    return vol

def _calc_vol(vol: float, info: dict, div: int) -> list[float]:
    """
    Calculate volume and comply with symbol's volume constraints and price and budget.
    Args:
        info: Symbol information dictionary containing contract size and currency details.
        div: Divisor to split volume into smaller parts.
    Returns:
        list[float]: Adjusted volume that complies with symbol constraints.
    Raises:
        RuntimeError: If volume_step is invalid or missing.
    """
    vol_step = info["volume_step"]

    if vol_step is None or vol_step < 1e-8:
        raise RuntimeError("Invalid volume_step in symbol info.")

    n_units = math.floor(vol/vol_step)

    base_vol = n_units // div
    r_vol = n_units % div
    
    vol_parts = [base_vol * vol_step] * div
    for i in range(r_vol):
        vol_parts[i] += vol_step

    return vol_parts

def prediction_to_orders(
        pred: PredictionData,
        budget: float,
        vol_divisor: int,
        base: mtBase,
    ) -> List[OrderData]:
    """
    Convert PredictionData into a list of OrderData objects for MT5 order placement.

    Args:
        pred: PredictionData instance containing trade signals.
        weight: Integer weight corresponding to the prediction.
        budget: Maximum total expenditure for all orders (in account currency).
    """

    pricetick = base.get_symbol_price(pred.symbol, wait_sec=0.02)
    symbolinfo = base.get_symbol_info(pred.symbol, wait_sec=0.02)

    # Eval Direction
    direction = mt5.ORDER_TYPE_BUY

    # Fresh prices
    bid, ask = pricetick['bid'], pricetick['ask']
    price = ask

    # Derive volume from target budget (account currency)
    vol = _volume_from_budget(budget, price, symbolinfo, base)
    logger.info(f"PLACE MARKET ORDER: Computed volume for {pred.symbol}: {vol} lots for budget {budget}.")

    vol_parts = _calc_vol(vol, symbolinfo, vol_divisor)
    if vol != sum(vol_parts):
        logger.info(f"PLACE MARKET ORDER: Adjusted volume from {vol} to {sum(vol_parts)} based on symbol constraints.")
        vol = sum(vol_parts)

    # SL/TP from % of entry
    sl, tp = _compute_sl_tp(price, pred.sl_pct, pred.tp_pct, symbolinfo['digits'])

    # Optional pre-check against stops level
    stops_level  = symbolinfo["trade_stops_level"] # in points
    ok, sl_adj, tp_adj = _check_stops_level(price, sl, tp, stops_level, symbolinfo['point'])
    if not ok:
        if sl_adj is not None:
            logger.warning(f"PLACE MARKET ORDER: Adjusted SL from {sl} to {sl_adj} based on stops level.")
            sl = sl_adj
        if tp_adj is not None:
            logger.warning(f"PLACE MARKET ORDER: Adjusted TP from {tp} to {tp_adj} based on stops level.")
            tp = tp_adj

    type_filling = _choose_filling(symbolinfo)

    def __create_order(volume) -> OrderData:
        dt = datetime.datetime.now(datetime.timezone.utc)
        formated_date = dt.strftime("%Y%m%d")
        return OrderData(
            type=direction,
            volume=volume,
            price=price,
            sl=sl,
            tp=tp,
            symbol=pred.symbol,
            comment=f"Darwinexclient:{formated_date}",  # MAX 31 chars
            magic=pred.magic,
            action=mt5.TRADE_ACTION_DEAL,
            type_time=mt5.ORDER_TIME_DAY,
            type_filling=type_filling,
            deviation=10
        )

    orders = [__create_order(v) for v in vol_parts]

    return orders

