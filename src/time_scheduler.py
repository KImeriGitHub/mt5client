"""Time scheduling utilities for order placement."""

import time
import logging
from src.infra.TimeModule import TimeModule

logger = logging.getLogger(__name__)


def parse_and_sleep_until_time(place_time_str: str) -> None:
    """
    Parse time string and sleep until the specified time.
    
    Args:
        place_time_str: Time string in HH:MM format (e.g., '14:30')
    """
    if not place_time_str:
        logger.info("No place_time specified. Proceeding immediately.")
        return
    
    try:
        # Parse the time string (HH:MM format)
        hour, minute = map(int, place_time_str.split(':'))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("Invalid time format")
        
        # Use TimeModule to calculate sleep time
        time_module = TimeModule()
        sleep_seconds = time_module.calc_sec_to_sleep(hour, minute)
        
        if sleep_seconds > 0:
            logger.info(f"Scheduled to place orders at {place_time_str}. Sleeping for {sleep_seconds:.0f} seconds...")
            time.sleep(sleep_seconds)
        else:
            logger.info(f"Specified time {place_time_str} has already passed today. Proceeding immediately.")
            
    except (ValueError, IndexError):
        logger.error(f"Invalid time format: {place_time_str}. Expected HH:MM format (e.g., '14:30'). Proceeding immediately.")