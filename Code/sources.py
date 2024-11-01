from __future__ import annotations

# Standard library imports
from typing import Literal, Any, TypedDict, get_args, Unpack, Optional, Union

# Third-party library imports
from lumapi_import import lumapi

# Local library imports
from base_classes import SettingTab, SubsettingTab
from geometry import CartesianGeometry
from simulation_object import SimulationObject
from type_hint_resources import PARAMETER_TYPES, LENGTH_UNITS, FREQUENCY_UNITS, TIME_UNITS, AXES
from local_resources import convert_length, convert_frequency, convert_time, Validate


########################################################################################################################
#                                         LITERALS AND CONSTANTS
########################################################################################################################

PULSE_TYPES = Literal["standard", "broadband"]
BEAM_PARAMETERS = Literal["Waist size and position", "Beam size and divergence angle"]
DIRECTION_DEFINITIONS = Literal["axis", "unit-vector", "k-vector"]
POLARIZATION_DEFINITIONS = Literal["angle", "S", "P"]
INJECTION_AXES = Literal["x-axis", "y-axis", "z-axis"]
DIRECTIONS = Literal["Forward", "Backward"]
PLANE_WAVE_TYPES = Literal["Bloch/periodic", "BFAST", "Diffracting"]
WAVE_SHAPES = Literal["Plane wave", "Gaussian", "Cauchy-Lorentzian"]
CONVERSIONS = Literal["center frequency", "maximum frequency", "minimum frequency",
                      "center wavelength", "maximum wavelength", "minimum wavelength"]
DEFINE_BY = Literal["wavelength", "frequency"]

########################################################################################################################
#                        OVERRIDE GEOMETRY CLASS FOR ERROR HANDLING SPCIFIC TO SOURCE-OBJECTS
########################################################################################################################


class SourceGeometry(CartesianGeometry):

    __slots__ = CartesianGeometry.__slots__

    def set_spans(
            self, x_span: Optional[Union[int, float]] = None, y_span: Optional[Union[int, float]] = None,
            z_span: Optional[Union[int, float]] = None, units: LENGTH_UNITS = None) -> None:

        injection_axis: str = self._get_parameter("injection axis", "str")
        spans = {"x": x_span, "y": y_span, "z": z_span}

        for axis, span in spans.items():
            if injection_axis.startswith(axis) and span is not None:
                raise UserWarning(f"You are trying to set the {axis}-span of the source when the injection axis "
                                  f"is along the {axis}-axis. The source does therefore not have a spatial extent in "
                                  f"this direction.")

        super().set_spans(x_span, y_span, z_span, units)


########################################################################################################################
#                     CLASSES FOR SUBSETTINGS (SHOULD BE MEMBER VARIABLES OF THE SETTING CLASSES)
########################################################################################################################


class ScalarApproximation(SubsettingTab):

    class _SettingsDict(SubsettingTab._SettingsDict):
        beam_parameters: BEAM_PARAMETERS
        waist_radius_w0: float
        distance_from_waist: float
        beam_radius_wz: float
        divergence_angle: float

    __slots__ = SubsettingTab.__slots__

    def _validate_use_scalar_approximation(self) -> None:
        """
        Validates if scalar approximation settings can be applied to the source.

        Raises:
            ValueError: If 'use scalar approximation' is disabled while 'use thin film' is enabled,
                        indicating that 'use scalar approximation' must be enabled first.
        """
        # Check if 'use scalar approximation' is disabled
        if not self._get_parameter("use scalar approximation", "bool"):
            raise ValueError(
                f"Cannot set 'Scalar approximation' settings for Gaussian source '{self._parent.name}' while "
                f"'use thin film' is enabled. Enable 'use scalar approximation' first."
            )

    def set_waist_size_and_distance_from_waist(self, waist_radius_w0: float, distance_from_waist: float,
                                               length_units: LENGTH_UNITS = None) -> None:
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
            length_units (LENGTH_UNITS, optional): Units for waist size and position. Defaults to
                                                    the simulation's global units.

        Returns:
            None

        Raises:
            ValueError: If the waist radius or distance from waist is not valid.
        """
        # Ensure scalar approximation is valid for this configuration
        self._validate_use_scalar_approximation()

        # Set units to simulation defaults if not specified
        if length_units is None:
            length_units = self._simulation.global_units
        else:
            # Validate the provided length units
            Validate.in_literal(length_units, "length_units", LENGTH_UNITS)

        # Set parameters for waist size and position
        self._set_parameter("beam parameters", "Waist size and position", "str")

        # Convert and set waist radius in meters
        waist_radius_w0_m = convert_length(waist_radius_w0, from_unit=length_units, to_unit="m")
        self._set_parameter("waist radius w0", waist_radius_w0_m, "float")

        # Convert and set distance from waist in meters
        distance_from_waist_m = convert_length(distance_from_waist, from_unit=length_units, to_unit="m")
        self._set_parameter("distance from waist", distance_from_waist_m, "float")

    def set_beam_size_and_divergence_angle(self, beam_radius_wz: float, divergence_angle: float,
                                           length_units: LENGTH_UNITS = None) -> None:
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
            length_units (LENGTH_UNITS, optional): Units for the beam radius. Defaults to the
                                                    simulation's global units.

        Returns:
            None

        Raises:
            ValueError: If the beam radius or divergence angle is not valid.
        """
        # Validate scalar approximation setting
        self._validate_use_scalar_approximation()

        # Set length units to global simulation units if not specified
        if length_units is None:
            length_units = self._simulation.global_units
        else:
            # Validate provided length units
            Validate.in_literal(length_units, "length_units", LENGTH_UNITS)

        # Set parameters for beam size and divergence angle
        self._set_parameter("beam parameters", "Beam size and divergence angle", "str")

        # Convert and set beam radius in meters
        beam_radius_wz_m = convert_length(beam_radius_wz, from_unit=length_units, to_unit="m")
        self._set_parameter("beam radius wz", beam_radius_wz_m, "float")

        # Set divergence angle
        self._set_parameter("divergence angle", divergence_angle, "float")

    def get_currently_active_simulation_parameters(self) -> ScalarApproximation._SettingsDict:

        # Initialize settings dictionary with default values
        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())

        # Retrieve beam parameter type
        settings["beam_parameters"] = self._get_parameter("beam parameters", "str")

        # Populate settings based on beam parameter type
        if settings["beam_parameters"] == "Waist size and position":
            settings["waist_radius_w0"] = self._get_parameter("waist radius w0", "float")
            settings["distance_from_waist"] = self._get_parameter("distance from waist", "float")
        else:
            settings["beam_radius_wz"] = self._get_parameter("beam radius wz", "float")
            settings["divergence_angle"] = self._get_parameter("divergence angle", "float")

        return settings


