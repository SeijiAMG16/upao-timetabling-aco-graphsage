"""Utility helpers for normalizing database values used by the ACO pipeline."""

from __future__ import annotations

from datetime import datetime, time
from math import ceil
from typing import Optional, Union
import unicodedata

_TimeLike = Union[time, str, None]

_DAY_ALIASES = {
    "LUN": 1,
    "LUNES": 1,
    "MON": 1,
    "MONDAY": 1,
    "MAR": 2,
    "MARTES": 2,
    "TUE": 2,
    "TUESDAY": 2,
    "MIE": 3,
    "MIERCOLES": 3,
    "MIERCOLES": 3,
    "MIERCOLES": 3,
    "MIERCOLES": 3,
    "MIE": 3,
}
