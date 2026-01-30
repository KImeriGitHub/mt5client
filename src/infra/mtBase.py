import MetaTrader5 as mt5
import yaml
import configparser
from typing import Literal, Any, Optional, Mapping
import polars as pl

from .mt_helper import (
    get_positions_helper, 
    get_symbol_price_helper, 
    get_symbol_info_helper
)

class mtBase:
    """
    Args:
        account (str): The account key from credentials YAML file (e.g., 'mt5demo_acc')
        credentials_path (str): Path to the YAML file with MT5 credentials
        config_path (str): Path to the INI file with MT5 terminal path
    """
    def __init__(self, account, credentials_path, config_path):
        self.account = account
        self.credentials_path = credentials_path
        self.config_path = config_path

        self.login_number = int(self.__load_yaml()[account]['apilogin'])

        config = configparser.ConfigParser()
        config.read(self.config_path)
        
        # Read all variables from INI file into self.mt5_loc_config
        self.mt5_loc_config = {}
        for section_name in config.sections():
            self.mt5_loc_config[section_name] = {}
            for key, value in config.items(section_name):
                self.mt5_loc_config[section_name][key] = value

    def __load_yaml(self):
        with open(self.credentials_path, 'r') as file:
            return yaml.safe_load(file)

    def _check_params(
        self,
        order_params: dict[str, Any],
        required_keys: tuple[str],
    ) -> bool:
        
        if any([order_params.get(key, None) is None for key in required_keys]):
            missing_list = ", ".join([key for key in required_keys if order_params.get(key, None) is None])
            raise ValueError(f"Order requires values for: {missing_list}.")

        return True

    def check_login(self) -> bool:
        """
        Check if the current MetaTrader 5 login matches the expected login number.
        
        Returns:
            bool: True if the current login matches, False otherwise
        """
        acc_info = mt5.account_info()
        if acc_info is None:
            return False
        
        acc_login = acc_info.login
        if acc_login is None:
            return False
        
        return int(acc_login) == self.login_number
    
    def mt5_init(self):
        acc_info = mt5.account_info()
        
        if acc_info is not None:
            print(f"MetaTrader 5 initialization: Logged in to account {acc_info.login}")
            if self.check_login():
                print(f"MetaTrader 5 initialization: Logged in to the correct account: {self.account} ({self.login_number})")
                return mt5
            else:
                print(f"MetaTrader 5 initialization: Logged in to a different account ({acc_info.login}). Re-initializing...")
                mt5.shutdown()

        credentials = self.__load_yaml()
        mt5_started = mt5.initialize(
            path=self.mt5_loc_config['MetaTrader5']['terminal_path'], 
            login=self.login_number, 
            password=credentials[self.account]['apipw'], 
            server=credentials[self.account]['server'], 
            portable=False
        )
        # Standard initialization with GUI
        if mt5_started:
            print("MetaTrader 5 connection established")
        else:
            _, le = mt5.last_error()
            print("MetaTrader 5 initialization failed, error code =", le)

        del credentials  #secrets cleanup

    def login(self):
        """
        Log in to the MetaTrader 5 account specified during initialization.
        """
        if self.check_login():
            print(f"Already logged in to the correct account: {self.account} ({self.login_number})")
            return

        credentials = self.__load_yaml()
        login_successful = mt5.login(
            login=self.login_number, 
            password=credentials[self.account]['apipw'], 
            server=credentials[self.account]['server']
        )
        if login_successful:
            print(f"Logged in to account {self.login_number} successfully.")
        else:
            _, le = mt5.last_error()
            print(f"Failed to log in to account {self.login_number}, error code =", le)

        del credentials  #secrets cleanup

    def shutdown(self):
        if not self.check_login():
            raise RuntimeError("Not logged in or wrong account.")
        mt5.shutdown()
        print("MetaTrader 5 connection closed")

    def get_positions_df(self) -> pl.DataFrame | None:
        if not self.check_login():
            raise RuntimeError("Not logged in or wrong account.")

        return get_positions_helper()
    
    def get_symbol_price(self, symbol: str, wait_sec: float = 0.2) -> dict:
        if not self.check_login():
            raise RuntimeError("Not logged in or wrong account.")
        return get_symbol_price_helper(symbol, wait_sec)

    def get_account_info(self):
        """Return the latest MetaTrader 5 account information."""
        if not self.check_login():
            raise RuntimeError("Not logged in or wrong account.")
        return mt5.account_info()

    def get_symbol_info(self, symbol: str, wait_sec: float = 0.2):
        """Wrapper around mt5.symbol_info for consistency."""
        if not self.check_login():
            raise RuntimeError("Not logged in or wrong account.")
        return get_symbol_info_helper(symbol, wait_sec)
    
    def copy_ticks_range(self, symbol: str, date_from, date_to, flags: int) -> Optional[Any]:
        """
        Get ticks for a symbol within a specified time range.
        
        Args:
            symbol: Trading symbol
            date_from: Start datetime
            date_to: End datetime
            flags: Type of ticks to return (e.g., mt5.COPY_TICKS_ALL)
            
        Returns:
            Ticks data or None if failed
        """
        if not self.check_login():
            raise RuntimeError("Not logged in or wrong account.")
        return mt5.copy_ticks_range(symbol, date_from, date_to, flags)

    def select_symbol(self, symbol: str, enable: bool = True) -> bool:
        """Ensure a symbol is available in the Market Watch list."""
        if not self.check_login():
            raise RuntimeError("Not logged in or wrong account.")
        return mt5.symbol_select(symbol, enable)
    
    def last_error(self) -> tuple[int, str]:
        """Return the last MetaTrader 5 error code and description."""
        if not self.check_login():
            raise RuntimeError("Not logged in or wrong account.")
        res, msg = mt5.last_error()
        return res, msg

    def order_check(self, order: dict) -> mt5.OrderCheckResult:
        """Return the result of mt5.order_check(req) for a given order request."""
        if not self.check_login():
            raise RuntimeError("Not logged in or wrong account.")
        return mt5.order_check(order)

    def place_market_order(self, req: dict) -> Any:
        """
            Place a market order with specified parameters.
            Returns the result of mt5.order_send(req)
        """
        if not self.check_login():
            raise RuntimeError("Not logged in or wrong account.")

        return mt5.order_send(req)
    
    def place_limit_order(self, req: dict) -> Any:
        """
            Place a limit order with specified parameters.
            Returns the result of mt5.order_send(req)
        """
        if not self.check_login():
            raise RuntimeError("Not logged in or wrong account.")

        return mt5.order_send(req)
    
    def close_position(self, req: dict) -> Any:
        """
            Close an open position by ticket number.
            Returns the result of mt5.order_send(req)
        """
        if not self.check_login():
            raise RuntimeError("Not logged in or wrong account.")

        return mt5.order_send(req)