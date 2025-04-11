# 🌐 Creating and Loading Simulations

FDTDream allows you to manipulate simulation files through a simulation object, typically referred to as `sim` in all examples. Structures and objects within the simulation environment are either created through the simulation object or through objects created by it.

There are three main ways to handle simulation environments in FDTDream:

1. ✨ **Creating a new simulation file**
2. 📂 **Loading an existing simulation file**
3. 🔄 **Using an existing simulation file as a base while saving to a different file**

## 🚀 Getting Started

Regardless of the approach you choose, you first need to import the `FDTDream` object:

```python
from fdtdream import FDTDream
```

---

## 1️⃣ Creating a New Simulation

To create a new simulation, use the following:

```python
sim = FDTDream.new_simulation()
```

When no arguments are provided, a file explorer will prompt you to select a name and location for the simulation file. You’ll see the following message in the console:

```cmd
Replace the new_simulation() call with this to do exactly the same without calling the file explorer.

sim = FDTDream.new_simulation(r'selected_save_path.fsp', units='nm', hide=False)
```

### Arguments:
- **Path**: The location and name of the new file. If provided, the file explorer won't appear.
- **units**: Defines the units for all length values (default is nanometers).
- **hide**: Determines whether the Lumerical application runs in the background (`True`) or opens (`False`).

---

## 2️⃣ Loading an Existing Simulation

To load an existing simulation file, use the following:

```python
sim = FDTDream.load_simulation()
```

If no file path is provided, a file explorer will prompt you to select a file. After the simulation is loaded, FDTDream reconstructs the corresponding Python objects from its contents. You’ll see type annotations in the console like this:

```cmd
Replace the load_simulation() call with this to do exactly the same without calling the file explorer.

sim = FDTDream.load_simulation(r'path_that_you_loaded_from.fsp', 
    units='nm', hide=True)

# region TYPE ANNOTATIONS

fdtd: FDTDream.i.FDTDRegion = getattr(sim, '_fdtd')
rectangle: FDTDream.i.Rectangle = getattr(sim, 'rectangle')
circle: FDTDream.i.Circle = getattr(sim, 'circle')

# endregion TYPE ANNOTATIONS
```

Copy and paste these lines into your script to skip the file explorer and ensure full control with complete auto-completion support.

### Example:

```python
sim = FDTDream.load_simulation(r'path_that_you_loaded_from.fsp', 
    units='nm', hide=True)

# region TYPE ANNOTATIONS

fdtd: FDTDream.i.FDTDRegion = getattr(sim, '_fdtd')
rectangle: FDTDream.i.Rectangle = getattr(sim, 'rectangle')
circle: FDTDream.i.Circle = getattr(sim, 'circle')

# endregion TYPE ANNOTATIONS

rectangle.x_span = 500  # Change width of rectangle to 500 nm
circle.settings.material.set_material("Au (Gold) - Johnson and Christy")  # Change the circle's material.

# Save the simulation.
sim.save()
```

When loading a simulation, FDTDream updates its internal material register based on the file contents, enabling material-related settings auto-completion. Calling `sim.save()` will overwrite the file unless a different save path is specified.

> ⚠️ **Note:** Loading simulation files that were not created with FDTDream may lead to unexpected behavior or errors. While most structures, monitors, and sources should load correctly, certain groups might not be interpreted properly unless they were originally created in FDTDream.

---

## 3️⃣ Loading Simulation Files as Base Environments

A powerful feature of FDTDream is the ability to load a predefined simulation environment as a starting point for a new simulation. For example, you can create a base simulation file in the Lumerical FDTD desktop application, customize it, and use it as a template in FDTDream. Your new simulation will be saved to a different file, leaving the original base file unchanged.

To load a base simulation, use:

```python
sim = FDTDream.load_base()
```

This method prompts for two file selections:
1. Select the base simulation file.
2. Choose the location where the modified simulation should be saved.

Calling `sim.save()` will overwrite the new simulation file, leaving the original base file untouched.

---

## 💾 Saving Simulation Files

Simulation files are automatically saved to the location specified when calling `new_simulation()`, `load_simulation()`, or `load_base()`. To specify a custom save location, pass it as the only argument to the `sim.save()` method.

```python
sim.save(r'custom_save_path.fsp')
```
