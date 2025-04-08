# FDTDream

FDTDream is a Python package designed to streamline the process of working with Lumerical FDTD simulations. Built on Lumerical's native Python API, FDTDream simplifies the creation and modification of simulation objects with a more intuitive and manageable syntax. Unlike the native API, FDTDream offers comprehensive auto-completion, well-structured documentation, and additional custom objects like lattices and regular polygons, making it significantly easier to use.

---

## Contents
[Installation](#Installation)

[Auto-completion and documentation](##Autocompletion-and-documentation)

---

## Installation  

To use FDTDream, you must have **Lumerical FDTD** installed on your computer, along with a valid license and the correct path to Lumerical's Python API.  

### 1. Install FDTDream  
Run the following command:  
```cmd
pip install fdtdream
```

### 2. Set the Lumerical API path
To permanently set the location of Lumerical’s lumapi.py file, run:
```python
from FDTDream import set_lumapi_location

set_lumapi_location("path_to_lumapi.py")
```
This needs to be done only once, as it updates the default search path for lumapi.py. Unless you reinstall or update FDTDream, no further action is required.

To get the currently set path, use:
```python
from FDTDream import get_lumapi_location

print(get_lumapi_location())
```

### Default *lumapi.py* location
By default, lumapi.py is typically found at:
```cmd
C:\Program Files\Lumerical\v241\api\python\lumapi.py
```
> Note: The v241 folder name may vary depending on your Lumerical installation version.

---
## Autocompletion and documentation
One of FDTDream's key features is its powerful auto-completion and structured documentation. Lumerical's FDTD desktop application has a complex interface with deeply nested menus and options, which can be difficult to translate into a pure Python workflow. FDTDream addresses this challenge by organizing simulation objects into well-structured submodules that closely mirror the original application's hierarchy. This design makes navigation intuitive and enables users to explore available options efficiently. To facilitate this, FDTDream leverages auto-completion, allowing users to "scroll" through available properties and methods instead of memorizing their locations.

For instance, adding an FDTD Region and modifying its boundary conditions is as simple as:
```python
from fdtdream import FDTDream

# Create a new simulation
sim = FDTDream.new_simulation("test_simulation")

# Add an FDTD Region
fdtd = sim.add.simulation.fdtd_region()
fdtd.settings.boundary_conditions.boundaries.set_boundary_types(
    x_min="anti_symmetric", x_max="anti-symmetric",
    y_min="symmetric", y_max="symmetric"
)
```

While this structure may seem extensive, auto-completion eliminates the need to remember exact method locations. Additionally, all methods come with clear documentation, including input variables, types, and explanations of how each setting affects the simulation.

In practice, auto-completion hints will appear as follows:

![image](readme_images/auto_completion/2.png)

![image](readme_images/auto_completion/3.png)

---


## Creating Simulations

FDTDream provides three ways to handle simulation environments:

1. Creating a new simulation file
2. Loading an existing simulation file
3. Using an existing simulation file as a base while saving to a different file

Regardless of the approach, start by importing the FDTDream object. This is the only import you need:
```python
from fdtdream import FDTDream
```

### Creating a new simulation.
To create a new simulation, use:
```python
sim = FDTDream.new_simulation()
```

If no arguments are provided, a file explorer will prompt you to select a name and location for the simulation file. The console will display the following message:
```cmd
Replace the new_simulation() call with this to do exactly the same without calling the file explorer.

sim = FDTDream.new_simulation(r'selected_save_path.fsp', units='nm', hide=False)
```

- The first argument is the location and name of the new file, and if it's provided, the file explorer doesn't appear. 
- The **units** argument defines what units all length values will be interpreted in, and is in nanometers by default. 
- The **hide** argument decides wether the Lumerical application should open or run in the background. 

### Loading an existing simulation.
To load an existing simulation file, use:
```python
sim = FDTDream.load_simulation()
```
If no file path is provided, the file explorer will prompt you to select a file. When a simulation is loaded, FDTDream analyzes its contents and reconstructs the corresponding Python objects. After loading, the program terminates and prints type annotations to the console.

For example, if your simulation contains an FDTD Region, a circle, and a rectangle, the console output will look like this:

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
Copy and paste these lines into your Python script, replacing the original method call. This ensures full control over the simulation objects with complete auto-completion support. Once loaded, you can modify the simulation as follows:

```python
sim = FDTDream.load_simulation(r'path_that_you_loaded_from.fsp',
                               units='nm', hide=True)

# region TYPE ANNOTATIONS

fdtd: FDTDream.i.FDTDRegion = getattr(sim, '_fdtd')
rectangle: FDTDream.i.PlanarSolid = getattr(sim, 'rectangle')
circle: FDTDream.i.Circle = getattr(sim, 'circle')

# endregion TYPE ANNOTATIONS

rectangle.x_span = 500  # Change width of rectangle to 500 nm
circle.settings.material.set_material("Au (Gold) - Johnson and Christy")  # Change the circle's material.

# Save the simulation.
sim.save()

```
Additionally, FDTDream updates its internal material register based on the loaded simulation file, enabling auto-completion for material-related settings. Calling `sim.save()` overwrites the existing file unless a different save path is provided.

> Note: Loading simulation files not created with FDTDream may lead to unexpected behavior or errors. While most structures, monitors, and sources should load correctly, groups might not be properly interpreted unless they were originally created within FDTDream.

### Loading simulation files as base environments
A useful feature of FDTDream is the ability to load a predefined simulation environment as a starting point for a new simulation. For example, you can create a base simulation file in the Lumerical FDTD desktop application, customize it with materials or settings, and then use it as a template. When you load this base file in FDTDream, your new simulation is saved to a different location, ensuring the original remains unchanged. To create a new simulation using a predefined base, run:

```python
sim = FDTDream.load_base()

```
This works exactly like `load_simulation()`, but prompts for two file selections:

1. The first prompt selects the base simulation file.
2. The second prompt specifies where the modified simulation should be saved.

### Saving simulation files
Simulation files are automatically saved to the location specified in the `new_simulation()`, `load_simulation()`, or `load_base()` methods when calling the `sim.save()` method.
You can also specify a custom save path by passing that as the only argument to the method.