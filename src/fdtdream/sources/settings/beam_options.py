from typing import Callable, TypeVar, Type

from ...base_classes.object_modules import Module, ModuleCollection
from ...resources.functions import convert_length, convert_time
from ...resources.literals import LENGTH_UNITS, TIME_UNITS

# region Type Variables
T = TypeVar("T")
GETTER = Callable[[str, Type[T]], T]
SETTER = Callable[[str, T], T]
UNIT_GETTER = Callable[[], str]
# endregion Type Variables


# region Submodules

class ScalarApproximation(Module):

    def _validate_use_scalar_approximation(self) -> None:
        """
        Validates if scalar approximation settings can be applied to the source.

        Raises:
            ValueError: If 'use scalar approximation' is disabled while 'use thin film' is enabled,
                        indicating that 'use scalar approximation' must be enabled first.
        """
        # Check if 'use scalar approximation' is disabled
        if not self._get("use scalar approximation", bool):
            raise ValueError(
                f"Cannot set 'Scalar approximation' settings for Gaussian source while "
                f"'use thin film' is enabled. Enable 'use scalar approximation' first.")

    def set_waist_size_and_distance_from_waist(self, waist_radius_w0: float, distance_from_waist: float,
                                               units: LENGTH_UNITS = None) -> None:
        """
        Sets the waist size and position for the beam within the simulation.

        This method configures the beam waist radius (1/e field radius for Gaussian beams
        or half-width half-maximum (HWHM) for Cauchy/Lorentzian beams) and the distance
        from the waist to the target location. It uses the provided units; if no units are
        specified, it defaults to the global simulation units.

        Args:
            waist_radius_w0 (float): Waist radius at the beam's waist, in specified length units.
            distance_from_waist (float): Distance from the beam's waist to the target location,
                                          in specified length units.
            units (LENGTH_UNITS, optional): Units for waist size and position. Defaults to
                                                    the simulation's global units.

        Returns:
            None

        Raises:
            ValueError: If the waist radius or distance from waist is not valid.
        """

        # Ensure scalar approximation is valid for this configuration
        self._validate_use_scalar_approximation()

        units = units if units is not None else self._units
        self._set("beam parameters", "Waist size and position")

        # Convert and set waist radius in meters
        waist_radius_w0_m = convert_length(waist_radius_w0, from_unit=units, to_unit="m")
        self._set("waist radius w0", waist_radius_w0_m)

        # Convert and set distance from waist in meters
        distance_from_waist_m = convert_length(distance_from_waist, from_unit=units, to_unit="m")
        self._set("distance from waist", distance_from_waist_m)

    def set_beam_size_and_divergence_angle(self, beam_radius_wz: float, divergence_angle: float,
                                           units: LENGTH_UNITS = None) -> None:
        """
        Sets the beam size and divergence angle for the simulation beam in Lumerical FDTD.

        This method configures the beam's radius at a specified position (1/e field radius for
        Gaussian beams or half-width half-maximum (HWHM) for Cauchy/Lorentzian beams) and its
        divergence angle. It uses the specified units; if none are provided, it defaults to
        the simulation's global units.

        Args:
            beam_radius_wz (float): Radius of the beam at position `wz`, in specified length units.
            divergence_angle (float): Beam's divergence angle in degrees, where a positive angle
                                      indicates a diverging beam and a negative angle indicates a
                                      converging beam.
            units (LENGTH_UNITS, optional): Units for the beam radius. Defaults to the
                                                    simulation's global units.

        Returns:
            None

        Raises:
            ValueError: If the beam radius or divergence angle is not valid.
        """

        # Validate scalar approximation setting
        self._validate_use_scalar_approximation()

        # Set length units to global simulation units if not specified
        units = units if units is not None else self._units

        # Set parameters for beam size and divergence angle
        self._set("beam parameters", "Beam size and divergence angle")

        # Convert and set beam radius in meters
        beam_radius_wz_m = convert_length(beam_radius_wz, from_unit=units, to_unit="m")
        self._set("beam radius wz", beam_radius_wz_m)

        # Set divergence angle
        self._set("divergence angle", divergence_angle)


