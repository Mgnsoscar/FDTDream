from __future__ import annotations

import io
from typing import List, Dict, Optional, Union, Tuple

import matplotlib.patches as mpatches
import matplotlib.path as mpath
import numpy as np
import shapely.geometry as geom
import shapely.ops as ops
from matplotlib.patches import PathPatch
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict
from shapely import MultiPolygon, Polygon
from sqlalchemy import Column, Integer, String, ForeignKey, JSON
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.types import TypeDecorator, LargeBinary
from trimesh import Trimesh


# region Pydantic models
class CustomBaseModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)


class FieldPydanticModel(CustomBaseModel):
    field_name: str
    components: str
    data: np.ndarray

    @classmethod
    def from_model(cls, model: FieldModel) -> FieldPydanticModel:
        return cls(
            field_name=model.field_name,
            components=model.components,
            data=model.data
        )


class FieldAndPowerMonitorPydanticModel(CustomBaseModel):
    name: str
    monitor_type: str = "field_and_power"
    parameters: Dict
    wavelengths: Optional[np.ndarray]
    x: Optional[np.ndarray]
    y: Optional[np.ndarray]
    z: Optional[np.ndarray]
    T: Optional[np.ndarray]
    power: Optional[np.ndarray]
    E: Optional[FieldPydanticModel]
    H: Optional[FieldPydanticModel]
    P: Optional[FieldPydanticModel]

    @classmethod
    def from_model(cls, model: FieldAndPowerMonitorModel) -> FieldAndPowerMonitorPydanticModel:

        # Fetch the fields.
        fields = {f.field_name: FieldPydanticModel.from_model(f) for f in model.fields}

        return cls(
            name=model.name,
            parameters=model.parameters,
            wavelengths=model.wavelengths,
            x=model.x,
            y=model.y,
            z=model.z,
            T=model.T,
            power=model.power,
            E=fields.get("E", None),  # type: ignore
            H=fields.get("H", None),  # type: ignore
            P=fields.get("P", None)  # type: ignore
        )


class StructurePydanticModel(CustomBaseModel):
    name: str
    vertices: np.ndarray
    faces: np.ndarray

    @classmethod
    def from_model(cls, model: StructureModel) -> StructurePydanticModel:
        return cls(
            name=model.name,
            vertices=model.vertices,
            faces=model.faces
        )


class SimulationPydanticModel(CustomBaseModel):
    category: str
    name: str
    parameters: Dict
    structures: List[StructurePydanticModel]
    monitors: List[FieldAndPowerMonitorPydanticModel]

    @classmethod
    def from_model(cls, model: SimulationModel) -> SimulationPydanticModel:
        return cls(
            category=model.category,
            name=model.name,
            parameters=model.parameters or {},
            structures=[StructurePydanticModel.from_model(s) for s in model.structures],
            monitors=[FieldAndPowerMonitorPydanticModel.from_model(m) for m in model.monitors
                      if m.monitor_type == "field_and_power"]
        )
