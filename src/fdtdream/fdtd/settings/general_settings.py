from ...base_classes import Module
from ...resources.literals import DIMENSION
from ...resources import validation
from ...resources import Materials


class FDTDGeneralSettings(Module):

    def set_dimension(self, dimension: DIMENSION) -> None:
        """
        Set the dimension of the simulation region.

        The dimension can be either 2D or 3D, affecting how the simulation is performed
        and the parameters that are available.

        Args:
            dimension (DIMENSION): The dimension of the simulation (2D or 3D).
        """
        validation.in_literal(dimension, "dimension", DIMENSION)
        self._set("dimension", dimension)

    def set_simulation_time(self, simulation_time: float) -> None:
        """
        Set the maximum duration of the simulation.

        The simulation time is specified in femtoseconds (fs). The actual simulation may
        terminate early if the autoshutoff criteria are met before reaching this maximum time.

        Args:
            simulation_time (float): Maximum simulation time in femtoseconds (fs).

        Raises:
            ValueError: If the provided simulation time is negative.
        """
        validation.positive_number(simulation_time, "simulation_time")
        self._set("simulation time", simulation_time)

    def set_simulation_temperature(self, simulation_temperature: float) -> None:
        """
        Set the temperature for the simulation.

        This temperature setting is used for simulations that include temperature-dependent
        objects, and it is specified in Kelvin (K).

        Args:
            simulation_temperature (float): Simulation temperature in Kelvin (K).

        Raises:
            ValueError: If the provided temperature is not positive.
        """
        validation.positive_number(simulation_temperature, "simulation_temperature")
        self._set("simulation temperature", simulation_temperature)

    def set_background_material(self, material: Materials, index: float = None) -> None:
        """
        Set the background material for the simulation.

        Optionally, a refractive index can be provided if the selected material is
        "<Object defined dielectric>". This allows for a more specific simulation setup
        based on the dielectric properties of the material.

        Args:
            material (Materials): The material to be used for the background.
            index (float, optional): The refractive index to be set if the material is
                                     "<Object defined dielectric>".

        Raises:
            ValueError:
                If the material is "<Object defined dielectric>" but no index is provided.
                If a non-dielectric material is provided but an index is given.
        """

        # Set the background material parameter
        self._set("background material", material)

        # Check for specific conditions related to "<Object defined dielectric>"
        if material == "<Object defined dielectric>" and index is None:
            raise ValueError(
                "A refractive index must be provided when the material is set to '<Object defined dielectric>'."
            )
        elif material != "<Object defined dielectric>" and index is not None:
            raise ValueError(
                f"The material '{material}' does not support a refractive index. Remove the index argument."
            )
        elif material == "<Object defined dielectric>" and index is not None:
            # Set the index if applicable
            self._set("index", index)
