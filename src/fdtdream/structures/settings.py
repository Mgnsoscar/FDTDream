from typing import Type

from .material import Material
from .rotation import Rotation
from ..base_classes import BaseGeometry, SimulationObject
from ..base_classes.object_modules import ModuleCollection


class StructureSettings(ModuleCollection):
    """
    Base settings module for structure-type objects.

    This class provides common settings for all structures, including material and rotation.
    Since geometry varies between structures, a subclass of `BaseGeometry` should be created
    for each specific structure type. When inheriting from this class, the `geometry` attribute
    should be redeclared with the appropriate geometry subclass and passed uninitialized
    to the constructor.

    Attributes:
        _parent_object (Structure): The parent object the settings belong to.
        material (Material): The material module.
        rotation (Rotation): The rotation module.
        geometry (BaseGeometry): The base_classes geometry module (should be overridden in subclasses).

    """
    material: Material
    rotation: Rotation
    geometry: BaseGeometry
    __slots__ = ["geometry", "material", "rotation"]

    def __init__(self, parent_object: SimulationObject, geometry: Type[BaseGeometry]) -> None:
        super().__init__(parent_object)
        self.material = Material(parent_object)
        self.rotation = Rotation(parent_object)
        self.geometry = geometry(parent_object)


__all__ = ["StructureSettings"]

