# Rotation Module – User Guide

This module allows users to **assign**, **modify**, and **stack rotations** for structure objects 
It handles rotation in 3D space using Euler angles and supports nested group rotations.

---

## 📦 Overview

The `Rotation` class extends the simulation object system and provides tools for:

- Rotating a structure relative to its current state.
- Setting an absolute rotation from an unrotated state.
- Resetting the rotation state of a structure to it's unrotated state.

---

## 🛠 Key Methods for Users

### 🔁 `rotate(rot_vec, rot_angle, rot_point=None)`

Rotates the object **from its current orientation**.

- **`rot_vec`**: Axis to rotate around – `"x"`, `"y"`, `"z"` or a 3D vector.
- **`rot_angle`**: Angle in degrees (counterclockwise).
- **`rot_point`** *(optional)*: Point the axis passes through – a tuple or another simulation object.

✅ **Stackable** – You can chain rotations:

```python
obj.settings.rotation.rotate("x", 90)("y", 45)("z", 30)
```
---

### 🧭 `set_rotation(rot_vec, rot_angle, rot_point=None)`

Sets the **absolute rotation from the default (unrotated) state**.

**Parameters:**

- Same arguments as `rotate`.

**Returns:**

- A reference to the `rotate()` method so you can immediately chain subsequent relative rotations.

```python
obj.settings.rotation.set_rotation("x", 90)("y", 45)
```

Use this to reset or define a new orientation baseline.

---
### 🔄 `reset_rotation()`

Restores the object to its **unrotated default state**.

This removes any applied rotation and repositions the object accordingly if needed.

Useful when:

- You want to clear all transformations.
- You need a clean baseline before applying new rotations.

```python
obj.settings.rotation.reset_rotation()
```

## ✅ Summary

If you're rotating or positioning simulation objects, you'll mostly use:

- `rotate(...)`
- `set_rotation(...)`

Stackable rotations make chaining transformations easy and expressive.

---