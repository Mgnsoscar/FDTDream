# Import the SimulationBase module
from Simulation import SimulationBase

# Import the DatabaseViewer module
from DatabaseViewer import DatabaseViewer

# Create a new simulation by initializing a SimulationBase object
simulation = SimulationBase(
    simulation_name="Example Simulation",  # The name of the simulation save file, also the name in the database
    folder_name="Example Simulations",  # Folder where the simulation file will be saved; created if it doesn't exist
    db_name="Example Database",  # Name of the database for saving results; created if it doesn't exist
    hide=True  # Optional parameter (default=True); hides FDTD if True, runs in the background
)

# Upon initialization, a new base simulation environment is created.
# This includes setting boundary symmetry for the FDTD region, adding six monitors,
# a source, and a substrate with its top surface at z=0.
# The environment is saved in the /Base Environment directory for future use.
# If a base environment file is found, subsequent simulations will build on it
# instead of starting from scratch.

# The base simulation environment created will look like this.
# To view the file in Lumerical, it will be located at:
# "/Simulations/Example Simulations/Example Simulation.fsp".

# Insert image in the README here.

# Now, let's add a simple structure—a 100x100x100 nm rectangle on top of the substrate.
# This can be done using the addrect() method.

simulation.addrect(
    structure_type_id="Example Rectangle",  # Identifier for this type of structure
    hole_in=None,  # Set if this structure is an etch in another structure
    spans=(100, 100, 100),  # Dimensions of the structure (x, y, z) in nm
    position=(0, 0, 100/2),  # Center the structure at this position (x, y, z)
    material="Au (Gold) - Johnson and Christy",  # Material for the structure
    edge_mesh_size=None,  # Optional: mesh cube size at rectangle corners (disabled by default)
    edge_mesh_stepsize=None,  # Optional: stepsize for mesh cubes at the corners
    bulk_mesh_enabled=True  # Enable bulk mesh for the structure (default=True)
)

# simulation.save()

# If you'd like to view the updated simulation geometry, the save() method
# will save the file in the same location.

# The FDTD region is automatically centered between the substrate and the tallest structure.
# By default, it is centered at z=50 nm, suitable for structures of up to 100 nm.
# To simulate a 150 nm thick gold film with an etched circular hole,
# we need to adjust the film thickness. Let's create a new simulation,
# this time running FDTD in the background (hide=True).

simulation_2 = SimulationBase(
    simulation_name="Example Simulation 2",
    folder_name="Example Simulations",
    db_name="Example Database",
    hide=True
)

# Fetch the spans of the FDTD region in the xy-plane
FDTD_xspan, FDTD_yspan, FDTD_zspan = simulation_2.get_FDTD_spans()

# Add a 150 nm thick gold film
simulation_2.addrect(
    structure_type_id="Gold Thin Film",
    hole_in=None,
    spans=(FDTD_xspan * 1.5, FDTD_yspan * 1.5, 150),  # Extend the film slightly beyond the FDTD region, z-span is 150 nm
    position=(0, 0, 150 / 2),  # Center the film in the xy-plane, position it on the substrate
    material="Au (Gold) - Johnson and Christy",
    bulk_mesh_enabled=False  # Disable bulk mesh for the film, focusing on the etched hole
)

# Adjust the FDTD region and monitor positions based on the film thickness
simulation_2.define_film_thickness(thickness=150)

# Add a circular etch into the gold thin film
simulation_2.addcircle(
    structure_type_id=1,  # Save hole parameters to the database
    hole_in="Gold Thin Film",  # This is an etched hole in the gold thin film
    spans=(50, 50, 150),  # Radius in x, radius in y, thickness (z)
    position=(0, 0, 150 / 2),  # Center the hole and make it extend through the film
    material="etch",
    bulk_mesh_enabled=True  # Enable bulk mesh around the hole (default=True)
)

simulation_2.save()

# Now, let’s create a grid of structures.
# We will use a material with data for wavelengths between 400 and 1000 nm,
# and adjust the simulation to this wavelength range.

# Create a new simulation
simulation_3 = SimulationBase(
    simulation_name="Example Simulation 3",
    folder_name="Example Simulations",
    db_name="Example Database"
)

# Set the global wavelength range
simulation_3.set_global_wavelength_range(
    wavelength_start=400,  # Minimum wavelength
    wavelength_stop=1000,  # Maximum wavelength
    frequency_points=1000  # Number of sample points for this range
)

# Set new FDTD spans, changing only the xy-plane and leaving the z-span unchanged
simulation_3.set_FDTD_spans((1000, 1000, None))

# Fetch boundary coordinates of the FDTD region using the get_FDTD_min_max() method.
# This returns a tuple with 3 tuples, each containing the min and max coordinate.
FDTD_x_min_max, FDTD_y_min_max, FDTD_z_min_max = simulation_3.get_FDTD_min_max()
FDTD_x_min, FDTD_x_max = FDTD_x_min_max
FDTD_y_min, FDTD_y_max = FDTD_y_min_max

