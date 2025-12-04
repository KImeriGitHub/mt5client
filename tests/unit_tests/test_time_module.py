import pytest
import datetime
from zoneinfo import ZoneInfo

from src.infra.TimeModule import TimeModule


class TestTimeModule:
    
    def test_init_with_default_timezone(self):
        """Test TimeModule initialization with default timezone."""
        tm = TimeModule()
        assert tm.timezone == ZoneInfo("Europe/Zurich")
    
    def test_init_with_custom_timezone_string(self):
        """Test TimeModule initialization with custom timezone string."""
        tm = TimeModule("America/New_York")
        assert tm.timezone == ZoneInfo("America/New_York")
    
    def test_timezone_property_setter_with_string(self):
        """Test timezone property setter with string value."""
        tm = TimeModule()
        tm.timezone = "Asia/Tokyo"
        assert tm.timezone == ZoneInfo("Asia/Tokyo")
    
    def test_timezone_property_setter_with_zoneinfo(self):
        """Test timezone property setter with ZoneInfo object."""
        tm = TimeModule()
        london_tz = ZoneInfo("Europe/London")
        tm.timezone = london_tz
        assert tm.timezone == london_tz
    
    def test_calc_sec_to_sleep_returns_positive_value(self):
        """Test calc_sec_to_sleep returns a non-negative value."""
        tm = TimeModule("UTC")
        
        # Test with a target time that should be in the future
        result = tm.calc_sec_to_sleep(23, 59)
        
        # Should return a non-negative float
        assert isinstance(result, float)
        assert result >= 0.0
        
        # Should be reasonable (less than 24 hours)
        assert result <= 86400.0