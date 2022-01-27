from __future__ import annotations

import datetime
import os
import sys
import time
from typing import Any, List, Optional

# LOCAL_TIMEZONE = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo
LOCAL_TIMEZONE = datetime.datetime.now().astimezone().tzinfo


def now_datetime() -> datetime.datetime:
    """Current time in the users local time zone."""
    return datetime.datetime.now(LOCAL_TIMEZONE)


def seconds_to_hour_min_sec(seconds: int) -> str:
    return ""
