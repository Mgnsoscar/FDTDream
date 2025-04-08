from ....base_classes import Module
from ....resources import validation


class FDTDAutoShutoffSubsettings(Module):

    def use_early_shutoff(self, true_or_false: bool, auto_shutoff_min: float = None) -> None:
        """
        Enable or disable early shutoff for the simulation based on energy levels.

        This method configures the simulation to automatically terminate when
        most of the energy has exited the simulation volume. By enabling early
        shutoff, you can save computation time by preventing the simulation
        from running longer than necessary.

        When enabled, the simulation will end when the total energy in the
        simulation volume falls to the specified fraction of the maximum
        energy injected. The simulation data will be automatically saved at
        this point.

        Parameters:
        - true_or_false: A boolean value indicating whether to enable (True)
          or disable (False) the early shutoff feature.
        - auto_shutoff_min: An optional float specifying the minimum fraction
          of maximum energy injected at which the simulation should terminate.
          This parameter is only considered if early shutoff is enabled.

        Usage:
        - Call this method when you want to implement early shutoff for your
          simulation, particularly useful in long-running simulations where
          energy loss is a key consideration.

        Raises:
        - ValueError: If the provided true_or_false value is not a boolean.

        """
        self._set("use early shutoff", true_or_false)

        if true_or_false and auto_shutoff_min is not None:
            validation.positive_number(auto_shutoff_min, "auto_shutoff_min")
            self._set("auto shutoff min", auto_shutoff_min)

    def use_divergence_checking(self, true_or_false: bool, auto_shutoff_max: float = None) -> None:
        """
        Enable or disable divergence checking for the simulation.

        This method allows the simulation to automatically terminate when
        the total energy in the simulation volume exceeds a specified
        multiple of the maximum energy injected. This feature is useful
        for preventing runaway simulations that could lead to excessive
        resource usage or invalid results.

        Parameters:
        - true_or_false: A boolean value indicating whether to enable
          (True) or disable (False) divergence checking.
        - auto_shutoff_max: An optional float specifying the maximum
          factor by which the total energy in the simulation volume can
          exceed the maximum energy injected before the simulation is
          automatically ended. If this parameter is provided, it is
          validated to ensure it is a positive number.

        Usage:
        - Call this method to configure the divergence checking behavior
          in the simulation. This ensures that the simulation can safely
          shut down if energy levels become unmanageable.

        Raises:
        - ValueError: If auto_shutoff_max is provided but is not a
          positive number.

        """
        self._set("use divergence checking", true_or_false)

        if true_or_false and auto_shutoff_max is not None:
            validation.positive_number(auto_shutoff_max, "auto_shutoff_max")
            self._set("auto shutoff max", auto_shutoff_max)

    def set_down_sample_time(self, down_sample_time: int) -> None:
        """
        Set the down sample time for checking auto shutoff conditions.

        This method specifies the interval at which the simulation checks
        the auto shutoff conditions. The simulation will evaluate whether
        to terminate based on energy levels every `down_sample_time`
        number of `dT` time steps.

        Setting a down sample time allows for efficient monitoring of the
        simulation's energy status without requiring continuous checks,
        which can improve performance.

        Parameters:
        - down_sample_time: An integer representing the number of time
          steps (dT) between each evaluation of the auto shutoff conditions.
          A value of 1 means that the conditions will be checked at every
          time step, while a larger value will reduce the frequency of checks.

        Usage:
        - Call this method to configure how often the simulation evaluates
          the auto shutoff conditions, allowing for better performance tuning
          in long simulations.

        Raises:
        - ValueError: If down_sample_time is not a positive integer.

        """
        validation.positive_integer(down_sample_time, "down_sample_time")
        self._set("down sample time", down_sample_time)

