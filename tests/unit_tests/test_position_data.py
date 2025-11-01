"""Unit tests for PositionData class."""

import pytest
from datetime import datetime
from unittest.mock import patch

from src.infra.PositionData import PositionData


class TestPositionData:
    """Test cases for PositionData class."""
    
    def test_init_required_params(self):
        """Test initialization with required parameters."""
        ticket = 123456789
        time = datetime(2025, 10, 27, 10, 30, 0)
        time_msc = 1698399000000
        type = 0  # POSITION_TYPE_BUY
        magic = 12345
        reason = 0
        volume = 1.0
        price_open = 1.2345
        price_current = 1.2400
        profit = 55.0
        symbol = "EURUSD"
        
        position = PositionData(
            ticket=ticket,
            time=time,
            time_msc=time_msc,
            type=type,
            magic=magic,
            reason=reason,
            volume=volume,
            price_open=price_open,
            price_current=price_current,
            profit=profit,
            symbol=symbol
        )
        
        assert position.ticket == ticket
        assert position.time == time
        assert position.time_msc == time_msc
        assert position.type == type
        assert position.magic == magic
        assert position.reason == reason
        assert position.volume == volume
        assert position.price_open == price_open
        assert position.price_current == price_current
        assert position.profit == profit
        assert position.symbol == symbol
        assert position.sl is None
        assert position.tp is None
        assert position.comment is None
    
    def test_init_all_params(self):
        """Test initialization with all parameters."""
        ticket = 987654321
        time = datetime(2025, 10, 27, 15, 45, 30)
        time_msc = 1698409530000
        type = 1  # POSITION_TYPE_SELL
        magic = 67890
        reason = 1
        volume = 0.5
        price_open = 1.2500
        price_current = 1.2450
        profit = 25.0
        symbol = "GBPUSD"
        sl = 1.2600
        tp = 1.2350
        comment = "Test position"
        
        position = PositionData(
            ticket=ticket,
            time=time,
            time_msc=time_msc,
            type=type,
            magic=magic,
            reason=reason,
            volume=volume,
            price_open=price_open,
            price_current=price_current,
            profit=profit,
            symbol=symbol,
            sl=sl,
            tp=tp,
            comment=comment
        )
        
        assert position.ticket == ticket
        assert position.time == time
        assert position.time_msc == time_msc
        assert position.type == type
        assert position.magic == magic
        assert position.reason == reason
        assert position.volume == volume
        assert position.price_open == price_open
        assert position.price_current == price_current
        assert position.profit == profit
        assert position.symbol == symbol
        assert position.sl == sl
        assert position.tp == tp
        assert position.comment == comment
    
    def test_repr(self):
        """Test string representation."""
        position = PositionData(
            ticket=111222333,
            time=datetime(2025, 10, 27, 12, 0, 0),
            time_msc=1698404400000,
            type=0,
            magic=11111,
            reason=0,
            volume=0.75,
            price_open=1.0850,
            price_current=1.0875,
            profit=18.75,
            symbol="EURUSD",
            sl=1.0800,
            tp=1.0900
        )
        
        expected = ("PositionData(ticket=111222333, "
                   "symbol='EURUSD', "
                   "type=0, "
                   "volume=0.75, "
                   "price_open=1.085, "
                   "price_current=1.0875, "
                   "profit=18.75, "
                   "sl=1.08, "
                   "tp=1.09, "
                   "magic=11111)")
        
        assert repr(position) == expected
    
    def test_to_dict_required_only(self):
        """Test to_dict with only required parameters."""
        time = datetime(2025, 10, 27, 10, 30, 0)
        
        position = PositionData(
            ticket=123456,
            time=time,
            time_msc=1698399000000,
            type=0,
            magic=12345,
            reason=0,
            volume=1.0,
            price_open=1.2345,
            price_current=1.2400,
            profit=55.0,
            symbol="EURUSD"
        )
        
        result = position.to_dict()
        
        expected = {
            'ticket': 123456,
            'time': '2025-10-27T10:30:00',
            'time_msc': 1698399000000,
            'type': 0,
            'magic': 12345,
            'reason': 0,
            'volume': 1.0,
            'price_open': 1.2345,
            'price_current': 1.2400,
            'profit': 55.0,
            'symbol': 'EURUSD'
        }
        
        assert result == expected
    
    def test_to_dict_all_params(self):
        """Test to_dict with all parameters."""
        time = datetime(2025, 10, 27, 15, 45, 30)
        
        position = PositionData(
            ticket=987654,
            time=time,
            time_msc=1698409530000,
            type=1,
            magic=67890,
            reason=1,
            volume=0.5,
            price_open=1.2500,
            price_current=1.2450,
            profit=25.0,
            symbol="GBPUSD",
            sl=1.2600,
            tp=1.2350,
            comment="Test position"
        )
        
        result = position.to_dict()
        
        expected = {
            'ticket': 987654,
            'time': '2025-10-27T15:45:30',
            'time_msc': 1698409530000,
            'type': 1,
            'magic': 67890,
            'reason': 1,
            'volume': 0.5,
            'price_open': 1.2500,
            'price_current': 1.2450,
            'profit': 25.0,
            'symbol': 'GBPUSD',
            'sl': 1.2600,
            'tp': 1.2350,
            'comment': 'Test position'
        }
        
        assert result == expected
    
    def test_is_long_property(self):
        """Test is_long property."""
        long_position = PositionData(
            ticket=123456,
            time=datetime.now(),
            time_msc=1698399000000,
            type=0,  # POSITION_TYPE_BUY
            magic=12345,
            reason=0,
            volume=1.0,
            price_open=1.2345,
            price_current=1.2400,
            profit=55.0,
            symbol="EURUSD"
        )
        
        short_position = PositionData(
            ticket=654321,
            time=datetime.now(),
            time_msc=1698399000000,
            type=1,  # POSITION_TYPE_SELL
            magic=12345,
            reason=0,
            volume=1.0,
            price_open=1.2345,
            price_current=1.2300,
            profit=45.0,
            symbol="EURUSD"
        )
        
        assert long_position.is_long is True
        assert short_position.is_long is False
    
    def test_is_short_property(self):
        """Test is_short property."""
        long_position = PositionData(
            ticket=123456,
            time=datetime.now(),
            time_msc=1698399000000,
            type=0,  # POSITION_TYPE_BUY
            magic=12345,
            reason=0,
            volume=1.0,
            price_open=1.2345,
            price_current=1.2400,
            profit=55.0,
            symbol="EURUSD"
        )
        
        short_position = PositionData(
            ticket=654321,
            time=datetime.now(),
            time_msc=1698399000000,
            type=1,  # POSITION_TYPE_SELL
            magic=12345,
            reason=0,
            volume=1.0,
            price_open=1.2345,
            price_current=1.2300,
            profit=45.0,
            symbol="EURUSD"
        )
        
        assert long_position.is_short is False
        assert short_position.is_short is True
    
    def test_is_profitable_property(self):
        """Test is_profitable property."""
        profitable_position = PositionData(
            ticket=123456,
            time=datetime.now(),
            time_msc=1698399000000,
            type=0,
            magic=12345,
            reason=0,
            volume=1.0,
            price_open=1.2345,
            price_current=1.2400,
            profit=55.0,  # Positive profit
            symbol="EURUSD"
        )
        
        losing_position = PositionData(
            ticket=654321,
            time=datetime.now(),
            time_msc=1698399000000,
            type=0,
            magic=12345,
            reason=0,
            volume=1.0,
            price_open=1.2345,
            price_current=1.2300,
            profit=-45.0,  # Negative profit
            symbol="EURUSD"
        )
        
        breakeven_position = PositionData(
            ticket=789012,
            time=datetime.now(),
            time_msc=1698399000000,
            type=0,
            magic=12345,
            reason=0,
            volume=1.0,
            price_open=1.2345,
            price_current=1.2345,
            profit=0.0,  # Zero profit
            symbol="EURUSD"
        )
        
        assert profitable_position.is_profitable is True
        assert losing_position.is_profitable is False
        assert breakeven_position.is_profitable is False
    
    def test_total_pnl_property(self):
        """Test total_pnl property."""
        position = PositionData(
            ticket=123456,
            time=datetime.now(),
            time_msc=1698399000000,
            type=0,
            magic=12345,
            reason=0,
            volume=1.0,
            price_open=1.2345,
            price_current=1.2400,
            profit=75.25,
            symbol="EURUSD"
        )
        
        assert position.total_pnl == 75.25
    
    def test_unrealized_pips_property_long(self):
        """Test unrealized_pips property for long position."""
        long_position = PositionData(
            ticket=123456,
            time=datetime.now(),
            time_msc=1698399000000,
            type=0,  # POSITION_TYPE_BUY
            magic=12345,
            reason=0,
            volume=1.0,
            price_open=1.2345,
            price_current=1.2400,
            profit=55.0,
            symbol="EURUSD"
        )
        
        expected_pips = 1.2400 - 1.2345  # 0.0055
        assert long_position.unrealized_pips == expected_pips
    
    def test_unrealized_pips_property_short(self):
        """Test unrealized_pips property for short position."""
        short_position = PositionData(
            ticket=654321,
            time=datetime.now(),
            time_msc=1698399000000,
            type=1,  # POSITION_TYPE_SELL
            magic=12345,
            reason=0,
            volume=1.0,
            price_open=1.2345,
            price_current=1.2300,
            profit=45.0,
            symbol="EURUSD"
        )
        
        expected_pips = 1.2345 - 1.2300  # 0.0045
        assert short_position.unrealized_pips == expected_pips
    
    def test_has_sl_property(self):
        """Test has_sl property."""
        position_with_sl = PositionData(
            ticket=123456,
            time=datetime.now(),
            time_msc=1698399000000,
            type=0,
            magic=12345,
            reason=0,
            volume=1.0,
            price_open=1.2345,
            price_current=1.2400,
            profit=55.0,
            symbol="EURUSD",
            sl=1.2300
        )
        
        position_without_sl = PositionData(
            ticket=654321,
            time=datetime.now(),
            time_msc=1698399000000,
            type=0,
            magic=12345,
            reason=0,
            volume=1.0,
            price_open=1.2345,
            price_current=1.2400,
            profit=55.0,
            symbol="EURUSD"
        )
        
        position_with_zero_sl = PositionData(
            ticket=789012,
            time=datetime.now(),
            time_msc=1698399000000,
            type=0,
            magic=12345,
            reason=0,
            volume=1.0,
            price_open=1.2345,
            price_current=1.2400,
            profit=55.0,
            symbol="EURUSD",
            sl=0.0
        )
        
        assert position_with_sl.has_sl is True
        assert position_without_sl.has_sl is False
        assert position_with_zero_sl.has_sl is False
    
    def test_has_tp_property(self):
        """Test has_tp property."""
        position_with_tp = PositionData(
            ticket=123456,
            time=datetime.now(),
            time_msc=1698399000000,
            type=0,
            magic=12345,
            reason=0,
            volume=1.0,
            price_open=1.2345,
            price_current=1.2400,
            profit=55.0,
            symbol="EURUSD",
            tp=1.2500
        )
        
        position_without_tp = PositionData(
            ticket=654321,
            time=datetime.now(),
            time_msc=1698399000000,
            type=0,
            magic=12345,
            reason=0,
            volume=1.0,
            price_open=1.2345,
            price_current=1.2400,
            profit=55.0,
            symbol="EURUSD"
        )
        
        position_with_zero_tp = PositionData(
            ticket=789012,
            time=datetime.now(),
            time_msc=1698399000000,
            type=0,
            magic=12345,
            reason=0,
            volume=1.0,
            price_open=1.2345,
            price_current=1.2400,
            profit=55.0,
            symbol="EURUSD",
            tp=0.0
        )
        
        assert position_with_tp.has_tp is True
        assert position_without_tp.has_tp is False
        assert position_with_zero_tp.has_tp is False