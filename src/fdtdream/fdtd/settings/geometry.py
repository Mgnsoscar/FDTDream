from typing import TypedDict, Unpack

from ...base_classes import Module, BaseGeometry
from ...resources.literals import DIMENSION
from ...resources import validation
from ...resources import Materials


class FDTDRegionGeometry(BaseGeometry):
    """
    Setting module for geometry specific to the FDTDRegion type.
    """

    class _Dimensions(TypedDict, total=False):
        x_span: float
        y_span: float
        z_span: float

    def set_dimensions(self, **kwargs: Unpack[_Dimensions]) -> None:
        """
        Sets the dimensions of the object.

        Args:
            x_span (float): The rectangle's span along the x-axis (as if the rectangle was unrotated).
            y_span (float): The rectangle's span along the y-axis (as if the rectangle was unrotated).
            z_span (float): The rectangle's span along the z-axis (as if the rectangle was unrotated).

        Returns:
            None

        """
        super().set_dimensions(**kwargs)
