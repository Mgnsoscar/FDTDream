from ....base_classes import Module
from ....resources import validation


class FDTDMiscellaneousSubsettings(Module):

    def set_always_use_complex_fields(self, true_or_false: bool) -> None:
        """
        Set the option to always use complex fields during simulation.

        This method enables or disables the use of complex fields
        for the simulation. When enabled, the algorithm will utilize
        complex fields throughout the simulation process, which may
        lead to slower simulation times and increased memory usage.
        This setting is generally recommended only when necessary.
        By default, complex fields are utilized only when Bloch
        boundary conditions are applied.

        As of version 2024 R2, this setting is compatible with the
        FDTD GPU solver, allowing for improved performance with
        complex fields on compatible hardware. It's important to
        note that if Bloch boundary conditions are selected, complex
        fields will be utilized regardless of the state of this
        checkbox.

        Parameters:
        - true_or_false: A boolean value indicating whether to
          always use complex fields (True) or not (False).

        """
        validation.boolean(true_or_false, "true_or_false")
        self._set("always use complex fields", true_or_false)

    def set_max_source_time_signal_length(self, length: int) -> None:
        """
        Set the maximum length of data used by sources to store the
        "time" and "time_signal" properties.

        This method allows advanced users to specify the maximum
        length for the data related to time and time signals in
        sources. Reducing this length can save memory, especially
        in simulations that utilize a large number of sources or
        when the simulation time is on the order of 100 picoseconds
        (ps), which is uncommon. However, caution should be taken
        when adjusting this parameter, as the "time" and "time_signal"
        properties are crucial for calculating source power, source
        normalization, and the normalization for transmission functions.

        Parameters:
        - length: An integer representing the maximum length of data
          for the "time" and "time_signal" properties. Should be a positive integer greater
          than or equal to 32.

        """
        validation.integer_in_range(length, "length", (32, float('inf')))
        self._set("max source time length signal", length)