class ThetaVsWavelength(Module):

    def set_frequency_dependent_profile(self, true_or_false: bool, nr_field_profile_samples: int = None) -> None:
        """
        Sets the frequency-dependent profile configuration and optionally the number of
        field profile samples.

        Args:
            true_or_false (bool): Whether the profile should be frequency-dependent.
            nr_field_profile_samples (int, optional): Number of samples for the field profile.
                                                      Defaults to None.
        """
        # Set the frequency-dependent profile parameter
        self._set("frequency dependent profile", true_or_false)

        # Optionally set the number of field profile samples if provided
        if nr_field_profile_samples is not None:
            self._set("number of field profile samples", nr_field_profile_samples)

    def set_maximum_convolution_time_window(self, true_or_false: bool, max_: float = None,
                                            units: TIME_UNITS = "fs") -> None:
        """
        Configures the maximum convolution time window for a source in the simulation.

        This method enables or disables the convolution time window setting based on the frequency
        dependence of the profile. If `true_or_false` is True, it sets the maximum convolution time
        window to the specified value and converts it to seconds.

        Args:
            true_or_false (bool): Whether to set the maximum convolution time window.
            max_ (float, optional): The maximum time window value, converted to seconds. Defaults to None.
            units (TIME_UNITS): Time units for the max time window, defaulting to "fs" (femtoseconds).

        Raises:
            ValueError: If `frequency dependent profile` is disabled for the Gaussian source.
        """
        # Verify that the frequency-dependent profile is enabled
        if not self._get("frequency dependent profile", bool):
            raise ValueError(
                f"Cannot set 'maximum convolution time window' for Gaussian source when "
                f"'frequency dependent profile' is disabled."
            )

        # Set the boolean parameter for maximum convolution time window configuration
        self._set("set maximum convolution time window", true_or_false)

        # Convert the maximum time window to seconds if provided
        if max_ is not None:
            max_in_seconds = convert_time(max_, from_unit=units, to_unit="s")
            self._set("maximum convolution time window", max_in_seconds)


class ThinLens(Module):

    def _validate_thin_lens(self) -> None:
        """
        Validates whether the thin lens settings can be applied to the Gaussian source.

        Raises:
            UserWarning: If 'use thin lens' is disabled while 'use scalar approximation' is enabled
                         for the Gaussian source, as this configuration is incompatible.
        """
        # Check if the 'use thin lens' parameter is disabled
        if not self._get("use thin lens", bool):
            raise UserWarning(
                f"Cannot set 'Thin lens' settings for Gaussian source while "
                f"'use scalar approximation' is enabled."
            )

    def set_numerical_aperture(self, NA: float) -> None:
        """
        Sets the numerical aperture (NA) for a Gaussian source.

        The numerical aperture is defined as NA = n * sin(a), where:
        - n is the refractive index of the medium where the source is located.
        - a is the half-angle of the beam.

        Note:
        - The refractive index may not be accurately defined in dispersive media.
        - Lenses should only be used in non-dispersive media.
        - The refractive index for the source is determined at the specified X, Y (and Z) coordinates.

        This method first validates that the thin lens settings are applicable. If valid, it updates
        the numerical aperture parameter.

        Args:
            NA (float): The numerical aperture value to set.

        Raises:
            UserWarning: If the thin lens settings cannot be applied.
            ValueError: If the NA value is invalid or outside expected ranges.
        """
        # Validate that the thin lens settings are appropriate for this configuration
        self._validate_thin_lens()

        # Additional validation for numerical aperture value
        if NA <= 0:
            raise ValueError("Numerical aperture must be a positive value.")

        # Set the numerical aperture parameter
        self._set("NA", NA)

    def set_distance_from_focus(self, distance: float, units: LENGTH_UNITS = None) -> None:
        """
        Sets the distance from the focus for the Gaussian source.

        This distance indicates the position relative to the focus of the beam:
        - A negative distance indicates a converging beam.
        - A positive distance indicates a diverging beam.

        This method validates that the thin lens settings are applicable. If valid,
        it converts the provided distance to the appropriate units (defaulting to the
        global simulation units if none are specified) and updates the distance parameter.

        Args:
            distance (float): The distance from the focus to set, in specified length units.
            units (LENGTH_UNITS, optional): Units for the distance. Defaults to the simulation's global units if None.

        Raises:
            UserWarning: If the thin lens settings cannot be applied.
            ValueError: If the provided length units are invalid or if the distance is not a numeric value.
        """

        # Validate that the thin lens settings are appropriate for this configuration
        self._validate_thin_lens()

        units = units if units is not None else self._units

        # Check if distance is a numeric value
        if not isinstance(distance, (int, float)):
            raise ValueError("Distance must be a numeric value.")

        # Convert length to meters
        distance_m = convert_length(distance, from_unit=units, to_unit="m")

        # Set the distance from the focus parameter
        self._set("distance from focus", distance_m)

    def fill_lens(self, fill_lens: bool) -> None:
        """
        Configures whether the lens is filled or not for the Gaussian source.

        When 'fill_lens' is set to True, the lens is illuminated with a plane wave
        that is clipped at the lens edge. If 'fill_lens' is False, it allows
        the configuration of the thin lens diameter (LENS DIAMETER) and the
        beam diameter prior to striking the lens (BEAM DIAMETER). In this case,
        a beam diameter that is much larger than the lens diameter is considered
        equivalent to a filled lens.

        Args:
            fill_lens (bool): A flag indicating whether to fill the lens.
                True to fill the lens with a plane wave, False to allow for
                diameter settings.

        Raises:
            UserWarning: If the thin lens settings cannot be applied.
        """

        # Validate that the thin lens settings are appropriate for this configuration
        self._validate_thin_lens()

        # Set the fill lens parameter
        self._set("fill lens", fill_lens)

    def set_lens_diameter(self, lens_diameter: float, units: LENGTH_UNITS = None) -> None:
        """
        Sets the lens diameter for the Gaussian source.

        Validates that 'fill_lens' is enabled and 'use thin lens' is applicable before setting the diameter.

        Args:
            lens_diameter (float): The diameter of the lens to set.
            units (LENGTH_UNITS, optional): The units for the lens diameter. If None,
                the global simulation units will be used.

        Raises:
            UserWarning: If the thin lens settings cannot be applied.
            ValueError: If 'fill_lens' is disabled.
        """

        # Validate that 'fill_lens' is enabled and thin lens settings are applicable
        if not self._get("fill lens", bool):
            raise ValueError(
                f"You cannot set the lens diameter when 'fill lens' is disabled for "
                f"Gaussian source.")

        self._validate_thin_lens()  # Validate thin lens settings

        units = units if units is not None else self._units

        # Convert and set lens diameter
        lens_diameter = convert_length(lens_diameter, from_unit=units, to_unit="m")
        self._set("lens diameter", lens_diameter)

    def set_beam_diameter(self, beam_diameter: float, units: LENGTH_UNITS = None) -> None:
        """
        Sets the beam diameter for the Gaussian source.

        Validates that 'fill_lens' is enabled and 'use thin lens' is applicable before setting the diameter.

        Args:
            beam_diameter (float): The diameter of the beam to set.
            units (LENGTH_UNITS, optional): The units for the beam diameter. If None,
                the global simulation units will be used.

        Raises:
            UserWarning: If the thin lens settings cannot be applied.
            ValueError: If 'fill_lens' is disabled.
        """

        # Validate that 'fill_lens' is enabled and thin lens settings are applicable
        if not self._get("fill lens", bool):
            raise ValueError(
                f"You cannot set the beam diameter when 'fill lens' is disabled for "
                f"Gaussian source.")

        self._validate_thin_lens()  # Validate thin lens settings

        units = units if units is not None else self._units

        # Convert and set beam diameter
        beam_diameter = convert_length(beam_diameter, from_unit=units, to_unit="m")
        self._set("beam diameter", beam_diameter)

    def set_number_of_plane_waves(self, nr_plane_waves: int) -> None:
        """
        Sets the number of plane waves used to construct the beam for the Gaussian source.

        Increasing the number of plane waves improves the accuracy of the beam profile,
        but it also increases the computation time. The default value in 2D is 1000.
        This method first validates that 'fill_lens' is enabled and that the thin lens
        settings are applicable before proceeding to set the number of plane waves.

        Args:
            nr_plane_waves (int): The number of plane waves to set for constructing the beam.

        Raises:
            UserWarning: If the thin lens settings cannot be applied.
            ValueError: If 'fill_lens' is disabled, preventing the setting of the number of plane waves.
        """

        # Validate that 'fill_lens' is enabled and thin lens settings are applicable
        if not self._get("fill lens", bool):
            raise ValueError(
                f"You cannot set the number of plane waves when 'fill lens' is disabled for "
                f"Gaussian source.")

        self._validate_thin_lens()  # Validate thin lens settings

        # Set the number of plane waves
        self._set("number of plane waves", nr_plane_waves)

