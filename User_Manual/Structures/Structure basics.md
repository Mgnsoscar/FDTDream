# Structure Basics

FDTDream supports not all, but most of the structure types present in the Lumerical FDTD desktop application.

**Lumerical FDTD native structure types**:
- Rectangle
- Circle
- Sphere
- Ring
- Pyramid
- Polygon
- Structure Group
- Planar Solid

**Custom FDTDream structure types**:
- Regular Polygon
- Lattice
- Triangle

All structures can be added to a simulation using the methods found in the `sim.add.structures` module. 
Each method initializes a specific structure type, adds it to the simulation, and returns a python object corresponding 
to the structure. All subsequent modifications of the structure is done through this returned object.

```python
# Create a rectangle structure.
rectangle = sim.add.structures.rectangle("rectangle")  # No keyword arguments -> rectangle with default values. Def. position is (0, 0, 0).

# Create a circles tructure.
circle = sim.add.structures.circle("circle")  # Creates a default circle
```
Each structure type as it's own set of keyword arguments that 
allow the user to set the structure's properties already in the initializing method. The keyword arguments are 
auto-complete compatible, and is listed in the documentation of each method.
```python
rectangle_2 = sim.add.structures.rectangle("rectangle 2", 
                                           x=100, y=100, z=0, 
                                           x_span=500, y_span=200, z_span=100, 
                                           rot_vec=(0, 0, 1), rot_angle=45,
                                           material="Au (Gold) - Johnson and Christy")
```
>In the Lumerical FDTD desktop application, several structures can share the same name, however, this makes it very difficult to modify the correct objects through the Lumerical API. Therefore, all object created by FDTDream must have a unique name. If not, an error will be raised.


All structures objects have a set of properties that can be directly modified. Some of these properties are shared between the different types, while some are unique to the specific structure type. Here's some examples:

```python
# Change x span to 400 nm and increase z span by 10 nm
rectangle.x_span = 400
rectangle.z_span += 200

# Disable the structure
rectangle.enabled = False

# Move the structure 100 nm in negative x-direction
rectangle.x -= 100

# Double the radius of the circle's y-radius
circle.radius_2 *= 2
```

All structures have a `settings` module with submodules that corresponds to the setting tabs in the desktop application. These are:
- [geometry](../Getting%20started/Geometry%20module.md)
- [material](Material%20module.md)
- [rotation](Rotation%20module.md)
