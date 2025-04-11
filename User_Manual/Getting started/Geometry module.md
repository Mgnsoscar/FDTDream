# Geometry Module – User Guide

## Overview
The Geometry module is a module containing the most universal geometry settings for simulation objects. 
Some types of simulation objects can directly use this module, while others have tailored versions.

---

## Public Methods

### 📏 `set_dimensions`
Sets the dimensions of the object. This method accepts key-value pairs defined in the documentation of the specific object type it belongs to.

**Arguments:**
- `**kwargs`: Key-value pairs representing the dimensions of the object.

**Returns:**
- None

**Example Usage:**
```python
obj.settings.geometry.set_dimensions(x_span=5.0, y_span=10.0, z_span=2.0)
```

---

### 📍 `set_position`
Sets the position of the object in 3D space. If no coordinate is provided for an axis, it remains unchanged.

**Arguments:**
- `x (float)`: The x-coordinate for the object.
- `y (float)`: The y-coordinate for the object.
- `z (float)`: The z-coordinate for the object.

**Returns:**
- None

**Example Usage:**
```python
obj.settings.geometry.set_position(x=2.0, y=3.0, z=4.0)
```

---

### 🔄 `set_position_cylindrically`
Sets the position of the object using cylindrical coordinates with the origin at the specified point. This method converts polar coordinates (theta, radius) into Cartesian coordinates.

**Arguments:**
- `origin (Tuple[float, float] | SimulationObjectInterface)`: A 2D tuple with x and y coordinates, or a simulation object. If a simulation object is provided, its center coordinate is used as the origin.
- `theta (float)`: The angle in degrees from the positive x-axis (counterclockwise).
- `radius (float)`: The radial displacement from the origin.
- `z_offset (Optional[float])`: The displacement along the z-axis. If `None`, the current z-coordinate is used.

**Returns:**
- None

**Example Usage:**
```python
obj.settings.geometry.set_position_cylindrically(origin=(0.0, 0.0), theta=45.0, radius=10.0)
```

---

### 🌐 `set_position_spherically`
Sets the position of the object using spherical coordinates with the origin at the specified point. This method converts spherical coordinates (radius, theta, phi) into Cartesian coordinates.

**Arguments:**
- `origin (Tuple[float, float, float] | SimulationObjectInterface)`: A 3D tuple with x, y, and z coordinates, or a simulation object. If a simulation object is provided, its center coordinate is used as the origin.
- `radius (float)`: The radial distance from the origin.
- `theta (float)`: The angle in degrees from the positive x-axis in the xy-plane.
- `phi (float)`: The angle from the positive z-axis in degrees.

**Returns:**
- None

**Example Usage:**
```python
obj.settings.geometry.set_position_spherically(origin=(0.0, 0.0, 0.0), radius=10.0, theta=30.0, phi=45.0)
```