# endregion Submodules


# region Modules

class PlaneWave(ModuleCollection):
    """
    Settings module for the PlaneWave object type.

    Attributes:
        _parent_object (Structure): The parent object the settings belong to.
        theta_vs_wavelength (ThetaVsWavelength): The theta vs wavelength module.

    """
    theta_vs_wavelength: ThetaVsWavelength

    def __init__(self, parent_object):
        super().__init__(parent_object)
        self.theta_vs_wavelength = ThetaVsWavelength(parent_object)


class CauchyLorentzian(PlaneWave):
    scalar_approximation: ScalarApproximation

    def __init__(self, parent_object) -> None:
        super().__init__(parent_object)
        self.scalar_approximation = ScalarApproximation(parent_object)


class Gaussian(CauchyLorentzian):

    thin_lens: ThinLens

    def __init__(self, parent_object) -> None:
        super().__init__(parent_object)
        self.thin_lens = ThinLens(parent_object)

    def use_scalar_approximation(self) -> None:
        """
        Enables the scalar approximation for the Gaussian source.

        The scalar approximation simplifies the modeling of wave propagation by treating the
        wave as a scalar field, which can significantly reduce computational complexity.
        This method sets the corresponding parameter to True.

        Raises:
            UserWarning: If the scalar approximation cannot be applied due to the current settings.
        """
        self._set("use scalar approximation", True)

    def use_thin_lens(self) -> None:
        """
        Enables the use of a thin lens in the Gaussian source configuration.

        This method configures the Gaussian source to utilize thin lens optics,
        which allows for simplified calculations regarding beam focusing and
        propagation. It sets the corresponding parameter to True.

        Raises:
            UserWarning: If the thin lens settings cannot be applied due to the current configuration.
        """
        self._set("use thin lens", True)


# endregion Modules
