import MetaTrader5 as mt5

from src.infra.OrderClient import OrderClient
from src.infra.OrderData import OrderData
from src.infra.mtBase import mtBase

import logging
logger = logging.getLogger(__name__)

def place_order(order: OrderData, order_client: OrderClient, base: mtBase, is_dry_run: bool = True) -> tuple[int, str]:
    req = order_client.to_request_dict(order)
            
    return place_order_req(req, base, is_dry_run)

def place_order_req(req: dict, base: mtBase, is_dry_run: bool = True) -> tuple[int, str]:
    sym = req.get("symbol", None)
    if sym is None:
        msg = "Order request missing 'symbol' field."
        return (1, msg)
            
    # Check order validity
    res_check: mt5.OrderCheckResult = base.order_check(req)
    if res_check is None:
        msg = f"Order check returned None for {sym}"
        return (1, msg)
    if res_check.retcode != 0:
        msg = f"Order check failed for {sym}: {res_check}"
        msg = "DRY RUN: " + msg if is_dry_run else msg
        return (1, msg)
    
    if is_dry_run:
        msg = f"DRY RUN: Order check passed for {sym}."
        return (0, msg)

    #Place Order
    logger.info(f"Placing order for {sym}...")
    res_placing = base.place_market_order(req)
    if res_placing is None:
        msg = f"Order placement returned None for {sym}"
        return (1, (msg))
    
    result_code = res_placing._asdict().get("retcode", -1)
    if result_code == -1:
        msg = f"Order placement returned unknown result for {sym}: {res_placing}"
        return (1, msg)
    if result_code == mt5.TRADE_RETCODE_MARKET_CLOSED:
        msg = f"Order placement failed for {sym}: Market is closed."
        return (10018, msg)
    if result_code != mt5.TRADE_RETCODE_DONE:
        msg = f"Order placement failed for {sym}: {res_placing}"
        return (1, msg)

    msg = f"Order placed successfully for {sym}: {res_placing}"
    return (0, msg)