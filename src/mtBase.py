import MetaTrader5 as mt5
import yaml
import configparser
from typing import Literal, Any, Optional, Mapping

from .mt_actions import (
    get_position_helper, 
    get_orders_helper, 
    get_symbol_price_helper, 
    place_market_order_helper, 
    place_limit_order_helper, 
    close_position_helper
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

    def _merge_call_params(
        self,
        defaults: dict[str, Any],
        overrides: Optional[Mapping[str, Any]],
        *,
        context: str,
        required_keys: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        """Merge defaults with user supplied overrides and validate required keys."""
        if overrides is not None:
            if not isinstance(overrides, Mapping):
                raise TypeError(f"{context} expects a mapping for parameter overrides, got {type(overrides).__name__}.")
            defaults = defaults.copy()
            for key, value in overrides.items():
                defaults[key] = value

        missing = [key for key in required_keys if defaults.get(key) is None]
        if missing:
            missing_list = ", ".join(missing)
            raise ValueError(f"{context} requires values for: {missing_list}.")

        return defaults

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
            server=credentials[self.account]['server'], portable=False
        )
        # Standard initialization with GUI
        if mt5_started:
            print("MetaTrader 5 connection established")
        else:
            print("MetaTrader 5 initialization failed, error code =", mt5.last_error())

        del credentials  #secrets cleanup

    def shutdown(self):
        if not self.check_login():
            raise RuntimeError("Not logged in or wrong account.")
        mt5.shutdown()
        print("MetaTrader 5 connection closed")

    def get_position_df(self):
        if not self.check_login():
            raise RuntimeError("Not logged in or wrong account.")

        return get_position_helper()
    
    def get_orders_df(self):
        if not self.check_login():
            raise RuntimeError("Not logged in or wrong account.")

        return get_orders_helper()
    
    def get_symbol_price(self, symbol: str) -> dict:
        """
        Get current price information for a symbol.

        Args:
            symbol: MT5 symbol (e.g., 'EURUSD').

        Returns:
            dict: Dictionary containing 'bid', 'ask', 'last', 'spread', and 'spread_pct'.
                  Returns empty dict if symbol not found or no tick data.
        """
        if not self.check_login():
            raise RuntimeError("Not logged in or wrong account.")

        return get_symbol_price_helper(symbol)

    def get_account_info(self):
        """Return the latest MetaTrader 5 account information."""
        if not self.check_login():
            raise RuntimeError("Not logged in or wrong account.")
        return mt5.account_info()

    def get_symbol_info(self, symbol: str):
        """Wrapper around mt5.symbol_info for consistency."""
        if not self.check_login():
            raise RuntimeError("Not logged in or wrong account.")
        return mt5.symbol_info(symbol)

    def get_symbol_tick(self, symbol: str):
        """Wrapper around mt5.symbol_info_tick for consistency."""
        if not self.check_login():
            raise RuntimeError("Not logged in or wrong account.")
        return mt5.symbol_info_tick(symbol)

    def select_symbol(self, symbol: str, enable: bool = True) -> bool:
        """Ensure a symbol is available in the Market Watch list."""
        if not self.check_login():
            raise RuntimeError("Not logged in or wrong account.")
        return mt5.symbol_select(symbol, enable)
    
    def place_market_order(
        self,
        symbol: Optional[str] = None,
        max_nom_value: Optional[float] = None,
        buy_sell: Optional[Literal["B","S","Buy","Sell","buy","sell","b","s"]] = None,
        sl_pct: Optional[float] = None,
        tp_pct: Optional[float] = None,
        magic: int = 0,
        order_params: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        if not self.check_login():
            raise RuntimeError("Not logged in or wrong account.")

        helper_params = self._merge_call_params(
            {
                "symbol": symbol,
                "max_nom_value": max_nom_value,
                "buy_sell": buy_sell,
                "sl_pct": sl_pct,
                "tp_pct": tp_pct,
                "deviation_pts": 10,
                "magic": magic,
            },
            order_params,
            context="place_market_order",
            required_keys=("symbol", "max_nom_value", "buy_sell"),
        )

        result = place_market_order_helper(**helper_params)
        return result
    
    def place_limit_order(
        self,
        symbol: Optional[str] = None,
        max_nom_value: Optional[float] = None,
        buy_sell: Optional[Literal["B","S","Buy","Sell","buy","sell","b","s"]] = None,
        pct_away: float = 0.01,
        sl_pct: Optional[float] = None,
        tp_pct: Optional[float] = None,
        magic: int = 0,
        order_params: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        if not self.check_login():
            raise RuntimeError("Not logged in or wrong account.")

        helper_params = self._merge_call_params(
            {
                "symbol": symbol,
                "max_nom_value": max_nom_value,
                "buy_sell": buy_sell,
                "pct_away": pct_away,
                "sl_pct": sl_pct,
                "tp_pct": tp_pct,
                "magic": magic,
            },
            order_params,
            context="place_limit_order",
            required_keys=("symbol", "max_nom_value", "buy_sell"),
        )

        result = place_limit_order_helper(**helper_params)
        return result
    
    def close_position(
        self,
        ticket: Optional[int] = None,
        deviation_pts: int = 10,
        magic: int = 0,
        close_params: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        if not self.check_login():
            raise RuntimeError("Not logged in or wrong account.")
        
        helper_params = self._merge_call_params(
            {
                "ticket": ticket,
                "deviation_pts": deviation_pts,
                "magic": magic,
            },
            close_params,
            context="close_position",
            required_keys=("ticket",),
        )

        result = close_position_helper(**helper_params)
        return result