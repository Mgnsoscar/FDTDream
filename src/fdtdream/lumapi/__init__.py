from typing import Any as _Any
import sys as _sys
from .lumapi_location import _lumapi_location, set_lumapi_location, get_lumapi_location

# Import the lumapi module
# Add the directory containing lumapi.py to sys.path
lumapi_dir = r'C:\Program Files\Lumerical\v241\api\python'
if lumapi_dir not in _sys.path:
    _sys.path.insert(0, lumapi_dir)

# Import the lumapi module using standard python import, utilizing cached .pyc if available.
# This way is faster than using importlib.util. Include typy hints to avoid python soft-errors.
lumapi: _Any
import lumapi

# Fetch the FDTD api from the lumapi module.
Lumapi = lumapi.FDTD

__all__ = ["lumapi", "Lumapi", "set_lumapi_location", "get_lumapi_location"]
