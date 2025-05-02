from __future__ import annotations

import io
from typing import List
from typing import Optional, Tuple

import numpy as np
from numpy.typing import NDArray
from sqlalchemy import Column, Integer, String, ForeignKey, JSON
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.types import TypeDecorator, LargeBinary
from trimesh import Trimesh

from typing import List, Dict, Optional
from matplotlib.collections import PolyCollection
from matplotlib.path import Path
import matplotlib.path as mpath
from matplotlib.patches import PathPatch
import matplotlib.patches as mpatches
import shapely.geometry as geom
from shapely import MultiPolygon
import shapely.ops as ops
import trimesh


class NumpyArrayType(TypeDecorator):
    impl = LargeBinary
    cache_ok = True  # Required for SQLAlchemy 1.4+

    def process_bind_param(self, value: Optional[np.ndarray], dialect):
        if value is None:
            return None
        with io.BytesIO() as buf:
            # Save both array data + metadata
            np.save(buf, value, allow_pickle=False)  # type: ignore
            return buf.getvalue()

    def process_result_value(self, value: Optional[bytes], dialect):
        if value is None:
            return None
        with io.BytesIO(value) as buf:
            return np.load(buf, allow_pickle=False)


Base = declarative_base()


class SimulationModel(Base):
    __tablename__ = 'simulations'

    id: int = Column(Integer, primary_key=True)
    category: str = Column(String)
    name: str = Column(String)
    parameters: dict = Column(JSON, nullable=True)

    _monitors = relationship(
        "MonitorModel",
        back_populates="_simulation",
        cascade="all, delete-orphan"
    )
    _structures = relationship(
        "StructureModel",
        back_populates="_simulation",
        cascade="all, delete-orphan"
    )

    @property
    def monitors(self) -> List[MonitorModel]:
        return self._monitors

    @property
    def structures(self) -> List[StructureModel]:
        return self._structures


