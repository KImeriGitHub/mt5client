"""
Logging utilities for the trading application.

This module provides centralized logging configuration and setup functions.
"""

import logging
import datetime as dt
from pathlib import Path
from typing import Optional

def setup_logging(
    log_dir: str,
    log_level: str,
    log_format: str,
    log_datefmt: str,
    script_name: str = "app",
    custom_filename: Optional[str] = None
) -> str:
    """
    Set up logging configuration for the application.
    
    Args:
        log_dir: Directory where log files should be stored
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format string for log messages
        log_datefmt: Date format string for timestamps
        script_name: Name of the script/application for the log filename
        custom_filename: Optional custom filename (overrides script_name if provided)
    
    Returns:
        str: Path to the created log file
    
    Raises:
        ValueError: If log_level is invalid
        OSError: If log directory cannot be created or accessed
    """
    # Validate log level
    valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    if log_level.upper() not in valid_levels:
        raise ValueError(f"Invalid log level: {log_level}. Must be one of: {valid_levels}")
    
    # Ensure log directory exists
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Generate log filename
    if custom_filename:
        log_filename = custom_filename
    else:
        formatted_date = dt.datetime.now().strftime("%d%b%y_%H%M")
        log_filename = f'{script_name}_{formatted_date}.log'
    
    full_log_path = log_path / log_filename
    
    # Clear existing handlers to avoid duplicate logs
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # Configure logging
    logging.basicConfig(
        filename=str(full_log_path),
        level=getattr(logging, log_level.upper()),
        format=log_format,
        datefmt=log_datefmt
    )
    
    return str(full_log_path)


def setup_console_and_file_logging(
    log_dir: str,
    log_level: str,
    log_format: str,
    log_datefmt: str,
    script_name: str = "app",
    custom_filename: Optional[str] = None,
    console_level: Optional[str] = None
) -> str:
    """
    Set up logging to both file and console.
    
    Args:
        log_dir: Directory where log files should be stored
        log_level: Logging level for file output
        log_format: Format string for log messages
        log_datefmt: Date format string for timestamps
        script_name: Name of the script/application for the log filename
        custom_filename: Optional custom filename (overrides script_name if provided)
        console_level: Logging level for console output (defaults to log_level if None)
    
    Returns:
        str: Path to the created log file
    """
    # Set up file logging
    log_file_path = setup_logging(
        log_dir=log_dir,
        log_level=log_level,
        log_format=log_format,
        log_datefmt=log_datefmt,
        script_name=script_name,
        custom_filename=custom_filename
    )
    
    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, (console_level or log_level).upper()))
    console_handler.setFormatter(logging.Formatter(log_format, log_datefmt))
    
    logging.getLogger().addHandler(console_handler)
    
    return log_file_path