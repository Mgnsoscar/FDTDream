from __future__ import annotations
import os

from typing import TypedDict, Unpack, Union, Sequence, Self, List, Tuple

import numpy as np
import trimesh
from numpy.typing import NDArray

from .settings import StructureSettings
from .structure import Structure
from ..base_classes import BaseGeometry
from ..interfaces import SimulationInterface, SimulationObjectInterface
from ..resources import validation, Materials
from ..resources.functions import convert_length
from ..resources.literals import AXES, LENGTH_UNITS


class PlanarSolidKwargs(TypedDict, total=False):
    """
    Key-value pairs that can be used in the Rectangle structure type's constructor.
    """
    x: float
    y: float
    z: float
    vertices: List[Tuple[float, float, float]]
    faces: List[Tuple[int, ...]]
    mesh: trimesh.Trimesh
    from_file: str
    scale: float
    rot_vec: AXES | Sequence[float]
    rot_angle: float
    rot_point: Sequence[float] | SimulationObjectInterface
    material: Materials
    material_index: Union[str, float]


class PlanarSolidGeometry(BaseGeometry):
    """
    Setting module for geometry specific to the planar solid structure type.
    """

    class _Dimensions(TypedDict, total=False):
        scale: float

    def set_dimensions(self, **kwargs: Unpack[_Dimensions]) -> None:
        """
        This method is deprecated, since a generic Planar Solid Object does not have generic dimensions.

        """
        if scale := kwargs.get("scale", None):
            self._parent_object.scale = scale


class PlanarSolidSettings(StructureSettings):
    """
    A module containing submodules for settings specific to the Rectangle structure type.
    """
    geometry: PlanarSolidGeometry