class ThetaVsWavelength(SubsettingTab):

    class _SettingsDict(SubsettingTab._SettingsDict):
        frequency_dependent_profile: bool
        number_of_field_profile_samples: int
        set_maximum_convolution_time_window: bool
        maximum_convolution_time_window: float

    __slots__ = SubsettingTab.__slots__

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
        self._set_parameter("frequency dependent profile", true_or_false, "bool")

        # Optionally set the number of field profile samples if provided
        if nr_field_profile_samples is not None:
            self._set_parameter("number of field profile samples", nr_field_profile_samples, "int")

    def set_maximum_convolution_time_window(self, true_or_false: bool, max_: float = None,
                                            time_units: TIME_UNITS = "fs") -> None:
        """
        Configures the maximum convolution time window for a source in the simulation.

        This method enables or disables the convolution time window setting based on the frequency
        dependence of the profile. If `true_or_false` is True, it sets the maximum convolution time
        window to the specified value and converts it to seconds.

        Args:
            true_or_false (bool): Whether to set the maximum convolution time window.
            max_ (float, optional): The maximum time window value, converted to seconds. Defaults to None.
            time_units (TIME_UNITS): Time units for the max time window, defaulting to "fs" (femtoseconds).

        Raises:
            ValueError: If `frequency dependent profile` is disabled for the Gaussian source.
        """
        # Verify that the frequency-dependent profile is enabled
        if not self._get_parameter("frequency dependent profile", "bool"):
            raise ValueError(
                f"Cannot set 'maximum convolution time window' for Gaussian source '{self._parent.name}' when "
                f"'frequency dependent profile' is disabled."
            )

        # Set the boolean parameter for maximum convolution time window configuration
        self._set_parameter("set maximum convolution time window", true_or_false, "bool")

        # Validate the specified time units
        Validate.in_literal(time_units, "time_units", TIME_UNITS)

        # Convert the maximum time window to seconds if provided
        if max_ is not None:
            max_in_seconds = convert_time(max_, from_unit=time_units, to_unit="s")
            self._set_parameter("maximum convolution time window", max_in_seconds, "float")

    def get_currently_active_simulation_parameters(self) -> ThetaVsWavelength._SettingsDict:
        # Initialize settings dictionary with default values
        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())

        # Retrieve frequency-dependent profile setting
        settings["frequency_dependent_profile"] = self._get_parameter(
            "frequency dependent profile", "bool")

        # Populate settings if frequency-dependent profile is enabled
        if settings["frequency_dependent_profile"]:
            settings["number_of_field_profile_samples"] = self._get_parameter(
                "number of field profile samples", "int")
            settings["set_maximum_convolution_time_window"] = self._get_parameter(
                "set maximum convolution time window", "bool")

            # Include maximum convolution time window if enabled
            if settings["set_maximum_convolution_time_window"]:
                settings["maximum_convolution_time_window"] = self._get_parameter(
                    "maximum convolution time window", "float")

        return settings


