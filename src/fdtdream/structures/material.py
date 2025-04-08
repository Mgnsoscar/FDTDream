from typing import Optional, Union
from warnings import warn

from ..resources import Materials, validation
from ..resources import errors
from ..resources.literals import INDEX_UNITS
from ..base_classes.object_modules import Module


class Material(Module):

    def set_material(self, material: Materials = None, material_index: Optional[Union[float, str]] = None) -> None:
        """
        Set the material of the object. If material is <Object defined dielectric>, a refractive
        index can also be provided. The refractive index can be specified as:
            - Isotropic: A single float > 1
            - Anisotropic: A semicolon-separated string of three float values for xx, yy,
                           and zz indices, e.g., "1;1.5;1"
            - Spatially Varying: A spatial equation in terms of x, y, and z, e.g., "2+0.1*x"
        """

        # Validate and assign material
        if material is not None:
            validation.material(str(material), "material")
            self._set("material", material)

        if material_index is not None:
            material = material if material is not None else self._get("material", str)
            if material == "<Object defined dielectric>":
                self._set("index", material_index)
            else:
                warn(f"'index' parameter is only applicable for '<Object defined dielectric>', not {material}. "
                     "Ignoring the provided index.")

    def set_index(self, index: Union[float, str], index_units: INDEX_UNITS = None) -> None:
        """
        Set the refractive index for the material if the material type is "<Object defined dielectric>".

        For structures with material type "<Object defined dielectric>", this method assigns a refractive index.
        The index can be a single float value greater than 1 or a spatially varying equation using x, y, z variables
        (e.g., "2 + 0.1 * x"). When specifying an equation, `index_units` is used to define the units for x, y, z.
        """
        material = self._get("material", str)
        if material == "<Object defined dielectric>":
            self._set("index", str(index))
        else:
            message = f"Expected material type '<Object defined dielectric', not '{material}'."
            raise errors.FDTDreamNotObjectDefinedDielectric(message)

        if index_units is not None:
            validation.in_literal(index_units, "index_units", INDEX_UNITS)
            self._set("index units", index_units)

    def override_mesh_order_from_material_database(self, override: bool, mesh_order: int = None) -> None:
        """
        Overrides the mesh order setting from the material database and allows manual setting of a mesh order.

        When `override` is set to True, the `mesh_order` parameter can be specified to determine priority
        during material overlap in the simulation engine. Higher-priority materials (lower mesh order values)
        will override lower-priority materials in overlap regions. If the 'override' parameter is True,
        the 'mesh_order' parameter will be ignored.
        """
        self._set("override mesh order from material database", bool)
        if override and mesh_order is not None:
            validation.positive_integer(mesh_order, "mesh_order")
            self._set("mesh order", int)

    def _set_grid_attribute_name(self, name: str) -> None:
        """
        Sets the name of the grid attribute that applies to this object.

        The grid attribute name is used to identify specific grid configurations
        relevant to the object's simulation. It is relevant when creating anisotropic optical materials.
        """
        if not name.strip():
            raise errors.FDTDreamEmptyNameError("Grid attribute name cannot be empty or only whitespace.")
        self._set("grid attribute name", name)


__all__ = ["Material"]
