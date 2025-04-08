from __future__ import annotations

from typing import TypedDict, Unpack, Sequence, TypeVar, Self, List

import trimesh

from .scripted_structures import *
from .settings import StructureSettings
from .structure import Structure
from .sphere import SphereKwargs
from .rectangle import RectangleKwargs
from .pyramid import PyramidKwargs
from .ring import RingKwargs
from .circle import CircleKwargs
from .polygon import PolygonKwargs
from .regular_polygon import RegularPolygonKwargs
from .triangle import TriangleKwargs
from .planar_solid import PlanarSolidKwargs

from ..base_classes import BaseGeometry, Module
from ..resources.functions import convert_length
from ..resources.literals import AXES, LENGTH_UNITS
from ..resources import validation

T = TypeVar("T")


# region Add Module

class Add(Module):
    _parent_object: StructureGroup

    def rectangle(self, name: str = "rectangle", **kwargs: Unpack[RectangleKwargs]) -> ScriptedRectangle:
        rect = ScriptedRectangle(self._parent_object._sim, name, **kwargs)
        rect._add_parent(self._parent_object)
        self._parent_object._update()
        return rect

    def circle(self, name: str = "circle", **kwargs: Unpack[CircleKwargs]) -> ScriptedCircle:
        circle = ScriptedCircle(self._parent_object._sim, name, **kwargs)
        circle._add_parent(self._parent_object)
        self._parent_object._update()
        return circle

    def sphere(self, name: str = "sphere", **kwargs: Unpack[SphereKwargs]) -> ScriptedSphere:
        sphere = ScriptedSphere(self._parent_object._sim, name, **kwargs)
        sphere._add_parent(self._parent_object)
        self._parent_object._update()
        return sphere

    def ring(self, name: str = "ring", **kwargs: Unpack[RingKwargs]) -> ScriptedRing:
        ring = ScriptedRing(self._parent_object._sim, name, **kwargs)
        ring._add_parent(self._parent_object)
        self._parent_object._update()
        return ring

    def pyramid(self, name: str = "pyramid", **kwargs: Unpack[PyramidKwargs]) -> ScriptedPyramid:
        pyramid = ScriptedPyramid(self._parent_object._sim, name, **kwargs)
        pyramid._add_parent(self._parent_object)
        self._parent_object._update()
        return pyramid

    def polygon(self, name: str = "polygon", **kwargs: Unpack[PolygonKwargs]) -> ScriptedPolygon:
        poly = ScriptedPolygon(self._parent_object._sim, name, **kwargs)
        poly._add_parent(self._parent_object)
        self._parent_object._update()
        return poly

    def regular_polygon(self, name: str = "polygon", **kwargs: Unpack[RegularPolygonKwargs]
                        ) -> ScriptedRegularPolygon:
        poly = ScriptedRegularPolygon(self._parent_object._sim, name, **kwargs)
        poly._add_parent(self._parent_object)
        self._parent_object._update()
        return poly

    def triangle(self, name: str = "triangle", **kwargs: Unpack[TriangleKwargs]) -> ScriptedTriangle:
        tri = ScriptedTriangle(self._parent_object._sim, name, **kwargs)
        tri._add_parent(self._parent_object)
        self._parent_object._update()
        return tri

    def planar_solid(self, name: str = "solid", **kwargs: Unpack[PlanarSolidKwargs]) -> ScriptedPlanarSolid:
        solid = ScriptedPlanarSolid(self._parent_object._sim, name, **kwargs)
        solid._add_parent(self._parent_object)
        self._parent_object._update()
        return solid

# endregion Add Module


# region Structure Group Settings and Kwargs

class StructureGroupKwargs(TypedDict, total=False):
    """
    Key-value pairs that can be used in the StructureGroup structure type's constructor.
    """
    x: float
    y: float
    z: float
    rot_vec: AXES | Sequence[float]
    rot_angle: float
    rot_point: Sequence[float]


class StructureGroupSettings(StructureSettings):
    """
    A module containing submodules for settings specific to the Rectangle structure type.
    """
    geometry: BaseGeometry


# endregion Structure Group Settings and Kwargs

# region Structure Group