class ThinLens(SubsettingTab):

    class _SettingsDict(SubsettingTab._SettingsDict):
        NA: float
        distance_from_focus: float
        fill_lens: bool
        lens_diameter: float
        beam_diameter: float
        number_of_plane_waves: int

    __slots__ = SubsettingTab.__slots__

    def _validate_thin_lens(self) -> None:
        """
        Validates whether the thin lens settings can be applied to the Gaussian source.

        Raises:
            UserWarning: If 'use thin lens' is disabled while 'use scalar approximation' is enabled
                         for the Gaussian source, as this configuration is incompatible.
        """
        # Check if the 'use thin lens' parameter is disabled
        if not self._get_parameter("use thin lens", "bool"):
            raise UserWarning(
                f"Cannot set 'Thin lens' settings for Gaussian source '{self._parent.name}' while "
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
        self._set_parameter("NA", NA, "float")

    def set_distance_from_focus(self, distance: float, length_units: LENGTH_UNITS = None) -> None:
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
            length_units (LENGTH_UNITS, optional): Units for the distance. Defaults to the simulation's global units if None.

        Raises:
            UserWarning: If the thin lens settings cannot be applied.
            ValueError: If the provided length units are invalid or if the distance is not a numeric value.
        """
        # Validate that the thin lens settings are appropriate for this configuration
        self._validate_thin_lens()

        # Determine the length units to use
        if length_units is None:
            length_units = self._simulation.global_units
        else:
            Validate.in_literal(length_units, "length_units", LENGTH_UNITS)

        # Check if distance is a numeric value
        if not isinstance(distance, (int, float)):
            raise ValueError("Distance must be a numeric value.")

        # Convert length to meters
        distance_m = convert_length(distance, from_unit=length_units, to_unit="m")

        # Set the distance from the focus parameter
        self._set_parameter("distance from focus", distance_m, "float")

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
        self._set_parameter("fill lens", fill_lens, "bool")

    def set_lens_diameter(self, lens_diameter: float, length_units: LENGTH_UNITS = None) -> None:
        """
        Sets the lens diameter for the Gaussian source.

        Validates that 'fill_lens' is enabled and 'use thin lens' is applicable before setting the diameter.

        Args:
            lens_diameter (float): The diameter of the lens to set.
            length_units (LENGTH_UNITS, optional): The units for the lens diameter. If None,
                the global simulation units will be used.

        Raises:
            UserWarning: If the thin lens settings cannot be applied.
            ValueError: If 'fill_lens' is disabled.
        """
        # Validate that 'fill_lens' is enabled and thin lens settings are applicable
        if not self._get_parameter("fill lens", "bool"):
            raise ValueError(
                f"You cannot set the lens diameter when 'fill lens' is disabled for Gaussian source '{self._parent.name}'.")

        self._validate_thin_lens()  # Validate thin lens settings

        # Determine the length units to use
        if length_units is None:
            length_units = self._simulation.global_units
        else:
            Validate.in_literal(length_units, "length_units", LENGTH_UNITS)

        # Convert and set lens diameter
        lens_diameter = convert_length(lens_diameter, from_unit=length_units, to_unit="m")
        self._set_parameter("lens diameter", lens_diameter, "float")

    def set_beam_diameter(self, beam_diameter: float, length_units: LENGTH_UNITS = None) -> None:
        """
        Sets the beam diameter for the Gaussian source.

        Validates that 'fill_lens' is enabled and 'use thin lens' is applicable before setting the diameter.

        Args:
            beam_diameter (float): The diameter of the beam to set.
            length_units (LENGTH_UNITS, optional): The units for the beam diameter. If None,
                the global simulation units will be used.

        Raises:
            UserWarning: If the thin lens settings cannot be applied.
            ValueError: If 'fill_lens' is disabled.
        """
        # Validate that 'fill_lens' is enabled and thin lens settings are applicable
        if not self._get_parameter("fill lens", "bool"):
            raise ValueError(
                f"You cannot set the beam diameter when 'fill lens' is disabled for "
                f"Gaussian source '{self._parent.name}'.")

        self._validate_thin_lens()  # Validate thin lens settings

        # Determine the length units to use
        if length_units is None:
            length_units = self._simulation.global_units
        else:
            Validate.in_literal(length_units, "length_units", LENGTH_UNITS)

        # Convert and set beam diameter
        beam_diameter = convert_length(beam_diameter, from_unit=length_units, to_unit="m")
        self._set_parameter("beam diameter", beam_diameter, "float")

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
        if not self._get_parameter("fill lens", "bool"):
            raise ValueError(
                f"You cannot set the number of plane waves when 'fill lens' is disabled for "
                f"Gaussian source '{self._parent.name}'.")

        self._validate_thin_lens()  # Validate thin lens settings

        # Set the number of plane waves
        self._set_parameter("number of plane waves", nr_plane_waves, "int")

    def get_currently_active_simulation_parameters(self) -> ThinLens._SettingsDict:
        # Initialize SettingsDict with all values None
        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())

        # Get basic parameters
        settings["NA"] = self._get_parameter("NA", "float")
        settings["distance_from_focus"] = self._get_parameter("distance from focus", "float")
        settings["fill_lens"] = self._get_parameter("fill lens", "bool")

        # Get lens parameters only if fill_lens is enabled
        if settings["fill_lens"]:
            settings["lens_diameter"] = self._get_parameter("lens diameter", "float")
            settings["beam_diameter"] = self._get_parameter("beam diameter", "float")

        # Get the number of plane waves
        settings["number_of_plane_waves"] = self._get_parameter("number of plane waves", "int")

        return settings


########################################################################################################################
#                                          CLASSES FOR MAIN SETTINGS CATEGORIES
########################################################################################################################


# General settings
class SourceGeneralBase(SettingTab):

    class _SettingsDict(SettingTab._SettingsDict):
        source_shape: WAVE_SHAPES
        amplitude: float
        phase: float
        direction_definition: DIRECTION_DEFINITIONS
        polarization_definition: POLARIZATION_DEFINITIONS
        injection_axis: INJECTION_AXES
        direction: DIRECTIONS
        theta: float
        phi: float
        polarization_angle: float
        ux: float
        uy: float
        uz: float
        kx: float
        ky: float
        kz: float
        angle_to_wavevector_conversions: CONVERSIONS
        define_by: DEFINE_BY
        frequency_point: float
        wavelength_point: float

    __slots__ = SettingTab.__slots__

    def set_amplitude(self, amplitude: float) -> None:
        """
        Sets the amplitude for the source.

        Args:
            amplitude (float): The amplitude value to set.

        Raises:
            ValueError: If amplitude is negative.
        """
        if amplitude < 0:
            raise ValueError("Amplitude must be non-negative.")
        self._set_parameter("amplitude", amplitude, "float")

    def set_phase(self, phase: float) -> None:
        """
        Sets the phase for the source.

        The phase of the point source, measured in units of degrees.
        This parameter is only useful for setting relative phase delays
        between multiple radiation sources.

        Args:
            phase (float): The phase value to set. Should be given in degrees.

        Raises:
            ValueError: If the phase is not within the expected range (0 to 360 degrees).
        """
        if not (0 <= phase <= 360):  # Assuming the phase should be in the range [0, 360]
            raise ValueError(f"Phase must be between 0 and 360 degrees, got '{phase}'.")
        self._set_parameter("phase", phase, "float")

    def set_direction_definition(self, definition: DIRECTION_DEFINITIONS) -> None:
        """
        Sets the direction definition for the source.

        Args:
            definition (DIRECTION_DEFINITIONS): The direction definition to set.
                Must be one of the predefined direction definitions.

        Raises:
            ValueError: If the definition is not valid.
        """
        Validate.in_literal(definition, "definition", DIRECTION_DEFINITIONS)
        self._set_parameter("direction definition", definition, "str")

    def set_polarization_definition(self, definition: POLARIZATION_DEFINITIONS) -> None:
        """
        Sets the polarization definition for the source.

        Args:
            definition (POLARIZATION_DEFINITIONS): The polarization definition to set.
                Must be one of the predefined polarization definitions.

        Raises:
            ValueError: If the definition is not valid.
        """
        Validate.in_literal(definition, "definition", POLARIZATION_DEFINITIONS)
        self._set_parameter("polarization definition", definition, "str")

    def set_injection_axis(self, axis: INJECTION_AXES) -> None:
        """
        Sets the injection axis for the source.

        This parameter sets the axis along which the radiation propagates.

        Args:
            axis (INJECTION_AXES): The injection axis to set.
                Must be one of the predefined injection axes.

        Raises:
            ValueError: If the axis is not valid.
        """
        Validate.in_literal(axis, "axis", INJECTION_AXES)
        self._set_parameter("injection axis", axis, "str")

    def set_direction(self, direction: DIRECTIONS) -> None:
        """
        Sets the direction for the source.

        This field specifies the direction in which the radiation propagates.
        Forward corresponds to propagation in the positive direction,
        while Backward corresponds to propagation in the negative direction.

        Args:
            direction (DIRECTIONS): The direction to set.
                Must be one of the predefined directions.

        Raises:
            ValueError: If the direction is not valid.
        """
        Validate.in_literal(direction, "direction", DIRECTIONS)
        self._set_parameter("direction", direction, "str")

    def set_unit_vectors(self, ux: float = None, uy: float = None, uz: float = None) -> None:
        """
        Sets the unit vectors for the source.

        Args:
            ux (float, optional): The x-component of the unit vector.
                If None, the x-component will not be set.
            uy (float, optional): The y-component of the unit vector.
                If None, the y-component will not be set.
            uz (float, optional): The z-component of the unit vector.
                If None, the z-component will not be set.

        Raises:
            ValueError: If the 'direction definition' is not set to 'unit-vector'.
        """
        if self._get_parameter("direction definition", "str") != "unit-vector":
            raise ValueError(
                f"You cannot set the unit vectors of '{self._parent.name}' when 'direction definition' is not "
                f"'unit-vector'."
            )

        if ux is not None:
            self._set_parameter("ux", ux, "float")
        if uy is not None:
            self._set_parameter("uy", uy, "float")
        if uz is not None:
            self._set_parameter("uz", uz, "float")

    def set_k_vectors(self, kx: float = None, ky: float = None, kz: float = None) -> None:
        """
        Sets the wave vector components for the source.

        Args:
            kx (float, optional): The x-component of the wave vector.
                If None, the x-component will not be set.
            ky (float, optional): The y-component of the wave vector.
                If None, the y-component will not be set.
            kz (float, optional): The z-component of the wave vector.
                If None, the z-component will not be set.

        Raises:
            ValueError: If the 'direction definition' is not set to 'k-vector'.
        """
        if self._get_parameter("direction definition", "str") != "k-vector":
            raise ValueError(
                f"You cannot set the k-vectors of '{self._parent.name}' when 'direction definition' is not "
                f"'k-vector'."
            )

        if kx is not None:
            self._set_parameter("kx", kx, "float")
        if ky is not None:
            self._set_parameter("ky", ky, "float")
        if kz is not None:
            self._set_parameter("kz", kz, "float")

    def set_polarization_angle_theta(self, theta: float) -> None:
        """
        Sets the polarization angle theta for the source.

        In 3D simulations, this is the angle of propagation, in degrees,
        with respect to the injection axis of the source.
        In 2D simulations, it is the angle of propagation, in degrees,
        rotated about the global Z-axis in a right-hand context,
        i.e., the angle of propagation in the XY plane.

        Args:
            theta (float): The angle of polarization in degrees.

        Raises:
            ValueError: If the 'direction definition' is not set to 'axis'.
        """
        if self._get_parameter("direction definition", "str") == "axis":
            self._set_parameter("theta", theta, "float")
        else:
            raise ValueError(
                f"You cannot set the polarization angle theta for '{self._parent.name}' when "
                f"'direction definition' is not 'axis'."
            )

    def set_polarization_angle_phi(self, phi: float) -> None:
        """
        Sets the polarization angle phi for the source.

        In 3D simulations, this is the angle of propagation, in degrees,
        rotated about the injection axis of the source in a right-hand context.
        In 2D simulations, this value is not used.

        Args:
            phi (float): The angle of polarization in degrees.

        Raises:
            ValueError: If the 'direction definition' is not set to 'axis'.
        """
        if self._get_parameter("direction definition", "str") == "axis":
            self._set_parameter("phi", phi, "float")
        else:
            raise ValueError(
                f"You cannot set the polarization angle phi for '{self._parent.name}' when "
                f"'direction definition' is not 'axis'."
            )

    def set_polarization_angle(self, angle: float) -> None:
        """
        Sets the polarization angle for the source.

        The polarization angle defines the orientation of the injected electric field
        and is measured with respect to the plane formed by the direction of propagation
        and the normal to the injection plane. A polarization angle of zero degrees defines
        P-polarized radiation, regardless of the direction of propagation, while a
        polarization angle of 90 degrees defines S-polarized radiation.

        Args:
            angle (float): The angle of polarization in degrees.

        Raises:
            ValueError: If the 'polarization definition' is not set to 'angle'.
        """
        if self._get_parameter("polarization definition", "str") == "angle":
            self._set_parameter("polarization angle", angle, "float")
        else:
            raise ValueError(
                f"You cannot set the polarization angle for '{self._parent.name}' when "
                f"'polarization definition' is not 'angle'."
            )

    def set_angle_to_wavevector_conversion(self, conversion: CONVERSIONS) -> None:
        """
        Sets the method of converting angles to wavevector components for the source.

        This parameter defines how angles are translated into wavevector components, which determine the
        propagation direction and phase velocity of the wave within the simulation space.

        Args:
            conversion (CONVERSIONS): The conversion method to set.
                Must be one of the predefined conversion options.

        Raises:
            ValueError: If the conversion method is not valid.
        """
        Validate.in_literal(conversion, "conversion", CONVERSIONS)
        self._set_parameter("angle to wavevector conversion", conversion, "str")

    def set_user_defined_angle_to_wavevector_conversion(self, wavelength_point: float = None,
                                                        frequency_point: float = None,
                                                        length_units: LENGTH_UNITS = None,
                                                        frequency_units: FREQUENCY_UNITS = "THz") -> None:
        """
        Sets a user-defined conversion from angle to wavevector using either a wavelength or frequency point.

        This method allows manual specification of the angle-to-wavevector conversion based on either
        a wavelength or frequency. If a wavelength point is provided, it is converted to meters based
        on the specified or global simulation units. If a frequency point is given, it is converted to
        Hz based on the provided frequency units. The user cannot specify both wavelength and frequency
        points simultaneously.

        Args:
            wavelength_point (float, optional): The wavelength for conversion, in the specified or global units.
            frequency_point (float, optional): The frequency for conversion, in the specified frequency units.
            length_units (LENGTH_UNITS, optional): Units for the wavelength, defaults to the global simulation units.
            frequency_units (FREQUENCY_UNITS): Units for the frequency, defaults to "THz".

        Raises:
            ValueError: If both wavelength_point and frequency_point are provided or if neither is provided.
            ValueError: If length_units or frequency_units are invalid.

        """
        if wavelength_point is not None and frequency_point is not None:
            raise ValueError(
                f"You cannot set both wavelength point and frequency point at the same time. Choose one."
            )
        elif wavelength_point is None and frequency_point is None:
            raise ValueError(
                f"You must provide either a wavelength point or a frequency point."
            )

        self._set_parameter("angle to wavelength conversion", "user defined", "str")

        if wavelength_point is not None:
            if length_units is None:
                length_units = self._simulation.global_units
            else:
                Validate.in_literal(length_units, "length_units", LENGTH_UNITS)
            wavelength_point = convert_length(wavelength_point, from_unit=length_units, to_unit="m")
            self._set_parameter("define by", "wavelength", "str")
            self._set_parameter("wavelength point", wavelength_point, "float")

        if frequency_point is not None:
            Validate.in_literal(frequency_units, "frequency_units", FREQUENCY_UNITS)
            frequency_point = convert_frequency(frequency_point, from_unit=frequency_units, to_unit="Hz")
            self._set_parameter("define by", "frequency", "str")
            self._set_parameter("frequency point", frequency_point, "float")

    def get_currently_active_simulation_parameters(self) -> SourceGeneralBase._SettingsDict:

        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())

        settings["source_shape"] = self._get_parameter("source shape", "str")
        settings["amplitude"] = self._get_parameter("amplitude", "float")
        settings["phase"] = self._get_parameter("phase", "float")

        settings["direction_definition"] = self._get_parameter("direction definition", "str")
        settings["polarization_definition"] = self._get_parameter("polarization definition",
                                                                  "str")
        settings["injection_axis"] = self._get_parameter("injection axis", "str")
        settings["direction"] = self._get_parameter("direction", "str")

        if settings["direction_definition"] == "axis":
            settings["theta"] = self._get_parameter("theta", "float")
            settings["phi"] = self._get_parameter("phi", "float")
        elif settings["direction_definition"] == "unit-vector":
            for axis in get_args(AXES):
                if settings["injection_axis"] != f"{axis}-axis":
                    settings[f"u{axis}"] = self._get_parameter(f"u{axis}", "float")
        else:
            for axis in get_args(AXES):
                if settings["injection_axis"] != f"{axis}-axis":
                    settings[f"k{axis}"] = self._get_parameter(f"k{axis}", "float")

        if settings["polarization_definition"] == "angle":
            settings["polarization_angle"] = self._get_parameter("polarization angle", "float")

        settings["angle_to_wavevector_conversions"] = self._get_parameter(
            "angle to wavevector conversion", "str")

        if settings["angle_to_wavevector_conversions"] == "user defined":
            settings["define_by"] = self._get_parameter("define by", "str")
            if settings["define_by"] == "wavelength":
                settings["wavelength_point"] = self._get_parameter("wavelength point", "float")
            else:
                settings["frequency_point"] = self._get_parameter("frequency point", "float")

        return settings


class PlaneGeneral(SourceGeneralBase):

    class _SettingsDict(SourceGeneralBase._SettingsDict):
        plane_wave_type: PLANE_WAVE_TYPES

    __slots__ = SourceGeneralBase.__slots__

    def set_plane_wave_type(self, type_: PLANE_WAVE_TYPES) -> None:
        """
        Sets the type of the plane wave source.

        This method allows setting the specific type of plane wave for the source.
        This setting applies only to plane wave sources and provides options that
        can be chosen from the predefined plane wave types.

        Args:
            type_ (PLANE_WAVE_TYPES): The plane wave type to set, chosen from the allowed plane wave types.

        Raises:
            ValueError: If the specified plane wave type is not valid.
        """
        Validate.in_literal(type_, "type_", PLANE_WAVE_TYPES)
        self._set_parameter("plane wave type", type_, "str")

    def get_currently_active_simulation_parameters(self) -> PlaneGeneral._SettingsDict:
        settings = self.__class__._SettingsDict(**super().get_currently_active_simulation_parameters())
        settings["plane_wave_type"] = self._get_parameter("plane wave type", "str")
        return settings


# Frequency/Wavelength settings
class FreqWavelength(SettingTab):

    class _SettingsDict(SettingTab._SettingsDict):
        wavelength_start: float
        wavelength_stop: float
        pulse_type: PULSE_TYPES
        frequency: float
        pulselength: float
        offset: float
        bandwidth: float
        eliminate_discontinuities: bool
        optimize_for_short_pulse: bool
        eliminate_dc: bool

    __slots__ = SettingTab.__slots__

    def override_global_source_settings(self, override_bool: bool) -> None:
        """
        Overrides the global source settings for this source.

        This method allows specific source settings to be configured independently of the
        global simulation settings. If not set to `True`, an attempt to configure
        source-specific parameters (such as frequency or wavelength ranges) will raise an error.

        Args:
            override_bool (bool): Set to `True` to override global source settings, enabling
                                  custom configuration of this source's parameters. Set to `False`
                                  to revert to using global settings.

        """
        self._set_parameter("override global source settings", override_bool, "bool")

    def set_frequency_wavelength(self) -> None:
        """
        Enables frequency/wavelength parameter customization for the source.

        This method allows the frequency or wavelength range of the source to be set only if
        the global source settings have been overridden. Attempts to configure these parameters
        without overriding the global settings will raise a `RuntimeError`.

        Raises:
            RuntimeError: If global source settings are not overridden.
        """
        if not self._get_parameter("override global source settings", "bool"):
            raise RuntimeError("Global source settings must be overridden to enable frequency/wavelength.")

    def set_wavelength_start_and_stop(self, start: float, stop: float, length_units: LENGTH_UNITS = None) -> None:
        """
        Sets the start and stop wavelengths for the source, with optional unit conversion.

        This method defines the wavelength range of the source by specifying the starting and
        ending wavelengths. If `length_units` are not provided, the simulation's global units
        are used as the default.

        Args:
            start (float): The starting wavelength value.
            stop (float): The stopping wavelength value.
            length_units (LENGTH_UNITS, optional): The units of the wavelength values
                (e.g., 'nm', 'um'). If not provided, the simulation's global length units are used.

        Raises:
            ValueError: If `start` or `stop` values are out of expected range.

        Notes:
            This method converts the wavelength values to meters internally for consistency.
        """
        if not self._get_parameter("override global source settings", "bool"):
            raise RuntimeError("Global source settings must be overridden to set wavelength start and stop.")

        if length_units is None:
            length_units = self._simulation.global_units

        start = convert_length(start, length_units, "m")
        stop = convert_length(stop, length_units, "m")

        self._set_parameter("set wavelength", True, "bool")
        self._set_parameter("wavelength start", start, "float")
        self._set_parameter("wavelength stop", stop, "float")

    def set_frequency_start_and_stop(self, start: float, stop: float, frequency_units: FREQUENCY_UNITS = "THz") -> None:
        """
        Sets the start and stop frequencies for the source, with optional unit conversion.

        This method defines the frequency range of the source by specifying the starting and
        ending frequencies. If `frequency_units` are not provided, the default units are THz.

        Args:
            start (float): The starting frequency value.
            stop (float): The stopping frequency value.
            frequency_units (FREQUENCY_UNITS, optional): The units of the frequency values
                (default is "THz").

        Raises:
            ValueError: If `start` or `stop` values are out of expected range.
            RuntimeError: If global source settings are not overridden.

        Notes:
            This method converts the frequency values to Hz internally for consistency.
        """
        if not self._get_parameter("override global source settings", "bool"):
            raise RuntimeError("Global source settings must be overridden to set frequency start and stop.")

        start = convert_frequency(start, from_unit=frequency_units, to_unit="Hz")
        stop = convert_frequency(stop, from_unit=frequency_units, to_unit="Hz")

        self._set_parameter("set frequency", True, "bool")
        self._set_parameter("frequency start", start, "float")
        self._set_parameter("frequency stop", stop, "float")

    def set_time_domain(self) -> None:
        """
        Enables the time domain setting for the source.

        Raises:
            RuntimeError: If global source settings are not overridden.
        """
        if not self._get_parameter("override global source settings", "bool"):
            raise RuntimeError("Global source settings must be overridden to enable time domain.")
        self._set_parameter("set time domain", True, "bool")

    def set_pulse_type(self, pulse_type: PULSE_TYPES) -> None:
        """
        Sets the pulse type for the source, specifying either a standard or broadband pulse.

        The `pulse_type` parameter configures the source as follows:
        - **Standard**: An optical carrier with a fixed frequency and a Gaussian envelope, ideal for
          narrowband applications.
        - **Broadband**: A chirped optical carrier with a Gaussian envelope, covering a wider spectrum
          suitable for broadband applications.

        Args:
            pulse_type (PULSE_TYPES): The type of pulse to set, either 'standard' or 'broadband'.

        Raises:
            RuntimeError: If global source settings are not overridden.
            ValueError: If 'eliminate dc' is enabled and the pulse type is not 'standard'.
        """
        if not self._get_parameter("override global source settings", "bool"):
            raise RuntimeError("Global source settings must be overridden to set pulse type.")

        eliminate_dc = self._get_parameter("eliminate dc", "bool")
        if eliminate_dc and pulse_type != "standard":
            raise ValueError(
                f"When 'eliminate dc' is enabled, pulse type can only be 'standard', not '{pulse_type}'."
            )

        self._set_parameter("pulse type", pulse_type, "str")

    def set_frequency(self, frequency: float, frequency_units: FREQUENCY_UNITS = "THz") -> None:
        """
        Sets the center frequency of the optical carrier for the source, with unit conversion.

        This method allows you to define the frequency at which the optical source operates.
        The frequency can be specified in various units, with the default set to Terahertz (THz).
        The provided frequency will be converted to Hertz (Hz) for internal consistency.

        Args:
            frequency (float): The frequency to set for the optical carrier.
            frequency_units (FREQUENCY_UNITS): The units of the frequency (default is "THz").

        Raises:
            RuntimeError: If global source settings are not overridden.

        Notes:
            This function expects a valid frequency value and will convert it to Hertz for internal processing.
        """
        if not self._get_parameter("override global source settings", "bool"):
            raise RuntimeError("Global source settings must be overridden to set frequency.")

        frequency = convert_frequency(frequency, frequency_units, "Hz")
        self._set_parameter("frequency", frequency, "float")

    def set_pulselength(self, pulselength: float, time_units: TIME_UNITS = "fs") -> None:
        """
        Sets the full-width at half-maximum (FWHM) power temporal duration of the pulse for the source, with unit conversion.

        This method allows you to define the pulselength of the optical source, which is
        represented as the full-width at half-maximum (FWHM) duration of the pulse. The
        pulselength can be specified in various units, with the default set to femtoseconds (fs).
        The provided pulselength will be converted to seconds (s) for internal consistency.

        Args:
            pulselength (float): The pulselength to set, specified as the FWHM duration of the pulse.
            time_units (TIME_UNITS): The units of the pulselength (default is "fs").

        Raises:
            RuntimeError: If global source settings are not overridden.

        Notes:
            This function expects a valid pulselength value and will convert it to seconds for internal processing.
        """
        if not self._get_parameter("override global source settings", "bool"):
            raise RuntimeError("Global source settings must be overridden to set pulselength.")

        pulselength = convert_time(pulselength, from_unit=time_units, to_unit="s")
        self._set_parameter("pulselength", pulselength, "float")

    def set_offset(self, offset: float, time_units: TIME_UNITS = "fs") -> None:
        """
        Sets the time at which the source reaches its peak amplitude, measured relative to the start of the simulation, with unit conversion.

        An offset of N seconds corresponds to a source that reaches its peak amplitude N seconds after
        the start of the simulation. This method allows you to define the offset for the optical source.
        The provided offset will be converted to seconds (s) for internal consistency.

        Args:
            offset (float): The offset time to set, indicating when the source reaches its peak amplitude.
            time_units (TIME_UNITS): The units of the offset (default is "fs").

        Raises:
            RuntimeError: If global source settings are not overridden.

        Notes:
            This function expects a valid offset value and will convert it to seconds for internal processing.
        """
        if not self._get_parameter("override global source settings", "bool"):
            raise RuntimeError("Global source settings must be overridden to set offset.")

        offset = convert_time(offset, from_unit=time_units, to_unit="s")
        self._set_parameter("offset", offset, "float")

    def set_bandwidth(self, bandwidth: float, frequency_units: FREQUENCY_UNITS = "THz") -> None:
        """
        Sets the bandwidth for the source if the pulse type is 'broadband'.

        The bandwidth represents the full-width at half-maximum (FWHM) frequency width of the time-domain
        pulse. This method allows you to specify the bandwidth, ensuring it is only applicable for sources
        configured with a 'broadband' pulse type. The provided bandwidth will be converted to Hertz (Hz)
        for internal consistency.

        Args:
            bandwidth (float): The bandwidth to set, indicating the frequency width of the pulse.
            frequency_units (FREQUENCY_UNITS): The units of the bandwidth (default is "THz").

        Raises:
            ValueError: If 'pulse type' is not set to 'broadband'.
            RuntimeError: If global source settings are not overridden.

        Notes:
            This function expects a valid bandwidth value and will convert it to Hertz for internal processing.
        """
        if not self._get_parameter("override global source settings", "bool"):
            raise RuntimeError("Global source settings must be overridden to set bandwidth.")

        pulse_type = self._get_parameter("pulse type", "str")
        if pulse_type != "broadband":
            raise ValueError(
                f"You can only set bandwidth when 'pulse type' is set to 'broadband', not '{pulse_type}'."
            )

        bandwidth = convert_frequency(bandwidth, from_unit=frequency_units, to_unit="Hz")
        self._set_parameter("bandwidth", bandwidth, "float")

    def set_eliminate_discontinuities(self, true_or_false: bool) -> None:
        """
        Enables or disables the elimination of discontinuities in the source.

        This setting ensures the function has a continuous derivative (smooth transitions from/to zero)
        at the start and end of a user-defined source time signal, reducing artifacts by eliminating
        abrupt changes in the source profile. It is enabled by default. Requires global source settings
        to be overridden.

        Args:
            true_or_false (bool): Set to `True` to enable the elimination of discontinuities,
                                  or `False` to disable it.

        Raises:
            RuntimeError: If global source settings are not overridden.
            ValueError: If 'eliminate dc' is enabled while setting 'eliminate discontinuities'.
        """
        if not self._get_parameter("override global source settings", "bool"):
            raise RuntimeError("Global source settings must be overridden to set 'eliminate discontinuities'.")

        eliminate_dc = self._get_parameter("eliminate dc", "bool")
        if eliminate_dc:
            raise ValueError("Cannot enable 'eliminate discontinuities' while 'eliminate dc' is enabled.")

        self._set_parameter("eliminate discontinuities", true_or_false, "bool")

    def set_optimize_for_short_pulse(self, true_or_false: bool) -> None:
        """
        Enables or disables optimization for short pulse sources.

        When enabled, this setting optimizes the source for better performance with short pulses.
        This option is enabled by default in the FDTD solver and should only be disabled when
        it is necessary to minimize the power injected by the source outside of the source range
        (e.g., convergence problems related to broadband steep angled injection).
        In the varFDTD solver, this option is disabled by default as it improves the algorithm's
        numerical stability. Requires global source settings to be overridden to be changed.

        Args:
            true_or_false (bool): Set to `True` to enable optimization for short pulses, or `False` to disable it.

        Raises:
            RuntimeError: If global source settings are not overridden.
            ValueError: If 'eliminate dc' is enabled while setting 'optimize for short pulse'.
        """
        if not self._get_parameter("override global source settings", "bool"):
            raise RuntimeError("Global source settings must be overridden to set 'optimize for short pulse'.")

        eliminate_dc = self._get_parameter("eliminate dc", "bool")
        if eliminate_dc:
            raise ValueError("Cannot enable 'optimize for short pulse' while 'eliminate dc' is enabled.")

        self._set_parameter("optimize for short pulse", true_or_false, "bool")

    def set_eliminate_dc(self, true_or_false: bool) -> None:
        """
        Enables or disables the elimination of DC (direct current) components in the source.

        The 'eliminate dc' option can be used to eliminate the DC component of the source signal
        by forcing a symmetry on it. This setting can be useful in applications where only AC
        (alternating current) components are relevant. Requires global source settings to be overridden.

        Args:
            true_or_false (bool): Set to `True` to enable DC elimination, or `False` to disable it.

        Raises:
            RuntimeError: If global source settings are not overridden.
        """
        if not self._get_parameter("override global source settings", "bool"):
            raise RuntimeError("Global source settings must be overridden to set 'eliminate dc'.")
        self._set_parameter("eliminate dc", true_or_false, "bool")

    def get_currently_active_simulation_parameters(self) -> FreqWavelength._SettingsDict:

        # Initialize dict with all values as None
        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())

        # Fill in the boolean parameters
        settings["eliminate_dc"] = self._get_parameter("eliminate dc", "bool")

        if not settings["eliminate_dc"]:
            settings["eliminate_discontinuities"] = self._get_parameter(
                "eliminate discontinuities", "bool")

            settings["optimize_for_short_pulse"] = self._get_parameter(
                "optimize for short pulse", "bool")

        # Check if defined by frequency/wavelength or time domain
        if self._get_parameter("set time domain", "bool"):
            settings["pulse_type"] = self._get_parameter("pulse type", "str")
            settings["frequency"] = self._get_parameter("frequency", "float")
            settings["pulselength"] = self._get_parameter("pulselength", "float")
            settings["offset"] = self._get_parameter("offset", "float")
            settings["bandwidth"] = self._get_parameter("bandwidth", "float")

        else:
            settings["wavelength_start"] = self._get_parameter("wavelength start", "float")
            settings["wavelength_stop"] = self._get_parameter("wavelength stop", "float")

        return settings


# Global source settings
class GlobalSource(FreqWavelength):

    __slots__ = FreqWavelength.__slots__

    def _get_parameter(
            self, parameter_name: str, type_: PARAMETER_TYPES, object_name: str = None, getter_function=None) -> Any:
        # Pass the getglobalmonitor() method as the getter method.
        return super()._get_parameter(object_name=object_name,
            parameter_name=parameter_name, type_=type_, getter_function=self._simulation.getglobalsource)

    def _set_parameter(self, parameter_name: str, value: Any, type_: PARAMETER_TYPES, object_name: str = None,
                       setter_function=None, getter_function=None) -> Any:
        return super()._set_parameter(
            parameter_name=parameter_name, value=value, type_=type_,
            setter_function=self._simulation.setglobalsource, getter_function=self._simulation.getglobalsource)


# Beam options
class GaussianBeamOptions(SettingTab):

    class _SettingsDict(SettingTab._SettingsDict):
        scalar_approximation_settings: ScalarApproximation._SettingsDict
        thin_lens_settings: ThinLens._SettingsDict
        theta_vs_wavelength_settings: ThetaVsWavelength._SettingsDict

    _sub_settings = [ScalarApproximation, ThinLens, ThetaVsWavelength]
    _sub_settings_names = ["scalar_approximation_settings", "thin_lens_settings", "theta_vs_wavelength_settings"]

    # Declare variables
    scalar_approximation_settings: ScalarApproximation
    thin_lens_settings: ThinLens
    theta_vs_wavelength_settings: ThetaVsWavelength

    __slots__ = SettingTab.__slots__ + _sub_settings_names

    def use_scalar_approximation(self) -> None:
        """
        Enables the scalar approximation for the Gaussian source.

        The scalar approximation simplifies the modeling of wave propagation by treating the
        wave as a scalar field, which can significantly reduce computational complexity.
        This method sets the corresponding parameter to True.

        Raises:
            UserWarning: If the scalar approximation cannot be applied due to the current settings.
        """
        self._set_parameter("use scalar approximation", True, "bool")

    def use_thin_lens(self) -> None:
        """
        Enables the use of a thin lens in the Gaussian source configuration.

        This method configures the Gaussian source to utilize thin lens optics,
        which allows for simplified calculations regarding beam focusing and
        propagation. It sets the corresponding parameter to True.

        Raises:
            UserWarning: If the thin lens settings cannot be applied due to the current configuration.
        """
        self._set_parameter("use thin lens", True, "bool")

    def get_currently_active_simulation_parameters(self) -> GaussianBeamOptions._SettingsDict:

        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())

        thin_lens = self._get_parameter("use thin lens", "bool")

        if thin_lens:
            settings["thin_lens_settings"] = self.thin_lens_settings.get_currently_active_simulation_parameters()

        else:
            settings["scalar_approximation_settings"] = (
                self.scalar_approximation_settings.get_currently_active_simulation_parameters())

        settings["theta_vs_wavelength_settings"] = (
            self.theta_vs_wavelength_settings.get_currently_active_simulation_parameters())

        return settings


class CauchyLorentzianBeamOptions(SettingTab):

    class _SettingsDict(SettingTab._SettingsDict):
        scalar_approximation_settings: ScalarApproximation._SettingsDict
        theta_vs_wavelength_settings: ThetaVsWavelength._SettingsDict

    _sub_settings = SettingTab._sub_settings + [ThetaVsWavelength, ScalarApproximation]
    _sub_settings_names = SettingTab._sub_settings_names + ["theta_vs_wavelength_settings",
                                                            "scalar_approximation_settings"]

    # Declare variables
    theta_vs_wavelength_settings: ThetaVsWavelength
    scalar_approximation_settings: ScalarApproximation

    __slots__ = SettingTab.__slots__ + _sub_settings_names

    def get_currently_active_simulation_parameters(self) -> CauchyLorentzianBeamOptions._SettingsDict:
        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())

        settings["scalar_approximation_settings"] = (
            self.scalar_approximation_settings.get_currently_active_simulation_parameters())
        settings["theta_vs_wavelength_settings"] = (
            self.theta_vs_wavelength_settings.get_currently_active_simulation_parameters())

        return settings


class PlaneBeamOptions(SettingTab):

    class _SettingsDict(SettingTab._SettingsDict):
        theta_vs_wavelength_settings: ThetaVsWavelength._SettingsDict

    _sub_settings = SettingTab._sub_settings + [ThetaVsWavelength]
    _sub_settings_names = SettingTab._sub_settings_names + ["theta_vs_wavelength_settings"]

    # Declare variables
    theta_vs_wavelength_settings: ThetaVsWavelength

    __slots__ = SettingTab.__slots__ + _sub_settings_names

    def get_currently_active_simulation_parameters(self) -> PlaneBeamOptions._SettingsDict:

        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())
        settings["theta_vs_wavelength_settings"] = (
            self.theta_vs_wavelength_settings.get_currently_active_simulation_parameters())

        return settings


########################################################################################################################
#                                  CLASSES REPRESENTING ACTUAL SOURCE OBJECTS
########################################################################################################################


# Base class
class SourceBase(SimulationObject):

    class _SettingsDict(SimulationObject._SettingsDict):
        geometry_settings: SourceGeometry._SettingsDict
        general_settings: SourceGeneralBase._SettingsDict
        frequency_and_wavelength_settings: FreqWavelength._SettingsDict

    class _Kwargs(TypedDict, total=False):
        injection_axis: INJECTION_AXES
        direction: DIRECTIONS
        x: float
        y: float
        z: float
        x_span: float
        y_span: float
        z_span: float

    # Helper lists to aid in initialization
    _settings = [SourceGeometry if _setting == CartesianGeometry
                 else _setting for _setting in SimulationObject._settings] + [FreqWavelength, SourceGeneralBase]
    _settings_names = SimulationObject._settings_names + ["frequency_and_wavelength_settings", "general_settings"]

    # Declare variables
    frequency_and_wavelength_settings: FreqWavelength
    geometry_settings: SourceGeometry
    general_settings: SourceGeneralBase

    __slots__ = SimulationObject.__slots__ + _settings_names

    def __init__(self, name: str, simulation: lumapi.FDTD, **kwargs: Unpack[SourceBase._Kwargs]) -> None:

        ordered = self.__class__._Kwargs(**{
            parameter: None for parameter in self.__class__.__annotations__.keys()})

        for key, value in kwargs.items():
            ordered[key] = value

        poppable = []
        for key, value in ordered.items():
            if value is None:
                poppable.append(key)

        for pop in poppable:
            ordered.pop(pop)

        super().__init__(name, simulation, **kwargs)
        simulation.__class__._sources.append(self)

    @property
    def polarization_angle(self) -> float:
        return self._get_parameter("polarization angle", "float")

    @polarization_angle.setter
    def polarization_angle(self, angle: float) -> None:
        self.general_settings.set_polarization_angle(angle)

    @property
    def x_span(self) -> float:
        return convert_length(self._get_parameter(
            "x span", "float"), "m", self._simulation.global_units)

    @x_span.setter
    def x_span(self, x_span: float) -> None:
        Validate.positive_number(x_span, "x_span")
        self.geometry_settings.set_spans(x_span=x_span)

    @property
    def y_span(self) -> float:
        return convert_length(self._get_parameter(
            "y span", "float"), "m", self._simulation.global_units)

    @y_span.setter
    def y_span(self, y_span: float) -> None:
        Validate.positive_number(y_span, "y_span")
        self.geometry_settings.set_spans(y_span=y_span)

    @property
    def z_span(self) -> float:
        return convert_length(self._get_parameter(
            "z span", "float"), "m", self._simulation.global_units)

    @z_span.setter
    def z_span(self, z_span: float) -> None:
        Validate.positive_number(z_span, "z_span")
        self.geometry_settings.set_spans(z_span=z_span)

    @property
    def x_min(self) -> float:
        return convert_length(self._get_parameter(
            "x min", "float"), "m", self._simulation.global_units)

    @property
    def x_max(self) -> float:
        return convert_length(self._get_parameter(
            "x max", "float"), "m", self._simulation.global_units)

    @property
    def y_min(self) -> float:
        return convert_length(self._get_parameter(
            "y min", "float"), "m", self._simulation.global_units)

    @property
    def y_max(self) -> float:
        return convert_length(self._get_parameter(
            "y max", "float"), "m", self._simulation.global_units)

    @property
    def z_min(self) -> float:
        return convert_length(self._get_parameter(
            "z min", "float"), "m", self._simulation.global_units)

    @property
    def z_max(self) -> float:
        return convert_length(self._get_parameter(
            "z max", "float"), "m", self._simulation.global_units)

    def get_currently_active_simulation_parameters(self) -> SourceBase._SettingsDict:
        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())
        settings["geometry_settings"] = self.geometry_settings.get_currently_active_simulation_parameters()
        settings["general_settings"] = self.general_settings.get_currently_active_simulation_parameters()
        settings["frequency_and_wavelength_settings"] = (
            self.frequency_and_wavelength_settings.get_currently_active_simulation_parameters())
        return settings


# Source classes
class PlaneSource(SourceBase):

    class _SettingsDict(SourceBase._SettingsDict):
        general_settings: PlaneGeneral._SettingsDict
        beam_options_settings: PlaneBeamOptions._SettingsDict

    class _Kwargs(SourceBase._Kwargs, total=False):
        pass

    _settings = SourceBase._settings + [PlaneGeneral, PlaneBeamOptions]
    _settings_names = SourceBase._settings_names + ["general_settings", "beam_options_settings"]

    # Declare variables
    general_settings: PlaneGeneral
    beam_options_settings: PlaneBeamOptions

    __slots__ = SourceBase.__slots__ + _settings_names

    def get_currently_active_simulation_parameters(self) -> PlaneSource._SettingsDict:

        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())
        settings.update(super().get_currently_active_simulation_parameters())
        settings["general_settings"] = self.general_settings.get_currently_active_simulation_parameters()
        settings["beam_options_settings"] = self.beam_options_settings.get_currently_active_simulation_parameters()
        return settings

    def __repr__(self) -> str:
        return "PlaneSource"


class GaussianSource(SourceBase):

    class _SettingsDict(SourceBase._SettingsDict):
        general_settings: SourceGeneralBase._SettingsDict
        beam_options_settings: GaussianBeamOptions._SettingsDict

    _settings = SourceBase._settings + [SourceGeneralBase, GaussianBeamOptions]
    _settings_names = SourceBase._settings_names + ["general_settings", "beam_options"]

    # Declare variables
    general_settings: SourceGeneralBase
    beam_options_settings: GaussianBeamOptions

    __slots__ = SourceBase.__slots__ + _settings_names

    def get_currently_active_simulation_parameters(self) -> GaussianSource._SettingsDict:

        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())
        settings.update(super().get_currently_active_simulation_parameters())
        settings["general_settings"] = self.general_settings.get_currently_active_simulation_parameters()
        settings["beam_options_settings"] = self.beam_options_settings.get_currently_active_simulation_parameters()
        return settings

    def __repr__(self) -> str:
        return "GaussianSource"


class CauchyLorentzianSource(SourceBase):

    class _SettingsDict(SourceBase._SettingsDict):
        general_settings: SourceGeneralBase._SettingsDict
        beam_options_settings: CauchyLorentzianBeamOptions._SettingsDict

    _settings = SourceBase._settings + [SourceGeneralBase, CauchyLorentzianBeamOptions]
    _settings_names = SourceBase._settings_names + ["general_settings", "beam_options"]

    # Declare variables
    general_settings: SourceGeneralBase
    beam_options_settings: CauchyLorentzianBeamOptions

    __slots__ = SourceBase.__slots__ + _settings_names

    def get_currently_active_simulation_parameters(self) -> CauchyLorentzianSource._SettingsDict:

        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())
        settings.update(super().get_currently_active_simulation_parameters())
        settings["general_settings"] = self.general_settings.get_currently_active_simulation_parameters()
        settings["beam_options_settings"] = self.beam_options_settings.get_currently_active_simulation_parameters()
        return settings

    def __repr__(self) -> str:
        return "CauchyLorentzianSource"
