import MetaTrader5 as mt5
import os
import yaml
import pandas as pd
import polars as pl

mtpath = r"C:\Program Files\Darwinex MetaTrader 5\terminal64.exe"

# Load credentials from YAML file
with open('./secrets/mt5_acc_cred.yaml', 'r') as file:
    credentials = yaml.safe_load(file)

# Extract credentials
darwinex_creds = credentials['darwinexzero_acc']
login = int(darwinex_creds['apilogin'])
password = darwinex_creds['apipw']
server = darwinex_creds['server']

def mt5_init(headless=True):
    """
    Initialize MetaTrader 5 connection using credentials from YAML file.
    
    Args:
        headless (bool): If True, initialize MT5 in headless mode (no GUI)
    """
    if headless:
        # For headless operation, you can try these approaches:
        # 1. Use portable mode (if available)
        # 2. Initialize without login first, then login separately
        
        # Method 1: Try portable initialization
        if mt5.initialize(path=mtpath, portable=True):
            print("MetaTrader 5 initialized in portable mode")
            # Then login
            if mt5.login(login=login, password=password, server=server):
                print("MetaTrader 5 login successful")
                return True
            else:
                print("MetaTrader 5 login failed, error code =", mt5.last_error())
                return False
        else:
            print("MetaTrader 5 portable initialization failed, trying standard init...")
            # Fallback to standard initialization
            if mt5.initialize(path=mtpath, login=login, password=password, server=server):
                print("MetaTrader 5 connection established (standard mode)")
                return True
            else:
                print("MetaTrader 5 initialization failed, error code =", mt5.last_error())
                return False
    else:
        # Standard initialization with GUI
        if mt5.initialize(path=mtpath, login=login, password=password, server=server):
            print("MetaTrader 5 connection established")
            return True
        else:
            print("MetaTrader 5 initialization failed, error code =", mt5.last_error())
            return False

def mt5_shutdown():
    """Shutdown MetaTrader 5 connection."""
    mt5.shutdown()
    print("MetaTrader 5 connection closed")