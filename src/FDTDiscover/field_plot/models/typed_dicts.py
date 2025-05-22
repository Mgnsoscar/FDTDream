from __future__ import annotations

from typing import TypedDict, Optional, Tuple


class SaveFigureState(TypedDict, total=False):
    """The state dictionary for the save figure dialog."""
    dpi: int
    transparent: bool
    bbox_inches: Optional[str]
    pad_inches_visible: bool
    pad_inches: Optional[float]


class FieldSliderConfig(TypedDict, total=False):
    x: Tuple[bool, int, int]
    """First the enabled state, then the range of the x slider (0 -> i), then the value to set it on."""
    y: Tuple[int, int]
    """First the enabled state, then therange of the y slider (0 -> i), then the value to set it on."""
    z: Tuple[int, int]
    """First the enabled state, then the range of the z slider (0 -> i), then the value to set it on."""
    wavelength: Tuple[int, int]
    """First the enabled state, then the range of the wavelength slider (0 -> i), then the value to set it on."""
