from ....base_classes import Module
from ....resources import validation


class FDTDParalellEngineSubsettings(Module):

    def set_process_grid(self, true_or_false: bool, nx: int = None, ny: int = None, nz: int = None) -> None:
        """
        Configure the process grid for dividing the simulation volume into
        sub-regions for parallel computation.

        This method allows users to set up a grid that divides the
        simulation volume into multiple processes, which can improve
        computational efficiency and performance during simulation runs.
        By specifying the number of subdivisions in the x, y, and z
        directions, users can tailor the processing setup to better
        utilize available computational resources.

        Parameters:
        - true_or_false: A boolean indicating whether to enable
          (True) or disable (False) the process grid configuration.
        - nx: An optional integer specifying the number of divisions
          along the x-axis. This parameter is only relevant if
          true_or_false is set to True.
        - ny: An optional integer specifying the number of divisions
          along the y-axis. This parameter is only relevant if
          true_or_false is set to True.
        - nz: An optional integer specifying the number of divisions
          along the z-axis. This parameter is only relevant if
          true_or_false is set to True.

        Usage:
        - This method should be called to configure the process grid
          for the simulation. Properly setting up the grid can lead to
          better performance and more efficient resource usage.

        Raises:
        - ValueError: If any of nx, ny, or nz are provided as
          negative integers.

        """
        self._set("set process grid", true_or_false)

        if true_or_false:
            if nx is not None:
                validation.positive_integer(nx, "nx")
                self._set("nx", nx)
            if ny is not None:
                validation.positive_integer(ny, "ny")
                self._set("ny", ny)
            if nz is not None:
                validation.positive_integer(nz, "nz")
                self._set("nz", nz)
