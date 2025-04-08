from __future__ import annotations

from typing import TypedDict, Unpack, Iterable

import numpy as np
import trimesh.boolean
from numpy.typing import NDArray
from trimesh import Trimesh

from .rotation import Rotation
from .structure import UpdatableStructure, Structure
from ..base_classes import BaseGeometry, ModuleCollection
from ..interfaces import SimulationInterface, SimulationObjectInterface
from ..resources import validation
from ..resources.constants import DECIMALS
from ..resources.functions import convert_length
from ..resources.literals import LENGTH_UNITS, AXES


class LatticeKwargs(TypedDict, total=False):
    x: float
    y: float
    z: float
    rows: int
    cols: int
    alpha: float
    beta: float
    gamma: float
    rot_vec: Iterable | AXES
    rot_angle: float
    rot_point: Iterable | SimulationObjectInterface
    structure: Structure


class LatticeGeometry(BaseGeometry):
    """
    Setting module for geometry specific to the Lattice structure type.
    """
    _parent_object: Lattice

    class _Dimensions(TypedDict, total=False):
        rows: int
        cols: int
        alpha: float
        beta: float
        gamma: float

    def set_dimensions(self, **kwargs: Unpack[_Dimensions]) -> None:
        """
        Sets the dimensions of the object.

        Args:
            alpha (float): The magnitude of the lattice vector along the x-axis.
            beta (float): The magnitude of the lattice vector along the y-axis.
            gamma (float): The angle (degrees) between the x- and y- lattice vector.
            rows (int): How many rows (in y-direction) The lattice should have.
            cols (int): How many columns (in x-direction) the lattice should have.

        Returns:
            None

        """
        # Return None if not any valid kwargs.
        if not any([k in kwargs for k in ["rows", "cols", "alpha", "beta", "gamma"]]):
            return

        if rows := kwargs.get("rows", None):
            validation.positive_integer(rows, "rows")
            self._parent_object._rows = rows
        if cols := kwargs.get("cols", None):
            validation.positive_integer(cols, "cols")
            self._parent_object._cols = cols
        if alpha := kwargs.get("alpha", None):
            validation.positive_number(alpha, "alpha")
            self._parent_object._alpha = convert_length(alpha, self._units, "m")
        if beta := kwargs.get("beta", None):
            validation.positive_number(beta, "beta")
            self._parent_object._beta = convert_length(beta, self._units, "m")
        if gamma := kwargs.get("gamma", None):
            validation.number_in_range(gamma, "gamma", (0, 180))
            self._parent_object._gamma = np.deg2rad(gamma)

        self._parent_object._sites = self._parent_object._construct_site_matrix()
        if self._parent_object._base_structure is not None:
            self._parent_object.set_structure(self._parent_object._base_structure)


class CopyKwargs(TypedDict, total=False):
    x: float
    y: float


class LatticeSettings(ModuleCollection):
    geometry: LatticeGeometry
    rotation: Rotation
    __slots__ = ["geometry", "rotation"]

    def __init__(self, parent_object) -> None:
        super().__init__(parent_object)
        self.geometry = LatticeGeometry(parent_object)
        self.rotation = Rotation(parent_object)


