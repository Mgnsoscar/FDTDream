# Material Module – User Guide

This module defines the `material` module, which allows users to set and manage materials for structure objects.

---

## 📦 Overview

The `material` module is designed to handle the material properties of structure objects. Key functionalities include:

- Setting and updating the material of an object.
- Specifying refractive indices for custom-defined dielectrics.
- Managing mesh order overrides for materials in the simulation.
- Defining grid attributes for anisotropic materials.

---

## 🛠 Key Methods for Users

### `set_material(material: Materials = None, material_index: Optional[Union[float, str]] = None) -> None`

Sets the material of the object and optionally assigns a refractive index if the material is an `<Object defined dielectric>`.

**Parameters:**

- `material`: The material to assign. Valid materials is listed in the Materials string literal, and is auto-complete compatible.
				The list of materials is updated to reflect the available materials in the current simulation environment.
- `material_index` *(optional)*: The refractive index for the material. This can be a single float for isotropic materials, a string of three float values for anisotropic materials (e.g., `"1;1.5;1"`), or a spatial equation in terms of `x`, `y`, `z` for spatially varying refractive indices (e.g., `"2 + 0.1 * x"`).

**Notes:**

- The `material_index` is only applicable to the `<Object defined dielectric>` material.

---

### `set_index(index: Union[float, str], index_units: INDEX_UNITS = None) -> None`

Sets the refractive index for the material when the material type is `<Object defined dielectric>`.

**Parameters:**

- `index`: The refractive index value, either a float for a constant index or a string for a spatially varying index.
- `index_units` *(optional)*: The units for the spatially varying index, specified using predefined units from `INDEX_UNITS`.

**Notes:**

- Only applicable for materials of type `<Object defined dielectric>`.
- If `index_units` are provided, they are validated against the accepted units in `INDEX_UNITS`.

---

### `override_mesh_order_from_material_database(override: bool, mesh_order: int = None) -> None`

Overrides the mesh order setting from the material database and allows the manual specification of a mesh order.

**Parameters:**

- `override`: A boolean value that determines whether the mesh order should be manually overridden.
- `mesh_order` *(optional)*: The mesh order value to set if `override` is `True`. This value determines the priority of the material during overlap regions in the simulation.

**Notes:**

- The mesh order controls the material priority in areas where multiple materials overlap. Lower mesh order values have higher priority.
- If `override` is `True`, the `mesh_order` must be specified.

---

### `_set_grid_attribute_name(name: str) -> None`

Sets the name of the grid attribute for the object, which is relevant for defining grid configurations, especially for anisotropic optical materials.

>This method has been set as private (underscore in front), and might not show up as code suggestion. This is because
some of the custom structure types built on the native Polygon use the grid attribute value as a way to store information about
what kind of polygon it is. This is used when loading simulations. If you need to use the grid attribute name, use this method,
but this means the object will be loaded as a polygon instead of the custom type.

**Parameters:**

- `name`: The name to assign to the grid attribute.

**Notes:**

- This name identifies specific grid configurations relevant to the simulation and must not be empty or only whitespace.

---

## ✅ Summary

The key public methods of the `Material` class are:

- `set_material()`: Assigns a material to the object and optionally specifies the refractive index.
- `set_index()`: Sets the refractive index for `<Object defined dielectric>` materials.
- `override_mesh_order_from_material_database()`: Overrides the material mesh order and allows manual specification for priority during material overlap.
- `_set_grid_attribute_name()`: Assigns a name to the grid attribute, relevant for anisotropic optical materials.

---