# Create a grid of structures
simulation_3.create_structure_grid(
    structure_type_id=1,
    shape="rect",  # Can also use 'circle'
    structure_spans=(100, 200, 150),
    structure_material="PZT",
    hole_in=None,
    min_max_x=(FDTD_x_min, FDTD_x_max),  # Grid boundaries in the x-direction
    min_max_y=(FDTD_y_min, FDTD_y_max),  # Grid boundaries in the y-direction
    num_x=3,  # Number of structures along the x-direction
    num_y=3,  # Number of structures along the y-direction
    # Optional parameters. The values here are the default values.
    min_x_solid_boundary=False,  # If the boundary is not the FDTD boundary, set to True.
    max_x_solid_boundary=False,  # This makes the distance to the boundary twice as big.
    min_y_solid_boundary=False,  # This keeps the periodicity constant when the FDTD region is used to create an infinite array.
    max_y_solid_boundary=False,
    edge_mesh_size=None,  # Defaults to None
    edge_mesh_step_size=None,  # Defaults to None
    bulk_mesh_enabled=True  # Defaults to True
)

# Adjust film thickness for proper FDTD placement
simulation_3.define_film_thickness(thickness=150)

# Save the simulation
simulation_3.save()
#
# # Now we'll try to create a more complicated structure.
# #
# # Insert image in the README here.
# #
# # We will add one large rectangle and two grids with smaller rectangles on each side.
# # The boundaries towards the rectangle in the middle will be a 'solid boundary'.
# # We'll start by setting the FDTD xy-plane to 5 µm.

simulation_4 = SimulationBase(
    simulation_name="Example Simulation 4",
    folder_name="Example Simulations",
    db_name="Example Database"
)

simulation_4.set_FDTD_spans((5000, 5000, None))

# Now we'll add the large rectangle
simulation_4.addrect(
    structure_type_id=1,
    hole_in=None,
    spans=(250, 3000, 150),
    position=(0, 0, 150 / 2),
    material="Au (Gold) - Johnson and Christy",
)

# Remember to define the film thickness, as our rectangle is 150 nm, and the default value is 100 nm
simulation_4.define_film_thickness(thickness=150)

# Now we'll use the get_structure_min_max() method to fetch the x-boundaries of the large rectangle
Rect_x_minmax, _, _ = simulation_4.get_structure_min_max(structure_type_id=1)  # We don't need the y and z, so we use _
Rect_xmin, Rect_xmax = Rect_x_minmax

# Now we'll fetch the FDTD x and y boundaries
FDTD_x_minmax, FDTD_y_minmax, _ = simulation_4.get_FDTD_min_max()
FDTD_xmin, FDTD_xmax = FDTD_x_minmax
FDTD_ymin, FDTD_ymax = FDTD_y_minmax

# Now we have everything we need to create the grids.
# Let's start with the one to the left of the large rectangle.
# Remember that the max x boundary here is the large rectangle, so this should be a solid boundary.
simulation_4.create_structure_grid(
    structure_type_id=2,
    shape="rect",
    structure_spans=(100, 200, 150),
    structure_material="Au (Gold) - Johnson and Christy",
    hole_in=None,
    min_max_x=(FDTD_xmin, Rect_xmin),  # Limit the x boundary to the large rectangle
    min_max_y=(FDTD_ymin, FDTD_ymax),
    num_x=4,
    num_y=4,
    max_x_solid_boundary=True,  # The right boundary is the larger rectangle, so this is a solid boundary
)

# Create the grid to the right of the large rectangle
simulation_4.create_structure_grid(
    structure_type_id=2,
    shape="rect",
    structure_spans=(100, 200, 150),
    structure_material="Au (Gold) - Johnson and Christy",
    hole_in=None,
    min_max_x=(Rect_xmax, FDTD_xmax),  # Limit the x boundary to the large rectangle
    min_max_y=(FDTD_ymin, FDTD_ymax),
    num_x=4,
    num_y=4,
    min_x_solid_boundary=True,  # The left boundary is the larger rectangle, so this is a solid boundary
)

simulation_4.save()

# ##################################################
# RUNNING SIMULATIONS, SWEEPS, SAVING TO DATABASE AND VIEWING DATABASE
# ##################################################

# In this section, we will explore how to tweak simulation parameters, run simulations, and examine the results.
# After executing a simulation, the program fetches the results from FDTD, which can accumulate a significant amount
# of data. Typically, results from a single simulation can range from 120 to 300 MB, which is excessive for our purposes.
# Most of this data is not particularly interesting.

