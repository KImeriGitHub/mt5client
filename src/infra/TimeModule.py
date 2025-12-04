from zoneinfo import ZoneInfo
import datetime

import logging
logger = logging.getLogger(__name__)

class TimeModule:
    def __init__(self, timezone_str: str = "Europe/Zurich"):
        self.timezone = timezone_str

    @property
    def timezone(self) -> ZoneInfo:
        return self._timezone

    @timezone.setter
    def timezone(self, value) -> None:
        if isinstance(value, ZoneInfo):
            self._timezone = value
        else:
            # accept strings (like "Europe/Zurich") or anything castable to str
            self._timezone = ZoneInfo(str(value))

    def calc_sec_to_sleep(self, target_hour: int, target_minute: int = 0) -> float:
        tz = self.timezone
        now = datetime.datetime.now(tz=tz)

        # today at target time in same tz
        target_time = now.replace(
            hour=target_hour,
            minute=target_minute,
            second=0,
            microsecond=0,
        )

        if target_time <= now:
            target_time += datetime.timedelta(days=1)

        seconds_to_wait = max(0.0, (target_time - now).total_seconds())
        logger.info("Calculated seconds to wait: %s", seconds_to_wait)
        return seconds_to_wait