# endregion


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
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    _structures = relationship(
        "StructureModel",
        back_populates="_simulation",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    @property
    def monitors(self) -> List[MonitorModel]:
        return self._monitors

    @property
    def structures(self) -> List[StructureModel]:
        return self._structures


class StructureModel(Base):
    # region Class Body
    __tablename__ = "structures"

    id: int = Column(Integer, primary_key=True)
    simulation_id: int = Column(Integer, ForeignKey("simulations.id", ondelete="CASCADE"))
    name: str = Column(String)
    vertices: NDArray = Column(NumpyArrayType)
    faces: NDArray = Column(NumpyArrayType)

    _simulation = relationship("SimulationModel", back_populates="_structures")
    # endregion

    @property
    def simulation(self) -> SimulationModel:
        return self._simulation

    def get_trimesh(self) -> Trimesh:
        """Reconstructs a trimesh object from the array of vertices and the array of face connections."""
        mesh = Trimesh(self.vertices, self.faces)
        return mesh

    def _polygon_to_pathpatch(self, polygon: Union[Polygon, MultiPolygon]) -> PathPatch:
        """Create a PathPatch accounting for exterior and interiors from a shapely Polygon."""

        if polygon.geom_type == "MultiPolygon":
            return self._multipolygon_to_single_pathpatch(polygon)

        vertices = []
        codes = []

        # Exterior ring
        ext_coords = np.array(polygon.exterior.coords)
        vertices.extend(ext_coords)
        codes.extend(
            [mpath.Path.MOVETO] + [mpath.Path.LINETO] * (len(ext_coords) - 2) + [mpath.Path.CLOSEPOLY])

        # Interior rings (holes)
        for interior in polygon.interiors:
            intr_coords = np.array(interior.coords)
            vertices.extend(intr_coords)
            codes.extend(
                [mpath.Path.MOVETO] + [mpath.Path.LINETO] * (len(intr_coords) - 2) + [mpath.Path.CLOSEPOLY])

        path = mpath.Path(vertices, codes)
        patch = mpatches.PathPatch(path)
        return patch

    @staticmethod
    def _multipolygon_to_single_pathpatch(polygon: MultiPolygon) -> Optional[PathPatch]:
        """Create a single PathPatch from a MultiPolygon (with all holes and parts combined)."""

        vertices = []
        codes = []

        for polygon in polygon.geoms:
            # Exterior
            ext = np.array(polygon.exterior.coords)
            vertices.extend(ext)
            codes.extend([mpath.Path.MOVETO] + [mpath.Path.LINETO] * (len(ext) - 2) + [mpath.Path.CLOSEPOLY])

            # Interiors (holes)
            for interior in polygon.interiors:
                hole = np.array(interior.coords)
                vertices.extend(hole)
                codes.extend([mpath.Path.MOVETO] + [mpath.Path.LINETO] * (len(hole) - 2) + [mpath.Path.CLOSEPOLY])

        vertices = np.array(vertices)
        codes = np.array(codes)

        if vertices.shape[0] == 0:
            return None

        path_ = mpath.Path(vertices, codes)
        patch = mpatches.PathPatch(path_)
        return patch

    def get_projections_and_intersections(self, x: NDArray, y: NDArray, z: NDArray
    ) -> Optional[Tuple[Dict[str, Optional[PathPatch]], Dict[str, List[Optional[PathPatch]]]]]:

        # Fetch the mesh
        mesh = self.get_trimesh()

        # Map plane names to indices
        plane_indices = {
            "XY Plane": (0, 1),
            "XZ Plane": (0, 2),
            "YZ Plane": (1, 2)
        }

        # region Handle 2D projections
        projections = {}

        for plane, indices in plane_indices.items():
            polys = []
            for face in mesh.faces:
                points_2d = mesh.vertices[face][:, indices]
                polygon = geom.Polygon(points_2d)
                if polygon.is_valid and not polygon.is_empty and polygon.minimum_clearance > 1e-4:
                    polys.append(polygon)

            if polys:
                total_shape = ops.unary_union(polys)
                patch = self._polygon_to_pathpatch(total_shape)
            else:
                patch = None

            projections[plane] = patch
        # endregion

        # region Handle 2D intersections
        intersection_slices: Dict[str, List[Optional[PathPatch]]] = {
            "XY Plane": [],
            "XZ Plane": [],
            "YZ Plane": []
        }

        slice_coords = {
            "XY Plane": z,
            "XZ Plane": y,
            "YZ Plane": x,
        }

        plane_normals = {
            "XY Plane": (0, 0, 1),
            "XZ Plane": (0, 1, 0),
            "YZ Plane": (1, 0, 0)
        }

        dummy_origin = (0, 0, 0)

        for plane, indices in plane_indices.items():

            coords = slice_coords[plane]
            normal = plane_normals[plane]

            sections = mesh.section_multiplane(
                plane_origin=dummy_origin,
                plane_normal=normal,
                heights=coords
            )

            if sections is None:
                intersection_slices[plane] = [None for _ in coords]

            for section in sections:
                if section is None or section.is_empty:
                    intersection_slices[plane].append(None)
                    continue

                if plane == "XZ Plane":
                    # First, mirror the intersection across the Y-axis (invert X-axis)
                    reflection = np.array([
                        [-1, 0, 0],  # Mirror X-axis
                        [0, 1, 0],  # Keep Y-axis
                        [0, 0, 1]  # Keep Z-axis
                    ])

                    section.apply_transform(reflection)  # Apply reflection first
                    # Rotate 90 degrees counter-clockwise to swap axes for XZ view
                    angle = np.deg2rad(90)
                    rotation = np.array([
                        [np.cos(angle), -np.sin(angle), 0],
                        [np.sin(angle), np.cos(angle), 0],
                        [0, 0, 1]
                    ])

                    # Apply transform to Path2D (trimesh.path.Path2D expects 3x3 for 2D)
                    section.apply_transform(rotation)

                elif plane == "YZ Plane":

                    # Rotate 180 degrees around origin
                    angle = np.deg2rad(-90)
                    rotation = np.array([
                        [np.cos(angle), -np.sin(angle), 0],
                        [np.sin(angle), np.cos(angle), 0],
                        [0, 0, 1]
                    ])
                    section.apply_transform(rotation)

                lines = []
                for entity in section.entities:
                    discrete = entity.discrete(section.vertices)
                    if len(discrete) > 1:
                        lines.append(geom.LineString(discrete))

                # Gather polygons into a multipolygon
                pgon = MultiPolygon(section.polygons_full)

                # Create the patch using your existing helper
                patch = self._polygon_to_pathpatch(pgon)

                intersection_slices[plane].append(patch)
        # endregion

        return projections, intersection_slices


class MonitorModel(Base):
    __tablename__ = 'monitors'

    id: int = Column(Integer, primary_key=True)
    simulation_id: int = Column(Integer, ForeignKey("simulations.id", ondelete="CASCADE"))
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
    _fields = relationship(
        "FieldModel",
        back_populates="_monitor",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

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
    monitor_id = Column(Integer, ForeignKey("monitors.id", ondelete="CASCADE"))
    field_name = Column(String)
    components = Column(String)
    data = Column(NumpyArrayType)  # NumPy data stored as binary

    _monitor = relationship("MonitorModel", back_populates="_fields")

    @property
    def monitor(self) -> MonitorModel:
        return self._monitor
