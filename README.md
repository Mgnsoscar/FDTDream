# FDTDream

**FDTDream** is a Python framework for creating simulation geometries in Lumerical FDTD, specifically designed for thin 
film applications. The framework includes a custom database where extracted simulation results are saved for easy access 
and analysis.

## Prerequisites

- A valid license for **Lumerical FDTD**.
- **FDTD** installed on your computer.
- Python packages listed in `requisites.txt` installed.
- Correctly configured path to the **Lumerical Python API** (`lumapi.py`). This is usually found in a default directory, 
but you may need to update the path if the code does not work.

## Initial Setup

1. **Verify lumapi.py Import:**

    \
    Ensure that you are importing `lumapi.py` from the correct directory. In the `Simulation.py` file, you will find the following code snippet:

    ```python
    # Import the Lumerical Python API
    import importlib.util 
    spec_win = importlib.util.spec_from_file_location(
        name='lumapi', 
        location=r"C:\Program Files\Lumerical\v241\api\python\lumapi.py"
    )
    lumapi = importlib.util.module_from_spec(spec_win)
    spec_win.loader.exec_module(lumapi)
    ```

    If you can't run the code initially, Your lumapi.py file is probably located elsewhere. With different FDTD releases, the \v241\ subfolder could be
    named differently, so try locating Your lumapi.py file and change the location variable in the code snippet above.


2. **Install required python packages:**\
    \
    Ensure that you have the required Python packages installed. From the Python console in you IDE you should just be able to run the command:
    ```
    pip install requirements.txt
    ```
    which will install all of them at once. If this doesn't work, you can run a **pip install** command for each one of the packages in the requirements.txt
    file separately in the python console.

## Getting started

1. **Import the SimulationBase class:**

    \
    First you need to import the SimulationBase class. This is the middle-man between you and the lumarical python API:

    ```python
    from Simulation import SimulationBase
    ```

2. **Creating a simulation enviroment:**
    
    \
    You can create a default simulation enviroment only by constructing an object from the SimulationBase class:
    ```python
    simulation = SimulationBase(
        simulation_name="Example Simulation",  # Name of the simulation. Will be called this in the database
        simulation_folder="Example Simulations",  # Name of the folder the simulation file will be saved to
        db_name="Example database",  # Name of the database results should be saved to
        hide=False  # Wether the FDTD program should open or run in the background.
   )
    ```
    If this is the first time you've made a simulation object, the SimulationBase-class will generate a default simulation
    enviroment with six monitors, a source, an FDTD region with appropriate boundary conditions, and a substrate with
    surface located at z=0, along with a bunch of other settings you would usually set manually. 
    This default enviroment will then be saved to the **Base Enviroment** directory, and all
    subsequent simulations created will load this base enviroment. This saves a lot of time. 

    \
    Also, a folder with the specified folder name will be created in the **Simulations** directory. Here, the simulation
    you create is saved with the specified simulation name, first when you create the simulation, but also if you call the 
    `simulation.save()` method. 
    
    \
    The `db_name` parameter is the name of the database your simulation results will be saved to. If the database doesn't
    exist, it will be created in the **Database** directory.

    \
    The `hide` input parameter is to specify wether the FDTD program should be opened, or
    if it should run in the background. It's cool to see the simulations generated automatically when the program opens,
    but when you create simulations with a lot of structures, FDTD spends quite some time and computational power on
    creating everything visually. Setting `hide=True` negates this.

    \
    The code above will result in this simulation enviroment:
    \
    ![Default simulation enviroment.](Example_images/Default_enviroment.png)
    
    
3. **Setting simulation bandwidth**

    \
    By default the simulation has a wavelength range from 400 nm to 1500 nm, where the monitors get results from
    1000 frequency points. You can easily change this by using the `set_global_wavelength_range()` method:
    ```python
    simulation.set_global_wavelength_range(
        wavelength_start=400,  # The smallest wavelength produced by the source
        wavelength_stop=1000,  # The largest wavelength produced by the source
        frequency_points=1000  # The number of frequency points recorded by the monitors
    )
    ```
   
    The space above the tallest simulation structure and the top of the FDTD-region should be at least half of the max
    wavelength simulated. Calling this function will automatically adjust the FDTD-region, source, and monitor 
    positions accordingly.

    

4. **Adding structures**

    \
    So far you can add two types of structures: rectangles and circles (I'll add custom polygon functionality later maybe).
    To add a rectangle you call the `addrect()` method:

    ```python
    # Add a rectangular etched slit in the PZT thin film
        simulation.addrect(
            structure_type_id=1,  # Identifier for this structure. 1, 2, or 3 means it's parameters are saved to the db.
            hole_in=None,  # This structure is not a hole etched into another structure.
            spans=(100, 200, 100),  # The rectangle is 100 nm wide, 200 nm long, and 100 nm thick
            position=(0, 0, 100/2),  # Positioned in the center of the FDTD-region, on top of the substrate.
            material="Au (Gold) - Johnson and Christy",  # Set material to gold from the Johnson and Christy dataset.
            edge_mesh_size=1,  # Side length of the meshing cubes added to each corner of the structure
            edge_mesh_stepsize=10,  # The mesh stepsize of the meshing cubes added to each corner.
            bulk_mesh_enabled=False  # Disable the mesh that's based on this structure.
        )
    ```
   
    **Structure_type_id:** This will efectively be the name of the structure you're adding. It can be whatever, but the
    structure parameters will only be saved to the database if the structure_type_id is 1, 2, or 3. You can add more than one
    structure with the same structure type id. If you call the `set_structure_spans()` method with the given structure
    type id as an input, you will then set the structure spans for all the structures with the given id. This is quite
    nice when creating structure grids later on.

    \
    **hole_in:** This specifies wether or not the structure you're creating is a hole in another structure. For example,
    if you've created a large rectangle, and you add a smaller rectangle within it of material "etch", then you could pass
    the structure type id of the large rectangle as a parameter here. Then the material of the smaller rectangle would
    be saved to the database as "etch in (large rectangle material)".

    \
    **spans:** Tuple containing the spans in each direction in nanometers.

    \
    **position:** Tuple containing the position coordinates in nanometers. The center of the structure is placed here.

    \
    **material:** A string specifying what material the structure is made out of. Is connected to a type checked list
    of all default FDTD materials, so when you start writing, the list of available materials should pop up.

    \
    **edge_mesh_size:** Optional parameter whichs defaults to None. If a value is passed, a mesh cube with the specified
    side length will be generated and placed at each corner of the structure.

    \
    **edge_mesh_stepsize:** Specifies the stepsize in all directions for the mesh cubes placed at each corner of the structure.

    \
    **bulk_mesh_enabled:** Each created structure has a mesh that covers only that structure. Specify wether this mesh is enabled or not.

    \
    The code snippets up to this point will create this simulation geometry:
    ![Simulation enviroment with added rectangle and specified simulation wavelength range](Example_images/Example_2.png)

    If passing values to the edge mesh cube input parameters, it will create these mesh cubes on each corner:
    ![Edge mesh cubes.](Example_images/edge_mesh.png)

   