class Lattice(UpdatableStructure):

    # region Class Body

    # Class variables
    _default_geometry = {"rows": 1, "cols": 1, "alpha": 500, "beta": 500, "gamma": 90}

    # Instance variables
    settings: LatticeSettings
    _sites: NDArray[np.float64]
    _rows: int
    _cols: int
    _alpha: np.float64
    _beta: np.float64
    _gamma: np.float64
    _base_structure: Structure | None
    __slots__ = ["settings", "_sites", "_rows", "_cols", "_alpha", "_beta", "_gamma", "_base_structure"]
    # endregion Class Body

    # region Dev Methods

    def __init__(self, name: str, sim: SimulationInterface, *args, **kwargs: Unpack[LatticeKwargs]) -> None:
        super().__init__(name, sim)

        # Assign the geometry settings
        self.settings = LatticeSettings(self)

        # Avoid running this bit when loading from a .fsp file.
        if not kwargs.get("from_load", None):  # type: ignore
            # Make sure the structure grou is a construction group
            self._set("construction group", True)

            # Init the base structure as None
            self._base_structure = None

            # Assign variables
            if "rows" not in kwargs:
                kwargs["rows"] = self._default_geometry["rows"]
            if "cols" not in kwargs:
                kwargs["cols"] = self._default_geometry["cols"]
            if "alpha" not in kwargs:
                kwargs["alpha"] = self._default_geometry["alpha"]
            if "beta" not in kwargs:
                kwargs["beta"] = self._default_geometry["beta"]
            if "gamma" not in kwargs:
                kwargs["gamma"] = self._default_geometry["gamma"]

            # Process kwargs
            self._process_kwargs(**kwargs)

            # Create the array of lattice points
            self._sites = self._construct_site_matrix()

            # Assign the base shape
            if self._base_structure is not None:
                self.set_structure(self._base_structure)
            else:
                script = (
                    f"deleteall;\n\n"
                    f"type = 'Lattice';\n"
                    f"rows = {self._rows};\n"
                    f"cols = {self._cols};\n"
                    f"alpha = {self._alpha};\n"
                    f"beta = {self._beta};\n"
                    f"gamma = {self._gamma};\n"
                    f"structure_name = '';")
                self._set("script", script)

    def __getitem__(self, indices) -> float | tuple[float, float] | tuple[float, float, float]:
        """
        Returns specific coordinate(s) of a lattice site.

        Args:
            indices: Can be:
                - (row, col): Returns (x, y, z).
                - (row, col, 0): Returns x.
                - (row, col, 1): Returns y.
                - (row, col, 2): Returns z.
                - (row, col, :2): Returns (x, y).

        Returns:
            - float: If a specific coordinate (x, y, or z) is requested.
            - tuple(float, float): If (x, y) is requested.
            - tuple(float, float, float): If (x, y, z) is requested.

        Raises:
            IndexError: If row or col is out of bounds.
            ValueError: If an invalid index format is used.
        """
        if not isinstance(indices, tuple) or not (2 <= len(indices) <= 3):
            raise ValueError("Indexing must be (row, col) or (row, col, index).")

        row, col, *extra = indices  # Unpack indices

        # Validate row and column
        if row > self._rows or row < 1:
            raise IndexError(f"Row {row} is out of bounds. Valid range: 1-{self._rows}.")
        if col > self._cols or col < 1:
            raise IndexError(f"Column {col} is out of bounds. Valid range: 1-{self._cols}.")

        # Fetch coordinates
        x, y = convert_length(self._sites[row, col], "m", self._units)
        z = self.z

        # Handle different index cases
        if not extra:  # (row, col) → return full tuple
            return x, y, z
        elif extra[0] == 0:  # (row, col, 0) → return x
            return x
        elif extra[0] == 1:  # (row, col, 1) → return y
            return y
        elif extra[0] == 2:  # (row, col, 2) → return z
            return z
        elif isinstance(extra[0], slice) and extra[0] == slice(None, 2):  # (row, col, :2) → return (x, y)
            return x, y

        raise ValueError("Invalid indexing. Use (row, col), (row, col, index), or (row, col, :2).")

    def _recreate_lattice(self) -> None:
        """Recreates the lattice sites according to the current settings and places the base structure at each site
        if a base struccture is assigned."""
        self._sites = self._construct_site_matrix()
        if self._base_structure is not None:
            self.set_structure(self._base_structure)

    def _update(self) -> None:
        """Updates the base structure. This method should be called from the _set() method of the base structure object
         whenever a variable is changed."""
        self.set_structure(self._base_structure)

    def _process_kwargs(self, copied: bool = False, **kwargs) -> None:
        """Filters and applies the kwargs specific to the Rectangle structure type."""

        # Abort if the kwargs are empty
        if not kwargs:
            return

        # Initialize dicts
        position = {}
        dimensions = {}
        rotation = {}
        structure = None

        # Filter kwargs
        for k, v in kwargs.items():
            if k in ["x", "y", "z"]:
                position[k] = v
            elif k in ["alpha", "beta", "gamma", "rows", "cols"]:
                dimensions[k] = v
            elif k in ["rot_vec", "rot_angle", "rot_point"]:
                rotation[k] = v
            elif k == "structure":
                structure = v

        # Apply kwargs
        if position:
            self.settings.geometry.set_position(**position)
        self.settings.geometry.set_dimensions(**kwargs)
        if rotation:
            self.settings.rotation.set_rotation(**rotation)
        if structure:
            self.set_structure(structure)

    def set_structure(self, structure: Structure) -> None:
        """
        Assigns a structure type or a structure group to each lattice point. The structure provided to this method
        will be disabled, so that only the copied structures in the lattice will be active objects in the parent
        simulation.

        For developers:
            This method is indirectly called by the _set() method of the base structure. The _set method is called
            every time a property of the base structure is set through the FDTDream framework. To avoid infinite
            recursion loops, all properties of the base structure modified in this method should be done directly
            through lumapi.

        Args:
            structure: The structure or structure group that shall occupy each lattice point.

        Returns:
            None
        """

        if not isinstance(structure, Structure):
            raise TypeError(f"Expected a Structure type, got {type(structure)}.")

        # Assign a reference to the base structure
        if structure != self._base_structure:
            if self._base_structure is not None:
                self._base_structure._updatable_parents.remove(self)
            self._base_structure = structure
            self._base_structure._updatable_parents.append(self)

        # Disable the structure in the parent simulation
        self._lumapi.setnamed(structure._get_scope(), "enabled", False)

        # Write a script that creates a copy of the structure at each lattice point.
        sites = self._sites
        z = 0
        script = (f"deleteall;\n\n"
                  f"type = 'Lattice';\n"
                  f"rows = {self._rows};\n"
                  f"cols = {self._cols};\n"
                  f"alpha = {self._alpha};\n"
                  f"beta = {self._beta};\n"
                  f"gamma = {self._gamma};\n"
                  f"structure_name = '{self._base_structure.name}';\n\n")

        i = 0
        for row in sites:
            for site in row:
                site = (site[0], site[1], z)
                if i == 0:
                    script += structure._get_scripted(site)
                else:
                    script += f"\ncopy();\nset('x', {site[0]});\nset('y', {site[1]});\nset('z', {z});\n"
                i += 1

        # Assign the script
        self._set("script", script)

    def _construct_first_unit_cell(self) -> NDArray[np.float64]:
        """
        Creates the first unit cell of the lattice.
        :return: An ndarray of shape (2, 2, 2), containing each vertex of the unit cell.
        """
        gamma_rad = self._gamma
        v1 = np.array([self._alpha, 0])
        v2 = np.array([self._beta * np.cos(gamma_rad), self._beta * np.sin(gamma_rad)])

        return np.round(np.array([[[0, 0], v1], [v2, v1 + v2]], dtype=np.float64), decimals=10)

    def _construct_site_matrix(self) -> NDArray[np.float64]:
        """
        Constructs a staggered lattice where every two rows form a repeating unit.
        Even-indexed rows (0,2,...) start at the same x-coordinate,
        while odd-indexed rows are shifted by b[0] in x.
        """
        unit_cell = self._construct_first_unit_cell()  # Shape: (2,2,2)
        a = unit_cell[0, 1]  # horizontal translation (e.g., (10, 0))
        b = unit_cell[1, 0]  # vertical translation (e.g., (5, 10))

        # Decompose b into horizontal (shift) and vertical (vertical) components.
        shift = b[0]
        vertical = b[1]

        # Create indices for the grid
        i_indices = np.arange(self._rows)
        j_indices = np.arange(self._cols)
        I, J = np.meshgrid(i_indices, j_indices, indexing='ij')

        # Compute the "pair" index and parity of each row
        pair = I // 2  # how many full pairs (each pair is two rows)
        parity = I % 2  # 0 for even rows, 1 for odd rows

        # Each point is given by:
        #   - j * a: column-wise translation
        #   - pair * [0, 2*vertical]: vertical translation for every two rows
        #   - parity * [shift, vertical]: extra offset for odd rows
        points = (J[..., np.newaxis] * a +
                  pair[..., np.newaxis] * np.array([0, 2 * vertical]) +
                  parity[..., np.newaxis] * np.array([shift, vertical]))
        points -= (np.max(points, axis=(0, 1)) / 2)

        # Reshape to a 2D array of points and enforce float64 dtype. Round to DECIMALS to avoid aritmetic errors.
        return np.round(points.astype(np.float64), DECIMALS)

    def _get_site_array(self, abspos: bool = False) -> NDArray[np.float64]:
        return self._sites.reshape(-1, 2).astype(np.float64) + self._get_position(abspos)

    def _get_trimesh(self, absolute: bool = False, units: LENGTH_UNITS = None) -> Trimesh:

        if self._base_structure is None:
            empty_mesh = Trimesh(vertices=[], faces=[])
            return empty_mesh

        else:

            if units is None:
                units = self._units
            else:
                validation.in_literal(units, "units", LENGTH_UNITS)

            # Fetch the trimesh of the base structure and reset to position (0, 0, 0)
            latticepos = convert_length(self._get_position(absolute=absolute), "m", units)
            base_structure_pos = convert_length(self._base_structure._get_position(absolute=False), self._units, units)
            base_poly = self._base_structure._get_trimesh(absolute=False, units=units)
            base_poly: Trimesh = base_poly.apply_translation(-base_structure_pos)

            # Make copies at each lattice site.
            polys = []
            sites = convert_length(self._sites, "m", units)
            for row in sites:
                for site in row:
                    site = np.array((site[0], site[0], 0)) + latticepos
                    copied = base_poly.copy()
                    polys.append(copied.apply_translation(site))

            # Merge all polygons
            merged: Trimesh = trimesh.boolean.union(polys)

            return merged

    def _get_scripted(self, position: Iterable) -> str:
        script = (f"addstructuregroup();\n"
                  f"set('name', '{self._name}');\n"
                  f"set('x', {self._get('x', float)});\n"
                  f"set('y', {self._get('y', float)});\n"
                  f"set('z', {self._get('z', float)});\n"
                  f'set("script", "{self._get("script", str)}");\n')

        return script

    # endregion Dev Methods

    # region User Properties

    @property
    def alpha(self) -> float:
        """Returns the magnitude of the lattice vector along the x-axis."""
        return float(convert_length(self._alpha, "m", self._units))

    @alpha.setter
    def alpha(self, alpha: float) -> None:
        """Sets the magnitude of the lattice vector along the x-axis."""
        self.settings.geometry.set_dimensions(alpha=alpha)

    @property
    def beta(self) -> float:
        """Returns the magnitude of the lattice vector along the y-axis."""
        return float(convert_length(self._beta, "m", self._units))

    @beta.setter
    def beta(self, beta: float) -> None:
        """Sets the magnitude of the lattice vector along the y-axis."""
        self.settings.geometry.set_dimensions(beta=beta)

    @property
    def gamma(self) -> float:
        """Returns the angle (deg) between the x and y lattice vectors."""
        return float(np.rad2deg(self._gamma))

    @gamma.setter
    def gamma(self, gamma: float) -> None:
        """Sets the angle (deg) between the x and y lattice vectors."""
        self.settings.geometry.set_dimensions(gamma=gamma)

    @property
    def rows(self) -> int:
        """Returns the number of rows (y axis) in the lattice."""
        return self._rows

    @rows.setter
    def rows(self, rows: int) -> None:
        """Sets the number of rows (y axis) in the lattice."""
        self.settings.geometry.set_dimensions(rows=rows)

    @property
    def cols(self) -> int:
        """Returns the number of columns (x axis) in the lattice."""
        return self._cols

    @cols.setter
    def cols(self, cols: int) -> None:
        """Sets the number of columns (x axis) in the lattice."""
        self.settings.geometry.set_dimensions(cols=cols)

    # endregion User Properties
