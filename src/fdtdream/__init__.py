import sys

from .fdtdream import FDTDream
from .lumapi import set_lumapi_location, get_lumapi_location

_REQUIRED_MAJOR = 3
_REQUIRED_MINOR = 11  # Change this to your minimum required version

if sys.version_info < (_REQUIRED_MAJOR, _REQUIRED_MINOR):
    raise RuntimeError(
        f"The FDTDream package requires Python {_REQUIRED_MAJOR}.{_REQUIRED_MINOR} or higher."
        f"You are currently using Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}."
    )

__all__ = ["FDTDream", "set_lumapi_location", "get_lumapi_location"]

