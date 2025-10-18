
from datetime import date
import zlib

def magic_from(symbol: str, d: date) -> int:
    """Derive a stable 31-bit magic number from symbol/date."""
    key = f"{symbol.upper()}|{d:%Y%m%d}"
    return zlib.crc32(key.encode()) & 0x7FFFFFFF