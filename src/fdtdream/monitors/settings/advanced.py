from ...base_classes.object_modules import Module
from ...resources import validation
from .literals import SPATIAL_INTERPOLATIONS


class Base(Module):

    def set_spatial_interpolation(self, argument: SPATIAL_INTERPOLATIONS) -> None:
        """
        Sets the method for spatial interpolation of electromagnetic fields recorded by the monitor.

        The interpolation method determines how the electric and magnetic field components are
        aligned spatially for calculations of the Poynting vector and electromagnetic energy density.

        Options:
            - NEAREST mesh CELL: Interpolates fields to the nearest FDTD mesh cell boundary
              (default for 'field and power' monitors).
            - SPECIFIED POSITION: Records fields exactly where the monitor is located
              (default for 'profile' monitors).
            - NONE: No interpolation is performed; each field component is recorded at a different
              position within the Yee cell.

        Args:
            argument (SPATIAL_INTERPOLATIONS): The interpolation method to be applied.
        """
        validation.in_literal(argument, "argument", SPATIAL_INTERPOLATIONS)
        prev_value = self._get("spatial interpolation", str)
        if prev_value != argument:
            self._set("override global monitor settings", True)
            self._set("spatial interpolation", argument)
        return

    def record_data_in_pml(self, true_or_false: bool) -> None:
        """
        Sets whether to collect monitor data within the Perfectly Matched Layer (PML) boundary
        condition region.

        Enabling this option allows the simulation to record data within the PML region, which is
        typically not recommended. It is advised to contact Lumerical support before using this
        feature as it is considered an advanced option.

        Note: The simulation region must have the
        'EXTEND STRUCTURE THROUGH PML' option disabled when this option is enabled.

        Args:
            true_or_false (bool): A flag indicating whether to record data in the PML region.

        Raises:
            UserWarning: If attempting to enable recording data in PML without disabling
            'EXTEND STRUCTURE THROUGH PML'.
        """
        self._set("record data in pml", true_or_false)


class IndexMonitor(Base):

    def record_conformal_mesh_when_possible(self, true_or_false: bool) -> None:
        """
        Enables or disables the recording of conformal mesh information.

        When enabled (default setting), this option allows the index monitor to record
        the effects of the conformal mesh. This information can be helpful for various
        analyses but may not be appropriate for absorption calculations.

        Conformal mesh information can only be recorded when:
        - The spatial interpolation setting is either 'NEAREST mesh CELL' or 'NONE'.
        - The spatial downsampling option is set to 1.

        Args:
            true_or_false (bool): A flag indicating whether to record conformal mesh information.

        Raises:
            UserWarning: If the setting is incompatible with the current spatial interpolation or downsampling settings.
        """

        # Set the parameter for recording conformal mesh
        self._set("record conformal mesh when possible", true_or_false)

    def record_surface_conductivity(self, true_or_false: bool) -> None:
        """
        Enables or disables the recording of surface conductivity.

        When enabled, the index monitor records the surface conductivity used in the simulation,
        which is returned as the SURFACE CONDUCTIVITY result. This feature is particularly useful
        when recording surface conductivity components over space with the spatial interpolation
        option set to either 'SPECIFIED POSITION' or 'NONE'.

        Args:
            true_or_false (bool): A flag indicating whether to record surface conductivity.
        """

        self._set("record surface conductivity", true_or_false)


class FreqAndTimeDomainMonitor(Base):

    def _override(self) -> None:
        if not self._get("override advanced global monitor settings", bool):
            self._set("override advanced global monitor settings", True)

    def override_advanced_global_monitor_settings(self, true_or_false: bool) -> None:
        """
        Enables or disables the option to override advanced global monitor settings.

        When this option is selected, the MIN SAMPLING PER CYCLE can be set. This setting allows for customization of
        monitor behavior beyond the global defaults.

        Args:
            true_or_false (bool):
                - True to enable overriding advanced global monitor settings.
                - False to disable overriding.

        Raises:
            ValueError: If the provided value is not a boolean.
        """

        # Validate that the input is a boolean
        validation.boolean(true_or_false, "true_or_false")
        self._override()
        # Set the parameter to override advanced global monitor settings
        self._set("override advanced global monitor settings", true_or_false)

    def set_min_sampling_per_cycle(self, min_sampling: float) -> None:
        """
        Sets the minimum sampling per optical cycle for the monitor.

        This parameter determines the minimum amount of sampling per optical cycle that can be used.
        By default, it is set at 2 (the Nyquist limit) for optimum efficiency.

        Args:
            min_sampling (float): The minimum sampling per cycle, must be greater than or equal to 2.

        Raises:
            ValueError: If 'override advanced global monitor settings' is not enabled.
            ValueError: If min_sampling is less than 2.
        """

        # Validate the minimum sampling value
        validation.number_in_range(min_sampling, "min_sampling", (2, float('inf')))

        self._override()

        # Set the minimum sampling per cycle
        self._set("min sampling per cycle", min_sampling)
