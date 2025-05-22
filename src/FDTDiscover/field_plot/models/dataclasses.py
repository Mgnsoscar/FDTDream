from __future__ import annotations
from dataclasses import dataclass
from numpy.typing import NDArray
from typing import Optional


@dataclass
class OriginalFieldData:
    E: Optional[FieldData]
    H: Optional[FieldData]
    P: Optional[FieldData]


@dataclass
class FieldData:
    components: str
    array: NDArray

