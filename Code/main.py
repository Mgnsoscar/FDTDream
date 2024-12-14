from fdtdream import FDTDream

# Create new file
sim = FDTDream.new_file("test")

# Add FDTD
fdtd = sim.add.simulation.fdtd_region(x_span=4800, y_span=4800, z_span=1000)
fdtd.settings.boundary_conditions.boundary_settings.set_boundary_types(x_min="anti-symmetric", x_max="anti-symmetric",
                                                                       y_min="symmetric", y_max="symmetric")
# Add substrate
substrate = sim.add.structures.substrate("substrate", "Si (Silicon) - Palik")

# Add large gold bar
bar = sim.add.structures.rectangle("bar", x_span=200, y_span=3800, z_span=100,
                                   material="Au (Gold) - CRC")
bar.place_on_top_of(substrate)

# Add grid, place on substrate
grid = sim.add.grids.rectangular("right grid", pitch_x=100, pitch_y=100)
grid.set_structure.circle(radius=50, radius_2=100, z_span=100, material="Au (Gold) - CRC")
grid.place_on_top_of(substrate)

# Calc. free space right of bar, calc. rows and cols
space = fdtd.x_max - bar.x_max
grid.set_rows_and_cols(rows=fdtd.y_span//grid.unit_cell_y, cols=space//grid.unit_cell_x)

# Place grid right to bar, maintain periodicity
grid.place_next_to(bar, "x_max", offset=grid.pitch_x)
fdtd.z_span = grid.x_max * 2 + grid.pitch_x

# Copy grid, place left of bar
grid_2 = sim.functions.copy(grid, "left grid", x=-grid.x)

# Save simulation
sim.save()