class StructureGroup(Structure):
    _structures: list[ScriptedStructure]
    add: Add

    # region Dev. Methods

    def __init__(self, name, sim, **kwargs: Unpack[StructureGroupKwargs]) -> None:
        super().__init__(name, sim)

        # Assign the add module
        self.add = Add(self)

        # Assign the settings module
        self.settings = StructureGroupSettings(self, BaseGeometry)

        # Avoid running this bit when loading from a .fsp file.
        if not kwargs.get("from_load", None):  # type: ignore

            # Make sure the structure group is a construction group
            self._set("construction group", True)

            # Init the list of contained structures
            self._structures = []

            # Process kwargs
            self._process_kwargs(**kwargs)

    def _process_kwargs(self, copied: bool = False, **kwargs) -> None:
        """Filters and applies the kwargs specific to the StructureGroup structure type."""

        # Abort if the kwargs are empty
        if not kwargs:
            return

        # Initialize dicts
        position = {}
        rotation = {}

        # Filter kwargs
        for k, v in kwargs.items():
            if k in ["x", "y", "z"]:
                position[k] = v
            elif k in ["rot_vec", "rot_angle", "rot_point"]:
                rotation[k] = v

        # Apply kwargs
        if position:
            self.settings.geometry.set_position(**position)
        if rotation:
            self.settings.rotation.set_rotation(**rotation)

    def _update(self) -> None:
        scripts = [obj._get_scripted((obj._x, obj._y, obj._z)) for obj in self._structures]

        script = "deleteall;\n\ntype = 'Construction group';\n\n"
        for s in scripts:
            newobj = s.replace("deleteall;", "")
            script += newobj
        self._set("script", script)

        if self._updatable_parents:
            for parent in self._updatable_parents:
                parent._update()


    def _get_trimesh(self, absolute: bool = False, units: LENGTH_UNITS = None) -> trimesh.Trimesh:

        if units is None:
            units = self._units
        else:
            validation.in_literal(units, "units", LENGTH_UNITS)

        trimeshes = [obj._get_trimesh(absolute=False, units="nm") for obj in self._structures]
        union = trimesh.boolean.union(trimeshes)
        union = trimesh.Trimesh(vertices=convert_length(union.vertices, "nm", units), faces=union.faces)
        translated = union.apply_translation(convert_length(self._get_position(absolute), "m", units))

        return translated

    def _get_scripted(self, position: Sequence[float, float, float]) -> str:

        script = (
            "addstructuregroup();\n"
            f"set('name', '{self._name}');\n"
            f"set('x', {position[0]});\n"
            f"set('y', {position[1]});\n"
            f"set('z', {position[2]});\n"
        )
        if self.settings.rotation.__getattribute__("_is_rotated"):
            axes, rotations = self.settings.rotation._get_rotation_euler()
            for axis, rotation, que, nr in zip(axes, rotations, ["first", "second", "third"], ["1", "2", "3"]):
                if rotation == 0:
                    continue
                else:
                    script += (
                        f"set('{que} axis', '{axis}');\n"
                        f"set('rotation {nr}', {rotation});\n"
                    )

        selfscript = self._get("script", str)
        # Replace quotes with escape quotes.
        selfscript = selfscript.replace('"', '\\"')

        s = self._get('script', str).replace("\n", '"+\n"')
        if s.startswith("deletall;"):
            s = s[9:]
        subscript = '"'
        subscript += self._get('script', str).replace("\n", '"+\n"')
        if subscript.endswith('\n"'):
            subscript = subscript[:-3]

        script += f"set('script', {subscript});\n"

        return script

    # endregion Dev Methods

    def copy(self, name, **kwargs: Unpack[StructureGroupKwargs]) -> Self:

        # Copy the group object
        new_obj = super().copy(name, **kwargs)

        # Copy the structures
        new_structures = []
        for structure in self._structures:
            new_structures.append(structure.copy(new_parent=new_obj))

        new_obj._structures = new_structures

        new_obj._update()

        return new_obj

    @property
    def structures(self) -> List[ScriptedStructure]:
        """Returns the list of scripted structures in the structure group."""
        return self._structures

# endregion Structure Group