# To optimize storage and readability, the program converts all length-based values from meters to nanometers and
# changes all values to 16-bit floating-point numbers instead of the default 64-bit. This reduces the data size by
# a factor of four without compromising accuracy since many values in the dataset consist primarily of leading zeroes.
# For instance, the program converts 0.000000001 m to 1 nm. This significantly conserves storage space and simplifies
# value interpretation.

# Additionally, the program fetches the reflection and transmission spectra, along with the near-field monitor vector fields.
# The raw data includes vector fields for each wavelength simulated; however, the program filters these to retain only the
# vector fields for peaks in the E-field enhancement spectra. The maximum E-field magnitude for each wavelength is calculated
# and saved to the database for plotting against wavelength. The vector fields at these peaks are also saved in the database,
# allowing for plotting within the database viewer.

# Furthermore, the simulation environment includes xz-plane and yz-plane monitors that capture the magnitude of the E-field
# and the Poynting vectors. These monitors are disabled by default but can be activated as needed.

# Let's create a simple infinite array of gold bars and perform a sweep on the bar lengths while saving the results to the database.

simulation_5 = SimulationBase(
    simulation_name="Example simulation 5",
    folder_name="Example Simulations",
    db_name="Example database"
)

# Define the film thickness
simulation_5.define_film_thickness(thickness=100)

# Define the wavelength range (default: 400 to 1500 nm with 1000 points)
simulation_5.set_global_wavelength_range(400, 1500, 1000)

# Create the gold bar structure
bar_xspan = 100
bar_yspan = 150
bar_zspan = 100
simulation_5.addrect(
    structure_type_id=1,
    hole_in=None,
    spans=(bar_xspan, bar_yspan, bar_zspan),
    position=(0, 0, bar_zspan / 2),
    material="Au (Gold) - Johnson and Christy",
    edge_mesh_size=1,
    edge_mesh_stepsize=3,
    bulk_mesh_enabled=False
)

# Define a separation distance between bars (in nanometers)
separation_distance = 150

# Set the FDTD region to achieve the desired separation distance, keeping the z-span unchanged
simulation_5.set_FDTD_spans((
    bar_xspan + separation_distance,
    bar_yspan + separation_distance,
    None
))

# Sweep the length of the gold bars while maintaining the separation distance
for bar_yspan in range(150, 250, 25):  # Sweep the y-span of the gold bar
    simulation_5.set_structure_spans(
        structure_type_id=1,
        spans=(None, bar_yspan, None)  # Change only the y-span
    )

    # Adjust the FDTD span to keep the separation distance constant
    simulation_5.set_FDTD_spans((None, bar_yspan + separation_distance, None))

    # Set a custom comment and parameter for the simulation result
    comment = ("Simulating a periodic array of gold bars. "
               "Sweeping the gold bar length while keeping the separation distance constant.")
    custom_parameter = separation_distance  # Constant separation distance

    # Set the simulation comment and custom parameter
    simulation_5.set_simulation_comment(comment=comment, custom_parameter=custom_parameter)

    # Save the simulation state before running it for better tracking
    simulation_5.run_and_save_to_db()  # Run simulation and save results to database

# After all simulations, check results in the database viewer
# DatabaseViewer.open_db_viewer("Example database")
#
# Note: The database viewer is currently a work in progress. It allows searching via input fields and sorting
# columns by clicking the headers. You can select multiple cells to plot different results together.
# If the application crashes or cells appear empty, restart the application to resolve issues.
#
# ########################
# Enabling/Disabling Monitors and Filling in Monitor Data
# ########################
#
# Each simulation generates a unique hash string based on parameters like structure spans and wavelength range.
# When running a simulation, the program checks if a simulation with the same hash already exists in the database.
# If found, it verifies if any new monitors have been enabled. If none are added, the program prints a message
# stating the simulation has already been saved, and it aborts the run.
#
# If a previous simulation has new monitors enabled, the program will disable existing monitors with saved results,
# run the simulation with the new monitors, and update the database entry accordingly. This approach saves time
# and computational resources.

# Example simulation with monitor enabling/disabling
simulation_6 = SimulationBase(
    simulation_name="Example simulation 6",
    folder_name="Example Simulations",
    db_name="Example database"
)

# Disable transmission and reflection profile monitors
simulation_6.set_monitor_enabled("trans_profile_monitor", False)
simulation_6.set_monitor_enabled("ref_profile_monitor", False)

# Run the simulation
simulation_6.run_and_save_to_db()

# Enable monitors again and add xz- and yz-profile monitors, ensuring all others are disabled
simulation_6.set_monitor_enabled("trans_profile_monitor", True)
simulation_6.set_monitor_enabled("ref_profile_monitor", True)
simulation_6.set_monitor_enabled("xz_profile_monitor", True)
simulation_6.set_monitor_enabled("yz_profile_monitor", True)

# Running the simulation again will update the old database entry with new monitor results
simulation_6.run_and_save_to_db()