class StructureModel(Base):
    __tablename__ = "structures"

    id: int = Column(Integer, primary_key=True)
    simulation_id: int = Column(Integer, ForeignKey("simulations.id"))
    name: str = Column(String)
    vertices: NDArray = Column(NumpyArrayType)
    faces: NDArray = Column(NumpyArrayType)

    _simulation = relationship("SimulationModel", back_populates="_structures")

    @property
    def simulation(self) -> SimulationModel:
        return self._simulation

    def get_trimesh(self) -> Trimesh:
        """Reconstructs a trimesh object from the array of vertices and the array of face connections."""
        mesh = Trimesh(self.vertices, self.faces)
        return mesh

    def get_projection_and_intersection(self, x_coords: NDArray, y_coords: NDArray,
                                        z_coords: NDArray) -> Tuple[dict, dict]:
        """
        Generate projections and intersection slices from a trimesh object.

        Returns:
            - projection_artists: Dict[str, PolyCollection]
            - intersection_slices: Dict[str, List[Optional[PolyCollection]]]
        """

        def polygon_to_pathpatch(p):
            """Create a PathPatch (with holes) from a shapely Polygon."""
            if p.geom_type == "MultiPolygon":
                return multipolygon_to_single_pathpatch(p)

            verts = []
            codes = []

            # Exterior ring
            ext_coords = np.array(p.exterior.coords)
            verts.extend(ext_coords)
            codes.extend(
                [mpath.Path.MOVETO] + [mpath.Path.LINETO] * (len(ext_coords) - 2) + [mpath.Path.CLOSEPOLY])

            # Interior rings (holes)
            for intr in p.interiors:
                intr_coords = np.array(intr.coords)
                verts.extend(intr_coords)
                codes.extend(
                    [mpath.Path.MOVETO] + [mpath.Path.LINETO] * (len(intr_coords) - 2) + [mpath.Path.CLOSEPOLY])

            path = mpath.Path(verts, codes)
            patch_ = mpatches.PathPatch(path)
            return patch_

        def multipolygon_to_single_pathpatch(multipolygon_):
            """Create a single PathPatch from a MultiPolygon (with all holes and parts combined)."""
            vertices_ = []
            codes_ = []

            for polygon_ in multipolygon_.geoms:
                # Exterior
                ext_ = np.array(polygon_.exterior.coords)
                vertices_.extend(ext_)
                codes_.extend([mpath.Path.MOVETO] + [mpath.Path.LINETO] * (len(ext_) - 2) + [mpath.Path.CLOSEPOLY])

                # Interiors (holes)
                for interior_ in polygon_.interiors:
                    hole_ = np.array(interior_.coords)
                    vertices_.extend(hole_)
                    codes_.extend([mpath.Path.MOVETO] + [mpath.Path.LINETO] * (len(hole_) - 2) + [mpath.Path.CLOSEPOLY])

            vertices_ = np.array(vertices_)
            codes_ = np.array(codes_)

            path_ = mpath.Path(vertices_, codes_)
            patch_ = mpatches.PathPatch(path_)
            return patch_

        # Fetch attributes
        mesh = self.get_trimesh()

        projection_artists: Dict[str, mpatches.PathPatch] = {}
        intersection_slices: Dict[str, List[Optional[mpatches.PathPatch]]] = {
            "xy": [],
            "xz": [],
            "yz": []
        }

        # --- Helper setup ---
        plane_indices = {
            "xy": (0, 1),
            "xz": (0, 2),
            "yz": (1, 2)
        }
        plane_normals = {
            "xy": (0, 0, 1),
            "xz": (0, 1, 0),
            "yz": (1, 0, 0)
        }
        slice_coords = {
            "xy": z_coords,
            "xz": y_coords,
            "yz": x_coords
        }

        # --- Create projections ---
        for plane, vtx_idx in plane_indices.items():

            # Collapse the normal-axis coordinates to 0 and create polygons for each face.
            polys = []
            for face in mesh.faces:
                points_2d = mesh.vertices[face][:, vtx_idx]
                polygon = geom.Polygon(points_2d)
                if polygon.is_valid and not polygon.is_empty and polygon.minimum_clearance > 1e-3:
                    polys.append(polygon)

            if polys:
                total_shape = ops.unary_union(polys)

                if total_shape.geom_type == "Polygon":
                    patch = polygon_to_pathpatch(total_shape)
                    projection_artists[plane] = patch

                elif total_shape.geom_type == "MultiPolygon":
                    patch = multipolygon_to_single_pathpatch(total_shape)
                    projection_artists[plane] = patch

        # --- Create intersections using section_multiplane ---
        for plane, coords in slice_coords.items():
            normal = plane_normals[plane]
            dummy_origin = (0, 0, 0)

            sections = mesh.section_multiplane(
                plane_origin=dummy_origin,
                plane_normal=normal,
                heights=coords
            )

            if sections is None:
                intersection_slices[plane] = [None for _ in coords]
                continue

            for section in sections:
                if section is None or section.is_empty:
                    intersection_slices[plane].append(None)
                    continue

                # try:
                #     if plane == "xz":
                #         reflection = np.array([
                #             [-1, 0, 0],
                #             [0, 1, 0],
                #             [0, 0, 1]
                #         ])
                #         section.apply_transform(reflection)
                #
                #         angle = np.deg2rad(90)
                #         rotation = np.array([
                #             [np.cos(angle), -np.sin(angle), 0],
                #             [np.sin(angle), np.cos(angle), 0],
                #             [0, 0, 1]
                #         ])
                #         section.apply_transform(rotation)
                #
                #     elif plane == "yz":
                #         angle = np.deg2rad(-90)
                #         rotation = np.array([
                #             [np.cos(angle), -np.sin(angle), 0],
                #             [np.sin(angle), np.cos(angle), 0],
                #             [0, 0, 1]
                #         ])
                #         section.apply_transform(rotation)
                #
                # except ValueError as e:
                #     print("to_planar failed:", e)
                #     intersection_slices[plane].append(None)
                #     continue

                lines = []
                for entity in section.entities:
                    discrete = entity.discrete(section.vertices)
                    if len(discrete) > 1:
                        lines.append(geom.LineString(discrete))

                pgon = MultiPolygon(section.polygons_full)

                # Create the patch using your existing helper
                patch = polygon_to_pathpatch(
                    pgon
                )

                intersection_slices[plane].append(patch)

        return projection_artists, intersection_slices


class MonitorModel(Base):
    __tablename__ = 'monitors'

    id: int = Column(Integer, primary_key=True)
    simulation_id: int = Column(Integer, ForeignKey("simulations.id"))
    name: str = Column(String)
    monitor_type: str = Column(String)  # discriminator
    parameters: dict = Column(JSON, nullable=False)

    # Optional FieldAndPowerMonitor fields
    wavelengths: NDArray = Column(NumpyArrayType, nullable=True)
    x: NDArray = Column(NumpyArrayType, nullable=True)
    y: NDArray = Column(NumpyArrayType, nullable=True)
    z: NDArray = Column(NumpyArrayType, nullable=True)
    T: NDArray = Column(NumpyArrayType, nullable=True)
    power: NDArray = Column(NumpyArrayType, nullable=True)

    __mapper_args__ = {
        "polymorphic_on": monitor_type,
        "polymorphic_identity": "base_monitor"
    }

    _simulation = relationship("SimulationModel", back_populates="_monitors")
    _fields = relationship("FieldModel", back_populates="_monitor", cascade="all, delete-orphan")

    @property
    def simulation(self) -> SimulationModel:
        return self._simulation

    @property
    def fields(self) -> List[FieldModel]:
        return self._fields


class FieldAndPowerMonitorModel(MonitorModel):
    __mapper_args__ = {
        "polymorphic_identity": "field_and_power"
    }


class FieldModel(Base):
    __tablename__ = 'fields'

    id = Column(Integer, primary_key=True)
    monitor_id = Column(Integer, ForeignKey("monitors.id"))
    field_name = Column(String)
    components = Column(String)
    data = Column(NumpyArrayType)  # NumPy data stored as binary

    _monitor = relationship("MonitorModel", back_populates="_fields")

    @property
    def monitor(self) -> MonitorModel:
        return self._monitor