class PlanarSolid(Structure):
    settings: PlanarSolidSettings
    _scale: float

    # region Dev. Methods

    def __init__(self, name: str, sim: SimulationInterface, **kwargs: Unpack[PlanarSolidKwargs]) -> None:
        super().__init__(name, sim)

        self._scale = 1

        # Assign the settings module
        self.settings = PlanarSolidSettings(self, PlanarSolidGeometry)

        # Filter and apply kwargs
        self._process_kwargs(**kwargs)

    def _process_kwargs(self, copied: bool = False, **kwargs) -> None:
        """Filters and applies the kwargs specific to the Rectangle structure type."""

        # Abort if the kwargs are empty
        if not kwargs:
            return

        # Initialize dicts
        position = {}
        dimensions = {}
        rotation = {}
        material = {}

        # Filter kwargs
        for k, v in kwargs.items():
            if k in ["x", "y", "z"]:
                position[k] = v
            elif k in ["vertices", "faces", "mesh", "from_file", "scale"]:
                dimensions[k] = v
            elif k in ["rot_vec", "rot_angle", "rot_point"]:
                rotation[k] = v
            elif k in ["material", "material_index"]:
                material[k] = v

        # Apply kwargs
        if position:
            self.settings.geometry.set_position(**position)
        if dimensions:
            if "scale" in dimensions:
                self.scale = dimensions["scale"]

            keys = set(dimensions.keys()) - {"scale"}  # Ignore 'scale' if present

            # Define valid input groups
            valid_groups = [
                {"mesh"},  # Only mesh
                {"from_file"},  # Only from_file
                {"vertices", "faces"}  # Both vertices and faces
            ]

            if keys not in valid_groups:
                raise ValueError(
                    "You can define a planar solid using either:\n"
                    "- A trimesh.Trimesh object ('mesh')\n"
                    "- A .obj file ('from_file')\n"
                    "- A list of vertices and a list of face connections ('vertices' and 'faces')\n"
                    "You cannot mix these options."
                )

            if "vertices" in keys:  # vertices and faces
                self._create_solid(np.array(dimensions["vertices"]), np.array(dimensions["faces"]))
            elif "mesh" in keys:  # mesh only
                self._create_solid_from_mesh(dimensions["mesh"])
            elif "from_file" in keys:  # from_file only
                self._create_solid_from_file(dimensions["from_file"])
        if rotation:
            self.settings.rotation.set_rotation(**rotation)
        if material:
            self.settings.material.set_material(**material)

    def _create_solid_from_vertices_and_faces(self, vertices: NDArray, faces: NDArray) -> None:
        # Create a trimesh
        mesh = trimesh.Trimesh(vertices, faces)
        self._create_solid_from_mesh(mesh)

    def _create_solid_from_file(self, file_path: str) -> None:
        # Check if file exists
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"The file '{file_path}' does not exist.")

        # Check if file has .obj extension
        if not file_path.lower().endswith(".obj"):
            raise ValueError("Only .obj files are supported.")

        # Load the .obj file
        with open(file_path, "rb") as file:
            mesh_data = trimesh.exchange.obj.load_obj(file)
            mesh = trimesh.Trimesh(vertices=mesh_data["vertices"], faces=mesh_data["faces"])

        # Define rotation matrices
        R_y = trimesh.transformations.rotation_matrix(np.radians(90), [0, 1, 0])  # 90° around Y-axis
        R_x = trimesh.transformations.rotation_matrix(np.radians(90), [1, 0, 0])  # 90° around X-axis

        # Apply rotations
        mesh.apply_transform(R_y)
        mesh.apply_transform(R_x)
        print(self._scale)
        # Store or process the transformed mesh
        self._create_solid_from_mesh(mesh)

    def _create_solid(self, vertices: NDArray, faces: NDArray) -> None:
        # Set vertices and faces
        self._set("vertices", vertices)
        self._set("facets", faces)

    def _create_solid_from_mesh(self, mesh: trimesh.Trimesh) -> None:
        """Fetches vertices and face connections from a trimesh and sends it to the _create_solid method."""
        # Scale it
        if self._scale != 1:
            mesh.apply_scale(self._scale)

        # Convert vertices to meters.
        vertices = np.array(convert_length(mesh.vertices, self._units, "m"))

        # Reshape faces
        faces = np.array(np.expand_dims(mesh.faces, axis=1).T + 1)

        self._create_solid(vertices,faces)

    def _get_corners(self, absolute: bool = False) -> NDArray:

        # Fetch position and spans
        position = self._get_position(absolute)
        vertices = self._get("vertices", np.ndarray)

        corners = vertices + position

        return corners

    def _get_trimesh(self, absolute: bool = False, units: LENGTH_UNITS = None) -> trimesh.Trimesh:

        if units is None:
            units = self._units
        else:
            validation.in_literal(units, "units", LENGTH_UNITS)

        vertices = convert_length(self._get("vertices", np.ndarray), "m", units)
        faces = self._get("facets", np.ndarray).T[:, 0, :] + -1

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces)

        return mesh

    def _get_scripted(self, position: Sequence[float, float, float]) -> str:
        material = self._get("material", str)

        script = (
            "addplanarsolid();\n"
            f"set('name', '{self._name}');\n"
            f"set('x', {position[0]});\n"
            f"set('y', {position[1]});\n"
            f"set('z', {position[2]});\n"
            f"set('material', '{material}');\n"
        )
        if material == "<Object defined dielectric>":
            script += f"set('index', '{self._get("index", str)}');\n"
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

        # Add vertices to the script.
        vertices = self._get("vertices", np.ndarray)
        script += f"vtx = matrix({vertices.shape[0]}, 3)\n;"
        for idx, vertex in enumerate(vertices, start=1):
            script += f"vtx({idx}, :) = [{vertex[0]}, {vertex[1]}, {vertex[2]}];\n"

        faces = self._get("facets", np.ndarray).T[:, 0, :].astype(int)
        script += f"facets = matrix({faces.shape[1]}, 3, {faces.shape[0]});\n"
        for idx, face in enumerate(faces, start=1):
            script += f"facets(:, 1, {idx}) = [{face[0]}, {face[1]}, {face[2]}];\n"

        script += "set('vertices', vtx);\nset('facets', facets);"

        return script

    # endregion Dev Methods

    @property
    def scale(self) -> float:
        """Returns the scale factor of the mesh."""
        return self._scale

    @scale.setter
    def scale(self, factor: float) -> None:
        """Sets the scale factor of the planar solif. Ie. if 2, the solid is scaled to twice
        the size in all directions."""
        if not isinstance(factor, (float, int)):
            raise TypeError(f"Expected int or float, got {type(factor)}.")
        elif factor <= 0:
            raise ValueError(f"The scale factor must be greater than zero. Got {factor}.")
        else:
            # Fetch the trimesh with scale reverted to original
            mesh = self._get_trimesh()
            mesh.apply_scale(1/self._scale)
            self._scale = factor
            # Recreate mesh
            self._create_solid_from_mesh(mesh)

    def copy(self, name, **kwargs: Unpack[PlanarSolidKwargs]) -> Self:
        return super().copy(name, **kwargs)