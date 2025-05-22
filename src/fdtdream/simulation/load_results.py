from __future__ import annotations
from dataclasses import dataclass
from typing import List, TypedDict
from ..base_classes import SimulationObject
from ..structures import Ring, Polygon, Rectangle, Circle, Sphere, Pyramid, PlanarSolid
from ..monitors import FreqDomainFieldAndPowerMonitor
import trimesh
import numpy as np
from ..resources import validation
from ..resources.functions import convert_length
from ..resources.literals import LENGTH_UNITS


STRUCTURE_TYPES = ["Ring", "Polygon", "Rectangle", "Circle", "Sphere", "Pyramid", "PlanarSolid"]
MONITOR_TYPES = ["DFTMonitor"]
GROUP_TYPES = ["Structure Group", "Layout Group"]


@dataclass
class Position:
    pos: np.ndarray
    relative_coordinates: bool


@dataclass
class FDTDObject:
    name: str
    object_type: str
    parents: List[FDTDObject]
    position: Position



def _get_simulation_objects_in_scope(lumapi,
                                     groupscope: str,
                                     iterated: List[dict[str, str]] = None,
                                     parent: FDTDObject = None) -> List[dict[str, str]]:

    if not iterated:
        iterated = []

    # Select the provided group as the groupscope and select all objects in it
    lumapi.groupscope(groupscope)
    lumapi.selectall()
    num_objects = int(lumapi.getnumber())

    # Iterate through all the objects in the group
    for i in range(num_objects):

        name = lumapi.get("name", i + 1)
        obj_type = lumapi.get("type", i + 1)
        pos = np.array([lumapi.get("x", i+1), lumapi.get("y", i+1), lumapi.get("z", i+1)])
        relative = lumapi.get("use relative coordinates",  i+1)
        position = Position(pos, relative)

        if parent:
            parents = parent.parents + [parent]
        else:
            parents = []

        obj = FDTDObject(name, obj_type, parents, position)
        iterated.append(obj)

        # Check if the object is another group, run this method recursively
        if obj_type in GROUP_TYPES:
            ...
        else:
            ...




    return iterated


# region Trimesh
def get_circle_trimesh(self, lumapi, idx, obj: FDTDObject) -> trimesh.Trimesh:

    # Fetch position and dimensions
    position = np.array([convert_length(x, "m", "nm"), convert_length(y, "m", "nm"), convert_length(z, "m", "nm")])
    radius = convert_length(self.radius, self._units, units)
    radius_2 = convert_length(self.radius_2, self._units, units)
    z_span = convert_length(self.z_span, self._units, units)

    # Create a base_classes cylinder with unit radius and height equal to z_span
    cylinder = trimesh.creation.cylinder(radius=1.0, height=z_span, sections=64)

    # Scale the cylinder to have the desired radii in x and y directions
    scale_matrix = np.diag([radius, radius_2, 1.0, 1.0])  # Scaling along x, y, and keep z unchanged
    cylinder.apply_transform(scale_matrix)

    # Translate the cylinder to the desired position
    cylinder.apply_translation(position)

    # Rotate the trimesh if neccessary.
    cylinder = self._rotate_trimesh(cylinder, position)

    return cylinder
# endregion