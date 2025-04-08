from __future__ import annotations

# Std library imports
from typing import Callable, Unpack

# Local imports
from ...interfaces import SimulationInterface
from ...lumapi import Lumapi
from ...resources.literals import LENGTH_UNITS
from ...structures import (Rectangle, RectangleKwargs, Circle, CircleKwargs, Sphere, SphereKwargs,
                           Ring, RingKwargs, Pyramid, PyramidKwargs, Polygon, PolygonKwargs, RegularPolygon,
                           RegularPolygonKwargs, StructureGroupKwargs, StructureGroup, Lattice, LatticeKwargs,
                           Triangle, TriangleKwargs, PlanarSolid, PlanarSolidKwargs)


class Structures:
    __slots__ = ["_sim", "_lumapi", "_units", "_check_name"]
    _check_name: Callable[[str], None]
    _sim: SimulationInterface
    _units: Callable[[], LENGTH_UNITS]
    _lumapi: Callable[[], Lumapi]

    def __init__(self, sim: SimulationInterface, lumapi: Lumapi, units: Callable[[], LENGTH_UNITS],
                 check_name: Callable[[str], None]):
        self._sim = sim
        self._lumapi = lumapi
        self._units = units
        self._check_name = check_name

    def structure_group(self, name: str, **kwargs: Unpack[StructureGroupKwargs]) -> StructureGroup:
        self._check_name(name)
        self._lumapi().addstructuregroup()
        self._lumapi().set("name", name)
        structure_group = StructureGroup(name, self._sim, **kwargs)
        self._sim._structures.append(structure_group)
        return structure_group

    def lattice(self, name: str, **kwargs: Unpack[LatticeKwargs]) -> Lattice:
        self._check_name(name)
        self._lumapi().addstructuregroup()
        self._lumapi().set("name", name)
        lattice = Lattice(name, self._sim, **kwargs)
        self._sim._structures.append(lattice)
        return lattice

    def rectangle(self, name: str, **kwargs: Unpack[RectangleKwargs]) -> Rectangle:
        self._check_name(name)
        self._lumapi().addrect()
        self._lumapi().set("name", name)
        rectangle = Rectangle(name, self._sim, **kwargs)
        self._sim._structures.append(rectangle)
        return rectangle

    def circle(self, name: str, **kwargs: Unpack[CircleKwargs]) -> Circle:
        self._check_name(name)
        self._lumapi().addcircle()
        self._lumapi().set("name", name)
        circle = Circle(name, self._sim, **kwargs)
        self._sim._structures.append(circle)
        return circle

    def sphere(self, name: str, **kwargs: Unpack[SphereKwargs]) -> Sphere:
        self._check_name(name)
        self._lumapi().addsphere()
        self._lumapi().set("name", name)
        sphere = Sphere(name, self._sim, **kwargs)
        self._sim._structures.append(sphere)
        return sphere

    def ring(self, name: str, **kwargs: Unpack[RingKwargs]) -> Ring:
        self._check_name(name)
        self._lumapi().addring()
        self._lumapi().set("name", name)
        ring = Ring(name, self._sim, **kwargs)
        self._sim._structures.append(ring)
        return ring

    def pyramid(self, name: str, **kwargs: Unpack[PyramidKwargs]) -> Pyramid:
        self._check_name(name)
        self._lumapi().addpyramid()
        self._lumapi().set("name", name)
        pyramid = Pyramid(name, self._sim, **kwargs)
        self._sim._structures.append(pyramid)
        return pyramid

    def polygon(self, name: str, **kwargs: Unpack[PolygonKwargs]) -> Polygon:
        self._check_name(name)
        self._lumapi().addpoly()
        self._lumapi().set("name", name)
        polygon = Polygon(name, self._sim, **kwargs)
        self._sim._structures.append(polygon)
        return polygon

    def regular_polygon(self, name: str, **kwargs: Unpack[RegularPolygonKwargs]) -> RegularPolygon:
        self._check_name(name)
        self._lumapi().addpoly()
        self._lumapi().set("name", name)
        polygon = RegularPolygon(name, self._sim, **kwargs)
        self._sim._structures.append(polygon)
        return polygon

    def triangle(self, name: str, **kwargs: Unpack[TriangleKwargs]) -> Triangle:
        self._check_name(name)
        self._lumapi().addpoly()
        self._lumapi().set("name", name)
        tri = Triangle(name, self._sim, **kwargs)
        self._sim._structures.append(tri)
        return tri

    def planar_solid(self, name: str, **kwargs: Unpack[PlanarSolidKwargs]) -> PlanarSolid:
        self._check_name(name)
        self._lumapi().addplanarsolid()
        self._lumapi().set("name", name)
        solid = PlanarSolid(name, self._sim, **kwargs)
        self._sim._structures.append(solid)
        return solid